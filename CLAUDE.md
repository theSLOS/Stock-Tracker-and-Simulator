# CLAUDE.md — Project Context for Claude Sessions

## What this project is

A desktop stock portfolio viewer and predictor built with Python + PyQt6. Multi-user, with per-user portfolios stored locally. Data comes from Yahoo Finance (`yfinance`). The UI is dark-themed using PyQt6's Fusion style + a custom QPalette.

---

## How to run

```bash
python main.py
```

From the project root. Login with an existing user or register a new one. On first login with an empty portfolio, the default stock (AAPL) is fetched automatically.

To skip the login dialog, pass credentials directly:

```bash
python main.py --user admin --password password
# or
python main.py -u admin -p password
```

Requires `ANTHROPIC_API_KEY` in a `.env` file for the AI analysis feature. Requires `FINNHUB_API_KEY` for the insider trades panel. All other features work without either key.

---

## File structure

```
main.py                        # Entry point only — wires login → main window
pyrightconfig.json             # Tells Pylance to treat root as source root (fixes IDE import errors)
requirements.txt
.env                           # ANTHROPIC_API_KEY + FINNHUB_API_KEY (gitignored)

ui/                            # All PyQt6 UI components
    mainwindow/                # Main app window package (see ui/mainwindow/CLAUDE.md)
        main_window.py         # MainWindow (QMainWindow) + StockFetchWorker + apply_dark/light_theme()
        info_panel.py          # InfoPanel (QWidget) — left panel (profile row, stock header, 3 tabs); theme-aware via set_theme()
        chart_panel.py         # ChartPanel (QWidget) — right panel
        stock_chart.py         # StockChart (QWidget) — self-contained chart
        explore_panel.py       # ExplorePanel (QWidget) — market explorer tab; theme-aware via set_theme()
        portfolio_page.py      # UserPage (QWidget) — full-window portfolio page; receives theme= at construction
        ai_analysis_dialog.py  # AIAnalysisDialog (QDialog); receives theme= at construction
        settings_dialog.py     # UserSettingsDialog (QDialog)
    login_page.py              # LoginDialog (QDialog)
    register_page.py           # RegisterDialog (QDialog)
    theme.py                   # Centralised token system: THEMES dict + _FONT_SCALE + _SIGNAL_COLORS; get_tokens(theme) → merged dict used by every UI component; apply_palette() sets Qt QPalette

core/                          # Business logic, data, background workers (see core/CLAUDE.md)
    stock_handler.py           # yfinance download, add_new_stock(), calculate_SMA/EMA()
    caching.py                 # CacheManager — per-user JSON cache
    user_manager.py            # load_users(), create_user(), get_user_profile()
    stock_model.py             # StockPackage dataclass (symbol, name, dfpath, lastUpdate, df)
    prediction_worker.py       # PredictionWorker (QThread) — Prophet
    ai_analysis_worker.py      # AIAnalysisWorker (QThread) — Finnhub + Claude API
    senate_worker.py           # SenateWorker (QThread) — insider trades from Finnhub
    explore_worker.py          # ExploreWorker (QThread) — S&P 500 fetch + daily cache + batch yfinance download for Explore tab

Users/
    <username>/
        profile.json           # {"username", "password", "email", "phone", "preferences": {"theme", "default_stock"}}
        cache                  # JSON file (gitignored) — maps symbol → {name, dfpath, lastUpdate, ai_analysis?, portfolio?}
        csvFiles/              # Downloaded CSVs (gitignored) — one per stock, e.g. AAPL.csv
```

---

## Architecture

