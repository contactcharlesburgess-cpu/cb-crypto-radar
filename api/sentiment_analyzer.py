"""
Sentiment and Catalyst Analyzer for Crypto AI Screener.
Evaluates news headlines and squawk from CoinDesk, Cointelegraph, Decrypt,
and FinancialJuice to determine sentiment direction, catalyst type,
impact weight, and asset associations.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

# Weighted sentiment rules
BULLISH_KEYWORDS = {
    # Institutional & ETFs (+8 to +10)
    "etf approval": 9.5, "approved etf": 9.5, "etp launch": 8.0, "physically backed": 8.0,
    "institutional inflow": 8.5, "record inflows": 8.5, "blackrock": 7.5, "fidelity": 7.0,
    "treasury reserve": 8.5, "corporate treasury": 8.0, "microstrategy": 7.5,
    # Regulatory Wins (+7 to +9)
    "sec dismisses": 9.0, "lawsuit dropped": 8.5, "regulatory clarity": 8.0,
    "custody path": 7.5, "favorable ruling": 8.5, "legal win": 8.0, "crypto task force": 7.0,
    "approved": 7.0, "cleared": 6.5, "green light": 7.0,
    # Technology, AI & Breakouts (+6 to +8)
    "ai agent": 7.5, "ai compute": 7.5, "gpu network": 7.0, "mainnet launch": 7.0,
    "token burn": 7.0, "halving": 7.5, "all-time high": 8.0, "ath": 7.5, "breakout": 7.0,
    "surges": 6.5, "soars": 7.0, "rallies": 6.0, "partnership": 6.5, "integration": 6.0,
    # Macro & Easing (+5 to +7)
    "rate cut": 7.5, "fed cuts": 8.0, "dovish": 7.0, "easing": 6.5, "liquidity injection": 8.0,
    "stimulus": 7.0, "cooling inflation": 6.5,
    # General positive
    "accumulate": 6.0, "bullish": 6.5, "expansion": 6.0, "adoption": 6.5,
}

BEARISH_KEYWORDS = {
    # Exploits & Insolvency (-8 to -10)
    "exploit": -9.5, "hacked": -9.5, "drain": -9.0, "funds stolen": -9.5,
    "insolvent": -10.0, "bankruptcy": -9.5, "freeze withdrawals": -10.0,
    "halts withdrawals": -10.0, "liquidation cascade": -9.0, "scam": -8.5, "rug pull": -9.5,
    # SEC & Regulatory Enforcement (-7 to -9)
    "sec sues": -9.0, "sec charges": -9.0, "subpoena": -7.5, "wells notice": -8.5,
    "criminal charges": -9.5, "doj": -8.0, "regulatory crackdown": -8.5, "banned": -8.5,
    "delisting": -8.0, "delisted": -8.0, "investigation": -7.0, "sanctions": -8.0,
    # Macro Hawkish & Inflation (-5 to -8)
    "rate hike": -8.0, "fed hikes": -8.5, "hawkish": -7.5, "inflation jumps": -7.5,
    "hot cpi": -7.5, "bond yield spike": -7.0, "quantitative tightening": -7.0,
    # Market Dumps & Sell-offs (-5 to -8)
    "crash": -8.0, "plunges": -7.5, "tumbles": -7.0, "sell-off": -6.5, "dump": -7.0,
    "whale dump": -7.5, "mt gox": -7.0, "government transfer": -6.5, "massive liquidation": -8.0,
    # General negative
    "bearish": -6.5, "collapse": -8.5, "outflows": -6.0, "panic": -7.5,
}

ASSET_PATTERNS = {
    "BTC": [r"\bbtc\b", r"\bbitcoin\b", r"\bsatoshi\b"],
    "ETH": [r"\beth\b", r"\bethereum\b", r"\bether\b", r"\bvitalik\b"],
    "SOL": [r"\bsol\b", r"\bsolana\b"],
    "XRP": [r"\bxrp\b", r"\bripple\b", r"\bgarlinghouse\b"],
    "DOGE": [r"\bdoge\b", r"\bdogecoin\b"],
    "ADA": [r"\bada\b", r"\bcardano\b", r"\bhoskinson\b"],
    "AVAX": [r"\bavax\b", r"\bavalanche\b"],
    "SHIB": [r"\bshib\b", r"\bshiba\b", r"\bshibarium\b"],
    "PEPE": [r"\bpepe\b"],
    "LINK": [r"\blink\b", r"\bchainlink\b"],
    "UNI": [r"\buni\b", r"\buniswap\b"],
    "LTC": [r"\bltc\b", r"\blitecoin\b"],
    "BCH": [r"\bbch\b", r"\bbitcoin cash\b"],
    "NEAR": [r"\bnear\b", r"\bnear protocol\b"],
    "SUI": [r"\bsui\b"],
    "XLM": [r"\bxlm\b", r"\bstellar\b"],
    "AAVE": [r"\baave\b"],
    "ETC": [r"\betc\b", r"\bethereum classic\b"],
    "COMP": [r"\bcomp\b", r"\bcompound\b"],
    "BONK": [r"\bbonk\b"],
    "WIF": [r"\bwif\b", r"\bdogwifhat\b"],
    "POL": [r"\bpol\b", r"\bpolygon\b", r"\bmatic\b"],
    "ARB": [r"\barb\b", r"\barbitrum\b"],
    "OP": [r"\bop\b", r"\boptimism\b"],
    "RENDER": [r"\brender\b", r"\brndr\b"],
    "FET": [r"\bfet\b", r"\bfetch\.ai\b", r"\basi\b", r"\bartificial superintelligence\b"],
    "XTZ": [r"\bxtz\b", r"\btezos\b"],
    "ATOM": [r"\batom\b", r"\bcosmos\b"],
    "FIL": [r"\bfil\b", r"\bfilecoin\b"],
    "DOT": [r"\bdot\b", r"\bpolkadot\b"],
    "INJ": [r"\binj\b", r"\binjective\b"],
}


def detect_assets(text: str) -> List[str]:
    """Detect associated cryptocurrency tickers in text."""
    text_lower = text.lower()
    matched = []
    for symbol, patterns in ASSET_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                matched.append(symbol)
                break
    return matched if matched else ["ALL_CRYPTO"]


def classify_catalyst(text: str) -> str:
    """Identify the fundamental catalyst driving the story."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["hack", "hacker", "exploit", "stolen", "insolvent", "drain", "freeze", "halt", "scam", "phishing", "rug pull"]):
        return "Security & Exploit Risk"
    if any(k in text_lower for k in ["etf", "etp", "blackrock", "fidelity", "21shares", "inflow", "outflow", "treasury", "institutional", "euronext", "custody"]):
        return "ETF & Institutional"
    if any(k in text_lower for k in ["sec", "lawsuit", "court", "ruling", "judge", "doj", "legal", "banned", "regulation", "regulatory", "subpoena", "wells notice"]):
        return "SEC & Regulation"
    if any(k in text_lower for k in ["fed", "fomc", "powell", "collins", "rate hike", "rate cut", "inflation", "cpi", "pmi", "treasury yield", "brent", "crude"]):
        return "Macro & Fed Policy"
    if any(k in text_lower for k in ["ai", "gpu", "bittensor", "render", "compute", "mainnet", "upgrade", "fork", "tokenomics"]):
        return "AI & Technology Upgrade"
    if any(k in text_lower for k in ["surge", "breakout", "ath", "liquidation", "short squeeze", "rally", "plunge", "dump"]):
        return "Market Structure & Momentum"
    return "Industry & Ecosystem"


