import logging
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.sector import SectorAnalysis
from src.execution.angelone_executor import AngelOneExecutor
from src.utils.config_loader import load_config

def main():
    """
    A simple script to test the SectorAnalysis module.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    config = load_config()
    angel_one_config = config.get('angelone', {})

    # We need a live executor to get data from the broker's API
    executor = AngelOneExecutor(
        api_key=angel_one_config.get('api_key'),
        secret_key=angel_one_config.get('secret_key'),
        access_token=angel_one_config.get('access_token')
    )

    if not executor.smart_api:
        logger.error("Could not connect AngelOneExecutor. Please check credentials. Aborting.")
        return

    analyzer = SectorAnalysis(executor=executor)
    strongest, weakest = analyzer.get_top_sectors(n_strongest=5, n_weakest=5)
    
    print("\n--- Strongest Sectors Today ---")
    print(strongest)
    
    print("\n--- Weakest Sectors Today ---")
    print(weakest)

if __name__ == "__main__":
    main()