# Stock App

A desktop stock portfolio viewer and predictor built with Python and PyQt6.

![Python](https://img.shields.io/badge/python-3.10--3.12-blue)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-informational)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Multi-user login** — branded card-style login and registration dialogs; each user has their own portfolio and cached data
- **Live stock data** — historical price data fetched from Yahoo Finance via `yfinance`
- **Interactive chart** — gradient price line with hover tooltip; compact bottom toolbar with date range buttons (1M / 3M / 6M / 1Y / All) on the left and indicator toggles on the right
- **Technical indicators** — toggle SMA 20, SMA 50, and EMA 20 overlays on the chart; buttons highlight when active
- **30-day prediction** — Meta's Prophet model draws a confidence band on the chart and emits a BUY / HOLD / SELL signal
- **AI market analysis** — Claude scores a stock −10 to +10 with a plain-English summary, pros/cons, and insider trade context; results are cached per user for 24 hours
- **Insider trades panel** — recent SEC insider transactions for the selected stock, sourced from Finnhub
- **Portfolio tracker** — record positions (shares, cost basis, optional sell target); interactive animated donut chart with per-holding hover detail and gain/loss stats; performance card shows total cost, current value, gain/loss %, and distance to sell target
- **Add Stock dialog** — card-style dialog matching the login aesthetic; shows Market Highlights (Top Gainers, Top Losers, Most Active) as clickable chips populated from the Explore cache; clicking a chip fills the symbol field
- **Stock rename** — pencil button (✎) next to the stock name in the info panel lets you set a custom display name per holding; updates the dropdown combo immediately
- **Market explorer** — Explore tab shows live Top Gainers, Top Losers, Most Active, and Biggest Movers across the full S&P 500 (~503 tickers), fetched fresh daily from Wikipedia and cached for the session; market overview bar shows gainers/losers count and average move at a glance; real-time search filters by symbol or company name across the active tab; directional arrows (▲/▼) on change %; double-click any row (or use the per-row button) to add a stock to your portfolio; status line shows the data timestamp so you always know how fresh the numbers are
- **User settings** — card-style sidebar dialog with four sections: Profile (avatar photo upload, username change with uniqueness validation, email, phone), Appearance (pill Dark/Light toggle), Security (inline password change with validation), and API Keys (per-key status chips with Update and Delete buttons); theme change applies instantly across every panel without restart
- **Per-user API keys** — each user stores their own Anthropic and Finnhub keys locally in a gitignored file; in-app prompts guide users to add keys the first time they use a feature that needs one; keys can also be managed from Settings → API Keys (shows ✓ Set / ✗ Not set status, Update opens the card-style key dialog, Delete removes the key immediately)

---

## Requirements

- **Python 3.10–3.12** — Prophet's dependencies are not always compatible with newer Python versions
- **Anthropic API key** — for AI analysis; get one at [console.anthropic.com](https://console.anthropic.com)
- **Finnhub API key** — for insider trades; free tier at [finnhub.io](https://finnhub.io), no credit card required

Both API keys are optional — all other features work without them. Keys are set per user inside the app (see below).

---

## Setup

### 1. Clone

```bash
git clone https://github.com/ssavory/Stock-App.git
cd Stock-App
```

### 2. Run the setup script

**Windows** — double-click `setup.bat`, or run it in a terminal:
```bat
setup.bat
```

**macOS / Linux** — make the script executable and run it:
```bash
chmod +x setup.sh && ./setup.sh
```

The script creates a virtual environment and installs all dependencies automatically. Prophet takes ~2 minutes to install on the first run.

> **Windows — enable long paths before running setup.**
> `prophet` installs Stan model files with deeply nested paths that exceed Windows' 260-character limit by default.
> Run this once in an **elevated PowerShell** session, then restart your terminal:
> ```powershell
> Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1
> ```

<details>
<summary>Manual setup (alternative)</summary>

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```
</details>

### 4. Add API keys (optional)

API keys are stored **per user** inside the app — no `.env` file required. The first time you trigger a feature that needs a key (AI analysis or insider trades), a dialog will prompt you to enter it. You can also add or update keys at any time via **User Page → Settings → API Keys**.

Keys are saved to `Users/<username>/api_keys.json`, which is gitignored and never committed.

> **Legacy `.env` support** — if you have an existing `.env` file with `ANTHROPIC_API_KEY` or `FINNHUB_API_KEY`, those values are used as a fallback for any user who hasn't set their own key yet.

---

## Running

```bash
# Activate the virtual environment first (if not already active)
# Windows:  venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

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
├── .env                         # Optional legacy API keys (gitignored)
│
├── ui/
│   ├── mainwindow/              # Main app window (all files use relative imports)
│   │   ├── main_window.py       # Thin coordinator — owns workers, connects panel signals
│   │   ├── info_panel.py        # Left panel — stock header, stats, insider trades, AI, portfolio tab
│   │   ├── chart_panel.py       # Right panel — stock selector, chart, date range, indicators
│   │   ├── stock_chart.py       # Self-contained pyqtgraph chart widget
│   │   ├── explore_panel.py     # Explore tab — market screener tables
│   │   ├── portfolio_page.py    # Full-window portfolio page with interactive donut chart
│   │   ├── add_stock_dialog.py  # AddStockDialog — card-style add dialog with market highlight chips
│   │   ├── ai_analysis_dialog.py
│   │   ├── api_key_dialog.py    # ApiKeyDialog — card-style dialog for adding/updating a single API key
│   │   └── settings_dialog.py   # UserSettingsDialog — card + sidebar nav (Profile / Appearance / Security / API Keys)
│   ├── login_page.py
│   ├── register_page.py
│   └── theme.py                 # Centralised colour + font token system; get_tokens() returns a merged dict used by every UI component
│
├── core/
│   ├── stock_handler.py         # yfinance fetching, SMA/EMA calculations
│   ├── caching.py               # Per-user cache manager (stock data + AI results + portfolio)
│   ├── user_manager.py          # Profile read/write
│   ├── key_manager.py           # Per-user API key storage (get_key / set_key / delete_key)
│   ├── stock_model.py           # StockPackage dataclass
│   ├── prediction_worker.py     # QThread — Prophet 30-day forecast
│   ├── ai_analysis_worker.py    # QThread — Claude API market analysis
│   ├── senate_worker.py         # QThread — Finnhub insider trades
│   └── explore_worker.py        # QThread — batch market data for Explore tab
│
└── Users/
    └── <username>/
        ├── profile.json         # Committed — preferences and hashed credentials
        ├── api_keys.json        # Gitignored — per-user API keys (Anthropic, Finnhub)
        ├── cache                # Gitignored — stock metadata, AI results, portfolio positions
        └── csvFiles/            # Gitignored — downloaded price CSVs (rebuilt on first use)
```

---

## Notes

- Stock CSVs and cache files are not committed to the repo — they are downloaded and rebuilt automatically on first use on any machine
- AI analysis results are cached per user for 24 hours to avoid redundant API calls
- The portfolio donut chart uses PyQt6's `QPainter` directly — `matplotlib` is only present as a transitive dependency of Prophet and is not used by the UI
- API keys are stored in `Users/<username>/api_keys.json` (gitignored); they are never written to `profile.json`, which is committed to git
