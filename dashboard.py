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

def load_portfolio_status():
    """Loads the latest portfolio status from the JSON file."""
    # For cloud deployment, read from a URL defined in secrets.
    # For local testing, fall back to the local file.
    status_url = st.secrets.get("GIST_RAW_URL")
    if status_url:
        try:
            response = requests.get(status_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error loading portfolio status from URL: {e}")
            return {}
    else: # Local fallback
        return _load_local_status_file()

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