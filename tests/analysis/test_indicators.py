import pandas as pd
import numpy as np
import sys
from pathlib import Path
import pytest

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.analysis.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands

@pytest.fixture
def sample_price_data():
    """Creates a sample DataFrame for testing indicator calculations."""
    # Data from a known RSI calculation example online
    prices = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64
    ]
    return pd.DataFrame({'close': prices})

def test_calculate_rsi(sample_price_data):
    """Tests the RSI calculation against a known value."""
    # Calculate RSI with a 14-day period
    data_with_rsi = calculate_rsi(sample_price_data, period=14)

    # The last RSI value for this specific dataset using pandas EWM is ~54.18.
    # Different RSI implementations can yield slightly different results due to
    # variations in the initial smoothing average. We test against our implementation's value.
    # We check if the last value is within a small tolerance
    last_rsi = data_with_rsi['rsi'].iloc[-1]
    assert np.isclose(last_rsi, 54.18, atol=0.01)

def test_calculate_macd(sample_price_data):
    """Tests the MACD calculation against known values."""
    # Calculate MACD with default periods
    data_with_macd = calculate_macd(sample_price_data)

    # Check the values of the last row against pre-calculated results
    last_row = data_with_macd.iloc[-1]
    
    assert np.isclose(last_row['macd'], 0.4383, atol=0.0001)
    assert np.isclose(last_row['signal_line'], 0.4268, atol=0.0001)
    assert np.isclose(last_row['histogram'], 0.0115, atol=0.0001)

def test_calculate_bollinger_bands(sample_price_data):
    """Tests the Bollinger Bands calculation against known values."""
    # Calculate Bollinger Bands with default period of 20
    data_with_bb = calculate_bollinger_bands(sample_price_data, period=20)

    # Check the values of the last row against pre-calculated results
    last_row = data_with_bb.iloc[-1]

    assert np.isclose(last_row['bb_middle'], 45.409, atol=0.001)
    assert np.isclose(last_row['bb_upper'], 47.160, atol=0.001)
    assert np.isclose(last_row['bb_lower'], 43.658, atol=0.001)