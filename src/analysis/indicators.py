import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculates the Relative Strength Index (RSI) for a given dataset.

    Args:
        data (pd.DataFrame): A DataFrame containing at least a 'close' column.
        period (int): The lookback period for the RSI calculation. Default is 14.

    Returns:
        pd.DataFrame: The original DataFrame with an added 'rsi' column.
    """
    if 'close' not in data.columns:
        logger.error("DataFrame must contain a 'close' column to calculate RSI.")
        raise ValueError("Missing 'close' column in DataFrame.")

    logger.info(f"Calculating RSI with a period of {period}...")

    # Calculate price changes
    delta = data['close'].diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate the exponential moving average of gains and losses
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    # Calculate the Relative Strength (RS)
    rs = avg_gain / avg_loss

    # Calculate the RSI
    rsi = 100 - (100 / (1 + rs))
    data['rsi'] = rsi

    logger.info("RSI calculation complete.")
    return data

def calculate_macd(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    """
    Calculates the Moving Average Convergence Divergence (MACD).

    Args:
        data (pd.DataFrame): A DataFrame containing at least a 'close' column.
        fast_period (int): The lookback period for the fast EMA.
        slow_period (int): The lookback period for the slow EMA.
        signal_period (int): The lookback period for the signal line EMA.

    Returns:
        pd.DataFrame: The original DataFrame with added 'macd', 'signal_line',
                      and 'histogram' columns.
    """
    if 'close' not in data.columns:
        logger.error("DataFrame must contain a 'close' column to calculate MACD.")
        raise ValueError("Missing 'close' column in DataFrame.")

    logger.info(f"Calculating MACD with periods: fast={fast_period}, slow={slow_period}, signal={signal_period}...")

    data['ema_fast'] = data['close'].ewm(span=fast_period, adjust=False).mean()
    data['ema_slow'] = data['close'].ewm(span=slow_period, adjust=False).mean()
    data['macd'] = data['ema_fast'] - data['ema_slow']
    data['signal_line'] = data['macd'].ewm(span=signal_period, adjust=False).mean()
    data['histogram'] = data['macd'] - data['signal_line']

    logger.info("MACD calculation complete.")
    return data

def calculate_bollinger_bands(data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """
    Calculates Bollinger Bands.

    Args:
        data (pd.DataFrame): A DataFrame containing at least a 'close' column.
        period (int): The lookback period for the moving average.
        std_dev (int): The number of standard deviations for the bands.

    Returns:
        pd.DataFrame: The original DataFrame with added 'bb_middle', 'bb_upper',
                      and 'bb_lower' columns.
    """
    if 'close' not in data.columns:
        logger.error("DataFrame must contain a 'close' column to calculate Bollinger Bands.")
        raise ValueError("Missing 'close' column in DataFrame.")

    logger.info(f"Calculating Bollinger Bands with period={period} and std_dev={std_dev}...")

    data['bb_middle'] = data['close'].rolling(window=period).mean()
    data['bb_std'] = data['close'].rolling(window=period).std()
    data['bb_upper'] = data['bb_middle'] + (data['bb_std'] * std_dev)
    data['bb_lower'] = data['bb_middle'] - (data['bb_std'] * std_dev)

    logger.info("Bollinger Bands calculation complete.")
    return data