### Data flow
1. `main.py` creates `CacheManager` and `MainWindow` after login
2. `MainWindow` wires `InfoPanel` and `ChartPanel` together via signals; owns all background workers
3. `ChartPanel.stock_changed` → `MainWindow.load_stock(symbol)` → reads CSV → `ChartPanel.set_data(df)` + `InfoPanel.update(symbol, df, cache)`
4. `StockChart` owns all chart state: x_data, y_data, plot_df, indicator curves, prediction curves
5. When stock data is stale or missing, `StockFetchWorker` (QThread) fetches from yfinance
6. Prediction runs in `PredictionWorker` (QThread) using Meta's Prophet model
7. AI analysis runs in `AIAnalysisWorker` (QThread) — fetches insider trades from Finnhub then calls Claude API
8. Insider trades panel is populated by `SenateWorker` (QThread), owned by `InfoPanel`, on every stock load
9. Explore tab: `ExploreWorker` (QThread) starts in the background at login via `start_background_load()`. It checks `Users/explore_cache.json` first — if today's data is already cached it emits immediately; otherwise it fetches the S&P 500 ticker list from Wikipedia (~503 tickers, falls back to a hardcoded 58-ticker curated list on failure), batch-downloads 5 days of data via `yf.download()`, saves the results to the daily cache, then emits. Results are sorted into Top Gainers / Top Losers / Most Active / Biggest Movers tables. The manual Refresh button always bypasses the cache and re-downloads. "+ Add" button emits `add_to_portfolio` → `MainWindow.add_stock_from_explore()` → `StockFetchWorker` (same path as manual add)

### Key design decisions
- **Cache stores only filenames** (`AAPL.csv`), not absolute paths. Full path reconstructed as `os.path.join(csv_path, filename)` at runtime — keeps the project portable.
- **Workers are QThreads** — `StockFetchWorker`, `PredictionWorker`, `AIAnalysisWorker`, `SenateWorker`, and `ExploreWorker` all emit `finished` and `error` signals. Never block the UI thread.
- **`ui/mainwindow/` package** — all main-window files use relative imports (`from .info_panel import InfoPanel`). Pre-login UI and `theme.py` stay in `ui/`. `main.py` imports from `ui.mainwindow.main_window`.
- **`QTabWidget` top-level navigation** — Tab 0: "Portfolio" (contains a `QStackedWidget` for stock view ↔ portfolio page); Tab 1: "Explore" (`ExplorePanel`). `ExploreWorker` is started at login via `start_background_load()` so data is usually ready before the user opens the tab. `refresh_if_empty()` on tab switch acts as a fallback if the background load hasn't fired yet.
- **`QStackedWidget` within Portfolio tab** — index 0: stock view (InfoPanel + ChartPanel). Index 1: `UserPage`, recreated fresh on every navigation so data is always current.
- **No menu bar** — settings accessed via the User Page (profile row in InfoPanel).
- **Centralised theme tokens** — `theme.py` is the single source of truth for all colours and font sizes. `get_tokens(theme)` merges `THEMES[theme]` + `_FONT_SCALE` + `_SIGNAL_COLORS` into one flat dict. Every UI component imports `get_tokens` and uses only token keys — no hardcoded hex values or pixel sizes. Persistent widgets (`InfoPanel`, `ExplorePanel`) expose `set_theme(theme)` and call `_apply_theme_styles(tokens)` on theme switch; one-shot widgets (`UserPage`, `AIAnalysisDialog`) receive `theme=` at construction. `MainWindow.open_settings()` is the single call site that triggers `apply_palette` + `set_theme` on all persistent panels.

---

## Dependencies

```
PyQt6, pyqtgraph, pandas, numpy, yfinance, python-dotenv, prophet, anthropic, requests
```

Prophet brings in `cmdstanpy`, `matplotlib`, `holidays` etc. — takes ~2 min to install fresh. `prophet` and `anthropic` imports are deferred to their respective worker `run()` methods so startup is not affected. `matplotlib` is not used directly by any UI file — the portfolio donut chart is pure QPainter.

---

## Existing users (for testing)

- `user1`, `user2`, `user3`, `admin` — all with password `password`
- `user3` has AAPL, NVDA, AMZN, GOOG, TSLA in their portfolio
- `admin` and `user2` have AAPL cached
- `user1` has no CSV or cache (will auto-download AAPL on first login)
