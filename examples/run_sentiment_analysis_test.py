import logging
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.sentiment import SentimentAnalysis
from src.execution.angelone_executor import AngelOneExecutor
from src.utils.config_loader import load_config

def main():
    """
    A simple script to test the SentimentAnalysis module.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    config = load_config()
    angel_one_config = config.get('angelone', {})

    executor = AngelOneExecutor(
        api_key=angel_one_config.get('api_key'),
        secret_key=angel_one_config.get('secret_key'),
        access_token=angel_one_config.get('access_token')
    )

    if not executor.smart_api:
        logger.error("Could not connect AngelOneExecutor. Please check credentials. Aborting.")
        return

    analyzer = SentimentAnalysis(executor=executor)
    sentiment_data = analyzer.get_market_sentiment()
    
    if sentiment_data:
        print(f"\n--- Pre-Market Sentiment Analysis ---")
        print(f"Overall Sentiment: {sentiment_data['sentiment']} (VIX Level: {sentiment_data['vix_level']:.2f})")
    else:
        print("\nCould not determine market sentiment.")

if __name__ == "__main__":
    main()