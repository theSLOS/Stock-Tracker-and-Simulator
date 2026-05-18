# Stock App

A desktop stock portfolio viewer and predictor built with Python and PyQt6.

## Features

- **Multi-user login** — each user has their own portfolio and cached data
- **Live stock data** — fetches historical price data from Yahoo Finance via `yfinance`
- **Interactive chart** — gradient price line with a hover tooltip showing date, price, and daily change
- **Technical indicators** — toggle SMA 20, SMA 50, and EMA 20 overlays on the chart
- **Date range filter** — view 1 month, 3 months, 6 months, 1 year, or all-time data
- **30-day price prediction** — powered by Meta's Prophet model, with a confidence band drawn on the chart and a BUY / HOLD / SELL signal

## Requirements

- Python 3.10+
- See `requirements.txt` for all dependencies

## Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/ssavory/Stock-App.git
cd Stock-App
pip install -r requirements.txt
```

> **Note:** `prophet` pulls in a number of dependencies (including `cmdstanpy` and `matplotlib`) and may take a minute to install.

## Running the app

```bash
python main.py
```

On first launch you will be prompted to log in. Use the **New User** button to create an account. Once logged in, your default stock (AAPL) will be fetched automatically if your portfolio is empty.

## Project structure

```
Stock-App/
├── main.py               # Entry point
├── requirements.txt
├── ui/                   # All UI components
│   ├── main_window.py    # Main window and app logic
│   ├── stock_chart.py    # Self-contained chart widget (pyqtgraph)
│   ├── login_page.py     # Login dialog
│   └── register_page.py  # New user registration dialog
├── core/                 # Business logic and data layer
│   ├── stock_handler.py  # yfinance data fetching and indicator calculations
│   ├── caching.py        # Per-user stock cache manager
│   ├── user_manager.py   # User profile read/write
│   ├── stock_model.py    # StockPackage data model
│   └── prediction_worker.py  # Background thread running the Prophet model
└── Users/
    └── <username>/
        ├── profile.json  # User settings and preferences
        ├── cache         # Cached stock metadata (gitignored)
        └── csvFiles/     # Downloaded price CSVs (gitignored)
```

## Notes

- Stock CSVs and cache files are **not committed to git** — they are downloaded fresh on each new machine
- The `.env` file (if used) can set a `CSV_PATH` override, but this is optional — the app defaults to per-user folders inside `Users/`
