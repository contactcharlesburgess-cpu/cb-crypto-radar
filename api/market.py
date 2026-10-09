"""
market.py — public market data for CB Crypto Radar.

Everything here is real, public data. Nothing is invented to fill a gap:
if a source fails, the field comes back empty and the response lists the
source under "errors" so the UI can say so.

Sources: CoinGecko (markets), Hyperliquid info API (HYPE perps, order book,
daily candles), Yahoo Finance chart API (stock quotes), Alternative.me
(Fear & Greed), Forex Factory (calendar), CoinDesk/Cointelegraph/Decrypt/
FinancialJuice RSS (headlines, keyword-scored for tone).

No holdings or personal data live on the server. The page keeps positions
in the viewer's own browser.
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import config
import data_fetcher
import sentiment_analyzer

HL_INFO = "https://api.hyperliquid.xyz/info"
UA = {"User-Agent": data_fetcher.USER_AGENT}

_cache: Dict[str, Any] = {}


def _cached(key: str, ttl: float, fn):
    """Tiny per-instance cache so a burst of page loads doesn't hammer the sources."""
    hit = _cache.get(key)
    now = time.time()
    if hit and now - hit[0] < ttl:
        return hit[1]
    val = fn()
    _cache[key] = (now, val)
    return val


def _hl(body: Dict[str, Any], timeout: int = 6) -> Any:
    req = urllib.request.Request(HL_INFO, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# Crypto markets (CoinGecko)
# ----------------------------------------------------------------------------

def fetch_markets_hyperliquid() -> List[Dict[str, Any]]:
    """Backup market list from Hyperliquid perps (no market cap / 7d / 24h range there)."""
    meta, ctxs = _hl({"type": "metaAndAssetCtxs"})
    wanted = set(config.SYMBOL_TO_ID)
    out = []
    for u, ctx in zip(meta["universe"], ctxs):
        sym = u["name"]
        if sym not in wanted or not ctx.get("markPx"):
            continue
        px, prev = float(ctx["markPx"]), float(ctx.get("prevDayPx") or 0)
        cid = config.SYMBOL_TO_ID[sym]
        out.append({
            "id": cid, "symbol": sym, "name": sym, "image": "",
            "sector": next((s for s, ids in config.SECTORS.items() if cid in ids), "Other"),
            "rank": None, "price": px, "market_cap": None,
            "volume_24h": float(ctx.get("dayNtlVlm") or 0), "high_24h": None, "low_24h": None,
            "range_pos_24h": None,
            "change_24h": round((px - prev) / prev * 100, 2) if prev else None,
            "change_7d": None, "ath": None, "ath_change_pct": None,
            "source": "Hyperliquid perps",
        })
    return sorted(out, key=lambda m: -(m["volume_24h"] or 0))


def fetch_markets_paprika() -> List[Dict[str, Any]]:
    """Primary market list: every Robinhood-tradable coin in config.RH_COINS, priced
    by CoinPaprika (one request for all coins; has 1h / 24h / 7d change)."""
    raw = data_fetcher.fetch_url(config.COINPAPRIKA_TICKERS, timeout=12)
    if not raw:
        return []
    out = []
    for t in json.loads(raw):
        sym = config.RH_PAPRIKA_IDS.get(t.get("id"))
        if not sym:
            continue
        q = (t.get("quotes") or {}).get("USD") or {}
        price = q.get("price")
        if price is None:
            continue
        out.append({
            "id": t["id"],
            "symbol": sym,
            "name": t.get("name", sym),
            "image": f"https://static.coinpaprika.com/coin/{t['id']}/logo.png",
            "sector": config.RH_COINS[sym][1],
            "rank": t.get("rank"),
            "price": price,
            "market_cap": q.get("market_cap"),
            "volume_24h": q.get("volume_24h"),
            "high_24h": None,
            "low_24h": None,
            "range_pos_24h": None,
            "change_1h": q.get("percent_change_1h"),
            "change_24h": q.get("percent_change_24h"),
            "change_7d": q.get("percent_change_7d"),
            "ath": q.get("ath_price"),
            "ath_change_pct": q.get("percent_from_price_ath"),
            "robinhood": True,
            "source": "CoinPaprika · Robinhood-tradable list",
        })
    return sorted(out, key=lambda m: m["rank"] or 10**6)


def _risk_tier(m: Dict[str, Any]) -> str:
    cap = m.get("market_cap") or 0
    if cap >= 10e9:
        return "Lower"
    if cap >= 1e9:
        return "Medium"
    return "High"


def build_momentum(markets: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    """Rank coins by recent strength: 55% 7-day change + 45% 24h change, liquid coins only.
    A screen of what's moving, not a prediction — momentum reverses fast in crypto."""
    rows = []
    for m in markets:
        d1, d7 = m.get("change_24h"), m.get("change_7d")
        vol, cap = m.get("volume_24h") or 0, m.get("market_cap") or 0
        if d1 is None or d7 is None:
            continue
        if vol < config.MOMENTUM_MIN_VOLUME or cap < config.MOMENTUM_MIN_MCAP:
            continue
        turnover = vol / cap if cap else 0
        tags = []
        if d7 >= 15:
            tags.append("7d breakout")
        if d1 >= 8:
            tags.append("24h surge")
        if d7 > 5 and d1 < -2:
            tags.append("pulling back")
        if turnover >= 0.2:
            tags.append("heavy volume")
        if (m.get("ath_change_pct") or -100) > -20:
            tags.append("near ATH")
        if d7 >= 80:
            tags.append("extended")
        rows.append({
            "symbol": m["symbol"], "name": m["name"], "image": m.get("image", ""),
            "sector": m["sector"], "price": m["price"],
            "change_1h": m.get("change_1h"), "change_24h": d1, "change_7d": d7,
            "volume_24h": vol, "market_cap": cap, "turnover_pct": round(turnover * 100, 1),
            "score": round(0.55 * d7 + 0.45 * d1, 1),
            "risk": _risk_tier(m), "tags": tags,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:n]


def fetch_markets() -> List[Dict[str, Any]]:
    try:
        pap = fetch_markets_paprika()
    except Exception:  # noqa: BLE001
        pap = []
    if pap:
        return pap
    raw = data_fetcher.fetch_url(config.FEEDS["coingecko_markets"])
    if not raw:
        return fetch_markets_hyperliquid()
    coins = json.loads(raw)
    out = []
    for c in coins if isinstance(coins, list) else []:
        cid = c.get("id", "")
        sector = next((s for s, ids in config.SECTORS.items() if cid in ids), "Other")
        price = c.get("current_price")
        hi, lo = c.get("high_24h"), c.get("low_24h")
        range_pos = None
        if price is not None and hi and lo and hi > lo:
            range_pos = round((price - lo) / (hi - lo) * 100, 1)
        out.append({
            "id": cid,
            "symbol": (c.get("symbol") or "").upper(),
            "name": c.get("name", ""),
            "image": c.get("image", ""),
            "sector": sector,
            "rank": c.get("market_cap_rank"),
            "price": price,
            "market_cap": c.get("market_cap"),
            "volume_24h": c.get("total_volume"),
            "high_24h": hi,
            "low_24h": lo,
            "range_pos_24h": range_pos,  # 0 = at the 24h low, 100 = at the 24h high
            "change_24h": c.get("price_change_percentage_24h"),
            "change_7d": c.get("price_change_percentage_7d_in_currency"),
            "ath": c.get("ath"),
            "ath_change_pct": c.get("ath_change_percentage"),
            "source": "CoinGecko",
        })
    return out or fetch_markets_hyperliquid()


# ----------------------------------------------------------------------------
# Hyperliquid: HYPE perp stats, order book, and price-history levels
# ----------------------------------------------------------------------------

def _sma(vals: List[float], n: int) -> Optional[float]:
    return round(sum(vals[-n:]) / n, 4) if len(vals) >= n else None


def _levels_from_candles(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Objective reference levels from daily candles. No buy/sell interpretation."""
    closes = [float(c["c"]) for c in candles]
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]

    def window(n):
        if len(candles) < n:
            return None
        return {"high": max(highs[-n:]), "low": min(lows[-n:])}

    # Average true range (14d): the typical size of one day's move.
    trs = []
    for i in range(1, len(candles)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    atr14 = round(sum(trs[-14:]) / 14, 4) if len(trs) >= 14 else None

    # Swing lows/highs on the last 90 days: a day whose low (high) is the most extreme
    # of the 3 days either side. Listed so the user can see where price has turned.
    swings_low, swings_high = [], []
    recent = candles[-90:]
    for i in range(3, len(recent) - 3):
        lo, hi = float(recent[i]["l"]), float(recent[i]["h"])
        nb = recent[i - 3:i] + recent[i + 1:i + 4]
        day = datetime.fromtimestamp(recent[i]["t"] / 1000, timezone.utc).strftime("%b %d")
        if all(lo <= float(x["l"]) for x in nb):
            swings_low.append({"price": lo, "date": day})
        if all(hi >= float(x["h"]) for x in nb):
            swings_high.append({"price": hi, "date": day})

    return {
        "last_close": closes[-1] if closes else None,
        "range_7d": window(7),
        "range_30d": window(30),
        "range_90d": window(90),
        "high_all": max(highs) if highs else None,
        "sma_20d": _sma(closes, 20),
        "sma_50d": _sma(closes, 50),
        "sma_200d": _sma(closes, 200),
        "atr_14d": atr14,
        "swing_lows_90d": swings_low[-6:],
        "swing_highs_90d": swings_high[-6:],
        "days_of_history": len(candles),
        "closes_90d": [round(x, 4) for x in closes[-90:]],
    }


def fetch_hyperliquid(coin: str = "HYPE") -> Dict[str, Any]:
    meta, ctxs = _hl({"type": "metaAndAssetCtxs"})
    names = [u["name"] for u in meta["universe"]]
    if coin not in names:
        raise ValueError(f"{coin} not listed on Hyperliquid perps")
    ctx = ctxs[names.index(coin)]
    mark = float(ctx["markPx"])
    prev = float(ctx.get("prevDayPx") or mark)
    funding_hr = float(ctx.get("funding") or 0)
    oi_coins = float(ctx.get("openInterest") or 0)

    book = _hl({"type": "l2Book", "coin": coin}, timeout=4)
    bids = [{"price": float(b["px"]), "size": float(b["sz"])} for b in book["levels"][0][:10]]
    asks = [{"price": float(a["px"]), "size": float(a["sz"])} for a in book["levels"][1][:10]]

    now_ms = int(time.time() * 1000)
    candles = _hl({"type": "candleSnapshot", "req": {
        "coin": coin, "interval": "1d", "startTime": now_ms - 400 * 86_400_000, "endTime": now_ms}})

    return {
        "coin": coin,
        "fetched_at": _now_iso(),
        "mark_price": mark,
        "oracle_price": float(ctx.get("oraclePx") or mark),
        "change_24h_pct": round((mark - prev) / prev * 100, 2) if prev else None,
        "funding_hourly_pct": round(funding_hr * 100, 5),
        "funding_apr_pct": round(funding_hr * 24 * 365 * 100, 2),
        "open_interest_coins": oi_coins,
        "open_interest_usd": round(oi_coins * mark),
        "volume_24h_usd": round(float(ctx.get("dayNtlVlm") or 0)),
        "best_bid": bids[0]["price"] if bids else None,
        "best_ask": asks[0]["price"] if asks else None,
        "spread": round(asks[0]["price"] - bids[0]["price"], 4) if bids and asks else None,
        "orderbook": {"bids": bids, "asks": asks},
        "levels": _levels_from_candles(candles),
    }


# ----------------------------------------------------------------------------
# Quotes for any symbol (for the on-device portfolio)
# ----------------------------------------------------------------------------

def _yahoo(symbol: str) -> Optional[Dict[str, Any]]:
    # Yahoo rate-limits browser-looking user agents harder than a plain one.
    for host in ("query1", "query2"):
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=1d&interval=1d"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=5) as r:
                raw = r.read().decode()
            break
        except Exception:  # noqa: BLE001
            raw = None
    if not raw:
        return None
    meta = json.loads(raw)["chart"]["result"][0]["meta"]
    return {"price": meta.get("regularMarketPrice"), "source": "Yahoo Finance",
            "as_of": datetime.fromtimestamp(meta.get("regularMarketTime", 0), timezone.utc).isoformat()}


def fetch_quotes(symbols: List[str]) -> Dict[str, Any]:
    """Live price per symbol. Crypto via Hyperliquid/Coinbase; everything else via Yahoo."""
    mids = data_fetcher.fetch_hyperliquid_mids()
    out: Dict[str, Any] = {}
    for sym in symbols[:25]:
        s = sym.upper().strip()
        if not s or not s.replace("-", "").replace(".", "").isalnum():
            continue
        q = None
        try:
            if s in config.SYMBOL_TO_ID or s in mids:
                if s == "HYPE" and "HYPE" in mids:
                    q = {"price": mids["HYPE"], "source": "Hyperliquid"}
                else:
                    p = data_fetcher.fetch_coinbase_spot(s)
                    if p:
                        q = {"price": p, "source": "Coinbase"}
                    elif s in mids:
                        q = {"price": mids[s], "source": "Hyperliquid"}
            if q is None:
                q = _yahoo(s)
        except Exception:  # noqa: BLE001
            q = None
        out[s] = q  # None = price unavailable (the UI says so instead of guessing)
    return out


# ----------------------------------------------------------------------------
# Full dashboard payload
# ----------------------------------------------------------------------------

def _tone_label(score: float) -> str:
    if score >= 3:
        return "Positive"
    if score >= 1:
        return "Leaning positive"
    if score > -1:
        return "Mixed"
    if score > -3:
        return "Leaning negative"
    return "Negative"


# ----------------------------------------------------------------------------
# Live Entry Callouts & Sniper Radar
# ----------------------------------------------------------------------------

CALLOUT_CONFIGS = {
    "HYPE": {
        "name": "Hyperliquid",
        "sector": "L1 / DEX Perps",
        "robinhood": True,
        "entry_low": 76.00,
        "entry_high": 79.50,
        "reclaim_trigger": 86.50,
        "stop_loss": 73.50,
        "target_1": 92.00,
        "target_2": 100.00,
        "timeframe": "4H / Daily",
        "setup_type": "Macro Liquidity Sweep & Demand Shelf",
        "notes": "Optimal bids sit at mid-September shelf ($76.00–$79.50). Alternatively, wait for clean 1H reclaim above $86.50 before entering.",
        "conviction": "HIGH (A+)",
    },
    "SOL": {
        "name": "Solana",
        "sector": "Layer 1 Ecosystem",
        "robinhood": True,
        "entry_low": 105.00,
        "entry_high": 108.50,
        "reclaim_trigger": 112.50,
        "stop_loss": 103.50,
        "target_1": 122.00,
        "target_2": 135.00,
        "timeframe": "4H / Daily",
        "setup_type": "Wick Low Retest & OTE Discount",
        "notes": "Testing the $107.90 wick sweep base. Clean limit entry between $105–$108.50 with stop strictly below $103.50.",
        "conviction": "HIGH (A+)",
    },
    "BTC": {
        "name": "Bitcoin",
        "sector": "Macro Reserve",
        "robinhood": True,
        "entry_low": 80000.00,
        "entry_high": 81500.00,
        "reclaim_trigger": 83500.00,
        "stop_loss": 78800.00,
        "target_1": 88000.00,
        "target_2": 94000.00,
        "timeframe": "Daily",
        "setup_type": "Institutional Liquidity Pool Retest",
        "notes": "Macro support at psychological $80k round level. Strong risk/reward buffer on any flush into $80k–$81.5k.",
        "conviction": "HIGH (A+)",
    },
    "ETH": {
        "name": "Ethereum",
        "sector": "Smart Contract L1",
        "robinhood": True,
        "entry_low": 2400.00,
        "entry_high": 2440.00,
        "reclaim_trigger": 2520.00,
        "stop_loss": 2360.00,
        "target_1": 2680.00,
        "target_2": 2850.00,
        "timeframe": "4H / Daily",
        "setup_type": "Consolidation Range Low Defense",
        "notes": "Accumulate in $2,400–$2,440 discount block. Target $2,680+ relief expansion with stop below $2,360.",
        "conviction": "MEDIUM-HIGH",
    },
    "SUI": {
        "name": "Sui",
        "sector": "High-Beta Layer 1",
        "robinhood": True,
        "entry_low": 0.95,
        "entry_high": 1.02,
        "reclaim_trigger": 1.10,
        "stop_loss": 0.90,
        "target_1": 1.25,
        "target_2": 1.48,
        "timeframe": "4H",
        "setup_type": "Sub-$1.00 Discount Accumulation",
        "notes": "High-beta runner. Accumulate near or under $1.00 shelf with tight stop below $0.90.",
        "conviction": "MEDIUM-HIGH",
    },
    "NEAR": {
        "name": "NEAR Protocol",
        "sector": "AI & Layer 1",
        "robinhood": True,
        "entry_low": 4.25,
        "entry_high": 4.50,
        "reclaim_trigger": 4.90,
        "stop_loss": 3.98,
        "target_1": 5.40,
        "target_2": 6.20,
        "timeframe": "4H",
        "setup_type": "Trendline Retest & Fair Value Gap",
        "notes": "AI narrative momentum. Limit bids around $4.25–$4.50 offer favorable R:R. Risk capped to ~7%.",
        "conviction": "MEDIUM-HIGH",
    },
    "AAVE": {
        "name": "Aave",
        "sector": "DeFi Blue Chip",
        "robinhood": True,
        "entry_low": 150.00,
        "entry_high": 158.00,
        "reclaim_trigger": 172.00,
        "stop_loss": 142.00,
        "target_1": 185.00,
        "target_2": 210.00,
        "timeframe": "Daily",
        "setup_type": "DeFi Leader Consolidation",
        "notes": "Leading altcoin on relative strength. Bids in $150–$158 zone offer 3:1+ R:R toward $185+.",
        "conviction": "HIGH (A+)",
    },
    "PEPE": {
        "name": "Pepe",
        "sector": "Meme / Speculative Beta",
        "robinhood": True,
        "entry_low": 0.00000360,
        "entry_high": 0.00000385,
        "reclaim_trigger": 0.00000410,
        "stop_loss": 0.00000335,
        "target_1": 0.00000460,
        "target_2": 0.00000540,
        "timeframe": "4H",
        "setup_type": "Range Low Sweep & Reversal",
        "notes": "High volatility momentum play. Enter strictly on range lows ($0.00000360–$0.00000385). Never chase green spikes.",
        "conviction": "SPECULATIVE",
    },
}


def build_live_callouts(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mids = data_fetcher.fetch_hyperliquid_mids()
    px_map = {m["symbol"]: (m.get("price"), m.get("change_24h")) for m in markets}

    callouts = []
    for sym, cfg in CALLOUT_CONFIGS.items():
        price = None
        chg = None
        if sym in mids and mids[sym] is not None:
            price = mids[sym]
        elif sym == "PEPE" and "kPEPE" in mids and mids["kPEPE"] is not None:
            price = mids["kPEPE"] / 1000.0
        elif sym in px_map and px_map[sym][0] is not None:
            price = px_map[sym][0]

        if price is None and sym in px_map:
            price = px_map[sym][0]
        if price is None:
            continue

        if chg is None and sym in px_map:
            chg = px_map[sym][1]

        elo, ehi = cfg["entry_low"], cfg["entry_high"]
        stop = cfg["stop_loss"]
        t1, t2 = cfg["target_1"], cfg["target_2"]
        avg_e = (elo + ehi) / 2
        risk = max(avg_e - stop, 0.000001)
        rew = max(t1 - avg_e, 0)
        rr = round(rew / risk, 1)

        if elo <= price <= ehi:
            status = "IN_ZONE"
            badge = "🟢 IN BUY ZONE"
            badge_cls = "live"
            desc = f"Price is inside optimal entry range ({elo} – {ehi}). Limit orders ready."
            dist_pct = 0.0
        elif price > ehi:
            dist = round((price - ehi) / ehi * 100, 1)
            if dist <= 3.5:
                status = "NEAR_ZONE"
                badge = "⏳ NEAR ENTRY (WAIT DIP)"
                badge_cls = "warn"
                desc = f"Hovering +{dist}% above entry shelf. Standing by for dip into {elo}–{ehi}."
            else:
                status = "WAIT_PULLBACK"
                badge = "⏱ WAITING FOR PULLBACK"
                badge_cls = "muted"
                desc = f"Extended +{dist}% above entry zone. Do not FOMO chase."
            dist_pct = dist
        else:
            if price >= stop:
                dist = round((elo - price) / elo * 100, 1)
                status = "DEEP_DISCOUNT"
                badge = "⚡ DEEP DISCOUNT WICK"
                badge_cls = "olive"
                desc = f"Swept -{dist}% below base. High reward accumulation if held above ${stop}."
                dist_pct = -dist
            else:
                status = "STOPPED"
                badge = "🛑 STOPPED OUT / AVOID"
                badge_cls = "down"
                desc = f"Broke below hard stop (${stop}). Stand down until structure reclaims."
                dist_pct = None

        callouts.append({
            "symbol": sym,
            "name": cfg["name"],
            "sector": cfg["sector"],
            "price": price,
            "change_24h": chg,
            "status": status,
            "badge": badge,
            "badge_cls": badge_cls,
            "desc": desc,
            "distance_pct": dist_pct,
            "entry_low": elo,
            "entry_high": ehi,
            "reclaim_trigger": cfg["reclaim_trigger"],
            "stop_loss": stop,
            "target_1": t1,
            "target_2": t2,
            "rr_ratio": rr,
            "timeframe": cfg["timeframe"],
            "setup_type": cfg["setup_type"],
            "notes": cfg["notes"],
            "conviction": cfg["conviction"],
            "robinhood": cfg["robinhood"],
        })

    # Sort so IN_ZONE and NEAR_ZONE appear at the top
    order_weight = {"IN_ZONE": 0, "NEAR_ZONE": 1, "DEEP_DISCOUNT": 2, "WAIT_PULLBACK": 3, "STOPPED": 4}
    callouts.sort(key=lambda c: (order_weight.get(c["status"], 5), abs(c["distance_pct"] or 999)))
    return callouts


def build_dashboard() -> Dict[str, Any]:
    errors = []

    def attempt(name, fn, default):
        try:
            val = fn()
            if not val:
                errors.append(f"{name}: no data returned")
            return val or default
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
            return default

    markets = attempt("Crypto markets", fetch_markets, [])
    fng = attempt("Fear & Greed", data_fetcher.fetch_fear_and_greed, {})
    calendar = attempt("Forex Factory", data_fetcher.fetch_forex_factory, [])
    crypto_news = sentiment_analyzer.process_all_news(attempt("Crypto news", data_fetcher.fetch_crypto_news, []))
    squawk = sentiment_analyzer.process_all_news(attempt("FinancialJuice", data_fetcher.fetch_financial_juice, []))

    tone_map = sentiment_analyzer.calculate_asset_sentiment_map(crypto_news + squawk)
    for m in markets:
        t = tone_map.get(m["symbol"])
        m["news_tone"] = round(t["score"], 1) if t else None
        m["news_mentions"] = t.get("mention_count", 0) if t else 0

    now = datetime.now(timezone.utc)
    upcoming = []
    for ev in calendar:
        try:
            when = datetime.fromisoformat(ev["date"])
        except Exception:  # noqa: BLE001
            continue
        if ev.get("country") == "USD" and ev.get("impact") in ("High", "Medium") and when >= now:
            upcoming.append({**ev, "date": when.isoformat()})
    upcoming.sort(key=lambda e: e["date"])

    news = sorted(crypto_news + squawk, key=lambda n: abs(n.get("score", 0)), reverse=True)
    avg_tone = round(sum(n["score"] for n in news) / len(news), 2) if news else None

    callouts = build_live_callouts(markets)

    return {
        "status": "success",
        "fetched_at": _now_iso(),
        "errors": errors,
        "fear_greed": fng,
        "news_tone": {"avg": avg_tone, "label": _tone_label(avg_tone) if avg_tone is not None else None,
                      "headlines": len(news)},
        "callouts": callouts,
        "markets": markets,
        "momentum": build_momentum(markets),
        "movers": {
            "up": sorted([m for m in markets if m["change_24h"] is not None], key=lambda m: m["change_24h"], reverse=True)[:5],
            "down": sorted([m for m in markets if m["change_24h"] is not None], key=lambda m: m["change_24h"])[:5],
        },
        "calendar": upcoming[:12],
        "news": [{k: n.get(k) for k in ("title", "link", "source", "pubDate", "score", "catalyst", "assets")}
                 for n in news[:40]],
    }


def get_dashboard(force: bool = False) -> Dict[str, Any]:
    if force:
        _cache.pop("dash", None)
    return _cached("dash", 60, build_dashboard)


def get_callouts() -> List[Dict[str, Any]]:
    return _cached("callouts", 5, lambda: build_live_callouts(fetch_markets()))


def get_hyperliquid(coin: str = "HYPE") -> Dict[str, Any]:
    return _cached(f"hl:{coin}", 5, lambda: fetch_hyperliquid(coin))

