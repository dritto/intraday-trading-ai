import logging
import requests
import time

logger = logging.getLogger(__name__)

# This is the API endpoint used by the official Nifty Indices website to load index data.
BASE_URL = "https://www.niftyindices.com/api/equity-stockWatch-data?index="

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
}

# Maps the symbols used in our app (from Angel One) to the names required by the Nifty Indices API.
API_INDEX_NAME_MAP = {
    "BANKNIFTY": "NIFTY BANK",
    "FINNIFTY": "NIFTY FINANCIAL SERVICES",
    "NIFTY PVT BANK": "NIFTY PRIVATE BANK"
}

def get_index_constituents(index_name: str) -> list[str]:
    """
    Fetches the list of constituent stock symbols for a given Nifty index by scraping the website's API.

    Args:
        index_name (str): The name of the index (e.g., "BANKNIFTY", "NIFTY AUTO").

    Returns:
        list[str]: A list of stock symbols, or an empty list on failure.
    """
    # Use the mapped name if available, otherwise use the original name.
    api_index_name = API_INDEX_NAME_MAP.get(index_name, index_name)
    
    # The API URL requires spaces to be encoded as '%20'. `requests` handles this, but we do it for clarity.
    url_encoded_index = api_index_name.replace(' ', '%20')
    url = f"{BASE_URL}{url_encoded_index}"
    
    logger.info(f"Fetching constituents for index: '{api_index_name}'")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        data = response.json().get('data', [])
        if not data:
            logger.warning(f"No constituent data found for index: {api_index_name}")
            return []
            
        symbols = [item['symbol'] for item in data]
        logger.info(f"Found {len(symbols)} constituents for {api_index_name}.")
        return symbols
        
    except requests.RequestException as e:
        logger.error(f"Error fetching constituents for {api_index_name}: {e}")
        return []