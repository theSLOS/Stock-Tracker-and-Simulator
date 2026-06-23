# ui/mainwindow — Widget Reference

All files here use relative imports (`from .info_panel import InfoPanel`).

---

## MainWindow (`main_window.py`)

Thin coordinator — owns workers, connects signals, manages navigation. No UI logic of its own.

- Owns `StockFetchWorker`, `PredictionWorker`, and `AIAnalysisWorker`
- Connects `InfoPanel` ↔ `ChartPanel` signals
- `_score_color()` and `_score_description()` are exported from `ai_analysis_dialog.py` and reused here for the inline panel score display
- Top-level layout is a `QTabWidget`: Tab 0 "Portfolio" holds a `QStackedWidget` (index 0 = stock view, index 1 = `UserPage`); Tab 1 "Explore" holds `ExplorePanel`. `start_background_load()` is called at the end of `__init__` so market data begins downloading immediately at login. `_on_tab_changed` calls `refresh_if_empty()` as a fallback if the background load hasn't completed yet.
- `add_stock_from_explore(symbol)` — called by `ExplorePanel.add_to_portfolio` signal; reuses `StockFetchWorker` and switches back to the Portfolio tab on success
- `add_new_stock_dialog()` — opens `AddStockDialog` (card-style, market-highlight chips); on accept launches `StockFetchWorker` with the symbol returned by `dialog.get_symbol()`
- `_on_stock_renamed(symbol, new_name)` — connected to `InfoPanel.stock_renamed`; calls `chart_panel.populate_stocks()` to refresh the combo dropdown label
- **Theme wiring** — `open_settings()` is the single site for theme changes: calls `apply_palette(app, new_theme)`, then `chart_panel.apply_theme()`, `info_panel.set_theme()`, and `explore_panel.set_theme()`. One-shot widgets (`UserPage`, `AIAnalysisDialog`) receive `theme=current_theme` at construction time, read from `user_profile["preferences"]["theme"]`.

---

## InfoPanel (`info_panel.py`)

Left panel. Constructed as `InfoPanel(username="", theme="dark")`.

Always visible at the top:
- **Profile header** — avatar circle (initials) + username + `›` chevron. Click emits `profile_clicked` → `MainWindow.open_portfolio()`
- Separator + symbol, name (+ `✎` rename button), price, day change
- **Rename** — `✎` pencil button beside the stock name; hidden when no stock is loaded. Click opens `QInputDialog` pre-filled with the current name. On confirm, calls `CacheManager.rename_stock()`, updates the label, and emits `stock_renamed = pyqtSignal(str, str)` (symbol, new_name).

Three tabs — styled as pill buttons matching the date range / indicator buttons in `ChartPanel` (flat border, active tab filled with `highlight` color):
- **Info** — Statistics (1M High/Low, 52W High/Low, Avg Vol 30d) + scrollable Insider Trades list. Trades color-coded: ▲ Purchase green, ▼ Sale red, neutral grey; each row shows name, type, date, share count, price.
- **Analysis** — Prediction section (button, predicted price, range, BUY/HOLD/SELL) + AI Analysis section (button, score, sentiment label, summary sentence). BUY ≥5%, SELL ≤-5%, otherwise HOLD.
- **Portfolio** — scrollable; position entry form (shares, cost/share pre-filled with current price, date pre-filled with today, optional sell target) + performance card. Details below.

**Portfolio tab detail:**
- Inputs have full border/focus-ring styling consistent with login/add-stock dialogs; tracked in `self._port_inputs` for theme re-application.
- **Save Position** — primary button (highlight blue). On save: flashes "Saved ✓" for 1.5 s via `QTimer.singleShot`, then resets. Invalid sell target (non-empty but non-numeric) now shows a `QMessageBox.warning` instead of being silently dropped.
- **Performance card** — shown after saving a position; `alternate_base` background with rounded corners. Header row shows "Performance" label + large colored `_port_gain_label` (e.g. `+16.1%`). Stat rows: Purchased, Current Price, Total Cost, Value Now, Change (colored), Sell Target distance.
- **Clear Position** — secondary/destructive button (outlined, turns red on hover); sits inside the performance card.
- Whole tab content wrapped in a `QScrollArea` (no border, transparent) so form + card don't overflow the narrow panel.

`SenateWorker` is owned by `InfoPanel` and fires on every stock load.

**Theme system** — `InfoPanel` is fully token-driven. Labels are registered at construction into tracking lists: `_labels_secondary`, `_labels_muted`, `_labels_faint`, `_labels_value` (primary-color labels with partial stylesheets). `_apply_theme_styles(tokens)` iterates all lists and rebuilds every stylesheet from scratch — no accumulation. `set_theme(theme)` updates `_tokens` and calls `_apply_theme_styles`. All labels with any stylesheet (even font-only) must be explicitly colored here; Qt does not reliably re-read the palette for styled widgets when the app palette changes. Portfolio inputs (`_port_inputs`), Save/Clear buttons, and the performance card are also restyled here.