def analyze_headline(title: str, summary: str = "", source: str = "") -> Dict[str, Any]:
    """Perform NLP sentiment and impact scoring on a single item."""
    full_text = f"{title} {summary}".lower()
    score = 0.0
    matches = []

    # Check bullish keywords
    for phrase, weight in BULLISH_KEYWORDS.items():
        if phrase in full_text:
            score += weight
            matches.append((phrase, weight))

    # Check bearish keywords
    for phrase, weight in BEARISH_KEYWORDS.items():
        if phrase in full_text:
            score += weight
            matches.append((phrase, weight))

    # Clamp raw score between -10.0 and +10.0
    clamped_score = max(-10.0, min(10.0, score))
    
    # Determine impact level
    abs_score = abs(clamped_score)
    if abs_score >= 6.5:
        impact = "HIGH"
    elif abs_score >= 3.0:
        impact = "MEDIUM"
    else:
        impact = "LOW"

    # Determine sentiment label
    if clamped_score >= 2.0:
        sentiment = "BULLISH"
    elif clamped_score <= -2.0:
        sentiment = "BEARISH"
    else:
        sentiment = "NEUTRAL"

    catalyst = classify_catalyst(full_text)
    assets = detect_assets(full_text)

    # Generate a brief AI tactical takeaway
    takeaway = generate_takeaway(title, sentiment, catalyst, assets)

    return {
        "score": round(clamped_score, 1),
        "sentiment": sentiment,
        "impact": impact,
        "catalyst": catalyst,
        "assets": assets,
        "takeaway": takeaway,
    }


