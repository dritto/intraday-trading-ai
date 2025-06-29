import logging
import sys
from pathlib import Path
from tvDatafeed import Interval
import pandas as pd

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_fetcher import DataFetcher
from src.analysis.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands

# Configure a basic logger for the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test_fetch():
    """
    An example script to initialize the DataFetcher, fetch sample data,
    and run a basic analysis (RSI calculation).
    """
    logger.info("--- Starting Data Fetch & Analysis Test ---")

    try:
        # Initialize DataFetcher. It will read the config and select the provider internally.
        data_fetcher = DataFetcher()

        # Define the parameters for the data fetch
        symbol = 'RELIANCE'
        exchange = 'NSE'
        interval = Interval.in_1_hour
        bars = 200  # Fetching more bars for a stable RSI calculation

        # Fetch the historical data
        reliance_data = data_fetcher.fetch_historical_data(symbol, exchange, interval, n_bars=bars)

        if reliance_data is not None:
            logger.info(f"Successfully fetched data for {symbol}.")

            data_with_indicators = reliance_data.copy()

            # Calculate RSI
            data_with_indicators = calculate_rsi(data_with_indicators)
            # Calculate MACD
            data_with_indicators = calculate_macd(data_with_indicators)
            # Calculate Bollinger Bands
            data_with_indicators = calculate_bollinger_bands(data_with_indicators)

            logger.info(f"Calculated indicators for {symbol}. Displaying last 5 rows:")
            # Displaying tail to see the latest RSI values
            print(data_with_indicators.tail())
        else:
            logger.warning(f"Failed to fetch data for {symbol}. Please check logs for details.")

    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Configuration or Setup Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the test run: {e}")

if __name__ == "__main__":
    run_test_fetch()