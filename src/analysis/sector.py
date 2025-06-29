import logging
import pandas as pd
import time

from src.execution.angelone_executor import AngelOneExecutor

logger = logging.getLogger(__name__)

class SectorAnalysis:
    """
    Fetches and analyzes sector-wide performance data using the Angel One API.
    This helps in identifying which sectors are showing strength or weakness.
    """

    def __init__(self, executor: AngelOneExecutor):
        """
        Initializes the SectorAnalysis class.

        Args:
            data_fetcher (DataFetcher): An instance of the data fetcher to get index data.
        """
        self.executor = executor
        self.sector_indices = [
            "NIFTY AUTO", "BANKNIFTY", "NIFTY FMCG", "NIFTY IT",
            "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA", "NIFTY PSU BANK",
            "NIFTY REALTY", "NIFTY PVT BANK", "FINNIFTY",
            "NIFTY CONSUMPTION", "NIFTY ENERGY"
            # Note: Healthcare, Cnsmp Dur, and Oil & Gas have been mapped to available equivalents.
        ]

    def fetch_sector_data(self) -> pd.DataFrame:
        """
        Fetches the latest performance data for all sectors using the AngelOneExecutor.
        Includes retry logic and delays to handle connection issues.

        Returns:
            pd.DataFrame: A DataFrame containing sector performance data, or an empty DataFrame on failure.
        """
        logger.info(f"Fetching performance data for {len(self.sector_indices)} sectors via Angel One...")
        sector_performance = []
        max_retries = 3
        retry_delay_seconds = 2

        for index_symbol in self.sector_indices:
            quote = None
            for attempt in range(max_retries):
                try:
                    quote = self.executor.get_ltp_data(name=index_symbol)
                    if quote and 'ltp' in quote and 'close' in quote:
                        break  # Success, exit retry loop
                    else:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries}: No data for {index_symbol}.")
                        quote = None # Ensure data is None if fetch failed
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1}/{max_retries}: Exception for {index_symbol}: {e}")
                    quote = None # Ensure data is None on exception

                if attempt < max_retries - 1:
                    logger.info(f"Retrying for {index_symbol} in {retry_delay_seconds} seconds...")
                    time.sleep(retry_delay_seconds)

            if quote:
                ltp = quote['ltp']
                prev_close = quote['close'] # This is previous day's close from the API
                if prev_close > 0:
                    pct_change = ((ltp - prev_close) / prev_close) * 100
                    sector_performance.append({'Index Name': index_symbol, '% Change': pct_change})
                else:
                    logger.warning(f"Previous day close is 0 for {index_symbol}, cannot calculate change.")
            else:
                logger.error(f"Failed to fetch data for {index_symbol} after {max_retries} attempts.")

        if not sector_performance:
            logger.error("Failed to fetch performance data for any sector.")
            return pd.DataFrame()
        
        df = pd.DataFrame(sector_performance)
        logger.info(f"Successfully fetched and calculated performance for {len(df)} sectors.")
        return df

    def get_top_sectors(self, n_strongest: int = 3, n_weakest: int = 3) -> tuple[list, list]:
        """
        Identifies the top N strongest and weakest sectors based on percentage change.
        """
        df = self.fetch_sector_data()
        if df.empty:
            return [], []

        sorted_df = df.sort_values(by='% Change', ascending=False)
        strongest = sorted_df.head(n_strongest)[['Index Name', '% Change']].to_dict('records')
        weakest = sorted_df.tail(n_weakest)[['Index Name', '% Change']].to_dict('records')
        
        return strongest, weakest