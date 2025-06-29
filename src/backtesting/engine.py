import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

from src.core.strategy import TradingStrategy

logger = logging.getLogger(__name__)

class BacktestingEngine:
    """
    A simple, event-driven backtesting engine.
    It simulates a trading strategy over historical data and calculates performance.    
    """

    def __init__(self, initial_capital: float = 100000.0, stop_loss_pct: float = 0.0, take_profit_pct: float = 0.0):
        """
        Initializes the backtesting engine.

        Args:
            initial_capital (float): The starting capital for the backtest.
            stop_loss_pct (float): The stop-loss percentage.
            take_profit_pct (float): The take-profit percentage.
        """
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.positions = {}  # To hold current positions, e.g., {'RELIANCE': 10}
        self.equity_curve = []  # To track portfolio value over time
        self.completed_trades = []  # A log of all completed trades (buy/sell pairs)
        self.open_trade_entry = None # To hold details of the current open trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.results_dir = "results"
        logger.info(f"Backtesting Engine initialized. Capital: {self.initial_capital}, SL: {self.stop_loss_pct}%, TP: {self.take_profit_pct}%")

    def run(self, data: pd.DataFrame, strategy: TradingStrategy, symbol: str, plot: bool = True):
        """
        Runs the backtest over the provided historical data.

        Args:
            data (pd.DataFrame): DataFrame with OHLCV data and indicators.
            strategy (TradingStrategy): An instance of a trading strategy class.
            symbol (str): The stock symbol being backtested, used for logging and plotting.
            plot (bool): If True, generates and saves result plots.
        """
        logger.info(f"Starting backtest on {len(data)} bars of data...")
        if len(data) < 2:
            logger.warning("Not enough data to run a backtest. Aborting.")
            return

        # Start the equity curve with the initial capital
        self.equity_curve = [self.initial_capital]

        # --- Main Backtesting Loop ---
        for i in range(1, len(data)):
            # We use a rolling window of data to simulate looking at the past
            # This is inefficient for large datasets but simple for this example.
            current_data_window = data.iloc[0:i+1]
            current_timestamp = current_data_window.index[-1]

            # --- Check for SL/TP on open positions ---
            if self.positions and self.open_trade_entry:
                position_details = self.open_trade_entry
                # Use high/low of the bar for a more realistic simulation
                low_price = current_data_window['low'].iloc[-1]
                high_price = current_data_window['high'].iloc[-1]

                # Check stop-loss
                if position_details.get('stop_loss', 0) > 0 and low_price <= position_details['stop_loss']:
                    # Exit at the stop-loss price, not the bar's low
                    self._close_position(position_details['stop_loss'], current_timestamp, 'STOP_LOSS_HIT')
                    # Update portfolio value and continue to next bar
                    self.equity_curve.append(self.equity)
                    continue
                
                # Check take-profit
                if high_price >= position_details.get('take_profit', float('inf')):
                    # Exit at the take-profit price
                    self._close_position(position_details['take_profit'], current_timestamp, 'TAKE_PROFIT_HIT')
                    # Update portfolio value and continue to next bar
                    self.equity_curve.append(self.equity)
                    continue

            # --- Simulate Trade Execution based on Strategy Signal ---
            signal = strategy.generate_signal(current_data_window)
            current_price = current_data_window['close'].iloc[-1]

            if signal == 'BUY' and not self.positions:
                quantity = self.equity / current_price
                self.positions['current_trade'] = {'quantity': quantity, 'entry_price': current_price}
                self.equity = 0
                # Log the entry point of the trade
                self.open_trade_entry = {
                    'entry_timestamp': current_timestamp,
                    'entry_price': current_price,
                    'quantity': quantity,
                    'stop_loss': current_price * (1 - self.stop_loss_pct / 100) if self.stop_loss_pct > 0 else 0,
                    'take_profit': current_price * (1 + self.take_profit_pct / 100) if self.take_profit_pct > 0 else float('inf')
                }
                logger.info(f"BUY {quantity:.2f} at {current_price:.2f} on {current_timestamp}")

            elif signal == 'SELL' and self.positions:
                self._close_position(current_price, current_timestamp, 'STRATEGY_SELL')

            # Update portfolio value at each step
            portfolio_value = self.equity
            if self.positions:
                portfolio_value += self.positions['current_trade']['quantity'] * current_price
            self.equity_curve.append(portfolio_value)
        # If a position is still open at the end, close it at the last price
        if self.positions and self.open_trade_entry:
            position = self.positions.pop('current_trade')
            last_price = data['close'].iloc[-1]
            last_timestamp = data.index[-1]
            self.equity = position['quantity'] * last_price
            # Note: We do not append to equity_curve here as the last value is already calculated in the loop.
            self._close_position(last_price, last_timestamp, 'EOD_CLOSE')

        logger.info("Backtest run complete.")
        results = self.calculate_performance()
        self.print_results(results)
        if plot:
            self.generate_plots(data, symbol)
        return results

    def _close_position(self, exit_price: float, exit_timestamp, reason: str):
        """A helper function to close an open position and log the trade."""
        if 'current_trade' not in self.positions or not self.open_trade_entry:
            logger.warning("Attempted to close a position that was not open.")
            return

        position = self.positions.pop('current_trade')
        self.equity = position['quantity'] * exit_price
        
        pnl = (exit_price - self.open_trade_entry['entry_price']) * self.open_trade_entry['quantity']
        completed_trade = {
            **self.open_trade_entry, 
            'exit_timestamp': exit_timestamp, 
            'exit_price': exit_price, 
            'pnl': pnl,
            'exit_reason': reason
        }
        self.completed_trades.append(completed_trade)
        self.open_trade_entry = None
        logger.info(f"SELL ({reason}) at {exit_price:.2f} on {exit_timestamp} | PnL: {pnl:.2f}")

    def calculate_performance(self) -> dict:
        """
        Calculates a dictionary of performance metrics for the backtest.
        """
        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        total_return = ((final_equity / self.initial_capital) - 1) * 100
        total_pnl = final_equity - self.initial_capital

        # --- Calculate Win Rate ---
        winning_trades = 0
        for trade in self.completed_trades:
            if trade.get('pnl', 0) > 0:
                winning_trades += 1
        win_rate = (winning_trades / len(self.completed_trades)) * 100 if self.completed_trades else 0.0

        # --- Calculate Max Drawdown ---
        equity_series = pd.Series(self.equity_curve)
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = drawdown.min() * 100 if not drawdown.empty else 0

        # --- Calculate Sharpe Ratio (annualized) ---
        # Assuming hourly data, approx. 252 * 6.5 trading hours in a year
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = 0
        if not returns.empty and returns.std() != 0:
            annualization_factor = np.sqrt(252 * 6.5)
            sharpe_ratio = (returns.mean() / returns.std()) * annualization_factor
        
        return {
            "initial_capital": self.initial_capital,
            "final_equity": final_equity,
            "net_pnl": total_pnl,
            "total_return_pct": total_return,
            "total_trades": len(self.completed_trades),
            "win_rate_pct": win_rate,
            "max_drawdown_pct": max_drawdown,
            "sharpe_ratio": sharpe_ratio
        }

    def print_results(self, results: dict):
        """Prints a summary of the backtest performance from a results dictionary."""
        logger.info("--- Backtest Results ---")
        for key, value in results.items():
            logger.info(f"{key.replace('_', ' ').title():<25}: {value:,.2f}")

    def generate_plots(self, data: pd.DataFrame, symbol: str):
        """
        Generates and saves all result plots into the 'results' directory.
        """
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            logger.info(f"Created results directory: {self.results_dir}")

        self._plot_equity_curve(data, symbol)
        self._plot_trades_on_price(data, symbol)

    def _plot_equity_curve(self, data: pd.DataFrame, symbol: str):
        """Plots and saves the equity curve."""
        if not self.equity_curve:
            logger.warning("Equity curve is empty, cannot generate plot.")
            return

        logger.info(f"Plotting equity curve for {symbol}...")
        plt.figure(figsize=(12, 6))
        # Use the data's index for the x-axis for accurate time representation
        # We slice equity_curve to match the length of the data index used in the loop
        plt.plot(data.index, self.equity_curve[1:], label='Equity Curve')
        plt.title(f'Portfolio Equity Curve for {symbol}')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.grid(True)
        plt.legend()
        
        plot_path = os.path.join(self.results_dir, f'equity_curve_{symbol}.png')
        plt.savefig(plot_path)
        plt.close()
        logger.info(f"Equity curve plot saved to {plot_path}")

    def _plot_trades_on_price(self, data: pd.DataFrame, symbol: str):
        """Plots the price chart with trade entry and exit markers."""
        if not self.completed_trades:
            logger.info(f"No completed trades for {symbol}, skipping trade plot.")
            return

        logger.info(f"Plotting trade entries and exits for {symbol}...")
        plt.figure(figsize=(15, 7))
        plt.plot(data.index, data['close'], label='Close Price', color='skyblue', alpha=0.8)

        entry_times = [trade['entry_timestamp'] for trade in self.completed_trades]
        entry_prices = [trade['entry_price'] for trade in self.completed_trades]
        exit_times = [trade['exit_timestamp'] for trade in self.completed_trades]
        exit_prices = [trade['exit_price'] for trade in self.completed_trades]

        plt.scatter(entry_times, entry_prices, marker='^', color='green', s=120, label='Buy Entry', zorder=5)
        plt.scatter(exit_times, exit_prices, marker='v', color='red', s=120, label='Sell Exit', zorder=5)

        plt.title(f'Trade Analysis for {symbol}')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        plot_path = os.path.join(self.results_dir, f'trades_chart_{symbol}.png')
        plt.savefig(plot_path)
        plt.close()
        logger.info(f"Trade analysis chart saved to {plot_path}")