def generate_takeaway(title: str, sentiment: str, catalyst: str, assets: List[str]) -> str:
    """Generate concise 1-sentence trader takeaway."""
    asset_str = ", ".join(assets) if assets and assets != ["ALL_CRYPTO"] else "Broad Market"
    
    if sentiment == "BULLISH":
        if catalyst == "ETF & Institutional":
            return f"Structural buy tailwind for {asset_str}; institutional liquidity entering."
        elif catalyst == "SEC & Regulation":
            return f"Regulatory de-risking catalyst; clears path for spot accumulation."
        elif catalyst == "AI & Technology Upgrade":
            return f"Strong momentum narrative for {asset_str}; look for intraday dip entries."
        return f"Bullish catalyst for {asset_str}; upside continuation supported."
    elif sentiment == "BEARISH":
        if catalyst == "Security & Exploit Risk":
            return f"High-risk alert on {asset_str}; exit exposure or avoid till verification."
        elif catalyst == "SEC & Regulation":
            return f"Regulatory headwind; defensive stance recommended on affected assets."
        elif catalyst == "Macro & Fed Policy":
            return f"Hawkish macro pressure; risk of liquidity drain on crypto beta."
        return f"Bearish friction on {asset_str}; tighten trailing stops."
    else:
        return f"Neutral development for {asset_str}; monitor order book and key levels."


def process_all_news(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process a list of news items and attach sentiment analysis."""
    enriched = []
    for art in articles:
        analysis = analyze_headline(art.get("title", ""), art.get("summary", ""), art.get("source", ""))
        merged = dict(art)
        merged.update(analysis)
        enriched.append(merged)
    return enriched


def calculate_asset_sentiment_map(enriched_news: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Compute aggregate sentiment score (-10 to +10) for each asset."""
    scores: Dict[str, List[float]] = {}
    high_impact_news: Dict[str, List[Dict[str, Any]]] = {}

    for item in enriched_news:
        item_score = item["score"]
        for asset in item.get("assets", []):
            if asset not in scores:
                scores[asset] = []
                high_impact_news[asset] = []
            scores[asset].append(item_score)
            if item.get("impact") in ["HIGH", "MEDIUM"]:
                high_impact_news[asset].append(item)

    asset_map = {}
    for asset, score_list in scores.items():
        if not score_list:
            continue
        avg_score = sum(score_list) / len(score_list)
        # Weight by maximum magnitude
        max_impact = max(score_list, key=lambda x: abs(x))
        combined = (avg_score * 0.5) + (max_impact * 0.5)
        
        asset_map[asset] = {
            "score": round(combined, 1),
            "mention_count": len(score_list),
            "top_news": high_impact_news[asset][:3],
        }

    return asset_map
