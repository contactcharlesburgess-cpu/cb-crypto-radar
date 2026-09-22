"""
Data fetcher module for Crypto AI Screener.
Aggregates data from Forex Factory, FinancialJuice, CoinDesk, Cointelegraph,
Decrypt, Alternative.me (Fear & Greed), and CoinGecko.
"""

import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import config

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

# In-memory and persistent disk cache
_CACHE: Dict[str, Any] = {}
_CACHE_TIMESTAMP: float = 0
CACHE_FILE = config.DATA_DIR / "cache.json"


def load_disk_cache() -> Optional[Dict[str, Any]]:
    """Load cached data from disk if available."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return None


def save_disk_cache(data: Dict[str, Any]):
    """Save data snapshot to disk cache."""
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Error saving cache to disk: {e}")


def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Safely fetch URL content with User-Agent header."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, application/xml, text/xml, */*",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"[WARN] HTTP {e.code} fetching {url}")
        return None
    except Exception as e:
        print(f"[WARN] Error fetching {url}: {e}")
        return None


def fetch_forex_factory() -> List[Dict[str, Any]]:
    """Fetch and parse Forex Factory calendar for this week."""
    raw = fetch_url(config.FEEDS["forex_factory"])
    if not raw:
        return []
    try:
        events = json.loads(raw)
        parsed = []
        now_iso = datetime.now(timezone.utc).isoformat()
        
        for ev in events:
            # We focus on USD, EUR, GBP, JPY, CAD
            country = ev.get("country", "")
            impact = ev.get("impact", "Low")
            title = ev.get("title", "")
            date_str = ev.get("date", "")
            forecast = ev.get("forecast", "")
            previous = ev.get("previous", "")
            
            parsed.append({
                "title": title,
                "country": country,
                "date": date_str,
                "impact": impact,
                "forecast": forecast,
                "previous": previous,
                "is_usd": country == "USD",
                "is_high_impact": impact in ["High", "Holiday"],
            })
        return parsed
    except Exception as e:
        print(f"[WARN] Error parsing Forex Factory: {e}")
        return []


def clean_html(text: str) -> str:
    """Strip HTML tags and unescape common XML entities."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Collapse multiple spaces
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def parse_rss_feed(xml_text: str, source_name: str) -> List[Dict[str, Any]]:
    """Generic XML RSS parser returning normalized articles."""
    articles = []
    if not xml_text:
        return articles
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            # Handle Atom or direct root
            items = root.findall(".//item")
        else:
            items = channel.findall("item")

        for item in items:
            title_node = item.find("title")
            link_node = item.find("link")
            desc_node = item.find("description")
            date_node = item.find("pubDate")
            author_node = item.find("author")
            if author_node is None:
                author_node = item.find("{http://purl.org/dc/elements/1.1/}creator")

            title = clean_html(title_node.text if title_node is not None else "")
            # Sometimes FinancialJuice prepends 'FinancialJuice: '
            if title.startswith("FinancialJuice:"):
                title = title.replace("FinancialJuice:", "").strip()

            link = link_node.text.strip() if link_node is not None and link_node.text else ""
            desc = clean_html(desc_node.text if desc_node is not None else "")
            pub_date = date_node.text.strip() if date_node is not None and date_node.text else ""
            author = author_node.text.strip() if author_node is not None and author_node.text else source_name

            if title:
                articles.append({
                    "title": title,
                    "summary": desc,
                    "link": link,
                    "pubDate": pub_date,
                    "source": source_name,
                    "author": author,
                })
    except Exception as e:
        print(f"[WARN] Error parsing RSS for {source_name}: {e}")
    return articles


def fetch_financial_juice() -> List[Dict[str, Any]]:
    """Fetch FinancialJuice real-time breaking market squawk feed."""
    raw = fetch_url(config.FEEDS["financial_juice"])
    return parse_rss_feed(raw, "FinancialJuice")


def fetch_crypto_news() -> List[Dict[str, Any]]:
    """Fetch and merge CoinTelegraph, CoinDesk, and Decrypt feeds."""
    articles = []
    
    ct_raw = fetch_url(config.FEEDS["cointelegraph"])
    articles.extend(parse_rss_feed(ct_raw, "CoinTelegraph"))

    cd_raw = fetch_url(config.FEEDS["coindesk"])
    articles.extend(parse_rss_feed(cd_raw, "CoinDesk"))

    dc_raw = fetch_url(config.FEEDS["decrypt"])
    articles.extend(parse_rss_feed(dc_raw, "Decrypt"))

    # Deduplicate by title similarity
    seen_titles = set()
    unique_articles = []
    for art in articles:
        norm = re.sub(r"[^a-zA-Z0-9]", "", art["title"].lower())[:40]
        if norm and norm not in seen_titles:
            seen_titles.add(norm)
            unique_articles.append(art)
            
    return unique_articles


