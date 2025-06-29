import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_config(config_path: str = 'config/settings.yaml') -> dict:
    """
    Loads the YAML configuration file from the given path.

    Args:
        config_path (str): The relative or absolute path to the configuration file.

    Returns:
        dict: A dictionary containing the configuration.

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        yaml.YAMLError: If there is an error parsing the file.
    """
    path = Path(config_path)
    logger.info(f"Attempting to load configuration from: {path.resolve()}")

    if not path.is_file():
        logger.error(f"Configuration file not found at: {path.resolve()}")
        raise FileNotFoundError(f"Configuration file not found at: {path.resolve()}")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    logger.info("Configuration loaded successfully.")
    return config