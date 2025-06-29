import pandas as pd
import pytest
import sys
from pathlib import Path

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.core.strategy import TradingStrategy

@pytest.fixture
def strategy_data():
    """Creates a sample DataFrame with indicators for strategy testing."""
    data = {
        'close':    [100, 101, 102, 103, 104],
        'rsi':      [50,  55,  60,  25,  75],
        'bb_lower': [98,  99,  100, 101, 102],
        'bb_upper': [102, 103, 104, 105, 106]
    }
    return pd.DataFrame(data)

def test_generate_signal_buy_with_custom_params(strategy_data):
    """
    Tests that a BUY signal is generated when RSI is below a custom
    oversold threshold and the price is below the lower Bollinger Band.
    """
    # Initialize strategy with a custom oversold threshold
    strategy = TradingStrategy(rsi_oversold=28)
    
    # Modify the last row to trigger the BUY condition
    strategy_data.loc[strategy_data.index[-1], 'rsi'] = 27
    strategy_data.loc[strategy_data.index[-1], 'close'] = 100 # Below bb_lower of 102

    assert strategy.generate_signal(strategy_data) == 'BUY'

def test_generate_signal_sell_with_custom_params(strategy_data):
    """
    Tests that a SELL signal is generated when RSI is above a custom
    overbought threshold and the price is above the upper Bollinger Band.
    """
    # Initialize strategy with a custom overbought threshold
    strategy = TradingStrategy(rsi_overbought=72)

    # The last row of the fixture already has RSI=75 and close=104 (below bb_upper of 106)
    # Modify the close price to be above the upper band to trigger the SELL condition
    strategy_data.loc[strategy_data.index[-1], 'close'] = 107 # Above bb_upper of 106

    assert strategy.generate_signal(strategy_data) == 'SELL'

def test_generate_signal_hold(strategy_data):
    """Tests that a HOLD signal is generated when no conditions are met."""
    strategy = TradingStrategy() # Default params
    # The default fixture data at index -2 (rsi=25, close=103) should be a HOLD
    assert strategy.generate_signal(strategy_data.head(4)) == 'HOLD'