def fetch_fear_and_greed() -> Dict[str, Any]:
    """Fetch current and previous Fear & Greed index."""
    raw = fetch_url(config.FEEDS["fear_and_greed"])
    default = {
        "value": 50,
        "classification": "Neutral",
        "prev_value": 50,
        "prev_classification": "Neutral",
    }
    if not raw:
        return default
    try:
        data = json.loads(raw)
        items = data.get("data", [])
        if items:
            current = items[0]
            prev = items[1] if len(items) > 1 else current
            return {
                "value": int(current.get("value", 50)),
                "classification": current.get("value_classification", "Neutral"),
                "prev_value": int(prev.get("value", 50)),
                "prev_classification": prev.get("value_classification", "Neutral"),
            }
    except Exception as e:
        print(f"[WARN] Error parsing Fear & Greed: {e}")
    return default


def fetch_coingecko_markets() -> List[Dict[str, Any]]:
    """Fetch live top 60 crypto markets from CoinGecko."""
    raw = fetch_url(config.FEEDS["coingecko_markets"])
    if not raw:
        return []
    try:
        coins = json.loads(raw)
        cleaned = []
        for c in coins:
            coin_id = c.get("id", "")
            symbol = c.get("symbol", "").upper()
            
            # Identify sector
            sector = "Altcoins"
            for sec_name, coin_ids in config.SECTORS.items():
                if coin_id in coin_ids:
                    sector = sec_name
                    break
            
            cleaned.append({
                "id": coin_id,
                "symbol": symbol,
                "name": c.get("name", ""),
                "price": c.get("current_price", 0.0),
                "market_cap": c.get("market_cap", 0),
                "rank": c.get("market_cap_rank", 999),
                "volume_24h": c.get("total_volume", 0),
                "high_24h": c.get("high_24h", 0.0),
                "low_24h": c.get("low_24h", 0.0),
                "change_24h": c.get("price_change_percentage_24h", 0.0) or 0.0,
                "change_7d": c.get("price_change_percentage_7d_in_currency", 0.0) or 0.0,
                "image": c.get("image", ""),
                "sector": sector,
            })
        return cleaned
    except Exception as e:
        print(f"[WARN] Error parsing CoinGecko: {e}")
        return []


def get_all_data(force_refresh: bool = False) -> Dict[str, Any]:
    """Retrieve all unified market and news feeds with caching and fallback."""
    global _CACHE, _CACHE_TIMESTAMP
    now = time.time()
    
    # 1. Check in-memory cache
    if not force_refresh and _CACHE and (now - _CACHE_TIMESTAMP < config.CACHE_TTL_SECONDS):
        return _CACHE

    # 2. Check disk cache
    disk_cached = load_disk_cache()
    if not force_refresh and disk_cached:
        cached_ts = disk_cached.get("_cached_at", 0)
        if now - cached_ts < config.CACHE_TTL_SECONDS:
            _CACHE = disk_cached
            _CACHE_TIMESTAMP = cached_ts
            return _CACHE

    print("[INFO] Refreshing feeds from network...")
    ff_events = fetch_forex_factory()
    fj_squawk = fetch_financial_juice()
    crypto_news = fetch_crypto_news()
    fng = fetch_fear_and_greed()
    markets = fetch_coingecko_markets()

    # Fallback to previous disk cache or seed data if an API rate-limited (e.g. 429)
    seed_file = config.DATA_DIR / "seed_macro.json"
    seed_data = {}
    if seed_file.exists():
        try:
            with open(seed_file, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
        except Exception:
            pass

    if not ff_events:
        if disk_cached and disk_cached.get("forex_factory"):
            ff_events = disk_cached["forex_factory"]
            print("[INFO] Used disk cached Forex Factory events.")
        elif seed_data.get("forex_factory"):
            ff_events = seed_data["forex_factory"]
            print("[INFO] Used seed Forex Factory calendar.")

    if not fj_squawk:
        if disk_cached and disk_cached.get("financial_juice"):
            fj_squawk = disk_cached["financial_juice"]
            print("[INFO] Used disk cached FinancialJuice headlines.")
        elif seed_data.get("financial_juice"):
            fj_squawk = seed_data["financial_juice"]
            print("[INFO] Used seed FinancialJuice headlines.")

    if not crypto_news and disk_cached and disk_cached.get("crypto_news"):
        crypto_news = disk_cached["crypto_news"]
    if not markets and disk_cached and disk_cached.get("markets"):
        markets = disk_cached["markets"]

    _CACHE = {
        "_cached_at": now,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "forex_factory": ff_events,
        "financial_juice": fj_squawk,
        "crypto_news": crypto_news,
        "fear_and_greed": fng,
        "markets": markets,
    }
    _CACHE_TIMESTAMP = now

    save_disk_cache(_CACHE)
    return _CACHE


if __name__ == "__main__":
    print("Testing data fetcher...")
    data = get_all_data(force_refresh=True)
    print(f"Forex Factory events: {len(data['forex_factory'])}")
    print(f"FinancialJuice headlines: {len(data['financial_juice'])}")
    print(f"Crypto news articles: {len(data['crypto_news'])}")
    print(f"Fear & Greed: {data['fear_and_greed']}")
    print(f"CoinGecko markets: {len(data['markets'])}")
