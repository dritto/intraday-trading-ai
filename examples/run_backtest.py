import logging
import sys
from pathlib import Path
from tvDatafeed import Interval

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_fetcher import DataFetcher
from src.core.strategy import TradingStrategy
from src.backtesting.engine import BacktestingEngine
from src.analysis.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands
from src.utils.config_loader import load_config

# Configure a basic logger for the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_backtest():
    """
    An example script to initialize and run the backtesting engine.
    """
    logger.info("--- Starting Backtest Example ---")

    try:
        # 1. Load configuration
        config = load_config()
        strategy_params = config.get('strategy_params', {})

        # 2. Define the list of stocks to backtest
        nifty50_sample = ['RELIANCE', 'HDFCBANK', 'INFY']

        # 3. Initialize components that are shared across all backtests
        data_fetcher = DataFetcher()
        strategy = TradingStrategy(
            rsi_overbought=strategy_params.get('rsi_overbought', 70),
            rsi_oversold=strategy_params.get('rsi_oversold', 30)
        )

        # 4. Loop through each stock and run an independent backtest
        for symbol in nifty50_sample:
            logger.info(f"================== Backtesting {symbol} ==================")
            
            # Fetch data for the stock
            data = data_fetcher.fetch_historical_data(symbol, 'NSE', Interval.in_1_hour, n_bars=500)

            if data is None:
                logger.error(f"Could not fetch data for {symbol}. Skipping backtest.")
                continue

            # Calculate all required indicators using configured params
            data = calculate_rsi(data)
            data = calculate_macd(data)
            data = calculate_bollinger_bands(
                data,
                period=strategy_params.get('bb_period', 20),
                std_dev=strategy_params.get('bb_std_dev', 2)
            )
            data.dropna(inplace=True)

            # Initialize a new engine for each backtest to reset its state
            engine = BacktestingEngine(initial_capital=100000.0)

            # Run the backtest for the current stock
            engine.run(data, strategy, symbol=symbol)

    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Configuration or Setup Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the backtest: {e}")

if __name__ == "__main__":
    run_backtest()