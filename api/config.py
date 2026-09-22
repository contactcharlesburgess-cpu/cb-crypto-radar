"""
Configuration for AI Crypto News & Sentiment Screener (Vercel & Local).
Exclusively tracks cryptocurrencies supported and tradable on Robinhood.
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

# Whitelist of all cryptocurrencies officially available on Robinhood
ROBINHOOD_COIN_IDS = [
    "bitcoin",
    "ethereum",
    "solana",
    "ripple",
    "dogecoin",
    "cardano",
    "avalanche-2",
    "shiba-inu",
    "pepe",
    "chainlink",
    "uniswap",
    "litecoin",
    "bitcoin-cash",
    "near",
    "sui",
    "stellar",
    "aave",
    "ethereum-classic",
    "compound-governance-token",
    "bonk",
    "dogwifcoin",
    "polygon-ecosystem-token",
    "arbitrum",
    "optimism",
    "render-token",
    "fetch-ai",
    "tezos",
    "cosmos",
    "filecoin",
    "polkadot",
    "injective-protocol",
]

FEEDS = {
    "forex_factory": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "financial_juice": "https://www.financialjuice.com/feed.ashx",
    "cointelegraph": "https://cointelegraph.com/rss",
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "decrypt": "https://decrypt.co/feed",
    "fear_and_greed": "https://api.alternative.me/fng/?limit=2",
    "coingecko_markets": (
        "https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency=usd&ids={','.join(ROBINHOOD_COIN_IDS)}"
        "&order=market_cap_desc&sparkline=false&price_change_percentage=24h,7d"
    ),
}

# Robinhood-specific sector classification
SECTORS = {
    "AI & Compute": ["render-token", "fetch-ai", "near"],
    "Mega Caps": ["bitcoin", "ethereum", "solana"],
    "Layer 1 / 2": [
        "ripple", "cardano", "avalanche-2", "sui", "polygon-ecosystem-token",
        "arbitrum", "optimism", "polkadot", "cosmos", "injective-protocol",
        "filecoin", "ethereum-classic", "tezos"
    ],
    "DeFi": ["uniswap", "aave", "chainlink", "compound-governance-token"],
    "Memes": ["dogecoin", "shiba-inu", "pepe", "bonk", "dogwifcoin"],
    "Payments & PoW": ["litecoin", "bitcoin-cash", "stellar"],
}

SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "SUI": "sui",
    "XLM": "stellar",
    "AAVE": "aave",
    "ETC": "ethereum-classic",
    "COMP": "compound-governance-token",
    "BONK": "bonk",
    "WIF": "dogwifcoin",
    "POL": "polygon-ecosystem-token",
    "ARB": "arbitrum",
    "OP": "optimism",
    "RENDER": "render-token",
    "FET": "fetch-ai",
    "XTZ": "tezos",
    "ATOM": "cosmos",
    "FIL": "filecoin",
    "DOT": "polkadot",
    "INJ": "injective-protocol",
}

ID_TO_SYMBOL = {v: k for k, v in SYMBOL_TO_ID.items()}

SIGNAL_THRESHOLDS = {
    "STRONG_BUY": 74,
    "DIP_ENTRY": 58,
    "HOLD": 43,
    "TIGHTEN_STOPS": 28,
    "DEFENSIVE_EXIT": 0,
}
