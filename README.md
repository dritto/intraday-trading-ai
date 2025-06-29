# Intelligent Intraday Trading System for Nifty 50

This project is an automated, intelligent intraday trading system for Nifty 50 stocks. It uses real-time and historical data from TradingView, performs multi-faceted analysis using technical indicators and AI, and executes trades via Angel One's SmartAPI.

## Project Goal

The primary objective is to develop a modular and adaptive trading bot that can:
1.  **Pre-Market Analysis:** Identify high-potential long and short candidates from the Nifty 50 list before the market opens.
2.  **Live Trading:** Execute high-probability trades during the intraday session based on a confluence of signals.
3.  **Backtesting:** Rigorously test and validate trading strategies on historical data.
4.  **AI-Driven Insights:** Leverage AI to refine strategies, justify trades, and adapt to changing market conditions.

## Installation and Setup

Follow these steps to set up your local development environment.

### 1. Prerequisites
- Python 3.8 or newer

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to manage project dependencies.

```bash
# Navigate to your project root directory
cd /path/to/trading_system

# Create a virtual environment
python -m venv venv

# Activate the environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Configure Credentials
Open the `config/settings.yaml` file and replace the placeholder values with your actual TradingView username and password.

### 5. Run the Example
To verify that your setup is working correctly, run the example script that fetches data from TradingView.

```bash
python examples/run_data_fetch_test.py
```

To ensure the system is modular, scalable, and easy to maintain, the following project structure is recommended. It organizes the code based on functionality and follows standard Python project conventions.

```
trading_system/
├── src/
│   ├── __init__.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── indicators.py         # Technical indicator calculations
│   │   ├── sentiment.py          # Sentiment analysis (e.g., Gift Nifty)
│   │   └── sector.py             # Sector influence analysis
│   ├── core/
│   │   ├── __init__.py
│   │   └── strategy.py           # Core trading logic and decision-making
│   ├── data/
│   │   ├── __init__.py
│   │   └── data_fetcher.py       # Handles TradingView data (historical & real-time)
│   ├── execution/
│   │   ├── __init__.py
│   │   └── angelone_executor.py  # Angel One SmartAPI integration
│   ├── backtesting/
│   │   ├── __init__.py
│   │   └── engine.py             # Backtesting engine
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py             # Centralized logging setup
│   │   └── trade_journal.py      # Trade logging and journaling
│   └── main.py                   # Main application entry point (to be created)
├── examples/
│   └── run_data_fetch_test.py    # Example script to test data fetching
├── tests/                        # Directory for unit and integration tests
│   └── ...
├── config/
│   └── settings.yaml             # Configuration for API keys, strategy params
├── notebooks/                    # Jupyter notebooks for research and analysis
│   └── initial_analysis.ipynb
├── logs/
│   └── app.log
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```