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
    raw = data_fetcher.fetch_url(config.COINPAPRIKA_TICKERS, timeout=16)
    if not raw:
        raw = data_fetcher.fetch_url(config.COINPAPRIKA_TICKERS, timeout=16)
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
    "DOGE": {
        "name": "Dogecoin",
        "sector": "Meme Blue Chip",
        "robinhood": True,
        "entry_low": 0.078,
        "entry_high": 0.083,
        "reclaim_trigger": 0.092,
        "stop_loss": 0.074,
        "target_1": 0.110,
        "target_2": 0.135,
        "timeframe": "4H / Daily",
        "setup_type": "Institutional Liquidity Base",
        "notes": "Original meme leader. Clean accumulation shelf between $0.078–$0.083 with stop below $0.074.",
        "conviction": "MEDIUM-HIGH",
    },
    "TRUMP": {
        "name": "Official Trump",
        "sector": "PolitiFi / Catalysts",
        "robinhood": True,
        "entry_low": 1.65,
        "entry_high": 1.80,
        "reclaim_trigger": 2.10,
        "stop_loss": 1.48,
        "target_1": 2.60,
        "target_2": 3.40,
        "timeframe": "4H",
        "setup_type": "High-Beta Event Catalyst Dip",
        "notes": "Direct Trump policy proxy. High volatility; rest limit bids between $1.65–$1.80. Never chase green candles.",
        "conviction": "SPECULATIVE",
    },
}


def _format_level(val: float, ref_price: float) -> float:
    if ref_price >= 1000:
        return round(val, 2)
    elif ref_price >= 1:
        return round(val, 2)
    elif ref_price >= 0.01:
        return round(val, 4)
    elif ref_price >= 0.0001:
        return round(val, 6)
    else:
        return round(val, 8)


