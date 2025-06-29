import logging
from src.execution.angelone_executor import AngelOneExecutor

logger = logging.getLogger(__name__)

class SentimentAnalysis:
    """
    Analyzes pre-market sentiment by checking the India VIX level.
    A high VIX suggests fear (negative sentiment), while a low VIX suggests confidence.
    """

    def __init__(self, executor: AngelOneExecutor):
        """
        Initializes the SentimentAnalysis class.

        Args:
            executor (AngelOneExecutor): An instance of the executor to get live market data.
        """
        self.executor = executor
        self.sentiment_symbol = 'INDIA VIX'

    def get_market_sentiment(self) -> dict:
        """
        Fetches India VIX data to determine the pre-market sentiment.

        Returns:
            dict: A dictionary containing sentiment ('Positive', 'Negative', 'Neutral')
                  and the last VIX price. Returns an empty dict on failure.
        """
        logger.info(f"Fetching pre-market sentiment from {self.sentiment_symbol} via Angel One...")
        try:
            data = self.executor.get_ltp_data(name=self.sentiment_symbol)

            if not data or 'ltp' not in data:
                logger.error(f"Could not fetch LTP data for {self.sentiment_symbol}.")
                return {}

            vix_level = data['ltp']
            
            # Define sentiment based on VIX levels. These thresholds can be configured.
            if vix_level > 20:
                sentiment = "Negative" # High fear
            elif vix_level < 15:
                sentiment = "Positive" # Low fear / Complacency
            else:
                sentiment = "Neutral"

            logger.info(f"Market sentiment is {sentiment} (India VIX: {vix_level:.2f})")
            return {"sentiment": sentiment, "vix_level": vix_level}
        except Exception as e:
            logger.error(f"An error occurred while fetching {self.sentiment_symbol} sentiment: {e}")
            return {}