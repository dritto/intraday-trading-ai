import logging
import csv
import os

logger = logging.getLogger(__name__)

class TradeJournal:
    """
    Handles logging of all completed round-trip trades to a persistent CSV file.
    """

    def __init__(self, filepath: str):
        """
        Initializes the TradeJournal.

        Args:
            filepath (str): The path to the CSV file where trades will be logged.
        """
        self.filepath = filepath
        self.fieldnames = [
            'symbol', 'entry_timestamp', 'entry_price', 'exit_timestamp', 
            'exit_price', 'quantity', 'pnl', 'exit_reason'
        ]
        self._initialize_file()

    def _initialize_file(self):
        """Creates the log file and writes the header if it doesn't exist."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            if not os.path.exists(self.filepath):
                with open(self.filepath, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                    writer.writeheader()
                logger.info(f"Trade journal created at: {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to initialize trade journal file: {e}")

    def log_trade(self, trade_record: dict):
        """Appends a single completed trade record to the CSV file."""
        try:
            with open(self.filepath, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writerow(trade_record)
            logger.info(f"Logged completed trade to journal for symbol: {trade_record['symbol']}")
        except Exception as e:
            logger.error(f"Failed to log trade to journal: {e}")