# CLAUDE.md — Project Context for Claude Sessions

## What this project is

A desktop stock portfolio viewer and predictor built with Python + PyQt6. Multi-user, with per-user portfolios stored locally. Data comes from Yahoo Finance (`yfinance`). The UI is dark-themed using PyQt6's Fusion style + a custom QPalette.

---

## How to run

```bash
python main.py
```

From the project root. Login with an existing user or register a new one. On first login with an empty portfolio, the default stock (AAPL) is fetched automatically.

Requires `ANTHROPIC_API_KEY` in a `.env` file for the AI analysis feature. Requires `FINNHUB_API_KEY` for the insider trades panel. All other features work without either key.

---

## File structure

```
main.py                        # Entry point only — wires login → main window
pyrightconfig.json             # Tells Pylance to treat root as source root (fixes IDE import errors)
requirements.txt
.env                           # ANTHROPIC_API_KEY + FINNHUB_API_KEY (gitignored)

ui/                            # All PyQt6 UI components
    main_window.py             # MainWindow (QMainWindow) + StockFetchWorker + apply_dark_theme()
    stock_chart.py             # StockChart (QWidget) — self-contained chart, tooltip, indicators, prediction overlay
    login_page.py              # LoginDialog (QDialog)
    register_page.py           # RegisterDialog (QDialog)
    ai_analysis_dialog.py      # AIAnalysisDialog (QDialog) — score gauge, summary, pros/cons, data-used toggle, cached timestamp

core/                          # Business logic, data, background workers
    stock_handler.py           # yfinance download, add_new_stock(), calculate_SMA/EMA()
    caching.py                 # CacheManager — per-user JSON cache of stock metadata + AI analysis
    user_manager.py            # load_users(), create_user(), get_user_profile()
    stock_model.py             # StockPackage dataclass (symbol, name, dfpath, lastUpdate, df)
    prediction_worker.py       # PredictionWorker (QThread) — runs Prophet in background
    ai_analysis_worker.py      # AIAnalysisWorker (QThread) — fetches insider trades + calls Claude API
    senate_worker.py           # SenateWorker (QThread) — fetches insider trades from Finnhub

Users/
    <username>/
        profile.json           # {"username", "password", "preferences": {"theme", "default_stock"}}
        cache                  # JSON file (gitignored) — maps symbol → {name, dfpath, lastUpdate, ai_analysis}
        csvFiles/              # Downloaded CSVs (gitignored) — one per stock, e.g. AAPL.csv
```

---

## Architecture

### Data flow
1. `main.py` creates `CacheManager` and `MainWindow` after login
2. `MainWindow` calls `load_stock(symbol)` → reads CSV → calls `chart.set_data(df)`
3. `StockChart` owns all chart state: x_data, y_data, plot_df, indicator curves, prediction curves
4. When stock data is stale or missing, `StockFetchWorker` (QThread) fetches from yfinance
5. Prediction runs in `PredictionWorker` (QThread) using Meta's Prophet model
6. AI analysis runs in `AIAnalysisWorker` (QThread) — fetches insider trades from Finnhub then calls Claude API
7. Insider trades panel is populated by `SenateWorker` (QThread) on every stock load

### Key design decisions
- **Cache stores only filenames** (`AAPL.csv`), not absolute paths. Full path is always reconstructed as `os.path.join(csv_path, filename)` at runtime. This makes the project portable across machines.
- **`StockChart` is fully self-contained** — `MainWindow` just calls `chart.set_data()`, `chart.toggle_indicator()`, `chart.set_prediction()`, `chart.clear()`. All pyqtgraph state lives inside `StockChart`.
- **Workers are QThreads** — `StockFetchWorker`, `PredictionWorker`, `AIAnalysisWorker`, and `SenateWorker` all emit `finished` and `error` signals. Never block the UI thread.
- **No table view** — the left panel shows a stock info panel (symbol, name, current price, day change, prediction results, AI score, insider trades).
- **AI analysis is cached per-stock per-user** for 24 hours inside the existing cache file. The button checks the cache first; only calls the API if the result is stale or missing.

### Left info panel layout (top to bottom)
1. Symbol + name + price + day change
2. Prediction section — button, predicted price, range, BUY/HOLD/SELL signal
3. AI Analysis section — button, score (+N / -N), description (Bullish / Bearish etc.), 1-2 sentence summary
4. Insider Trades section — scrollable list of recent executive/director SEC trades for the selected stock

### Indicators
Registered on `StockChart` at startup in `MainWindow.__init__`:
```python
chart.register_indicator("SMA 20", lambda df: stock_handler.calculate_SMA(df, 20), (0, 255, 0), "SMA 20")
```
Toggle with `chart.toggle_indicator(key, enabled)`. Indicators auto-redraw on date range change.

### Prediction (Prophet)
- Trains on last 2 years of data (`cutoff = max_date - 730 days`)
- `changepoint_prior_scale=0.05`, `changepoint_range=0.80` — tuned to reduce upward bias; 0.80 is Prophet's own default and prevents the model from over-anchoring to very recent momentum
- Returns (predicted_price, low, high) for 30 days ahead
- BUY/HOLD/SELL signal: ≥5% = BUY, ≤-5% = SELL, otherwise HOLD
- Draws a dashed cornflower-blue line + semi-transparent confidence band on the chart

