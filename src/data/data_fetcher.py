import logging
from datetime import datetime, timedelta
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
from SmartApi import SmartConnect

# Local application imports
from src.utils.config_loader import load_config

# Configure a basic logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Mappings for Angel One ---
# TODO: Replace this with a dynamic instrument list fetcher
ANGELONE_SYMBOL_TOKEN_MAP = {
    'RELIANCE': '3045',
    'HDFCBANK': '1333',
    'INFY': '1594',
    'TCS': '2963'
}

ANGELONE_INTERVAL_MAP = {
    Interval.in_1_minute: "ONE_MINUTE",
    Interval.in_3_minute: "THREE_MINUTE",
    Interval.in_5_minute: "FIVE_MINUTE",
    Interval.in_15_minute: "FIFTEEN_MINUTE",
    Interval.in_30_minute: "THIRTY_MINUTE",
    Interval.in_1_hour: "ONE_HOUR",
    Interval.in_daily: "ONE_DAY",
}

class DataFetcher:
    """
    Handles fetching historical market data from different providers.
    This class acts as an abstraction layer, allowing the user to switch
    between TradingView and Angel One via the config file.
    """

    def __init__(self):
        """
        Initializes the DataFetcher based on the 'data_provider' setting
        in the configuration file.
        """
        self.config = load_config()
        self.provider = self.config.get('data_provider', 'tradingview')
        self.client = None
        logger.info(f"Initializing DataFetcher with provider: {self.provider}")

        if self.provider == 'tradingview':
            tv_config = self.config.get('tradingview', {})
            username = tv_config.get('username')
            password = tv_config.get('password')
            if "YOUR_" in username:
                raise ValueError("TradingView credentials are placeholders. Please update config/settings.yaml.")
            self.client = TvDatafeed(username, password)
        elif self.provider == 'angelone':
            angel_config = self.config.get('angelone', {})
            api_key = angel_config.get('api_key')
            access_token = angel_config.get('access_token')
            if "YOUR_" in access_token:
                raise ValueError("Angel One access_token is a placeholder. Please generate a new one.")
            self.client = SmartConnect(api_key=api_key, access_token=access_token)
        else:
            raise ValueError(f"Unsupported data_provider in config: '{self.provider}'")

    def fetch_historical_data(self, symbol: str, exchange: str, interval: Interval, n_bars: int = 1000):
        """Fetches historical OHLCV data for a given symbol from the configured provider."""
        logger.info(f"Fetching {n_bars} bars for {symbol} from provider: {self.provider}")
        if self.provider == 'tradingview':
            return self._fetch_from_tradingview(symbol, exchange, interval, n_bars)
        elif self.provider == 'angelone':
            return self._fetch_from_angelone(symbol, exchange, interval, n_bars)
        return None

    def _fetch_from_tradingview(self, symbol: str, exchange: str, interval: Interval, n_bars: int):
        """Fetches data using the tvdatafeed library."""
        try:
            data = self.client.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
            if data is None or data.empty:
                logger.warning(f"No data returned for {symbol} from TradingView.")
                return None
            logger.info(f"Successfully fetched {len(data)} bars for {symbol} from TradingView.")
            return data
        except Exception as e:
            logger.error(f"An error occurred while fetching from TradingView for {symbol}: {e}")
            return None

    def _fetch_from_angelone(self, symbol: str, exchange: str, interval: Interval, n_bars: int):
        """Fetches data using the Angel One SmartAPI."""
        if symbol not in ANGELONE_SYMBOL_TOKEN_MAP:
            logger.error(f"Symbol '{symbol}' not found in ANGELONE_SYMBOL_TOKEN_MAP. Cannot fetch from Angel One.")
            return None
        if interval not in ANGELONE_INTERVAL_MAP:
            logger.error(f"Interval '{interval}' not supported for Angel One. Cannot fetch.")
            return None

        try:
            # Angel One API requires a date range, so we calculate it.
            # We fetch a generous fixed range and then slice it to get n_bars.
            to_date = datetime.now()
            
            # Estimate a safe start date to ensure we get enough data
            if interval == Interval.in_1_hour:
                # Approx. 6.5 trading hours a day. Fetch ~45 calendar days for 200 bars.
                from_date = to_date - timedelta(days=45)
            elif interval == Interval.in_daily:
                # Fetch more calendar days than bars needed to account for weekends.
                from_date = to_date - timedelta(days=n_bars * 1.8)
            else: # For smaller intervals like 5-min, 15-min etc.
                from_date = to_date - timedelta(days=30)

            historic_params = {
                "exchange": exchange,
                "symboltoken": ANGELONE_SYMBOL_TOKEN_MAP[symbol],
                "interval": ANGELONE_INTERVAL_MAP[interval],
                "fromdate": from_date.strftime('%Y-%m-%d 09:00'),
                "todate": to_date.strftime('%Y-%m-%d %H:%M')
            }
            
            raw_data = self.client.getCandleData(historic_params)

            if not raw_data or raw_data.get("status") is False:
                logger.warning(f"No data returned for {symbol} from Angel One: {raw_data.get('message')}")
                return None

            # Convert Angel One's list-of-lists format to a standard pandas DataFrame
            df = pd.DataFrame(raw_data['data'], columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)

            # Slice the DataFrame to return the last n_bars
            if len(df) > n_bars:
                df = df.tail(n_bars)
            
            logger.info(f"Successfully fetched and sliced {len(df)} bars for {symbol} from Angel One.")
            return df

        except Exception as e:
            logger.error(f"An error occurred while fetching from Angel One for {symbol}: {e}")
            return None