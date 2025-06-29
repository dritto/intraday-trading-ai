import logging
import sys
from pathlib import Path

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_fetcher import DataFetcher
from src.core.strategy import TradingStrategy
from src.core.trader import LiveTrader
from src.execution.angelone_executor import AngelOneExecutor
from src.utils.config_loader import load_config

# Configure a basic logger for the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_strategy_test():
    """
    An example script to initialize and run the main TradingStrategy.
    """
    logger.info("--- Starting Trading Strategy Analysis Test ---")

    try:
        # 1. Load configuration
        config = load_config()
        strategy_params = config.get('strategy_params', {})
        angel_one_config = config.get('angelone', {})

        # 2. Initialize all components
        data_fetcher = DataFetcher()
        strategy = TradingStrategy(
            rsi_overbought=strategy_params.get('rsi_overbought', 70),
            rsi_oversold=strategy_params.get('rsi_oversold', 30)
        )
        executor = AngelOneExecutor(
            api_key=angel_one_config.get('api_key'),
            secret_key=angel_one_config.get('secret_key'),
            access_token=angel_one_config.get('access_token')
        )

        # 3. Initialize the LiveTrader with all the components.
        live_trader = LiveTrader(
            data_fetcher=data_fetcher,
            strategy=strategy,
            executor=executor,
            params=strategy_params
        )
        
        # 4. Define a list of stocks to analyze and run the trader
        nifty50_sample = ['RELIANCE', 'HDFCBANK', 'INFY', 'TCS']
        live_trader.scan_and_trade(nifty50_sample)

    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Configuration or Setup Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the test run: {e}")

if __name__ == "__main__":
    run_strategy_test()