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

# Legacy CoinGecko ids (backup source only). Aptos, Fantom and Polygon removed:
# not tradable on Robinhood as of 2026-09-29.
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
    "near",
    "uniswap",
    "litecoin",
    "bitcoin-cash",
    "stellar",
    "aave",
    "ripple",
    "sui",
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
        "avalanche-2", "cardano", "sui"
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


# ----------------------------------------------------------------------------
# Robinhood crypto universe — primary market list.
# Verified against Robinhood's tradable USD pairs on 2026-09-29 (stablecoins
# and PAXG excluded; DOT and GRAM left out: CoinPaprika data for them is
# unreliable). symbol -> (CoinPaprika id, sector).
# Only coins in this map are shown on the site, so everything listed is
# buyable on Robinhood. Re-check when Robinhood adds or removes coins.
# ----------------------------------------------------------------------------
COINPAPRIKA_TICKERS = "https://api.coinpaprika.com/v1/tickers?quotes=USD"

RH_COINS = {
    # Mega caps
    "BTC": ("btc-bitcoin", "Mega Caps"),
    "ETH": ("eth-ethereum", "Mega Caps"),
    "SOL": ("sol-solana", "Mega Caps"),
    "XRP": ("xrp-xrp", "Mega Caps"),
    "BNB": ("bnb-binance-coin", "Mega Caps"),
    # Perp DEX
    "HYPE": ("hype-hyperliquid", "Perp DEX & L1"),
    "ASTER": ("aster-aster", "Perp DEX & L1"),
    "LIT": ("lit-lighter", "Perp DEX & L1"),
    "AVNT": ("avantis", "Perp DEX & L1"),
    # Layer 1 / 2
    "AVAX": ("avax-avalanche", "Layer 1 / 2"),
    "ADA": ("ada-cardano", "Layer 1 / 2"),
    "SUI": ("sui-sui", "Layer 1 / 2"),
    "NEAR": ("near-near-protocol", "Layer 1 / 2"),
    "SEI": ("sei-sei", "Layer 1 / 2"),
    "ALGO": ("algo-algorand", "Layer 1 / 2"),
    "HBAR": ("hbar-hedera-hashgraph", "Layer 1 / 2"),
    "XLM": ("xlm-stellar", "Layer 1 / 2"),
    "ATOM": ("atom-cosmos", "Layer 1 / 2"),
    "LTC": ("ltc-litecoin", "Layer 1 / 2"),
    "BCH": ("bch-bitcoin-cash", "Layer 1 / 2"),
    "ETC": ("etc-ethereum-classic", "Layer 1 / 2"),
    "ZEC": ("zec-zcash", "Layer 1 / 2"),
    "XTZ": ("xtz-tezos", "Layer 1 / 2"),
    "ARB": ("arb-arbitrum", "Layer 1 / 2"),
    "OP": ("op-optimism", "Layer 1 / 2"),
    "STRK": ("strk-starknet", "Layer 1 / 2"),
    "MNT": ("mnt-mantle", "Layer 1 / 2"),
    "IMX": ("imx-immutable-x", "Layer 1 / 2"),
    "MEGA": ("mega-megaeth", "Layer 1 / 2"),
    "XPL": ("xpl-plasma", "Layer 1 / 2"),
    "CC": ("cc-canton-network", "Layer 1 / 2"),
    "FLR": ("flr-flare-network", "Layer 1 / 2"),
    "XCN": ("xcn-chain", "Layer 1 / 2"),
    "SKR": ("skr-seeker", "Layer 1 / 2"),
    # DeFi & infra
    "AAVE": ("aave-new", "DeFi"),
    "UNI": ("uni-uniswap", "DeFi"),
    "CRV": ("crv-curve-dao-token", "DeFi"),
    "COMP": ("comp-compoundd", "DeFi"),
    "LDO": ("ldo-lido-dao", "DeFi"),
    "MORPHO": ("morpho-morpho", "DeFi"),
    "AERO": ("aero-aerodrome-finance", "DeFi"),
    "SYRUP": ("syrup-syrup-token", "DeFi"),
    "ENA": ("ena-ethena", "DeFi"),
    "ONDO": ("ondo-ondo", "DeFi"),
    "SKY": ("sky-sky", "DeFi"),
    "SNX": ("snx-synthetix-network-token", "DeFi"),
    "RAY": ("ray-raydium", "DeFi"),
    "ORCA": ("orca-orca", "DeFi"),
    "JTO": ("jto-jito", "DeFi"),
    "PYTH": ("pyth-pyth-network", "DeFi"),
    "LINK": ("link-chainlink", "DeFi"),
    "QNT": ("qnt-quant", "DeFi"),
    "ZRO": ("zro-layerzero", "DeFi"),
    "W": ("w-wormhole", "DeFi"),
    "EIGEN": ("eigen-eigenlayer", "DeFi"),
    "ZRX": ("zrx-0x", "DeFi"),
    "GRT": ("grt-the-graph", "DeFi"),
    "WLFI": ("wlfi-official-world-liberty-financial", "DeFi"),
    "CHIP": ("chip-usdai", "DeFi"),
    "RE": ("re-re", "DeFi"),
    "BILL": ("bill-billions-network", "DeFi"),
    # AI & data
    "FET": ("fetch-ai", "AI & Data"),
    "RENDER": ("rndr-render-token", "AI & Data"),
    "VIRTUAL": ("virtual-virtual-protocol", "AI & Data"),
    "WLD": ("wld-worldcoin", "AI & Data"),
    "VVV": ("vvv-venice-token", "AI & Data"),
    "BIO": ("bio-bio-protocol", "AI & Data"),
    "SENT": ("sent-sentient", "AI & Data"),
    # Gaming / consumer
    "AXS": ("axs-axie-infinity", "Gaming & Consumer"),
    "BAT": ("bat-basic-attention-token", "Gaming & Consumer"),
    "ZORA": ("zora-zora", "Gaming & Consumer"),
    # Memes
    "DOGE": ("doge-dogecoin", "Memes"),
    "SHIB": ("shib-shiba-inu", "Memes"),
    "PEPE": ("pepe-pepe", "Memes"),
    "BONK": ("bonk-bonk", "Memes"),
    "WIF": ("wif-dogwifcoin", "Memes"),
    "FLOKI": ("floki-floki-inu", "Memes"),
    "PENGU": ("pengu-pudgy-penguins", "Memes"),
    "TRUMP": ("trump-official-trump", "Memes"),
    "POPCAT": ("popcat-popcat", "Memes"),
    "MEW": ("mew-cat-in-a-dogs-world", "Memes"),
    "MOODENG": ("moodeng-moo-deng-moodengsolcom", "Memes"),
    "PNUT": ("pnut-peanut-the-squirrel", "Memes"),
    "CASHCAT": ("cashcat-cash-cat", "Memes"),
}
RH_PAPRIKA_IDS = {v[0]: k for k, v in RH_COINS.items()}

# Momentum board: minimum liquidity so thin coins can't top the list on noise.
MOMENTUM_MIN_VOLUME = 10_000_000   # $ traded in 24h
MOMENTUM_MIN_MCAP = 100_000_000
