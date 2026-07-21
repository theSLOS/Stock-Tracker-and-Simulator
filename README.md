# Stock App

A desktop stock portfolio tracker with ML price predictions, AI analysis, and real-time S&P 500 screening — built with Python and PyQt6.

![Python](https://img.shields.io/badge/python-3.10--3.12-blue)
![PyQt6](https://img.shields.io/badge/UI-PyQt6%206.11-informational)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

<p align="center">
  <img src="https://github.com/user-attachments/assets/a63f54d6-0b08-4373-bf70-191696fe461e" width="49%" alt="Main view — dark mode" />
  <img src="https://github.com/user-attachments/assets/f0b9c24d-ba75-4e49-8872-c8776d73fde2" width="49%" alt="Portfolio — animated donut chart" />
</p>
<p align="center">
  <img src="https://github.com/user-attachments/assets/2078c31c-5651-4268-9b15-5cea2bf61de5" width="49%" alt="Market explorer — S&amp;P 500 screener" />
  <img src="https://github.com/user-attachments/assets/b214eea1-8d55-4678-ada1-ee28e452cc2d" width="49%" alt="Main view — light mode" />
</p>

---

## Features

**Portfolio**
- Track positions: shares, cost basis, optional sell target
- Animated donut chart (900ms eased cubic) with interactive hover — per-holding breakdown, gain/loss %, and distance to sell target
- Performance card: total cost, current value, and overall return

**Analysis**
- Interactive price chart with gradient fill; hover tooltip shows date, price, and day-change %
- Toggle overlays: SMA 20, SMA 50, EMA 20
- **30-day prediction** — Meta's Prophet model draws a confidence band and emits a BUY / HOLD / SELL signal
- **AI analysis** — Claude scores a stock −10 to +10 with a plain-English summary and pros/cons breakdown, incorporating recent insider trade context; results are cached per user for 24 hours
- **Insider trades panel** — recent SEC filings for the loaded stock, sourced from Finnhub; color-coded by transaction type

**Market**
- Explore tab: Top Gainers, Top Losers, Most Active, and Biggest Movers across the full S&P 500 (~503 tickers)
- Live search filters by symbol or company name; data loads in the background at login so the tab is ready when you get there
- One-click add from the screener to your portfolio; market highlights also appear as chips in the Add Stock dialog

**System**
- Multi-user login with per-user isolated portfolios, settings, and cached data
- Instant dark/light theme switching — all panels update in under 100ms, no restart
- Per-user API key storage in a gitignored file; in-app prompts guide first-time setup
- Settings sidebar: profile, avatar upload, username rename, password change, API key management

---

## Architecture

`MainWindow` is a thin coordinator — it owns all background workers and connects signals between panels. No panel references another panel directly.

```
┌─────────────────────────────────────────────────────┐
│                    MainWindow                       │
│  ┌──────────────────┐  ┌────────────────────────┐  │
│  │    InfoPanel     │◄─►│      ChartPanel        │  │  ← Portfolio tab
│  │   (fixed 380px)  │  │   (pyqtgraph chart)    │  │
│  └──────────────────┘  └────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │               ExplorePanel                   │  │  ← Explore tab
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                     │ owns and connects
                     ▼
  ┌──────────────────────────────────────────────────┐
  │                Background Workers                │
  │  StockFetchWorker   PredictionWorker             │
  │  AIAnalysisWorker   SenateWorker  ExploreWorker  │
  └──────────────────────────────────────────────────┘
```

### Background workers

All network calls and compute run on `QThread` workers. Workers emit signals and never touch the UI directly.

| Worker | Trigger | Data source | Signals |
|---|---|---|---|
| `StockFetchWorker` | Stock select / add | yfinance → CSV | `finished(StockPackage)` · `error(str)` |
| `PredictionWorker` | Predict button | Prophet (local) | `finished(DataFrame)` · `error(str)` |
| `AIAnalysisWorker` | AI Analysis button | Claude API + Finnhub | `finished(dict)` · `status(str)` · `error(str)` |
| `SenateWorker` | Every stock load | Finnhub | `finished(list)` · `error(str)` |
| `ExploreWorker` | Login / manual refresh | yfinance batch (~503 tickers) | `finished(list)` · `progress(str)` · `error(str)` |

### Caching

| Data | Location | Strategy |
|---|---|---|
| Stock price CSV | `Users/<user>/csvFiles/` | On-demand; re-fetched when stale |
| AI analysis results | `Users/<user>/cache` | 24-hour TTL per stock |
| S&P 500 explore data | `Users/explore_cache.json` | Daily; keyed by calendar date |

---

## Design system

All colours and font sizes live in [`ui/theme.py`](ui/theme.py) as named tokens:

```python
get_tokens("dark")   # → 30+ keys: window, base, price_line, font_symbol, buy_color, …
get_tokens("light")  # → same keys, different values
```

Every widget reads from this dict — no hardcoded hex values or pixel sizes anywhere in the UI layer. Theme switching calls `apply_palette(app, theme)` once on the `QApplication`, then each persistent panel's `set_theme()` rebuilds its stylesheet from the new tokens. The font scale covers eleven steps from `font_micro` (10px, used for timestamps) to `font_score` (52px, used for the AI score number).

---

## Tech stack

| Library | Version | Role |
|---|---|---|
| PyQt6 | 6.11 | UI framework, custom widgets, threading |
| pyqtgraph | 0.14 | Interactive stock chart |
| yfinance | 1.3 | Historical price data from Yahoo Finance |
| pandas | 3.0 | DataFrame operations, CSV I/O |
| numpy | 2.4 | SMA / EMA indicator math |
| prophet | 1.3 | 30-day price forecasting (Meta) |
| anthropic | 0.105 | Claude API — AI stock analysis |
| requests | 2.34 | Finnhub API, Wikipedia S&P 500 list |
| lxml | 6.1 | HTML parsing for ticker list |
| python-dotenv | 1.2 | Legacy `.env` fallback for API keys |

---

## Technical highlights

- **Deferred heavy imports** — `prophet` and `anthropic` are imported inside each worker's `run()` method, not at module load. Both libraries have substantial initialization overhead; deferring them keeps the app launch fast regardless.

- **Timing-safe credentials** — passwords are hashed with PBKDF2-HMAC-SHA256 at 260,000 iterations and compared with `secrets.compare_digest()` to prevent timing attacks. Per-user API keys are stored in a separate gitignored JSON file, never mixed into the committed `profile.json`.

- **Calendar-keyed explore cache** — the S&P 500 screener batch-downloads ~503 tickers in a single `yf.download()` call on first use each day and stores results keyed by date. Repeat opens within the same day are instant; the manual Refresh button bypasses the cache entirely with `force=True`.

- **Custom QPainter donut chart** — the portfolio chart is drawn entirely with Qt's native 2D painter; `matplotlib` is not used by any UI file (it's present only as a transitive Prophet dependency). The chart runs a 900ms OutCubic animation on entry and renders a 3-layer concentric glow on hover.

- **PyInstaller bundling** — `StockApp.spec` and `runtime_hook_cmdstan.py` handle Prophet's CmdStan backend, which installs into deeply nested paths that exceed Windows' default 260-character path limit. The result is a standalone `.exe` / `.app` with no Python installation required.

---

## Getting started

### Requirements

- **Python 3.10–3.12** — Prophet's dependencies are not always compatible with 3.13+
- API keys for [Anthropic](https://console.anthropic.com) and [Finnhub](https://finnhub.io) are **optional** — every feature works without them except AI analysis and insider trades

### 1. Clone

```bash
git clone https://github.com/theSLOS/Stock-Tracker-and-Simulator.git
cd Stock-App
```

### 2. Run the setup script

**Windows:**
```bat
setup.bat
```

**macOS / Linux:**
```bash
chmod +x setup.sh && ./setup.sh
```

Creates a virtual environment and installs all dependencies. Prophet takes ~2 minutes on first install.

> **Windows — enable long paths before running setup.**
> Prophet's CmdStan files have deeply nested paths that hit the 260-character Windows default. Run once in an **elevated PowerShell**, then restart your terminal:
> ```powershell
> Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1
> ```

<details>
<summary>Manual setup</summary>

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```
</details>

### 3. Run

```bash
python main.py
```

Register an account on first launch — AAPL data downloads automatically when your portfolio is empty.

**Skip the login prompt:**
```bash
python main.py --user <username> --password <password>
```

**Add API keys** inside the app: the first time you trigger AI analysis or insider trades, a dialog prompts you to enter the relevant key. Keys can also be managed from Settings → API Keys at any time.

---

## Project layout

```
Stock-App/
├── main.py                      # Entry point — icon, arg parsing, login, theme init
├── requirements.txt
├── StockApp.spec                # PyInstaller config (handles Prophet / CmdStan)
│
├── ui/
│   ├── theme.py                 # Token system — all colours and font sizes
│   ├── login_page.py
│   ├── register_page.py
│   ├── logo/                    # SVG brand assets
│   └── mainwindow/
│       ├── main_window.py       # Coordinator — owns workers, connects signals
│       ├── info_panel.py        # Left panel (stats, insider trades, AI tab)
│       ├── chart_panel.py       # Right panel (chart, date range, indicators)
│       ├── stock_chart.py       # Self-contained pyqtgraph chart widget
│       ├── explore_panel.py     # S&P 500 screener tab
│       ├── portfolio_page.py    # Full-window donut chart + performance card
│       ├── add_stock_dialog.py  # Card dialog with market highlight chips
│       └── settings_dialog.py   # Sidebar nav (Profile / Appearance / Security / API Keys)
│
├── core/
│   ├── stock_handler.py         # yfinance fetching, SMA/EMA calculations
│   ├── caching.py               # Per-user cache (stock data, AI results, portfolio)
│   ├── user_manager.py          # Profile CRUD, PBKDF2 password hashing
│   ├── key_manager.py           # Per-user API key storage with .env fallback
│   ├── prediction_worker.py     # QThread — Prophet 30-day forecast
│   ├── ai_analysis_worker.py    # QThread — Claude API + Finnhub insider data
│   ├── senate_worker.py         # QThread — Finnhub insider trades
│   └── explore_worker.py        # QThread — batch S&P 500 market data
│
└── Users/
    └── <username>/
        ├── profile.json         # Committed — hashed credentials, theme preference
        ├── api_keys.json        # Gitignored — Anthropic + Finnhub keys
        ├── cache                # Gitignored — stock metadata, AI results, portfolio
        └── csvFiles/            # Gitignored — price CSVs (rebuilt automatically on first use)
```

---

## Notes

- **Local only** — all data lives on your machine; there is no server or sync
- **Prophet forecasts are illustrative** — the model is tuned for trend direction, not price accuracy; this is not financial advice
- **yfinance reliability** — data is scraped from Yahoo Finance; availability can vary
- Stock CSVs and cache files are gitignored and rebuild automatically on first use on any machine

<details>
<summary>Sample accounts for testing</summary>

| Username | Password | Portfolio |
|---|---|---|
| `user3` | `password` | AAPL, NVDA, AMZN, GOOG, TSLA |
| `admin` | `password` | AAPL |
| `user2` | `password` | AAPL |
| `user1` | `password` | Empty (auto-downloads AAPL on first login) |

</details>
