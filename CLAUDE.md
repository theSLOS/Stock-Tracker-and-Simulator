# CLAUDE.md — Project Context for Claude Sessions

## What this project is

A desktop stock portfolio viewer and predictor built with Python + PyQt6. Multi-user, with per-user portfolios stored locally. Data comes from Yahoo Finance (`yfinance`). The UI is dark-themed using PyQt6's Fusion style + a custom QPalette.

---

## How to run

```bash
python main.py
```

From the project root. Login with an existing user or register a new one. On first login with an empty portfolio, the default stock (AAPL) is fetched automatically.

---

## File structure

```
main.py                        # Entry point only — wires login → main window
pyrightconfig.json             # Tells Pylance to treat root as source root (fixes IDE import errors)
requirements.txt

ui/                            # All PyQt6 UI components
    main_window.py             # MainWindow (QMainWindow) + StockFetchWorker + apply_dark_theme()
    stock_chart.py             # StockChart (QWidget) — self-contained chart, tooltip, indicators, prediction overlay
    login_page.py              # LoginDialog (QDialog)
    register_page.py           # RegisterDialog (QDialog)

core/                          # Business logic, data, background workers
    stock_handler.py           # yfinance download, add_new_stock(), calculate_SMA/EMA()
    caching.py                 # CacheManager — per-user JSON cache of stock metadata
    user_manager.py            # load_users(), create_user(), get_user_profile()
    stock_model.py             # StockPackage dataclass (symbol, name, dfpath, lastUpdate, df)
    prediction_worker.py       # PredictionWorker (QThread) — runs Prophet in background

Users/
    <username>/
        profile.json           # {"username", "password", "preferences": {"theme", "default_stock"}}
        cache                  # JSON file (gitignored) — maps symbol → {name, dfpath, lastUpdate}
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

### Key design decisions
- **Cache stores only filenames** (`AAPL.csv`), not absolute paths. Full path is always reconstructed as `os.path.join(csv_path, filename)` at runtime. This makes the project portable across machines.
- **`StockChart` is fully self-contained** — `MainWindow` just calls `chart.set_data()`, `chart.toggle_indicator()`, `chart.set_prediction()`, `chart.clear()`. All pyqtgraph state lives inside `StockChart`.
- **Workers are QThreads** — `StockFetchWorker` and `PredictionWorker` both emit `finished` and `error` signals. Never block the UI thread.
- **No table view** — the left panel shows a stock info panel (symbol, name, current price, day change, prediction results). The old `QTableView`/`PandasModel` approach was removed.

### Indicators
Registered on `StockChart` at startup in `MainWindow.__init__`:
```python
chart.register_indicator("SMA 20", lambda df: stock_handler.calculate_SMA(df, 20), (0, 255, 0), "SMA 20")
```
Toggle with `chart.toggle_indicator(key, enabled)`. Indicators auto-redraw on date range change.

### Prediction (Prophet)
- Trains on last 2 years of data (`cutoff = max_date - 730 days`)
- `changepoint_prior_scale=0.15`, `changepoint_range=0.95` — tuned for a middle ground between anchoring to long-term trend and following recent momentum
- Returns (predicted_price, low, high) for 30 days ahead
- BUY/HOLD/SELL signal: ≥5% = BUY, ≤-5% = SELL, otherwise HOLD
- Draws a dashed cornflower-blue line + semi-transparent confidence band on the chart

---

## Cache format (`Users/<username>/cache`)

```json
{
    "AAPL": {
        "name": "Apple",
        "symbol": "AAPL",
        "dfpath": "AAPL.csv",
        "lastUpdate": "2026-05-18T14:01:37.540076"
    }
}
```

`dfpath` is **filename only** — always join with `csv_path` to get the full path. Cache is gitignored; fresh machines start with an empty cache.

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

---

## Gitignore highlights

```
*.csv          # Stock price data — downloaded fresh on each machine
Users/*/cache  # Per-user cache files — regenerated automatically
.env           # Optional CSV_PATH override (not needed — app uses per-user folders)
```

Profile JSONs and `pyrightconfig.json` **are** committed.

---

## Dependencies

```
PyQt6, pyqtgraph, pandas, numpy, yfinance, python-dotenv, prophet
```

Prophet brings in `cmdstanpy`, `matplotlib`, `holidays` etc. — takes ~2 min to install fresh. Import is deferred to `PredictionWorker.run()` so startup is not affected.

---

## Existing users (for testing)

- `user1`, `user2`, `user3`, `admin` — all with password `password`
- `user3` has AAPL and NVDA in their portfolio
- `admin` and `user2` have AAPL cached
- `user1` has no CSV or cache (will auto-download AAPL on first login)
