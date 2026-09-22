"""
Signal Generator for Crypto AI Screener.
Synthesizes news sentiment, Fear & Greed regime, price momentum,
and Forex Factory macro risk to generate quantitative Entry and Exit signals (0-100).
"""

from typing import Dict, List, Any
import config


def evaluate_macro_risk(ff_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assess whether high-impact macro announcements are imminent."""
    high_impact_usd = [e for e in ff_events if e.get("is_usd") and e.get("is_high_impact")]
    medium_impact_usd = [e for e in ff_events if e.get("is_usd") and e.get("impact") == "Medium"]

    if high_impact_usd:
        upcoming_title = high_impact_usd[0].get("title", "")
        upcoming_date = high_impact_usd[0].get("date", "")
        return {
            "status": "ELEVATED_RISK",
            "message": f"High Impact USD Event Upcoming: {upcoming_title}",
            "next_event": upcoming_title,
            "next_date": upcoming_date,
            "caution_level": "HIGH",
        }
    elif medium_impact_usd:
        upcoming_title = medium_impact_usd[0].get("title", "")
        return {
            "status": "MODERATE_RISK",
            "message": f"Moderate USD Release: {upcoming_title}",
            "next_event": upcoming_title,
            "next_date": medium_impact_usd[0].get("date", ""),
            "caution_level": "MODERATE",
        }
    return {
        "status": "CLEAR",
        "message": "No immediate high-impact USD economic events scheduled today.",
        "next_event": "None today",
        "next_date": "",
        "caution_level": "LOW",
    }


def compute_market_radar_score(fng: Dict[str, Any], enriched_news: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall market-wide Bull/Bear radar score (0-100)."""
    fng_val = fng.get("value", 50)
    
    # Compute average news sentiment from crypto + FinancialJuice
    if enriched_news:
        avg_news_score = sum(n["score"] for n in enriched_news) / len(enriched_news)
    else:
        avg_news_score = 0.0

    # Base market score around 50
    # 40% Fear & Greed, 60% News & Squawk Sentiment
    fng_component = (fng_val - 50) * 0.4
    news_component = avg_news_score * 4.0  # -10 to +10 becomes -40 to +40

    radar_score = 50.0 + fng_component + news_component
    radar_score = max(0.0, min(100.0, radar_score))
    radar_score = round(radar_score, 1)

    # Determine market posture
    if radar_score >= config.SIGNAL_THRESHOLDS["STRONG_BUY"]:
        posture = "STRONG RISK-ON (ACCUMULATE)"
        bias = "BULLISH"
        action = "Institutions accumulating; look for continuation setups and hold runners."
    elif radar_score >= config.SIGNAL_THRESHOLDS["DIP_ENTRY"]:
        posture = "BULLISH BIAS (BUY DIPS)"
        bias = "MODERATELY_BULLISH"
        action = "Market healthy; avoid chasing tops, buy 15m/1h discount retracements."
    elif radar_score >= config.SIGNAL_THRESHOLDS["HOLD"]:
        posture = "NEUTRAL / ROTATION"
        bias = "NEUTRAL"
        action = "Consolidation phase; stay selective, prioritize sector leaders (e.g. AI tokens)."
    elif radar_score >= config.SIGNAL_THRESHOLDS["TIGHTEN_STOPS"]:
        posture = "DEFENSIVE (TIGHTEN STOPS)"
        bias = "MODERATELY_BEARISH"
        action = "Negative catalysts emerging; trim weak positions and raise stop losses."
    else:
        posture = "RISK-OFF (DEFENSIVE EXIT)"
        bias = "BEARISH"
        action = "High-severity headwind / exploit / macro shock; preserve capital in cash/USDT."

    return {
        "radar_score": radar_score,
        "posture": posture,
        "bias": bias,
        "action": action,
        "avg_news_sentiment": round(avg_news_score, 2),
        "fear_and_greed_val": fng_val,
        "fear_and_greed_label": fng.get("classification", "Neutral"),
    }


def compute_asset_signals(
    markets: List[Dict[str, Any]],
    asset_sentiment_map: Dict[str, Dict[str, Any]],
    market_radar: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Compute individual entry/exit score (0-100) and actionable plan for each coin."""
    results = []

    for coin in markets:
        symbol = coin["symbol"].upper()
        name = coin["name"]
        price = coin["price"]
        chg_24h = coin["change_24h"]
        chg_7d = coin.get("change_7d", 0.0)
        high_24h = coin.get("high_24h", price * 1.03)
        low_24h = coin.get("low_24h", price * 0.97)

        # Retrieve specific news sentiment if available
        sent_info = asset_sentiment_map.get(symbol) or asset_sentiment_map.get("ALL_CRYPTO", {"score": 0.0, "mention_count": 0, "top_news": []})
        asset_news_score = sent_info.get("score", 0.0)

        # Baseline: 50 + News Impact (45%) + Momentum Impact (35%) + Macro Bias (20%)
        news_adj = asset_news_score * 3.5  # -10 to +10 -> -35 to +35
        mom_adj = max(-20.0, min(20.0, chg_24h * 1.5))  # capped at +/- 20
        macro_adj = (market_radar["radar_score"] - 50.0) * 0.2

        raw_score = 50.0 + news_adj + mom_adj + macro_adj

        # Overbought / Oversold adjustments
        # If coin pumped >15% today, avoid giving 'Strong Buy' to prevent chasing tops
        if chg_24h > 15.0 and raw_score > 70:
            raw_score -= 8.0  # slight penalty to encourage waiting for pullback
        # If coin dumped >10% on positive or neutral news, boost for dip opportunity
        elif chg_24h < -8.0 and asset_news_score >= 0:
            raw_score += 6.0

        score = max(0.0, min(100.0, raw_score))
        score = round(score, 1)

        # Precise Trade Execution Metrics
        entry_low = round(price * 0.988, 4 if price < 10 else 2)
        entry_high = round(price * 1.004, 4 if price < 10 else 2)
        stop_val = round(min(low_24h * 0.99, price * 0.965), 4 if price < 10 else 2)
        target1_val = round(price * 1.06, 4 if price < 10 else 2)
        target2_val = round(price * 1.12, 4 if price < 10 else 2)

        risk = max(0.0001, price - stop_val)
        reward = max(0.0001, target1_val - price)
        rr_ratio = round(reward / risk, 1)

        conviction = min(98, max(45, int(score * 1.12)))

        # Determine Signal Category
        if score >= config.SIGNAL_THRESHOLDS["STRONG_BUY"]:
            signal = "STRONG BUY"
            badge_class = "badge-buy"
            recommendation = "ACCUMULATE NOW"
            buy_urgency = "HIGH_CONVICTION_ENTRY"
            tactical_plan = f"Confirmed momentum + catalyst. Buy {entry_low} - {entry_high}. Stop below {stop_val}. Target {target1_val}."
            why_buy = f"Bullish catalyst ({sent_info.get('top_news', [{'catalyst': 'Sector Surge'}])[0].get('catalyst', 'Sector Surge')}) aligned with +{chg_24h}% daily momentum."
        elif score >= config.SIGNAL_THRESHOLDS["DIP_ENTRY"]:
            signal = "DIP ENTRY"
            badge_class = "badge-dip"
            recommendation = "BUY ON PULLBACK"
            buy_urgency = "LIMIT_ORDER_DIP"
            tactical_plan = f"Bullish structure coiling. Set limit orders in discount zone {entry_low} - {price}. Stop: {stop_val}."
            why_buy = f"Healthy trend continuation; wait for 15m liquidity grab into discount before entering."
        elif score >= config.SIGNAL_THRESHOLDS["HOLD"]:
            signal = "HOLD"
            badge_class = "badge-hold"
            recommendation = "WAIT FOR TRIGGER"
            buy_urgency = "STAND_DOWN"
            tactical_plan = f"Consolidating in range ({round(low_24h, 2)} - {round(high_24h, 2)}). Wait for breakout confirmation."
            why_buy = f"No dominant catalyst; wait for directional expansion."
        elif score >= config.SIGNAL_THRESHOLDS["TIGHTEN_STOPS"]:
            signal = "TIGHTEN STOPS"
            badge_class = "badge-warning"
            recommendation = "TAKE PROFIT / TRAIL"
            buy_urgency = "EXIT_LONG_POSITIONS"
            tactical_plan = f"Momentum slowing or macro resistance. Move stops up to {round(price * 0.98, 2)}."
            why_buy = f"High risk of rejection; lock in unrealized profits."
        else:
            signal = "DEFENSIVE EXIT"
            badge_class = "badge-exit"
            recommendation = "DE-RISK / CASH"
            buy_urgency = "AVOID_OR_EXIT"
            tactical_plan = f"Critical negative news friction or structural breakdown. Preserve capital in cash/USDT."
            why_buy = f"Severe bearish catalyst detected; avoid entering."

        # Key technical levels
        support_level = round(low_24h, 4 if price < 10 else 2)
        resistance_level = round(high_24h, 4 if price < 10 else 2)
        invalidation = stop_val

        results.append({
            "id": coin["id"],
            "symbol": symbol,
            "name": name,
            "price": price,
            "change_24h": round(chg_24h, 2),
            "change_7d": round(chg_7d, 2),
            "volume_24h": coin["volume_24h"],
            "market_cap": coin["market_cap"],
            "rank": coin["rank"],
            "sector": coin["sector"],
            "image": coin["image"],
            "score": score,
            "signal": signal,
            "badge_class": badge_class,
            "recommendation": recommendation,
            "buy_urgency": buy_urgency,
            "tactical_plan": tactical_plan,
            "why_buy": why_buy,
            "entry_zone": f"${entry_low:,.4f}" if price < 1 else f"${entry_low:,.2f} – ${entry_high:,.2f}",
            "stop_loss": f"${stop_val:,.4f}" if price < 1 else f"${stop_val:,.2f}",
            "target_1": f"${target1_val:,.4f}" if price < 1 else f"${target1_val:,.2f}",
            "target_2": f"${target2_val:,.4f}" if price < 1 else f"${target2_val:,.2f}",
            "risk_reward": f"{rr_ratio} : 1",
            "conviction": conviction,
            "news_sentiment": round(asset_news_score, 1),
            "support": support_level,
            "resistance": resistance_level,
            "invalidation": invalidation,
            "top_news": sent_info.get("top_news", []),
        })

    # Sort descending by score (best buy candidates on top)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def build_full_intelligence_report(data: Dict[str, Any], enriched_news: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Produce unified intelligence report combining all dimensions."""
    fng = data.get("fear_and_greed", {})
    markets = data.get("markets", [])
    ff_events = data.get("forex_factory", [])
    fj_squawk = data.get("financial_juice", [])

    macro_risk = evaluate_macro_risk(ff_events)
    market_radar = compute_market_radar_score(fng, enriched_news)
    
    import sentiment_analyzer
    asset_sentiment_map = sentiment_analyzer.calculate_asset_sentiment_map(enriched_news)
    asset_signals = compute_asset_signals(markets, asset_sentiment_map, market_radar)

    # Filter top buy opportunities and exit warnings
    top_entries = [a for a in asset_signals if a["signal"] in ["STRONG BUY", "DIP ENTRY"]][:6]
    top_exits = [a for a in asset_signals if a["signal"] in ["DEFENSIVE EXIT", "TIGHTEN STOPS"]][:6]

    return {
        "timestamp": data.get("timestamp"),
        "macro_risk": macro_risk,
        "market_radar": market_radar,
        "top_entries": top_entries,
        "top_exits": top_exits,
        "asset_signals": asset_signals,
        "total_assets_tracked": len(asset_signals),
    }