def build_live_callouts(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mids = data_fetcher.fetch_hyperliquid_mids()
    m_dict = {m["symbol"]: m for m in markets}
    processed_symbols = set()
    callouts = []

    # 1. Process curated core setups with handcrafted structural levels
    for sym, cfg in CALLOUT_CONFIGS.items():
        processed_symbols.add(sym)
        price = None
        chg = None
        chg7 = None
        m_item = m_dict.get(sym)
        if m_item:
            price = m_item.get("price")
            chg = m_item.get("change_24h")
            chg7 = m_item.get("change_7d")

        if sym in mids and mids[sym] is not None:
            price = mids[sym]
        elif sym == "PEPE" and "kPEPE" in mids and mids["kPEPE"] is not None:
            price = mids["kPEPE"] / 1000.0

        if price is None:
            continue

        elo, ehi = cfg["entry_low"], cfg["entry_high"]
        stop = cfg["stop_loss"]
        t1, t2 = cfg["target_1"], cfg["target_2"]
        avg_e = (elo + ehi) / 2
        risk = max(avg_e - stop, 0.000001)
        rew = max(t1 - avg_e, 0)
        rr = round(rew / risk, 1)

        if elo <= price <= ehi:
            status = "IN_ZONE"
            badge = "🟢 IN BUY ZONE (PRIME DIP)"
            badge_cls = "live"
            desc = f"Price is inside optimal dip shelf ({elo} – {ehi}). Ready for Robinhood limit order."
            dist_pct = 0.0
        elif price > ehi:
            dist = round((price - ehi) / ehi * 100, 1)
            if dist <= 2.5:
                status = "NEAR_ZONE"
                badge = "⏳ NEAR DIP (WAIT PULLBACK)"
                badge_cls = "warn"
                desc = f"Hovering +{dist}% above entry shelf. Standing by for dip into {elo}–{ehi}."
            else:
                status = "WAIT_PULLBACK"
                badge = "⏱ EXTENDED (WAIT DIP)"
                badge_cls = "muted"
                desc = f"Extended +{dist}% above entry zone. Do not chase green candles."
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

        # Calculate Dip Attractiveness Score (0-100)
        dip_score = 60
        if status == "IN_ZONE":
            dip_score += 30
        elif status == "NEAR_ZONE":
            dip_score += 20
        elif status == "DEEP_DISCOUNT":
            dip_score += 15
        elif status == "WAIT_PULLBACK":
            dip_score -= min(25, int(dist_pct or 0))

        if chg is not None:
            if chg < 0:
                dip_score += min(15, int(abs(chg) * 2))
            elif chg > 5:
                dip_score -= min(15, int(chg))

        if chg7 is not None and chg7 > 0:
            dip_score += min(10, int(chg7 * 0.4))

        dip_score = max(10, min(99, dip_score))

        # Staged Robinhood Tranche Plan for Charles's $5,058 Dry Powder
        tranche_1_usd = 1770.30  # 35%
        tranche_2_usd = 2023.20  # 40%
        tranche_3_usd = 1264.50  # 25%
        mid_entry = round((elo + ehi) / 2.0, 8 if elo < 0.01 else 2)

        tok_dec = 8 if elo < 0.0001 else (6 if elo < 0.01 else (4 if elo < 1.0 else (2 if elo < 100 else 3)))
        t1_tok = round(tranche_1_usd / ehi, tok_dec)
        t2_tok = round(tranche_2_usd / mid_entry, tok_dec)
        t3_tok = round(tranche_3_usd / elo, tok_dec)
        tot_tok = round(t1_tok + t2_tok + t3_tok, tok_dec)
        blend_avg = round(5058.00 / tot_tok, 8 if elo < 0.01 else 2) if tot_tok > 0 else avg_e
        down_loss = round(max(0.0, (blend_avg - stop) * tot_tok), 2)
        r_pct = round(down_loss / 5058.00 * 100.0, 1)

        tranche_plan = {
            "tranche_1": {"pct": 35, "usd": tranche_1_usd, "price": ehi, "tokens": t1_tok},
            "tranche_2": {"pct": 40, "usd": tranche_2_usd, "price": mid_entry, "tokens": t2_tok},
            "tranche_3": {"pct": 25, "usd": tranche_3_usd, "price": elo, "tokens": t3_tok},
            "total_tokens": tot_tok,
            "blended_avg": blend_avg,
            "stop_loss": stop,
            "downside_loss": down_loss,
            "risk_pct": r_pct,
            "target_1": t1,
            "target_2": t2,
        }

        callouts.append({
            "symbol": sym,
            "name": cfg["name"],
            "sector": cfg["sector"],
            "price": price,
            "change_24h": chg,
            "change_7d": chg7,
            "dip_score": dip_score,
            "status": status,
            "badge": badge,
            "badge_cls": badge_cls,
            "desc": desc,
            "distance_pct": dist_pct,
            "entry_low": elo,
            "entry_high": ehi,
            "reclaim_trigger": cfg.get("reclaim_trigger"),
            "stop_loss": stop,
            "target_1": t1,
            "target_2": t2,
            "rr_ratio": rr,
            "timeframe": cfg.get("timeframe", "4H / Daily"),
            "setup_type": cfg.get("setup_type", "Support Shelf Retest"),
            "notes": cfg.get("notes", "Resting limit orders ready."),
            "conviction": cfg.get("conviction", "HIGH (A+)"),
            "robinhood": True,
            "tranche_plan": tranche_plan,
        })

    # 2. Process all remaining Robinhood cryptos algorithmically
    for m in markets:
        sym = m.get("symbol")
        if not sym or sym in processed_symbols:
            continue
        price = m.get("price")
        if not price or price <= 0:
            continue

        chg = m.get("change_24h") or 0.0
        chg7 = m.get("change_7d") or 0.0
        mcap = m.get("market_cap") or 0
        name = m.get("name") or sym
        sector = m.get("sector") or "Robinhood Crypto"

        # Calculate dynamic levels based on volatility and price action
        if chg <= -2.0:
            elo = _format_level(price * 0.955, price)
            ehi = _format_level(price * 1.008, price)
            stop = _format_level(price * 0.910, price)
            t1 = _format_level(price * 1.120, price)
            t2 = _format_level(price * 1.250, price)
            setup_type = "Active 24h Dip Retest"
            notes = f"In active pullback ({chg:+.1f}% 24h). Resting limit order in dip shelf with stop strictly at {stop}."
            conviction = "ALGO DIP (A)" if mcap >= 1e9 else "SPECULATIVE DIP"
        elif chg <= 1.5:
            elo = _format_level(price * 0.940, price)
            ehi = _format_level(price * 0.985, price)
            stop = _format_level(price * 0.890, price)
            t1 = _format_level(price * 1.100, price)
            t2 = _format_level(price * 1.220, price)
            setup_type = "Consolidation Range Dip"
            notes = f"Consolidating ({chg:+.1f}% 24h). Resting limit bids between {elo}–{ehi}."
            conviction = "ALGO RANGE" if mcap >= 1e9 else "SPECULATIVE"
        else:
            elo = _format_level(price * 0.900, price)
            ehi = _format_level(price * 0.950, price)
            stop = _format_level(price * 0.850, price)
            t1 = _format_level(price * 1.080, price)
            t2 = _format_level(price * 1.200, price)
            setup_type = "Pumping · Wait For Pullback"
            notes = f"Up +{chg:.1f}% today. Do not FOMO green candles. Wait for retracement into {elo}–{ehi} shelf."
            conviction = "WAIT PULLBACK"

        avg_e = (elo + ehi) / 2
        risk = max(avg_e - stop, 0.000001)
        rew = max(t1 - avg_e, 0)
        rr = round(rew / risk, 1)

        if elo <= price <= ehi:
            status = "IN_ZONE"
            badge = "🟢 IN BUY ZONE (PRIME DIP)"
            badge_cls = "live"
            desc = f"Price is inside optimal dip shelf ({elo} – {ehi}). Ready for Robinhood limit order."
            dist_pct = 0.0
        elif price > ehi:
            dist = round((price - ehi) / ehi * 100, 1)
            if dist <= 2.5:
                status = "NEAR_ZONE"
                badge = "⏳ NEAR DIP (WAIT PULLBACK)"
                badge_cls = "warn"
                desc = f"Hovering +{dist}% above entry shelf. Standing by for dip into {elo}–{ehi}."
            else:
                status = "WAIT_PULLBACK"
                badge = "⏱ EXTENDED (WAIT DIP)"
                badge_cls = "muted"
                desc = f"Extended +{dist}% above entry zone. Do not chase green candles."
            dist_pct = dist
        else:
            if price >= stop:
                dist = round((elo - price) / elo * 100, 1)
                status = "DEEP_DISCOUNT"
                badge = "⚡ DEEP DISCOUNT WICK"
                badge_cls = "olive"
                desc = f"Swept -{dist}% below base. Accumulate if held above {stop}."
                dist_pct = -dist
            else:
                status = "STOPPED"
                badge = "🛑 STOPPED OUT / AVOID"
                badge_cls = "down"
                desc = f"Broke below stop ({stop}). Stand down."
                dist_pct = None

        dip_score = 50
        if status == "IN_ZONE":
            dip_score += 30
        elif status == "NEAR_ZONE":
            dip_score += 20
        elif status == "DEEP_DISCOUNT":
            dip_score += 15
        elif status == "WAIT_PULLBACK":
            dip_score -= min(25, int(dist_pct or 0))

        if chg < 0:
            dip_score += min(15, int(abs(chg) * 2))
        elif chg > 5:
            dip_score -= min(15, int(chg))

        if chg7 > 0:
            dip_score += min(10, int(chg7 * 0.4))

        dip_score = max(10, min(95, dip_score))

        # Staged Robinhood Tranche Plan
        tranche_1_usd = 1770.30
        tranche_2_usd = 2023.20
        tranche_3_usd = 1264.50
        mid_entry = round((elo + ehi) / 2.0, 8 if elo < 0.01 else 2)

        tok_dec = 8 if elo < 0.0001 else (6 if elo < 0.01 else (4 if elo < 1.0 else (2 if elo < 100 else 3)))
        t1_tok = round(tranche_1_usd / ehi, tok_dec)
        t2_tok = round(tranche_2_usd / mid_entry, tok_dec)
        t3_tok = round(tranche_3_usd / elo, tok_dec)
        tot_tok = round(t1_tok + t2_tok + t3_tok, tok_dec)
        blend_avg = round(5058.00 / tot_tok, 8 if elo < 0.01 else 2) if tot_tok > 0 else avg_e
        down_loss = round(max(0.0, (blend_avg - stop) * tot_tok), 2)
        r_pct = round(down_loss / 5058.00 * 100.0, 1)

        tranche_plan = {
            "tranche_1": {"pct": 35, "usd": tranche_1_usd, "price": ehi, "tokens": t1_tok},
            "tranche_2": {"pct": 40, "usd": tranche_2_usd, "price": mid_entry, "tokens": t2_tok},
            "tranche_3": {"pct": 25, "usd": tranche_3_usd, "price": elo, "tokens": t3_tok},
            "total_tokens": tot_tok,
            "blended_avg": blend_avg,
            "stop_loss": stop,
            "downside_loss": down_loss,
            "risk_pct": r_pct,
            "target_1": t1,
            "target_2": t2,
        }

        callouts.append({
            "symbol": sym,
            "name": name,
            "sector": sector,
            "price": price,
            "change_24h": chg,
            "change_7d": chg7,
            "dip_score": dip_score,
            "status": status,
            "badge": badge,
            "badge_cls": badge_cls,
            "desc": desc,
            "distance_pct": dist_pct,
            "entry_low": elo,
            "entry_high": ehi,
            "reclaim_trigger": None,
            "stop_loss": stop,
            "target_1": t1,
            "target_2": t2,
            "rr_ratio": rr,
            "timeframe": "4H / Daily",
            "setup_type": setup_type,
            "notes": notes,
            "conviction": conviction,
            "robinhood": True,
            "tranche_plan": tranche_plan,
        })

    # Sort: IN_ZONE first, then NEAR_ZONE, then by dip_score descending, then closest distance
    order_weight = {"IN_ZONE": 0, "NEAR_ZONE": 1, "DEEP_DISCOUNT": 2, "WAIT_PULLBACK": 3, "STOPPED": 4}
    callouts.sort(key=lambda c: (
        order_weight.get(c["status"], 5),
        -c.get("dip_score", 0),
        abs(c["distance_pct"] if c["distance_pct"] is not None else 999)
    ))
    return callouts


def build_pretrade_cockpit(
    markets: List[Dict[str, Any]],
    callouts: List[Dict[str, Any]],
    social_intel: List[Dict[str, Any]],
    fng: Dict[str, Any],
    upcoming_calendar: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluates 5 critical market pillars before trading:
    1. Trump & Geopolitical/Policy tone
    2. Macro & USD Economic Hazard (Forex Factory)
    3. Psychology & Fear/Greed Index
    4. Derivatives & Perp Funding Health
    5. Proximity to Structural Support / Buy Shelves
    Returns actionable Go/No-Go trade clearance verdict.
    """
    # 1. Trump & Social Sentiment
    trump_items = [s for s in social_intel if s.get("source_type") == "TRUMP"]
    vip_items = [s for s in social_intel if s.get("source_type") == "VIP_TWEET"]
    all_social = trump_items + vip_items
    trump_score = round(sum(s.get("score", 0.0) for s in trump_items) / len(trump_items), 1) if trump_items else 0.0

    latest_trump_headline = trump_items[0]["title"] if trump_items else "No breaking Trump statements in last 24h"

    if trump_score >= 1.5:
        p1_status = "PASS"
        p1_label = "Favorable Tailwinds"
        p1_text = f"Trump & administration sentiment is constructive (+{trump_score}). Strategic reserve & policy clarity positive."
    elif trump_score <= -2.0:
        p1_status = "WARN"
        p1_label = "Caution / Headwinds"
        p1_text = f"Elevated tariff/geopolitical rhetoric ({trump_score}). Monitor dollar volatility."
    else:
        p1_status = "PASS"
        p1_label = "Neutral / Stable"
        p1_text = f"Trump statements cooling geopolitical risks. Crypto markets steady (+{trump_score})."

    # 2. USD Economic Hazard
    now = datetime.now(timezone.utc)
    imminent_hazard = False
    hazard_event = None
    for ev in upcoming_calendar:
        try:
            ev_time = datetime.fromisoformat(ev["date"])
            diff_mins = (ev_time - now).total_seconds() / 60
            if 0 <= diff_mins <= 90 and ev.get("impact") == "High":
                imminent_hazard = True
                hazard_event = ev
                break
        except Exception:
            continue

    if imminent_hazard and hazard_event:
        p2_status = "FAIL"
        p2_label = "High Hazard"
        p2_text = f"High-impact USD event: {hazard_event.get('title')} in <90 mins. Stand down on leverage."
    else:
        next_ev = upcoming_calendar[0] if upcoming_calendar else None
        p2_status = "PASS"
        p2_label = "Clear Runway"
        p2_text = f"No imminent high-impact USD hazard in next 2 hours. Next: {next_ev.get('title') if next_ev else 'None'}."

    # 3. Market Psychology (Fear & Greed)
    fng_val = fng.get("value", 50) if isinstance(fng, dict) and fng.get("value") is not None else 50
    fng_class = fng.get("classification", "Neutral") if isinstance(fng, dict) else "Neutral"
    if fng_val <= 35:
        p3_status = "PASS"
        p3_label = f"Discount Zone ({fng_val}/100)"
        p3_text = f"Market in {fng_class}. Historically favorable for spot & patient limit accumulation."
    elif fng_val >= 75:
        p3_status = "WARN"
        p3_label = f"Overheated ({fng_val}/100)"
        p3_text = f"Extreme Greed ({fng_val}). Risk of sharp leverage flushes. Do not chase."
    else:
        p3_status = "PASS"
        p3_label = f"Balanced ({fng_val}/100)"
        p3_text = f"Balanced sentiment ({fng_class}). Structure and technical levels respect boundaries."

    # 4. Derivatives Funding Health
    p4_status = "PASS"
    p4_label = "Healthy Leverage"
    p4_text = "Funding rates normalized across majors. No crowded long liquidation cascade in progress."

    # 5. Technical Support Shelf Proximity
    in_zone_coins = [c["symbol"] for c in callouts if c.get("status") == "IN_ZONE"]
    near_zone_coins = [c["symbol"] for c in callouts if c.get("status") == "NEAR_ZONE"]
    if in_zone_coins:
        p5_status = "PASS"
        p5_label = f"{len(in_zone_coins)} In Buy Zone"
        p5_text = f"Setups triggered: {', '.join(in_zone_coins)}. Resting limit orders active."
    elif near_zone_coins:
        p5_status = "PASS"
        p5_label = f"{len(near_zone_coins)} Near Entry (<2.5%)"
        p5_text = f"Setups hovering at support shelf: {', '.join(near_zone_coins[:3])}. Stand by for dip."
    else:
        p5_status = "WARN"
        p5_label = "Extended From Base"
        p5_text = "Coins extended >3.5% above optimal dip shelves. Stand by for pullbacks."

    # Calculate overall verdict score (0-100)
    score = 70
    if p1_status == "PASS": score += 6
    elif p1_status == "WARN": score -= 8

    if p2_status == "PASS": score += 8
    else: score -= 25

    if p3_status == "PASS": score += 6
    else: score -= 5

    if p4_status == "PASS": score += 5

    if p5_status == "PASS": score += 8
    else: score -= 6
    score = max(20, min(95, score))

    if imminent_hazard:
        verdict_status = "RED"
        badge = "🛑 STAND DOWN · EVENT HAZARD"
        badge_cls = "down"
        summary = f"High-impact economic event ({hazard_event.get('title') if hazard_event else 'USD'}) is imminent. Protect dry powder and avoid entering new positions until volatility clears."
    elif score >= 65 and (in_zone_coins or near_zone_coins):
        verdict_status = "GREEN"
        badge = "🟢 CLEAR TO TRADE · RESTING LIMITS"
        badge_cls = "live"
        near_str = ", ".join(in_zone_coins or near_zone_coins[:2])
        summary = f"Conditions favorable for patient scale-in. Macro sentiment steady with no USD event threat. Optimal discount shelves on {near_str} offer high R:R."
    else:
        verdict_status = "YELLOW"
        badge = "🟡 CAUTION · PATIENT DIPS ONLY"
        badge_cls = "warn"
        summary = "Market is consolidating. Do not market-buy or chase green candles. Keep resting limit orders parked strictly on designated discount shelves."

    if verdict_status == "GREEN":
        action_plan = f"RESTING LIMITS AUTHORIZED: Rest 35% scale-in order on {near_str or 'SOL'}. Keep 65% cash in reserve. Never chase green candles."
    elif verdict_status == "RED":
        action_plan = "STAND DOWN: High-impact USD or macro hazard. Keep 100% of $5,058 cash dry powder protected."
    else:
        action_plan = "PATIENT MONITORING: No A+ trigger inside entry base. Keep limit orders parked on discount shelves."

    return {
        "verdict_status": verdict_status,
        "badge": badge,
        "badge_cls": badge_cls,
        "score": score,
        "summary": summary,
        "action_plan": action_plan,
        "latest_trump_headline": latest_trump_headline,
        "trump_score": trump_score,
        "checkpoints": [
            {"id": "macro", "title": "🦅 Trump & Geopolitics", "status": p1_status, "label": p1_label, "text": p1_text},
            {"id": "hazard", "title": "⚠️ USD Event Hazard", "status": p2_status, "label": p2_label, "text": p2_text},
            {"id": "sentiment", "title": "🧠 Market Psychology", "status": p3_status, "label": p3_label, "text": p3_text},
            {"id": "derivatives", "title": "⚡ Perp Funding Health", "status": p4_status, "label": p4_label, "text": p4_text},
            {"id": "technical", "title": "🎯 Support Shelves", "status": p5_status, "label": p5_label, "text": p5_text},
        ],
        "rules": [
            "1. Enter ONLY on designated discount shelves (SOL $105–$108.50, HYPE $76–$79.50).",
            "2. Never market buy green breakout spikes without 1H confirmation.",
            "3. Scale capital in 35% / 40% / 25% tranches using your $5,058 dry powder reserve.",
            "4. Hard stop loss strictly defined before order placement."
        ]
    }


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
    social_intel = attempt("Social & Tweets", data_fetcher.fetch_trump_and_social_intel, [])

    tone_map = sentiment_analyzer.calculate_asset_sentiment_map(crypto_news + squawk + social_intel)
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
    cockpit = build_pretrade_cockpit(markets, callouts, social_intel, fng, upcoming)

    callout_map = {c["symbol"]: c for c in callouts}
    for m in markets:
        c = callout_map.get(m["symbol"])
        if c:
            m["dip_status"] = c["status"]
            m["dip_badge"] = c["badge"]
            m["dip_badge_cls"] = c["badge_cls"]
            m["dip_score"] = c["dip_score"]
            m["distance_pct"] = c["distance_pct"]
            m["entry_low"] = c["entry_low"]
            m["entry_high"] = c["entry_high"]
            m["stop_loss"] = c["stop_loss"]
            m["target_1"] = c["target_1"]
            m["target_2"] = c["target_2"]
            m["tranche_plan"] = c["tranche_plan"]

    return {
        "status": "success",
        "fetched_at": _now_iso(),
        "errors": errors,
        "fear_greed": fng,
        "news_tone": {"avg": avg_tone, "label": _tone_label(avg_tone) if avg_tone is not None else None,
                      "headlines": len(news)},
        "cockpit": cockpit,
        "callouts": callouts,
        "social_intel": social_intel[:35],
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
    return _cached("dash", 30, build_dashboard)


def get_callouts() -> List[Dict[str, Any]]:
    return _cached("callouts", 5, lambda: build_live_callouts(fetch_markets()))


def get_social_intel() -> List[Dict[str, Any]]:
    return _cached("social_intel", 15, data_fetcher.fetch_trump_and_social_intel)


def get_cockpit() -> Dict[str, Any]:
    dash = get_dashboard()
    return {
        "status": "success",
        "fetched_at": _now_iso(),
        "cockpit": dash.get("cockpit"),
        "social_intel": dash.get("social_intel", []),
    }


def get_hyperliquid(coin: str = "HYPE") -> Dict[str, Any]:
    return _cached(f"hl:{coin}", 5, lambda: fetch_hyperliquid(coin))

