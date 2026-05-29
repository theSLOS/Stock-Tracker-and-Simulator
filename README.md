# Stock App

A desktop stock portfolio viewer and predictor built with Python and PyQt6.

## Features

- **Multi-user login** — each user has their own portfolio and cached data
- **Live stock data** — fetches historical price data from Yahoo Finance via `yfinance`
- **Interactive chart** — gradient price line with a hover tooltip showing date, price, and daily change
- **Technical indicators** — toggle SMA 20, SMA 50, and EMA 20 overlays on the chart
- **Date range filter** — view 1 month, 3 months, 6 months, 1 year, or all-time data
- **30-day price prediction** — powered by Meta's Prophet model, with a confidence band drawn on the chart and a BUY / HOLD / SELL signal
- **AI market analysis** — uses the Claude API to score a stock -10 to +10, with a plain-English summary, pros and cons, and insider trade context; results are cached per-user for 24 hours
- **Insider trades panel** — shows recent executive and director trades (SEC filings) for the selected stock, sourced from Finnhub

## Requirements

- Python 3.10+
- An **Anthropic API key** (for AI analysis) — `ANTHROPIC_API_KEY=sk-ant-...`
- A **Finnhub API key** (for insider trades) — `FINNHUB_API_KEY=...` — free account at [finnhub.io](https://finnhub.io), no credit card required
- See `requirements.txt` for all Python dependencies

## Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/ssavory/Stock-App.git
cd Stock-App
pip install -r requirements.txt
```

> **Note:** `prophet` pulls in a number of dependencies (including `cmdstanpy` and `matplotlib`) and may take a minute or two to install. On Windows, you may need to enable long path support first — see [pip's long paths guide](https://pip.pypa.io/warnings/enable-long-paths).

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=your_finnhub_key
```

The AI analysis feature requires `ANTHROPIC_API_KEY`. The insider trades panel requires `FINNHUB_API_KEY`. All other features work without either key.

## Running the app

```bash
python main.py
```

On first launch you will be prompted to log in. Use the **New User** button to create an account. Once logged in, your default stock (AAPL) will be fetched automatically if your portfolio is empty.

To skip the login dialog and auto-login from the terminal, pass `--user` and `--password`:

```bash
python main.py --user admin --password password
```

Short flags also work:

```bash
python main.py -u admin -p password
```

If the credentials are invalid the app falls back to the normal login dialog.

## Project structure

```
Stock-App/
├── main.py               # Entry point
├── requirements.txt
├── .env                  # API keys (not committed)
├── ui/                   # All UI components
│   ├── main_window.py        # Main window — wires panels, owns background workers
│   ├── info_panel.py         # Left panel — stock header, stats tabs, insider trades, AI/prediction
│   ├── chart_panel.py        # Right panel — stock selector, chart, date range, indicators
│   ├── stock_chart.py        # Self-contained chart widget (pyqtgraph)
│   ├── login_page.py         # Login dialog
│   ├── register_page.py      # New user registration dialog
│   └── ai_analysis_dialog.py # AI analysis results dialog
├── core/                 # Business logic and data layer
│   ├── stock_handler.py      # yfinance data fetching and indicator calculations
│   ├── caching.py            # Per-user stock cache manager (also stores AI analysis)
│   ├── user_manager.py       # User profile read/write
│   ├── stock_model.py        # StockPackage data model
│   ├── prediction_worker.py  # Background thread running the Prophet model
│   ├── ai_analysis_worker.py # Background thread running the Claude AI analysis
│   └── senate_worker.py      # Background thread fetching insider trades from Finnhub
└── Users/
    └── <username>/
        ├── profile.json  # User settings and preferences
        ├── cache         # Cached stock metadata + AI analysis results (gitignored)
        └── csvFiles/     # Downloaded price CSVs (gitignored)
```

## Notes

- Stock CSVs and cache files are **not committed to git** — they are downloaded fresh on each new machine
- AI analysis results are cached inside the user's cache file for 24 hours to avoid redundant API calls
- The `.env` file sets `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`, and optional `CSV_PATH`/`CACHE_PATH` overrides