### AI Analysis (Claude API)
- `AIAnalysisWorker` fetches up to 15 recent insider trades for the symbol from Finnhub (`FINNHUB_API_KEY`)
- Builds a 30-day price summary (current price, change %, high, low, avg volume)
- Sends both to Claude (`claude-sonnet-4-6`) with a structured prompt requesting a JSON response: `{score, summary, pros, cons}`
- Score is -10 (strongly bearish) to +10 (strongly bullish)
- `summary` is a 1-2 sentence plain-English explanation of the key driver behind the score
- Result is saved to the user's cache file with a timestamp; re-used for 24 hours before fetching again
- The dialog (`AIAnalysisDialog`) shows: score as a large coloured number, center-zero bar, sentiment label, italic summary sentence, two-column pros/cons list, collapsible "Show data used" section, "Cached · <timestamp>" when showing a saved result
- The summary sentence is also shown directly on the main window panel below the score
- Helper functions `_score_color()` and `_score_description()` are exported from `ai_analysis_dialog.py` and reused in `main_window.py` for the panel score display

### Insider Trades (Finnhub)
- `SenateWorker` (file kept as-is for historical reasons) fires on every stock load
- Fetches up to 20 recent SEC insider transactions via `finnhub.io/api/v1/stock/insider-transactions`
- Transaction codes mapped: `P` → Purchase, `S` → Sale, `A` → Award, `D` → Disposition, `G` → Gift, `F` → Tax Withholding
- Displayed in a scrollable section at the bottom of the left panel
- Color-coded: ▲ Purchase in green, ▼ Sale in red, neutral types in grey; each row shows name, type, date, share count and price
- Failures are handled silently — shows "No recent insider trades found"
- Requires `FINNHUB_API_KEY` in `.env`; silently shows nothing if key is absent

---

## Cache format (`Users/<username>/cache`)

```json
{
    "AAPL": {
        "name": "Apple",
        "symbol": "AAPL",
        "dfpath": "AAPL.csv",
        "lastUpdate": "2026-05-18T14:01:37.540076",
        "ai_analysis": {
            "timestamp": "2026-05-25T10:30:00.000000",
            "score": 7,
            "summary": "Apple's iPhone supercycle narrative...",
            "pros": ["Strong earnings growth", "..."],
            "cons": ["High valuation", "..."]
        }
    }
}
```

`dfpath` is **filename only** — always join with `csv_path` to get the full path. `ai_analysis` is optional; absent if the user has never run analysis for that stock. `summary` may be absent in old cached entries (pre-feature); the UI handles this gracefully.

---

## User profile format (`Users/<username>/profile.json`)

```json
{
    "username": "user3",
    "password": "password",
    "preferences": {
        "theme": "dark",
        "default_stock": "AAPL"
    }
}
```

Profile files **are** committed to git (no secrets beyond plaintext passwords — this is a local desktop app). Cache and CSV files are gitignored.

---

## Known quirks / things already fixed

- **Stale absolute paths in cache**: old cache files had full absolute paths in `dfpath`. Fixed by storing only the filename. All existing cache files were updated.
- **Double `load_stock` call on startup**: `populate_stock_combo()` already calls `on_stock_changed` → `load_stock`, so the explicit second call was removed to prevent duplicate QThreads being spawned.
- **`StockFetchWorker` refresh path bug**: was passing `stock_handler.path` (a module-level `os.getenv('CSV_PATH')` that was always `None`). Fixed to pass `self.csv_path`.
- **SMA/EMA crash**: indicator values were pandas Series with DatetimeIndex — pyqtgraph needs numpy arrays. Fixed with `np.array(...)` wrapping.
- **`QThread: Destroyed while thread is still running`**: caused by the duplicate `load_stock` call creating a second worker that overwrote the reference to the first.
- **`'QPoint' object has no attribute 'toPoint'`**: `mapFromScene()` already returns `QPoint` in PyQt6. Removed the redundant `.toPoint()` call.
- **Prophet upward bias**: original config used `changepoint_prior_scale=0.15` and `changepoint_range=0.95`. Reduced to `0.05` / `0.80` to stop the model over-fitting to recent upward momentum.
- **Windows long path error installing Prophet**: Prophet's Stan model directory exceeds Windows' 260-character path limit. Fix: enable long path support via registry (`LongPathsEnabled = 1`) in an elevated PowerShell session.
- **senatestockwatcher.com / housestockwatcher.com both offline**: original Senate trades feature pointed at these domains; both are DNS-dead as of 2026. Replaced with Finnhub's free insider transactions endpoint (`/api/v1/stock/insider-transactions`). Note: Finnhub's congressional trading endpoint (`/api/v1/stock/congressional-trading`) requires a paid plan — the free tier only covers corporate insider trades.

---

## Gitignore highlights

```
*.csv          # Stock price data — downloaded fresh on each machine
Users/*/cache  # Per-user cache files — regenerated automatically
.env           # API keys
```

Profile JSONs and `pyrightconfig.json` **are** committed.

---

## Dependencies

```
PyQt6, pyqtgraph, pandas, numpy, yfinance, python-dotenv, prophet, anthropic, requests
```

Prophet brings in `cmdstanpy`, `matplotlib`, `holidays` etc. — takes ~2 min to install fresh. Import is deferred to `PredictionWorker.run()` so startup is not affected. `anthropic` import is similarly deferred to `AIAnalysisWorker.run()`.

---

## Existing users (for testing)

- `user1`, `user2`, `user3`, `admin` — all with password `password`
- `user3` has AAPL, NVDA, AMZN, GOOG, TLSA in their portfolio
- `admin` and `user2` have AAPL cached
- `user1` has no CSV or cache (will auto-download AAPL on first login)
