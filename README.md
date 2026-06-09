# Stock App

A desktop stock portfolio viewer and predictor built with Python and PyQt6.

![Python](https://img.shields.io/badge/python-3.10--3.12-blue)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-informational)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Multi-user login** — register or log in; each user has their own portfolio and cached data
- **Live stock data** — historical price data fetched from Yahoo Finance via `yfinance`
- **Interactive chart** — gradient price line with hover tooltip; configurable date range (1M / 3M / 6M / 1Y / All)
- **Technical indicators** — toggle SMA 20, SMA 50, and EMA 20 overlays on the chart
- **30-day prediction** — Meta's Prophet model draws a confidence band on the chart and emits a BUY / HOLD / SELL signal
- **AI market analysis** — Claude scores a stock −10 to +10 with a plain-English summary, pros/cons, and insider trade context; results are cached per user for 24 hours
- **Insider trades panel** — recent SEC insider transactions for the selected stock, sourced from Finnhub
- **Portfolio tracker** — record positions (shares, cost basis, optional sell target); interactive animated donut chart with per-holding hover detail and gain/loss stats
- **User settings** — edit profile fields, change password, toggle dark/light theme

---

## Requirements

- **Python 3.10–3.12** — Prophet's dependencies are not always compatible with newer Python versions
- **Anthropic API key** — for AI analysis (`ANTHROPIC_API_KEY`)
- **Finnhub API key** — for insider trades (`FINNHUB_API_KEY`); free tier at [finnhub.io](https://finnhub.io), no credit card required

Both API keys are optional — all other features work without them.

---

## Setup

### 1. Clone

```bash
git clone https://github.com/ssavory/Stock-App.git
cd Stock-App
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Windows — enable long paths before installing.**
> `prophet` installs Stan model files with deeply nested paths that exceed Windows' 260-character limit by default.
> Run this once in an **elevated PowerShell** session, then restart your terminal:
> ```powershell
> Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1
> ```

`prophet` also pulls in `cmdstanpy` and `matplotlib` — expect the first install to take a couple of minutes.

### 4. Add API keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=your_key_here
```

---

## Running

```bash
python main.py
```

On first launch you will be prompted to log in. Register a new account or use one of the test accounts below. AAPL data is fetched automatically when your portfolio is empty.

**Skip the login prompt** by passing credentials directly:

```bash
python main.py --user admin --password password
python main.py -u admin -p password        # short flags
```

If credentials are invalid, the app falls back to the normal login dialog.

### Test accounts

All test accounts use the password `password`.

| Username | Notes |
|---|---|
| `admin` | AAPL cached |
| `user3` | AAPL, NVDA, AMZN, GOOG, TSLA in portfolio |
| `user2` | AAPL cached |
| `user1` | Empty — downloads AAPL on first login |

---

## Project structure

```
Stock-App/
├── main.py                      # Entry point — wires login → main window
├── requirements.txt
├── .env                         # API keys (not committed)
│
├── ui/
│   ├── mainwindow/              # Main app window (all files use relative imports)
│   │   ├── main_window.py       # Thin coordinator — owns workers, connects panel signals
│   │   ├── info_panel.py        # Left panel — stock header, stats, insider trades, AI, portfolio tab
│   │   ├── chart_panel.py       # Right panel — stock selector, chart, date range, indicators
│   │   ├── stock_chart.py       # Self-contained pyqtgraph chart widget
│   │   ├── portfolio_page.py    # Full-window portfolio page with interactive donut chart
│   │   ├── ai_analysis_dialog.py
│   │   └── settings_dialog.py
│   ├── login_page.py
│   ├── register_page.py
│   └── theme.py                 # Shared dark/light palette utility
│
├── core/
│   ├── stock_handler.py         # yfinance fetching, SMA/EMA calculations
│   ├── caching.py               # Per-user cache manager (stock data + AI results + portfolio)
│   ├── user_manager.py          # Profile read/write
│   ├── stock_model.py           # StockPackage dataclass
│   ├── prediction_worker.py     # QThread — Prophet 30-day forecast
│   ├── ai_analysis_worker.py    # QThread — Claude API market analysis
│   └── senate_worker.py         # QThread — Finnhub insider trades
│
└── Users/
    └── <username>/
        ├── profile.json         # Committed — preferences and hashed credentials
        ├── cache                # Gitignored — stock metadata, AI results, portfolio positions
        └── csvFiles/            # Gitignored — downloaded price CSVs (rebuilt on first use)
```

---

## Notes

- Stock CSVs and cache files are not committed to the repo — they are downloaded and rebuilt automatically on first use on any machine
- AI analysis results are cached per user for 24 hours to avoid redundant API calls
- The portfolio donut chart uses PyQt6's `QPainter` directly — `matplotlib` is only present as a transitive dependency of Prophet and is not used by the UI
