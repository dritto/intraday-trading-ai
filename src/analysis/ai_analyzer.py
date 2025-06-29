import logging
import google.generativeai as genai

from src.utils.news_fetcher import NewsFetcher

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """
    Uses a Large Language Model (LLM) to provide qualitative analysis on trade setups.
    """

    def __init__(self, api_key: str, news_fetcher: NewsFetcher):
        """
        Initializes the AI Analyzer and configures the generative AI model.
        """
        try:
            if not news_fetcher:
                raise ValueError("NewsFetcher instance is required.")
            self.news_fetcher = news_fetcher
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("AI Analyzer initialized successfully with Gemini-Pro model.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Generative AI: {e}")
            self.model = None

    def analyze_trade_setup(self, symbol: str, data: 'pd.DataFrame') -> str:
        """
        Asks the AI to analyze a trade setup and provide a verdict.

        Args:
            symbol (str): The stock symbol.
            data (pd.DataFrame): The historical data with indicators for the stock.

        Returns:
            str: A verdict, either "CONFIRM" or "REJECT". Returns "REJECT" on failure.
        """
        if not self.model:
            logger.warning("AI model not available. Rejecting trade by default.")
            return "REJECT"

        # Fetch recent news headlines
        headlines = self.news_fetcher.get_recent_news(symbol)
        news_section = "No recent news available."
        if headlines:
            news_section = "\n".join([f"- {h}" for h in headlines])

        try:
            # Extract the latest indicator values
            latest_data = data.iloc[-1]
            prompt = f"""
            As an expert stock market analyst, evaluate the following intraday BUY signal for the Indian stock '{symbol}'.
            Provide a concise, one-sentence justification and a final verdict.

            Current Technical Data:
            - Price: {latest_data['close']:.2f}
            - RSI: {latest_data.get('rsi', 'N/A'):.2f}
            - MACD: {latest_data.get('macd', 'N/A'):.2f}
            - MACD Signal: {latest_data.get('macdsignal', 'N/A'):.2f}
            - Bollinger Band Upper: {latest_data.get('bb_upper', 'N/A'):.2f}
            - Bollinger Band Lower: {latest_data.get('bb_lower', 'N/A'):.2f}

            Recent News Headlines:
            {news_section}

            Considering both the technical data and the recent news, is this a high-probability trade?
            Your response must end with either "Verdict: CONFIRM" or "Verdict: REJECT".
            """

            response = self.model.generate_content(prompt)
            logger.info(f"AI Analysis for {symbol}: {response.text.strip()}")

            return "CONFIRM" if "Verdict: CONFIRM" in response.text else "REJECT"

        except Exception as e:
            logger.error(f"An error occurred during AI analysis for {symbol}: {e}")
            return "REJECT"