import argparse
import logging
import sys
import itertools
import multiprocessing
import os
from pathlib import Path
import pandas as pd

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config_loader import load_config
from src.data.data_fetcher import DataFetcher
from src.core.strategy import TradingStrategy
from src.core.trader import LiveTrader
from src.execution.angelone_executor import AngelOneExecutor
from src.backtesting.engine import BacktestingEngine
from src.analysis.sector import SectorAnalysis
from src.analysis.sentiment import SentimentAnalysis
from src.analysis.ai_analyzer import AIAnalyzer
from src.utils.news_fetcher import NewsFetcher
from src.utils.index_constituents import get_index_constituents
from src.analysis.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands
from tvDatafeed import Interval

# Configure a basic logger for the main application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_backtest_worker(args):
    """
    A worker function designed to be run in a separate process for a single backtest.
    It takes a single tuple of arguments to be compatible with multiprocessing.Pool.
    """
    symbol, params, strategy_params, base_data = args
    
    # Each process should have its own logger instance.
    worker_logger = logging.getLogger(f"worker_{os.getpid()}")
    worker_logger.info(f"Processing: {symbol} with {params}")

    try:
        data = base_data.copy()
        data = calculate_rsi(data)
        data = calculate_macd(data)
        data = calculate_bollinger_bands(data, period=params['bb_period'], std_dev=params['bb_std_dev'])
        data.dropna(inplace=True)

        if data.empty:
            return None

        strategy = TradingStrategy(rsi_oversold=params['rsi_oversold'], rsi_overbought=params['rsi_overbought'])
        engine = BacktestingEngine(
            initial_capital=100000.0,
            stop_loss_pct=strategy_params.get('stop_loss_pct', 0.0),
            take_profit_pct=strategy_params.get('take_profit_pct', 0.0)
        )
        performance = engine.run(data, strategy, symbol, plot=False)
        return {'symbol': symbol, **params, **performance}
    except Exception as e:
        worker_logger.error(f"Error in worker for {symbol} with {params}: {e}")
        return None

def run_live_trading(config):
    """Initializes and runs the live trading bot."""
    logger.info("--- Starting Live Trading Mode ---")
    strategy_params = config.get('strategy_params', {})
    angel_one_config = config.get('angelone', {})
    ai_config = config.get('ai', {})
    github_config = config.get('github', {})

    # --- Initialize Core Components ---
    data_fetcher = DataFetcher()
    news_fetcher = NewsFetcher()

    # Initialize executor first for pre-market analysis
    executor = AngelOneExecutor(
        api_key=angel_one_config.get('api_key'),
        secret_key=angel_one_config.get('secret_key'),
        access_token=angel_one_config.get('access_token')
    )

    if not executor.smart_api:
        logger.error("Could not connect AngelOneExecutor. Please check credentials. Aborting live trading.")
        return

    # --- Initialize AI Analyzer ---
    google_api_key = ai_config.get('google_api_key')
    ai_analyzer = None
    if google_api_key and "YOUR_" not in google_api_key:
        logger.info("Initializing AI Analyzer...")
        ai_analyzer = AIAnalyzer(api_key=google_api_key, news_fetcher=news_fetcher)
    else:
        logger.warning("Google AI API key not found in config. AI analysis will be skipped.")

    # --- Pre-Market Analysis: Market Sentiment ---
    logger.info("--- Running Pre-Market Sentiment Analysis ---")
    sentiment_analyzer = SentimentAnalysis(executor=executor)
    market_sentiment_data = sentiment_analyzer.get_market_sentiment()

    if not market_sentiment_data:
        logger.warning("Could not determine market sentiment. Proceeding with caution.")
    elif market_sentiment_data.get('sentiment') == 'Negative':
        logger.warning(f"Market sentiment is Negative (VIX: {market_sentiment_data.get('vix_level'):.2f}). No trades will be placed today.")
        return # Exit if market sentiment is negative

    # --- Pre-Market Analysis: Sector Strength ---
    logger.info("--- Running Pre-Market Sector Analysis ---")
    sector_analyzer = SectorAnalysis(executor=executor)
    strongest_sectors, _ = sector_analyzer.get_top_sectors(n_strongest=3, n_weakest=0)

    stocks_to_trade = []
    if strongest_sectors:
        logger.info(f"Top 3 strongest sectors found: {[s['Index Name'] for s in strongest_sectors]}")
        for sector in strongest_sectors:
            sector_name = sector['Index Name']
            constituents = get_index_constituents(sector_name)
            if constituents:
                stocks_to_trade.extend(constituents)
            else:
                logger.warning(f"Could not fetch constituents for {sector_name}. It will be skipped.")
        stocks_to_trade = sorted(list(set(stocks_to_trade))) # Get unique stocks
    
    if not stocks_to_trade:
        logger.warning("No stocks identified from sector analysis. Using default Nifty 50 sample.")
        stocks_to_trade = ['RELIANCE', 'HDFCBANK', 'INFY', 'TCS']

    logger.info(f"Stocks selected for trading today: {stocks_to_trade}")

    # --- Initialize Core Trading Components ---
    strategy = TradingStrategy(
        rsi_overbought=strategy_params.get('rsi_overbought', 70),
        rsi_oversold=strategy_params.get('rsi_oversold', 30)
    )
    live_trader = LiveTrader(
        data_fetcher=data_fetcher,
        strategy=strategy,
        executor=executor,
        ai_analyzer=ai_analyzer,
        params={**strategy_params, **github_config}
    )
    
    live_trader.run(stocks_to_trade)


