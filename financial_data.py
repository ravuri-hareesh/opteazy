import yfinance as yf
import requests
from bs4 import BeautifulSoup
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("FinancialData")

def fetch_from_yahoo() -> Optional[Dict[str, Any]]:
    """Primary fetch from Yahoo Finance."""
    symbols = {
        "USD_INR": "INR=X",
        "WTI_Crude": "CL=F",
        "Brent_Crude": "BZ=F"
    }
    results = {}
    try:
        for name, sym in symbols.items():
            ticker = yf.Ticker(sym)
            info = ticker.info
            price = info.get("regularMarketPrice") or info.get("previousClose")
            
            if not price:
                # Fallback to history for last close
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            results[name] = price
            # Store full data for MongoDB dump
            results[f"{name}_full"] = info
        
        results["source"] = "Yahoo Finance"
        results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return results
    except Exception as e:
        logger.error(f"Yahoo Finance fetch failed: {e}")
        return None

def fetch_from_google() -> Optional[Dict[str, Any]]:
    """Backup fetch from Google Finance scraping."""
    # Note: Scrapers are brittle, but this is a backup as requested
    urls = {
        "USD_INR": "https://www.google.com/finance/quote/USD-INR",
        "WTI_Crude": "https://www.google.com/finance/quote/CLW00:NYMEX",
        "Brent_Crude": "https://www.google.com/finance/quote/LCO00:ICEEUR"
    }
    results = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        for name, url in urls.items():
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Find the price element (Google uses classes like 'YMl7A' which change, 
                # but we can look for data-last-price or specific structure)
                price_div = soup.find('div', {'class': 'YMl7A'})
                if price_div:
                    price = float(price_div.text.replace(',', ''))
                    results[name] = price
                else:
                    # Fallback to meta tags
                    meta_price = soup.find('meta', {'itemprop': 'price'})
                    if meta_price:
                        results[name] = float(meta_price['content'])
        
        if results:
            results["source"] = "Google Finance"
            results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return results
        return None
    except Exception as e:
        logger.error(f"Google Finance fetch failed: {e}")
        return None

def fetch_market_indicators_orchestrator() -> Dict[str, Any]:
    """Primary Yahoo -> Backup Google Finance."""
    data = fetch_from_yahoo()
    if not data or not all(k in data for k in ["USD_INR", "WTI_Crude", "Brent_Crude"]):
        logger.warning("Yahoo fetch incomplete, attempting Google Finance...")
        google_data = fetch_from_google()
        if google_data:
            return google_data
    return data

def run_indicator_service(db_manager, stop_event):
    """Background loop to fetch indicators every 5 minutes."""
    from data_manager import get_current_date_str
    
    logger.info("Financial Indicator Service Started (5m interval)")
    while not stop_event.is_set():
        try:
            data = fetch_market_indicators_orchestrator()
            if data:
                date_str = get_current_date_str()
                db_manager.save_market_indicators(data, date_str)
                logger.info(f"Updated Market Indicators: USD/INR={data.get('USD_INR')}")
        except Exception as e:
            logger.error(f"Error in indicator service loop: {e}")
        
        # Wait 5 minutes, checking stop_event every second
        for _ in range(300):
            if stop_event.is_set():
                break
            time.sleep(1)
