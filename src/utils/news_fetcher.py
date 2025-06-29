import logging
import yfinance as yf

logger = logging.getLogger(__name__)

class NewsFetcher:
    """
    Fetches recent news headlines for a given stock symbol using yfinance.
    """

    def get_recent_news(self, symbol: str, n_headlines: int = 5) -> list[str]:
        """
        Gets the most recent news headlines for a stock.

        Args:
            symbol (str): The stock symbol (e.g., "RELIANCE").
            n_headlines (int): The maximum number of headlines to return.

        Returns:
            list[str]: A list of news headlines, or an empty list on failure.
        """
        logger.info(f"Fetching recent news for {symbol}...")
        try:
            # yfinance expects symbols to be in the format 'RELIANCE.NS' for NSE stocks
            ticker = yf.Ticker(f"{symbol.upper()}.NS")
            news = ticker.news

            return [item['title'] for item in news[:n_headlines]] if news else []

        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol} using yfinance: {e}")
            return []