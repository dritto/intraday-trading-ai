import logging
from SmartApi import SmartConnect
import requests
import pandas as pd
import io

logger = logging.getLogger(__name__)

class AngelOneExecutor:
    """
    Handles all trade execution logic via Angel One's SmartAPI.
    This class is responsible for placing, modifying, and canceling orders.
    This is a placeholder and does not connect to the actual API yet.
    """

    def __init__(self, api_key: str, secret_key: str, access_token: str):
        """
        Initializes the Angel One executor and would authenticate with the SmartAPI.

        Args:
            api_key (str): The API key for Angel One.
            secret_key (str): The secret key for Angel One.
            access_token (str): The access token for the current session.
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = access_token
        self.smart_api = None
        self.instrument_map = {}

        if not all([api_key, access_token]) or "YOUR_" in access_token:
            logger.warning("Angel One API key or access token is missing. Executor will run in placeholder mode.")
        else:
            try:
                logger.info("Initializing Angel One Executor and authenticating...")
                self.smart_api = SmartConnect(api_key=self.api_key, access_token=self.access_token)
                profile = self.smart_api.getProfile(self.smart_api.refresh_token)
                if profile.get('status'):
                    logger.info(f"Angel One connection successful for user: {profile['data']['name']}")
                    self._initialize_instrument_map()
                else:
                    logger.error(f"Angel One authentication failed: {profile.get('message')}")
                    self.smart_api = None # Invalidate API object on failure
            except Exception as e:
                logger.error(f"Failed to initialize Angel One SmartAPI client: {e}")
                self.smart_api = None

    def _initialize_instrument_map(self):
        """Downloads the Angel One instrument list and creates a symbol-to-token map."""
        try:
            logger.info("Downloading Angel One instrument list...")
            # This URL provides the complete list of instruments from Angel One
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(url)
            response.raise_for_status() # Raise an exception for bad status codes
            
            instrument_data = response.json() 

            # Create a comprehensive map keyed by the instrument 'name' (e.g., "RELIANCE", "NIFTY BANK")
            # This allows easy lookup for both equities and indices.
            self.instrument_map = {
                item['name'].upper(): {'token': item['token'], 'symbol': item['symbol']}
                for item in instrument_data 
                if item.get('name') and item.get('exch_seg') == 'NSE' and 
                   item.get('instrumenttype') in ['EQ', 'INDEX', 'AMXIDX']
            }
            logger.info(f"Successfully loaded {len(self.instrument_map)} NSE equity and index instruments.")
        except Exception as e:
            logger.error(f"Failed to download or process Angel One instrument list: {e}")
            # If this fails, the executor cannot place trades.
            self.smart_api = None

    def place_order(self, symbol: str, quantity: int, order_type: str, transaction_type: str):
        """
        Places a trade order.

        Args:
            symbol (str): The stock symbol to trade.
            quantity (int): The number of shares.
            order_type (str): e.g., 'MARKET', 'LIMIT'.
            transaction_type (str): 'BUY' or 'SELL'.
        """
        if not self.smart_api:
            logger.warning("Executor is in placeholder mode. Not placing real order.")
            return {"status": "placeholder", "order_id": "placeholder_12345"}

        instrument = self.instrument_map.get(symbol.upper())
        if not instrument:
            logger.error(f"Could not find instrument details for {symbol}. Cannot place order.")
            return {"status": "failed", "message": f"Instrument details not found for {symbol}"}

        trading_symbol = instrument['symbol']
        symbol_token = instrument['token']

        try:
            # This is the structure required by the official documentation
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": trading_symbol,
                "symboltoken": symbol_token,
                "transactiontype": transaction_type.upper(), # 'BUY' or 'SELL'
                "exchange": "NSE",
                "ordertype": order_type.upper(), # 'MARKET', 'LIMIT', etc.
                "producttype": "INTRADAY", # Or 'DELIVERY'
                "duration": "DAY",
                "quantity": quantity
            }
            logger.info(f"Placing order with params: {order_params}")
            order_response = self.smart_api.placeOrder(order_params)
            
            if order_response.get("status"):
                order_id = order_response.get("data", {}).get("orderid")
                logger.info(f"Successfully placed order. Order ID: {order_id}")
                return {"status": "success", "order_id": order_id, "response": order_response}
            else:
                logger.error(f"Failed to place order: {order_response.get('message')}")
                return {"status": "failed", "response": order_response}
        except Exception as e:
            logger.error(f"An exception occurred while placing order: {e}")
            return {"status": "error", "message": str(e)}

    def get_ltp_data(self, name: str):
        """Fetches Last Traded Price and other details for a given instrument name."""
        if not self.smart_api:
            logger.warning("Executor is in placeholder mode. Cannot fetch LTP data.")
            return None

        instrument = self.instrument_map.get(name.upper())
        if not instrument:
            logger.error(f"Could not find instrument details for {name}.")
            return None

        try:
            ltp_params = {
                "exchange": "NSE",
                "tradingsymbol": instrument['symbol'],
                "symboltoken": instrument['token']
            }
            response = self.smart_api.ltpData(
                ltp_params["exchange"],
                ltp_params["tradingsymbol"],
                ltp_params["symboltoken"]
            )
            if response.get("status") and response.get("data"):
                return response["data"]
            else:
                logger.error(f"Failed to get LTP for {name}: {response.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Exception getting LTP for {name}: {e}")
            return None

    def cancel_order(self, order_id: str):
        """
        Cancels an existing order.

        Args:
            order_id (str): The ID of the order to cancel.
        """
        if not self.smart_api:
            logger.warning("Executor is in placeholder mode. Not canceling real order.")
            return {"status": "placeholder"}
        
        try:
            logger.info(f"Attempting to cancel order ID: {order_id}")
            # The 'variety' must match the one used to place the order.
            cancel_response = self.smart_api.cancelOrder(order_id=order_id, variety="NORMAL")
            
            if cancel_response.get("status"):
                canceled_id = cancel_response.get("data", {}).get("orderid")
                logger.info(f"Successfully canceled order ID: {canceled_id}")
                return {"status": "success", "response": cancel_response}
            else:
                logger.error(f"Failed to cancel order {order_id}: {cancel_response.get('message')}")
                return {"status": "failed", "response": cancel_response}
        except Exception as e:
            logger.error(f"An exception occurred while canceling order {order_id}: {e}")
            return {"status": "error", "message": str(e)}