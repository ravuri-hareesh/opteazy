import requests
import random
import time
import logging
from typing import Optional, Dict, Any

# --- LOGGING ---
logger = logging.getLogger("Spot_Utils")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

def get_nifty_spot_fresh() -> Optional[float]:
    """
    Robustly fetches the NIFTY 50 spot price using multiple fresh sources.
    Prioritizes NSE's allIndices API over individual index quote endpoints which can be stale.
    """
    # Tier 1: Direct NSE allIndices API (Most Reliable for live market)
    try:
        session = requests.Session()
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        # Clear cookies by visiting homepage first
        session.get("https://www.nseindia.com/", headers=headers, timeout=10)
        
        api_headers = {
            **headers,
            "Accept": "*/*",
            "Referer": "https://www.nseindia.com/market-data/live-equity-market",
            "X-Requested-With": "XMLHttpRequest"
        }
        response = session.get("https://www.nseindia.com/api/allIndices", headers=api_headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for index in data.get("data", []):
                if index.get("index") == "NIFTY 50":
                    price = float(str(index.get("last")).replace(",", ""))
                    logger.info(f"Retrieved NIFTY 50 spot from direct API: {price} (TS: {data.get('timestamp')})")
                    return price
    except Exception as e:
        logger.warning(f"Direct API fetch failed: {e}")

    # Tier 2: nsetools Fallback
    try:
        from nsetools import Nse
        nse = Nse()
        index_data = nse.get_index_quote("NIFTY 50")
        if index_data and index_data.get("lastPrice"):
            price = float(str(index_data.get("lastPrice")).replace(",", ""))
            logger.info(f"Retrieved NIFTY 50 spot from nsetools: {price}")
            return price
    except Exception as e:
        logger.warning(f"nsetools fetch failed: {e}")

    # Tier 3: nsepython stale fallback (only if both Tier 1 and 2 fail)
    try:
        from nsepython import nse_get_index_quote
        data = nse_get_index_quote("NIFTY 50")
        if isinstance(data, dict):
            raw_val = data.get('last') or data.get('lastPrice') or data.get('underlyingValue')
            if raw_val:
                # Log warning because this source is often stale
                price = float(str(raw_val).replace(",", ""))
                logger.warning(f"CRITICAL: Falling back to potentially STALE nsepython spot: {price} (TS: {data.get('timeVal')})")
                return price
    except Exception as e:
        logger.error(f"Legacy stale fallback failed: {e}")

    return None

def get_stock_spot_fresh(symbol: str) -> Optional[float]:
    """Robustly fetches the spot price for a given stock symbol."""
    # Tier 1: nsepython ltp
    try:
        from nsepython import nse_quote_ltp
        price = nse_quote_ltp(symbol)
        if price:
            return float(str(price).replace(",", ""))
    except: pass

    # Tier 2: nsetools
    try:
        from nsetools import Nse
        nse = Nse()
        quote = nse.get_quote(symbol)
        if quote and quote.get("lastPrice"):
            return float(str(quote.get("lastPrice")).replace(",", ""))
    except: pass

    return None
