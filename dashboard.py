import streamlit as st
import pandas as pd
import requests
import json
import os
from glob import glob
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="🤖",
    layout="wide",
)

# --- Helper Functions ---
def get_latest_file(pattern):
    """Finds the most recently modified file matching a pattern."""
    try:
        list_of_files = glob(pattern)
        if not list_of_files:
            return None
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file
    except Exception as e:
        st.error(f"Error finding latest file for pattern '{pattern}': {e}")
        return None

def load_trade_journal():
    """Loads the most recent trade journal into a pandas DataFrame."""
    journal_file = get_latest_file('logs/trade_journal_*.csv')
    if journal_file:
        try:
            df = pd.read_csv(journal_file)
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Error loading trade journal '{journal_file}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def get_backtest_symbols():
    """Scans the results directory to find available backtested symbols."""
    results_dir = 'results'
    if not os.path.exists(results_dir):
        return []
    files = os.listdir(results_dir)
    # Extract symbol from filenames like 'RELIANCE_performance.json'
    symbols = [f.split('_performance.json')[0] for f in files if f.endswith('_performance.json')]
    return sorted(list(set(symbols)))

def _load_local_status_file():
    """Helper to load local status file for testing."""
    status_file = 'logs/portfolio_status.json'
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading local portfolio status file: {e}")
            return {}
    return {}

def load_portfolio_status():
    """Loads the latest portfolio status from the JSON file."""
    try:
        # This block will execute successfully in the cloud where secrets are defined.
        status_url = st.secrets["GIST_RAW_URL"]
        response = requests.get(status_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except (st.errors.StreamlitAPIException, KeyError):
        # This block will execute on a local machine where secrets are not available.
        return _load_local_status_file()
    except requests.RequestException as e:
        st.error(f"Error loading portfolio status from URL: {e}")
        return {}

# --- Main Dashboard ---
st.title("📈 Live Trading Bot Dashboard")

# Auto-refreshing mechanism
st.button("Refresh")

# --- Load Data ---
journal_df = load_trade_journal()
status_data = load_portfolio_status()

# --- KPIs from Completed Trades ---
st.header("Journal Performance (Completed Trades)")

total_pnl = journal_df['pnl'].sum() if not journal_df.empty else 0
total_trades = len(journal_df)
winning_trades = len(journal_df[journal_df['pnl'] > 0]) if total_trades > 0 else 0
win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total PnL", f"₹{total_pnl:,.2f}")
col2.metric("Total Trades", total_trades)
col3.metric("Winning Trades", winning_trades)
col4.metric("Win Rate", f"{win_rate:.2f}%")

# --- Live Portfolio Status ---
st.header("Live Portfolio Status")

if status_data:
    last_updated = datetime.fromisoformat(status_data.get('last_updated', ''))
    st.caption(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
    
    p_col1, p_col2, p_col3 = st.columns(3)
    p_col1.metric("Current Portfolio Value", f"₹{status_data.get('portfolio_value', 0):,.2f}")
    p_col2.metric("Live PnL", f"₹{status_data.get('pnl', 0):,.2f} ({status_data.get('pnl_pct', 0):.2f}%)")
    p_col3.metric("Cash", f"₹{status_data.get('cash', 0):,.2f}")

    st.subheader("Open Positions")
    open_positions = status_data.get('open_positions', {})
    if open_positions:
        positions_list = [{'Symbol': symbol, **data} for symbol, data in open_positions.items()]
        positions_df = pd.DataFrame(positions_list)
        st.dataframe(positions_df, use_container_width=True)
    else:
        st.info("No open positions.")
else:
    st.warning("Portfolio status file not found. Is the live trader running?")

# --- Trade Journal ---
st.header("Completed Trade Journal")
if not journal_df.empty:
    st.dataframe(journal_df.sort_values(by='exit_timestamp', ascending=False), use_container_width=True)
else:
    st.info("No completed trades in the journal yet.")

# --- Backtest Results ---
st.header("Backtest Analysis")
backtest_symbols = get_backtest_symbols()

if not backtest_symbols:
    st.info("No backtest results found. Run a backtest first using `python src/main.py backtest`.")
else:
    selected_symbol = st.selectbox("Select a stock to view its backtest results:", backtest_symbols)

    if selected_symbol:
        # Load performance data
        perf_file = f"results/{selected_symbol}_performance.json"
        if os.path.exists(perf_file):
            with open(perf_file, 'r') as f:
                perf_data = json.load(f)
            
            st.subheader(f"Performance Metrics for {selected_symbol}")
            
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Net PnL", f"₹{perf_data.get('net_pnl', 0):,.2f}")
            m_col2.metric("Total Return", f"{perf_data.get('total_return_pct', 0):.2f}%")
            m_col3.metric("Win Rate", f"{perf_data.get('win_rate_pct', 0):.2f}%")
            m_col4.metric("Sharpe Ratio", f"{perf_data.get('sharpe_ratio', 0):.2f}")
        
        # Display plots
        st.subheader("Backtest Charts")
        equity_chart_path = f"results/equity_curve_{selected_symbol}.png"
        trades_chart_path = f"results/trades_chart_{selected_symbol}.png"

        if os.path.exists(equity_chart_path):
            st.image(equity_chart_path, caption="Equity Curve", use_column_width=True)

        if os.path.exists(trades_chart_path):
            st.image(trades_chart_path, caption="Trade Analysis Chart", use_column_width=True)