---

## ChartPanel (`chart_panel.py`)

Right panel. Owns stock selector combo, date range buttons, indicator toggles. All chart state delegated to `StockChart`.

Indicators registered at startup:
```python
self._chart.register_indicator("SMA 20", lambda df: stock_handler.calculate_SMA(df, 20), (0, 255, 0), "SMA 20")
```
Toggle buttons call `self._chart.toggle_indicator(key, enabled)` directly. Indicators auto-redraw on date range change.

---

## StockChart (`stock_chart.py`)

Self-contained pyqtgraph widget. `ChartPanel` calls `set_data()`, `toggle_indicator()`, `set_prediction()`, `clear()`. All pyqtgraph state lives inside here.

Prediction overlay: dashed cornflower-blue line + semi-transparent confidence band.

---

## UserPage (`portfolio_page.py`)

Full-window page, takes over `QStackedWidget` index 1. Recreated fresh on every navigation.

- **Nav bar** — `← Back` (→ index 0) left; `Settings` right
- **Profile header** — large avatar, username, email/phone if set
- **Portfolio section** — `DonutChartWidget` (pure QPainter, no matplotlib):
  - Sweeps in counter-clockwise over 900ms (eased cubic) on open
  - Hover: segment explodes outward with a 3-layer color glow; centre text switches from total value to that holding's symbol / value / portfolio % / gain-loss
  - Bidirectional legend sync: hovering a segment highlights the matching legend row in its segment color, and vice versa
  - Empty state shown if no positions recorded
- **Summary stats** — total cost, current value, total gain/loss, avg daily % change (weighted by current position value, calculated from each holding's `purchase_date` — not the full CSV history)

Signals: `back_requested`, `settings_requested` — connected by `MainWindow`.

---

## ExplorePanel (`explore_panel.py`)

Market screener shown in the "Explore" top-level tab. Data fetched by `ExploreWorker` (`core/explore_worker.py`). Constructed as `ExplorePanel(theme="dark")`.

- **Ticker universe** — full S&P 500 (~503 tickers) fetched from Wikipedia at runtime; falls back to a hardcoded 58-ticker curated list if the fetch fails
- **Daily cache** — results stored in `Users/explore_cache.json` keyed by date; served instantly on the same calendar day without re-downloading
- **Four sub-tabs** — Top Gainers (% change desc), Top Losers (% change asc), Most Active (volume desc), Biggest Movers (absolute % change desc); each shows top 20
- **Table columns** — Symbol, Name, Price, Change % (green/red), Volume, "+ Add" button
- **Load flow** — `start_background_load()` called by `MainWindow.__init__` at login (`force=False`, cache-aware); `refresh_if_empty()` is the tab-switch fallback; manual Refresh button uses `force=True` to always re-download and overwrite the cache
- **Add flow** — "+ Add" emits `add_to_portfolio(symbol)` → `MainWindow.add_stock_from_explore()` → `StockFetchWorker` → switches to Portfolio tab
- **Theme** — `set_theme(theme)` updates `_tokens` and refreshes the status label stylesheet; gain/loss colours use `tokens["buy_color"]` / `tokens["sell_color"]` from the token dict

---

## AddStockDialog (`add_stock_dialog.py`)

Constructed as `AddStockDialog(theme="dark", parent=None)`. Card-style dialog matching the login/register aesthetic (dark outer background, rounded card, blue `▲` header icon).

- **Symbol input** — single `QLineEdit`; Enter triggers add; uppercased on submit
- **Market Highlights** — if `Users/explore_cache.json` exists and is dated today, reads it directly at construction and renders three rows of clickable chip buttons: ▲ Top Gainers (green border), ▼ Top Losers (red), ⚡ Most Active (highlight blue). Each chip shows `SYMBOL  +X.X%`. Clicking a chip fills the symbol field.
- If the cache is absent or stale, a hint label is shown instead ("Open the Explore tab to load market highlights").
- `get_symbol()` returns the uppercased symbol after `exec()` returns `Accepted`.
- Width fixed at 480 px; height auto-sized via `adjustSize()`.

---

## AIAnalysisDialog (`ai_analysis_dialog.py`)

Constructed as `AIAnalysisDialog(symbol, name, theme="dark", parent=None)`. Score as large coloured number, center-zero bar, sentiment label, italic summary, two-column pros/cons, collapsible "Show data used" section, "Cached · \<timestamp\>" when serving a cached result.

Exports `_score_color(score)` and `_score_description(score)` — reused by `MainWindow` for the inline panel display. All colours and font sizes use `get_tokens(theme)` — no hardcoded values. `ScoreBar` receives the token dict at construction.

---

## UserSettingsDialog (`settings_dialog.py`)

- Edit email, phone → saved to `profile.json`
- Toggle Dark / Light theme → applies immediately to the running app
- Change password → requires current password, validates confirmation match

Writes via `user_manager.save_user_profile()`.
