"""
Configuration for AI Crypto News & Sentiment Screener (Vercel & Local).
Defines endpoints, monitored assets, sector categorization, and signal thresholds.
Tracks Robinhood cryptocurrencies + Hyperliquid L1/Perp DEX.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

# On Vercel serverless environment, filesystem is read-only except /tmp
if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp")
else:
    DATA_DIR = BASE_DIR / "data"

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

PORT = 5080
CACHE_TTL_SECONDS = 30  # 30-second cache for high-frequency live updates

# Monitored cryptocurrencies (Robinhood tradable + Hyperliquid L1)
ROBINHOOD_COIN_IDS = [
    "hyperliquid",
    "bitcoin",
    "ethereum",
    "solana",
    "dogecoin",
    "shiba-inu",
    "pepe",
    "bonk",
    "dogwifcoin",
    "avalanche-2",
    "cardano",
    "chainlink",
    "polygon-ecosystem-token",
    "near",
    "uniswap",
    "litecoin",
    "bitcoin-cash",
    "stellar",
    "aave",
    "ripple",
    "sui",
    "aptos",
    "fantom",
    "render-token",
    "fetch-ai",
    "compound-governance-token",
    "injective-protocol",
]

# Asset exchange tags
EXCHANGE_TAGS = {
    "hyperliquid": "Hyperliquid L1",
}

# Endpoints
FEEDS = {
    "forex_factory": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "financial_juice": "https://www.financialjuice.com/feed.ashx",
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "decrypt": "https://decrypt.co/feed",
    "fear_and_greed": "https://api.alternative.me/fng/?limit=7",
    "cryptocompare_news": "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
    "coingecko_markets": (
        "https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency=usd&ids={','.join(ROBINHOOD_COIN_IDS)}"
        "&order=market_cap_desc&sparkline=false&price_change_percentage=24h,7d"
    ),
    "hyperliquid_info": "https://api.hyperliquid.xyz/info",
}

# Sector classification
SECTORS = {
    "Perp DEX & L1": ["hyperliquid"],
    "AI & Compute": ["render-token", "fetch-ai", "near"],
    "Mega Caps": ["bitcoin", "ethereum", "solana"],
    "Layer 1 / 2": [
        "avalanche-2", "cardano", "polygon-ecosystem-token",
        "sui", "aptos", "fantom"
    ],
    "DeFi": ["uniswap", "aave", "chainlink", "compound-governance-token"],
    "Memes": ["dogecoin", "shiba-inu", "pepe", "bonk", "dogwifcoin"],
    "Payments & Pow": ["litecoin", "bitcoin-cash", "stellar"],
}

SYMBOL_TO_ID = {
    "HYPE": "hyperliquid",
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "BONK": "bonk",
    "WIF": "dogwifcoin",
    "AVAX": "avalanche-2",
    "ADA": "cardano",
    "LINK": "chainlink",
    "POL": "polygon-ecosystem-token",
    "MATIC": "polygon-ecosystem-token",
    "NEAR": "near",
    "UNI": "uniswap",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "XLM": "stellar",
    "AAVE": "aave",
    "XRP": "ripple",
    "SUI": "sui",
    "APT": "aptos",
    "FTM": "fantom",
    "RENDER": "render-token",
    "FET": "fetch-ai",
    "COMP": "compound-governance-token",
    "INJ": "injective-protocol",
}

ID_TO_SYMBOL = {v: k for k, v in SYMBOL_TO_ID.items()}

# Charles Burgess Active Portfolio Defaults
PORTFOLIO_CONFIG = {
    "hype": {
        "symbol": "HYPE",
        "name": "Hyperliquid",
        "entry_price": 93.11,
        "tokens": 39.970,
        "cost_basis": 3580.0,
        "stop_loss": 89.633,
        "target_1": 120.00,
        "target_2": 150.00,
        "exchange": "Hyperliquid Perp DEX",
        "thesis": "Perp DEX cash flow titan with 100% buyback/burn tokenomics. Defending $89.633 demand shield.",
    },
    "sol": {
        "symbol": "SOL",
        "name": "Solana",
        "entry_price": 114.40,
        "tokens": 15.58619,
        "cost_basis": 1800.0,
        "stop_loss": 108.50,
        "target_1": 125.00,
        "target_2": 140.00,
        "target_3": 180.00,
        "exchange": "Robinhood Crypto",
        "thesis": "High-throughput L1 blue-chip. Filled at $114.40 discount shelf; targeting $125 swing and $140 breakout.",
    },
    "meta": {
        "symbol": "META",
        "name": "Meta Platforms",
        "entry_price": 769.31,
        "shares": 0.25997,
        "cost_basis": 200.0,
        "stop_loss": None,
        "target_1": 850.00,
        "target_2": 1000.00,
        "exchange": "Robinhood Equities",
        "thesis": "Permanent compounding investment (3.2B users, Llama AI open-source moat, huge buybacks). No stop loss.",
    }
}

# Signal Thresholds (0 to 100 Scale)
SIGNAL_THRESHOLDS = {
    "STRONG_BUY": 74,       # Clear catalyst + favorable momentum
    "DIP_ENTRY": 58,        # Positive sentiment, buy support/iFVG pullback
    "HOLD": 43,             # Choppy/neutral, wait for trigger
    "TIGHTEN_STOPS": 28,    # Warning signs, lock in profits
    "DEFENSIVE_EXIT": 0,    # Severe negative catalyst / exploit / macro shock
}
