import logging
import pandas as pd

logger = logging.getLogger(__name__)

class TradingStrategy:
    """
    Encapsulates the core trading logic. This class will analyze market data
    for a list of stocks and identify potential trading opportunities based on
    a confluence of technical indicator signals. This refactored version
    separates signal generation from data fetching and execution, making it
    reusable for both live trading and backtesting.
    """

    def __init__(self, rsi_overbought=70, rsi_oversold=30, **kwargs):
        """
        Initializes the trading strategy with its parameters.

        Args:
            rsi_overbought (int): The RSI level to consider as overbought.
            rsi_oversold (int): The RSI level to consider as oversold.
            **kwargs: Catches any other strategy parameters for future use.
        """
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        logger.info(f"RSI/Bollinger Bands Strategy initialized with thresholds: Overbought={self.rsi_overbought}, Oversold={self.rsi_oversold}")

    def generate_signal(self, data: pd.DataFrame) -> str:
        """
        Generates a trading signal ('BUY', 'SELL', 'HOLD') for the latest data point.

        Args:
            data (pd.DataFrame): A DataFrame with OHLCV data and pre-calculated indicators.

        Returns:
            str: The trading signal.
        """
        latest_data = data.iloc[-1]

        is_oversold = latest_data['rsi'] < self.rsi_oversold
        is_overbought = latest_data['rsi'] > self.rsi_overbought
        price_below_lower_band = latest_data['close'] < latest_data['bb_lower']
        price_above_upper_band = latest_data['close'] > latest_data['bb_upper']

        if is_oversold and price_below_lower_band:
            return 'BUY'
        elif is_overbought and price_above_upper_band:
            return 'SELL'
        else:
            return 'HOLD'