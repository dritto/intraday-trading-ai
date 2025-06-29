import logging
import time
from tvDatafeed import Interval
from datetime import datetime
import json
from github import Github, InputFileContent
import os

from src.utils.trade_journal import TradeJournal
from src.analysis.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands

logger = logging.getLogger(__name__)

class LiveTrader:
    """
    Orchestrates live trading by managing a portfolio, tracking open positions,
    and executing trades based on strategy signals and risk management rules.
    """

    def __init__(self, data_fetcher, strategy, executor, ai_analyzer, params):
        self.data_fetcher = data_fetcher
        self.strategy = strategy
        self.executor = executor
        self.ai_analyzer = ai_analyzer
        self.params = params

        # --- Portfolio & Journaling ---
        self.initial_capital = params.get('initial_capital', 100000.0)
        self.cash = self.initial_capital
        # Example position: {'RELIANCE': {'quantity': 10, 'entry_price': 2500, 'stop_loss': 2450, 'take_profit': 2600}}
        self.positions = {}
        self.trade_log = []
        self.journal = TradeJournal(filepath=f"logs/trade_journal_{datetime.now().strftime('%Y%m%d')}.csv")
        self.status_filepath = "logs/portfolio_status.json"
        self.github_token = self.params.get('github_pat')
        self.gist_id = self.params.get('gist_id')
        self.github = None
        if self.github_token and self.gist_id and "YOUR_" not in self.github_token:
            self.github = Github(self.github_token)
            logger.info("GitHub client initialized for Gist updates.")

        self.loop_counter = 0

        # --- Risk Management ---
        self.stop_loss_pct = params.get('stop_loss_pct', 2.0)
        self.take_profit_pct = params.get('take_profit_pct', 5.0)
        self.max_active_positions = params.get('max_active_positions', 5)
        self.capital_per_trade_pct = params.get('capital_per_trade_pct', 20.0) # Use 20% of available cash per trade

    def run(self, watchlist: list[str]):
        """
        Starts the main trading loop. This loop will run continuously.
        """
        logger.info("--- Live Trader is running ---")
        logger.info(f"Risk Params: Stop Loss={self.stop_loss_pct}%, Take Profit={self.take_profit_pct}%, Max Positions={self.max_active_positions}")
        
        # Report initial status immediately so the dashboard has data on startup
        self.report_portfolio_status()
        
        while True:
            try:
                # 1. Manage existing open positions for risk (SL/TP)
                self.manage_open_positions()

                # 2. Scan for new trading opportunities if we have capacity
                if len(self.positions) < self.max_active_positions:
                    self.scan_for_new_trades(watchlist)

                self.loop_counter += 1
                if self.loop_counter % 5 == 0: # Report status every 5 loops (approx. 5 minutes)
                    self.report_portfolio_status()
                else:
                    logger.info(f"Loop complete. Positions: {len(self.positions)}/{self.max_active_positions}. Cash: {self.cash:.2f}. Waiting for next interval...")
                time.sleep(60)  # Wait for 1 minute before the next cycle

            except KeyboardInterrupt:
                logger.info("Live trader stopped by user. Closing all open positions...")
                self.close_all_positions()
                break
            except Exception as e:
                logger.error(f"An error occurred in the main trading loop: {e}", exc_info=True)
                time.sleep(60)

    def report_portfolio_status(self):
        """Calculates and logs the current portfolio value and PnL."""
        open_positions_value = 0
        for symbol, position in self.positions.items():
            ltp_data = self.executor.get_ltp_data(name=symbol)
            current_price = ltp_data['ltp'] if ltp_data and 'ltp' in ltp_data else position['entry_price']
            open_positions_value += position['quantity'] * current_price

        portfolio_value = self.cash + open_positions_value
        pnl = portfolio_value - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100 if self.initial_capital != 0 else 0

        logger.info("--- PORTFOLIO STATUS ---")
        logger.info(f"Portfolio Value: {portfolio_value:,.2f} | PnL: {pnl:,.2f} ({pnl_pct:.2f}%)")
        logger.info(f"Cash: {self.cash:,.2f} | Open Positions Value: {open_positions_value:,.2f} | Count: {len(self.positions)}")
        
        # --- Write status to file for dashboard ---
        serializable_positions = {}
        for symbol, pos_data in self.positions.items():
            serializable_positions[symbol] = pos_data.copy()
            if isinstance(pos_data.get('entry_timestamp'), datetime):
                serializable_positions[symbol]['entry_timestamp'] = pos_data['entry_timestamp'].isoformat()

        status_data = {
            'portfolio_value': portfolio_value, 'pnl': pnl, 'pnl_pct': pnl_pct,
            'cash': self.cash, 'open_positions_value': open_positions_value,
            'open_positions': serializable_positions,
            'last_updated': datetime.now().isoformat()
        }
        try:
            os.makedirs(os.path.dirname(self.status_filepath), exist_ok=True)
            with open(self.status_filepath, 'w') as f:
                json.dump(status_data, f, indent=4)
            logger.debug("Portfolio status file updated.")
        except Exception as e:
            logger.error(f"Failed to write portfolio status file: {e}")

        # --- Upload status to GitHub Gist ---
        if self.github:
            try:
                gist = self.github.get_gist(self.gist_id)
                gist.edit(files={"portfolio_status.json": InputFileContent(json.dumps(status_data, indent=4))})
                logger.info("Successfully updated portfolio status Gist.")
            except Exception as e:
                logger.error(f"Failed to update portfolio status Gist: {e}")


    def manage_open_positions(self):
        """Checks each open position against its stop-loss and take-profit levels."""
        if not self.positions:
            return

        logger.debug(f"Managing {len(self.positions)} open positions...")
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            ltp_data = self.executor.get_ltp_data(name=symbol)
            
            if not ltp_data or 'ltp' not in ltp_data:
                logger.warning(f"Could not get LTP for open position {symbol}. Skipping management check.")
                continue
            
            current_price = ltp_data['ltp']
            
            if current_price <= position['stop_loss']:
                logger.info(f"STOP-LOSS triggered for {symbol} at {current_price:.2f}")
                self.execute_sell(symbol, position['quantity'], 'STOP_LOSS_HIT')
            elif current_price >= position['take_profit']:
                logger.info(f"TAKE-PROFIT triggered for {symbol} at {current_price:.2f}")
                self.execute_sell(symbol, position['quantity'], 'TAKE_PROFIT_HIT')

    def scan_for_new_trades(self, watchlist: list[str]):
        """Scans the watchlist for new BUY signals."""
        logger.debug(f"Scanning {len(watchlist)} stocks for new trades...")
        for symbol in watchlist:
            if symbol in self.positions:
                continue  # Already have a position in this stock

            data = self.data_fetcher.fetch_historical_data(symbol, 'NSE', Interval.in_5_minute, 100)
            if data is None:
                continue

            # --- Calculate Indicators ---
            # This step was missing. We must enrich the raw data with indicators before passing it to the strategy.
            data = calculate_rsi(data)
            data = calculate_macd(data)
            data = calculate_bollinger_bands(
                data,
                period=self.params.get('bb_period', 20),
                std_dev=self.params.get('bb_std_dev', 2)
            )
            data.dropna(inplace=True)
            if data.empty:
                logger.warning(f"Data for {symbol} became empty after indicator calculation. Skipping.")
                continue
            
            signal = self.strategy.generate_signal(data)
            if signal == 'BUY':
                logger.info(f"Technical BUY signal detected for {symbol}.")
                
                # --- AI Confirmation Step ---
                if self.ai_analyzer:
                    ai_verdict = self.ai_analyzer.analyze_trade_setup(symbol, data)
                    if ai_verdict == "CONFIRM":
                        logger.info(f"AI has CONFIRMED the trade for {symbol}. Proceeding to execute.")
                        self.execute_buy(symbol, data['close'].iloc[-1])
                    else:
                        logger.info(f"AI has REJECTED the trade for {symbol}. Skipping.")
                else:
                    # Fallback if no AI analyzer is provided
                    self.execute_buy(symbol, data['close'].iloc[-1])

                if len(self.positions) >= self.max_active_positions:
                    logger.info("Max active positions reached. Pausing new trade scans.")
                    break

    def execute_buy(self, symbol: str, price: float):
        """Executes a buy order and updates the portfolio state."""
        trade_value = self.cash * (self.capital_per_trade_pct / 100)
        quantity = int(trade_value / price)

        if quantity == 0:
            logger.warning(f"Not enough cash to buy even 1 share of {symbol} at {price:.2f}")
            return

        logger.info(f"Attempting to BUY {quantity} of {symbol} at market price.")
        order_response = self.executor.place_order(symbol, quantity, 'MARKET', 'BUY')

        if order_response and order_response.get('status') == 'success':
            entry_price = price  # Approximate with current price for now
            self.cash -= (entry_price * quantity)
            
            self.positions[symbol] = {
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': entry_price * (1 - self.stop_loss_pct / 100),
                'take_profit': entry_price * (1 + self.take_profit_pct / 100),
                'entry_timestamp': datetime.now(),
                'order_id': order_response.get('order_id')
            }
            logger.info(f"Successfully opened position for {symbol}: {self.positions[symbol]}")
        else:
            logger.error(f"Failed to execute BUY order for {symbol}: {order_response}")

    def execute_sell(self, symbol: str, quantity: int, reason: str):
        """Executes a sell order and updates the portfolio state."""
        logger.info(f"Attempting to SELL {quantity} of {symbol} at market price due to: {reason}")
        order_response = self.executor.place_order(symbol, quantity, 'MARKET', 'SELL')

        if order_response and order_response.get('status') == 'success':
            position = self.positions.pop(symbol)
            ltp_data = self.executor.get_ltp_data(name=symbol)
            exit_price = ltp_data['ltp'] if ltp_data else position['entry_price']
            pnl = (exit_price - position['entry_price']) * quantity
            self.cash += (exit_price * quantity)

            # Create and log the completed trade record
            trade_record = {
                'symbol': symbol,
                'entry_timestamp': position['entry_timestamp'],
                'entry_price': position['entry_price'],
                'exit_timestamp': datetime.now(),
                'exit_price': exit_price,
                'quantity': quantity,
                'pnl': pnl,
                'exit_reason': reason
            }
            self.trade_log.append(trade_record)
            self.journal.log_trade(trade_record)

            logger.info(f"Successfully closed position for {symbol}. PnL: {pnl:.2f}. New Cash: {self.cash:.2f}")
        else:
            logger.error(f"Failed to execute SELL order for {symbol}: {order_response}")

    def close_all_positions(self):
        """Closes all currently open positions."""
        logger.info("Closing all open positions...")
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            self.execute_sell(symbol, position['quantity'], 'EOD_CLOSE')