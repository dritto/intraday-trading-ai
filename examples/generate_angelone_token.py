import logging
import sys
from pathlib import Path
from getpass import getpass

# Add the project root to the Python path to allow imports from `src`
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from SmartApi import SmartConnect
from src.utils.config_loader import load_config

# Configure a basic logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_token():
    """
    A utility script to perform the one-time login for Angel One and generate
    the necessary access token for the day.
    """
    logger.info("--- Starting Angel One Token Generation ---")
    try:
        # 1. Load configuration
        config = load_config()
        angel_one_config = config.get('angelone', {})
        api_key = angel_one_config.get('api_key')

        if not api_key or "YOUR_API_KEY" in api_key:
            logger.error("Please set your Angel One 'api_key' in config/settings.yaml first.")
            return

        # 2. Initialize the SmartAPI client
        smart_api = SmartConnect(api_key=api_key)

        # 3. Get user credentials securely
        client_id = input("Enter your Angel One Client ID: ")
        mpin = getpass("Enter your Angel One MPIN: ")
        totp = input("Enter the TOTP from your authenticator app: ")

        # 4. Generate the session
        data = smart_api.generateSession(client_id, mpin, totp)

        if data.get('status') and data.get('data', {}).get('jwtToken'):
            logger.info("Session generated successfully!")
            access_token = data['data']['jwtToken']
            refresh_token = data['data']['refreshToken']
            print("\n" + "="*50)
            print("Please copy the following tokens into your config/settings.yaml file:")
            print(f"access_token: {access_token}")
            print(f"refresh_token: {refresh_token}")
            print("="*50 + "\n")
        else:
            logger.error(f"Failed to generate session: {data['message']}")

    except Exception as e:
        logger.error(f"An error occurred during token generation: {e}")

if __name__ == "__main__":
    generate_token()