def run_full_backtest(config, stock_list):
    """Initializes and runs the backtesting engine."""
    logger.info(f"--- Starting Backtesting Mode for stocks: {', '.join(stock_list)} ---")
    strategy_params = config.get('strategy_params', {})

    data_fetcher = DataFetcher()
    strategy = TradingStrategy(
        rsi_overbought=strategy_params.get('rsi_overbought', 70),
        rsi_oversold=strategy_params.get('rsi_oversold', 30)
    )

    for symbol in stock_list:
        logger.info(f"================== Backtesting {symbol} ==================")
        data = data_fetcher.fetch_historical_data(symbol, 'NSE', Interval.in_1_hour, n_bars=500)

        if data is None:
            logger.error(f"Could not fetch data for {symbol}. Skipping backtest.")
            continue

        data = calculate_rsi(data)
        data = calculate_macd(data)
        data = calculate_bollinger_bands(
            data,
            period=strategy_params.get('bb_period', 20),
            std_dev=strategy_params.get('bb_std_dev', 2)
        )
        data.dropna(inplace=True)

        engine = BacktestingEngine(
            initial_capital=100000.0,
            stop_loss_pct=strategy_params.get('stop_loss_pct', 0.0),
            take_profit_pct=strategy_params.get('take_profit_pct', 0.0)
        )
        engine.run(data, strategy, symbol=symbol)

def run_optimization(config, stock_list):
    """Runs parameter optimization for the trading strategy."""
    logger.info(f"--- Starting Optimization Mode for stocks: {', '.join(stock_list)} ---")
    strategy_params = config.get('strategy_params', {})

    # 1. Define the grid of parameters to search
    param_grid = {
        'rsi_oversold': [25, 30, 35],
        'rsi_overbought': [65, 70, 75],
        'bb_period': [15, 20, 25],
        'bb_std_dev': [2.0, 2.5]
    }

    # 2. Create all unique combinations of parameters
    keys, values = zip(*param_grid.items())
    param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    logger.info(f"Will test {len(param_combinations)} parameter combinations for each stock.")

    data_fetcher = DataFetcher()
    tasks = []

    # 3. Prepare the list of tasks to be executed in parallel
    for symbol in stock_list:
        logger.info(f"================== Preparing tasks for {symbol} ==================")
        base_data = data_fetcher.fetch_historical_data(symbol, 'NSE', Interval.in_1_hour, n_bars=500)
        if base_data is None:
            logger.error(f"Could not fetch data for {symbol}. Skipping optimization.")
            continue
        
        for params in param_combinations:
            tasks.append((symbol, params, strategy_params, base_data))

    # 4. Run tasks in parallel using a process pool
    # We use cpu_count() - 1 to leave one core free for system operations.
    num_processes = max(1, multiprocessing.cpu_count() - 1)
    logger.info(f"Distributing {len(tasks)} backtesting tasks across {num_processes} processes...")
    
    with multiprocessing.Pool(processes=num_processes) as pool:
        all_results_list = pool.map(run_backtest_worker, tasks)

    # 5. Process the results
    # Filter out any failed runs which return None
    all_results_list = [r for r in all_results_list if r is not None]

    if all_results_list:
        results_df = pd.DataFrame(all_results_list)
        best_run = results_df.loc[results_df['sharpe_ratio'].idxmax()]
        logger.info("--- Overall Best Parameters (by Sharpe Ratio) ---")
        logger.info(best_run)
        results_df.to_csv("optimization_results.csv", index=False)
        logger.info("Full optimization results saved to optimization_results.csv")

def main():
    """Main entry point for the trading bot."""
    parser = argparse.ArgumentParser(description="Intelligent Intraday Trading System")
    parser.add_argument(
        'mode',
        choices=['live', 'backtest', 'optimize'],
        help="The mode to run the bot in: 'live' for live trading or 'backtest' for historical simulation."
    )
    parser.add_argument(
        '--stocks',
        nargs='+',
        metavar='SYMBOL',
        default=None,
        help='A list of stock symbols to backtest (e.g., RELIANCE HDFCBANK). Only used in backtest mode.'
    )
    args = parser.parse_args()

    try:
        config = load_config()
        if args.mode == 'live':
            run_live_trading(config)
        elif args.mode == 'backtest':
            stocks_to_backtest = args.stocks if args.stocks else ['RELIANCE', 'HDFCBANK', 'INFY']
            run_full_backtest(config, stocks_to_backtest)
        elif args.mode == 'optimize':
            stocks_to_optimize = args.stocks if args.stocks else ['RELIANCE', 'HDFCBANK', 'INFY']
            run_optimization(config, stocks_to_optimize)
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Initialization Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}")


if __name__ == "__main__":
    main()