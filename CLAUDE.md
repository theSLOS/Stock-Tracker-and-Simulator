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

API keys are stored **per user** in `Users/<username>/api_keys.json` (gitignored). The app prompts the user to enter a key the first time they trigger a feature that needs one; keys can also be managed via Settings → API Keys. The global `.env` file is still read as a fallback via `core/key_manager.get_key()` for any user who hasn't set their own key yet. All features except AI analysis and insider trades work without any keys.

---

## File structure

```
main.py                        # Entry point only — wires login → main window
pyrightconfig.json             # Tells Pylance to treat root as source root (fixes IDE import errors)
requirements.txt
.env                           # Optional legacy fallback for ANTHROPIC_API_KEY + FINNHUB_API_KEY (gitignored)

ui/                            # All PyQt6 UI components
    mainwindow/                # Main app window package (see ui/mainwindow/CLAUDE.md)
        main_window.py         # MainWindow (QMainWindow) + StockFetchWorker + apply_dark/light_theme()
        info_panel.py          # InfoPanel (QWidget) — left panel (profile row, stock header, 3 tabs); theme-aware via set_theme()
        chart_panel.py         # ChartPanel (QWidget) — right panel; top combo row (+ Add Stock, dropdown, Delete); single bottom toolbar (date range buttons 1Y/6M/3M/1M/All on left, SMA/EMA indicator toggles on right); apply_theme() rebuilds stylesheet from get_tokens()
        stock_chart.py         # StockChart (QWidget) — self-contained chart; calls autoRange() after every _redraw() so date-range changes snap the viewport
        explore_panel.py       # ExplorePanel (QWidget) — market explorer tab; market overview bar (gainers/losers/avg move); real-time search filter (symbol or name); rank # column; ▲/▼ change arrows; double-click row to add; load timestamp in status; theme-aware via set_theme()
        portfolio_page.py      # UserPage (QWidget) — full-window portfolio page; receives theme= at construction
        add_stock_dialog.py    # AddStockDialog (QDialog) — card-style add dialog; reads explore cache for market highlight chips; returns symbol via get_symbol()
        ai_analysis_dialog.py  # AIAnalysisDialog (QDialog); receives theme= at construction
        api_key_dialog.py      # ApiKeyDialog (QDialog) — card-style dialog for entering/updating a single API key; used inline and from settings
        settings_dialog.py     # UserSettingsDialog (QDialog) — card + sidebar nav: Profile, Appearance (pill theme toggle), Security (inline password change), API Keys (per-key status + Update/Delete)
    login_page.py              # LoginDialog (QDialog) — fixed 440×540 card-on-dark layout; styled with get_tokens("dark"); always shown with dark theme regardless of user preference
    register_page.py           # RegisterDialog (QDialog) — matching 440×560 card design to login_page; opened from login footer
    theme.py                   # Centralised token system: THEMES dict + _FONT_SCALE + _SIGNAL_COLORS; get_tokens(theme) → merged dict used by every UI component; apply_palette() sets Qt QPalette

core/                          # Business logic, data, background workers (see core/CLAUDE.md)
    stock_handler.py           # yfinance download, add_new_stock(), calculate_SMA/EMA()
    caching.py                 # CacheManager — per-user JSON cache
    user_manager.py            # load_users(), create_user(), get_user_profile(), save_user_profile(), hash_password(), verify_password()
    key_manager.py             # get_key(username, name), set_key(username, name, value), delete_key() — reads/writes Users/<username>/api_keys.json; falls back to os.getenv() if no per-user key is set
    stock_model.py             # StockPackage dataclass (symbol, name, dfpath, lastUpdate, df)
    prediction_worker.py       # PredictionWorker (QThread) — Prophet
    ai_analysis_worker.py      # AIAnalysisWorker (QThread, anthropic_key=, finnhub_key=) — Finnhub + Claude API
    senate_worker.py           # SenateWorker (QThread, finnhub_key=) — insider trades from Finnhub
    explore_worker.py          # ExploreWorker (QThread) — S&P 500 fetch + daily cache + batch yfinance download for Explore tab

Users/
    <username>/
        profile.json           # {"username", "password" (pbkdf2sha256 hash), "email", "phone", "preferences": {"theme", "default_stock"}} — COMMITTED to git
        api_keys.json          # {"ANTHROPIC_API_KEY": "...", "FINNHUB_API_KEY": "..."} — gitignored, never committed
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
10. "+ Add Stock" button opens `AddStockDialog` — a card-style dialog that reads `Users/explore_cache.json` directly at construction time and renders Top Gainers, Top Losers, and Most Active as clickable chip buttons. Clicking a chip fills the symbol field. On accept, `MainWindow.add_new_stock_dialog()` launches `StockFetchWorker` with the entered symbol.
11. Stock rename: `InfoPanel` exposes a `stock_renamed = pyqtSignal(str, str)` signal. A small `✎` pencil button appears beside the stock name when a stock is loaded; clicking it opens a `QInputDialog` pre-filled with the current name. On confirm, `CacheManager.rename_stock()` updates the cache and the signal is emitted → `MainWindow._on_stock_renamed()` refreshes the combo dropdown.
12. API keys: `core/key_manager.py` is the single source of truth for per-user API key access. `get_key(username, name)` checks `Users/<username>/api_keys.json` first, then falls back to `os.getenv()` for `.env` compatibility. Workers (`AIAnalysisWorker`, `SenateWorker`) receive keys as constructor params — they never call `os.getenv()` themselves. `MainWindow.run_ai_analysis()` loads the Anthropic key before starting the worker and opens `ApiKeyDialog` if it is absent. `InfoPanel._fetch_senate_trades()` checks for the Finnhub key and shows a "Set Finnhub API Key" inline button rather than silently doing nothing. `UserSettingsDialog` has an API Keys section for viewing (placeholder hints whether a key is set) and updating both keys.

### Key design decisions
- **Cache stores only filenames** (`AAPL.csv`), not absolute paths. Full path reconstructed as `os.path.join(csv_path, filename)` at runtime — keeps the project portable.
- **Workers are QThreads** — `StockFetchWorker`, `PredictionWorker`, `AIAnalysisWorker`, `SenateWorker`, and `ExploreWorker` all emit `finished` and `error` signals. Never block the UI thread.
- **`ui/mainwindow/` package** — all main-window files use relative imports (`from .info_panel import InfoPanel`). Pre-login UI and `theme.py` stay in `ui/`. `main.py` imports from `ui.mainwindow.main_window`.
- **`QTabWidget` top-level navigation** — Tab 0: "Portfolio" (contains a `QStackedWidget` for stock view ↔ portfolio page); Tab 1: "Explore" (`ExplorePanel`). `ExploreWorker` is started at login via `start_background_load()` so data is usually ready before the user opens the tab. `refresh_if_empty()` on tab switch acts as a fallback if the background load hasn't fired yet.
- **`QStackedWidget` within Portfolio tab** — index 0: stock view (InfoPanel + ChartPanel). Index 1: `UserPage`, recreated fresh on every navigation so data is always current.
- **No menu bar** — settings accessed via the User Page (profile row in InfoPanel).
- **Per-user API keys** — stored in `Users/<username>/api_keys.json` (gitignored), separate from `profile.json` (which is committed). `core/key_manager.py` handles all reads/writes and falls back to `os.getenv()` so the legacy `.env` file keeps working. Keys are never hardcoded in workers; they are passed as constructor params so tests or future callers can supply them directly.
- **Centralised theme tokens** — `theme.py` is the single source of truth for all colours and font sizes. `get_tokens(theme)` merges `THEMES[theme]` + `_FONT_SCALE` + `_SIGNAL_COLORS` into one flat dict. Every UI component imports `get_tokens` and uses only token keys — **no hardcoded hex values or pixel sizes anywhere in UI files**. Pre-login dialogs (`LoginDialog`, `RegisterDialog`) call `get_tokens("dark")` directly since the user hasn't chosen a theme yet. Persistent widgets (`InfoPanel`, `ExplorePanel`, `ChartPanel`) expose `set_theme(theme)` / `apply_theme(theme)` and rebuild their stylesheets on theme switch; one-shot widgets (`UserPage`, `AIAnalysisDialog`) receive `theme=` at construction. `MainWindow.open_settings()` is the single call site that triggers `apply_palette` + `set_theme` on all persistent panels.

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
