"""
Configuration for AI Crypto News & Sentiment Screener (Vercel & Local).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

# On Vercel, only /tmp is writable
if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp")
else:
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

PORT = 5080
CACHE_TTL_SECONDS = 30  # High-frequency 30-second cache

FEEDS = {
    "forex_factory": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "financial_juice": "https://www.financialjuice.com/feed.ashx",
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "decrypt": "https://decrypt.co/feed",
    "fear_and_greed": "https://api.alternative.me/fng/?limit=2",
    "coingecko_markets": (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&order=market_cap_desc&per_page=60&page=1"
        "&sparkline=false&price_change_percentage=24h,7d"
    ),
}

SECTORS = {
    "AI Sector": ["near", "bittensor", "render-token", "fetch-ai", "artificial-superintelligence-alliance", "internet-computer", "akash-network"],
    "Mega Caps": ["bitcoin", "ethereum", "solana"],
    "Layer 1 / 2": ["binancecoin", "ripple", "cardano", "avalanche-2", "sui", "aptos", "arbitrum", "optimism", "polkadot"],
    "DeFi": ["uniswap", "aave", "chainlink", "maker", "synthetix-network-token"],
    "Memes": ["dogecoin", "shiba-inu", "pepe", "dogwifhat", "bonk"],
}

SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "NEAR": "near",
    "TAO": "bittensor",
    "RENDER": "render-token",
    "FET": "fetch-ai",
    "ASI": "artificial-superintelligence-alliance",
    "ICP": "internet-computer",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "SUI": "sui",
    "APT": "aptos",
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "WIF": "dogwifhat",
    "LINK": "chainlink",
    "AAVE": "aave",
    "UNI": "uniswap",
}

ID_TO_SYMBOL = {v: k for k, v in SYMBOL_TO_ID.items()}

SIGNAL_THRESHOLDS = {
    "STRONG_BUY": 74,
    "DIP_ENTRY": 58,
    "HOLD": 43,
    "TIGHTEN_STOPS": 28,
    "DEFENSIVE_EXIT": 0,
}
