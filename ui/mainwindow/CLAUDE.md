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
- **Theme wiring** — `open_settings()` is the single site for theme changes: calls `apply_palette(app, new_theme)`, then `chart_panel.apply_theme()`, `info_panel.set_theme()`, and `explore_panel.set_theme()`. One-shot widgets (`UserPage`, `AIAnalysisDialog`) receive `theme=current_theme` at construction time, read from `user_profile["preferences"]["theme"]`.

---

## InfoPanel (`info_panel.py`)

Left panel. Constructed as `InfoPanel(username="", theme="dark")`.

Always visible at the top:
- **Profile header** — avatar circle (initials) + username + `›` chevron. Click emits `profile_clicked` → `MainWindow.open_portfolio()`
- Separator + symbol, name, price, day change

Three tabs:
- **Info** — Statistics (1M High/Low, 52W High/Low, Avg Vol 30d) + scrollable Insider Trades list. Trades color-coded: ▲ Purchase green, ▼ Sale red, neutral grey; each row shows name, type, date, share count, price.
- **Analysis** — Prediction section (button, predicted price, range, BUY/HOLD/SELL) + AI Analysis section (button, score, sentiment label, summary sentence). BUY ≥5%, SELL ≤-5%, otherwise HOLD.
- **Portfolio** — Position entry form (shares, cost/share pre-filled with current price, date pre-filled with today, optional sell target) + Performance section (cost, current value, % change, distance to sell target). Save/Clear persist to cache.

`SenateWorker` is owned by `InfoPanel` and fires on every stock load.

**Theme system** — `InfoPanel` is fully token-driven. Labels are registered at construction into tracking lists: `_labels_secondary`, `_labels_muted`, `_labels_faint`, `_labels_value` (primary-color labels with partial stylesheets). `_apply_theme_styles(tokens)` iterates all lists and rebuilds every stylesheet from scratch — no accumulation. `set_theme(theme)` updates `_tokens` and calls `_apply_theme_styles`. All labels with any stylesheet (even font-only) must be explicitly colored here; Qt does not reliably re-read the palette for styled widgets when the app palette changes.

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

## AIAnalysisDialog (`ai_analysis_dialog.py`)

Constructed as `AIAnalysisDialog(symbol, name, theme="dark", parent=None)`. Score as large coloured number, center-zero bar, sentiment label, italic summary, two-column pros/cons, collapsible "Show data used" section, "Cached · \<timestamp\>" when serving a cached result.

Exports `_score_color(score)` and `_score_description(score)` — reused by `MainWindow` for the inline panel display. All colours and font sizes use `get_tokens(theme)` — no hardcoded values. `ScoreBar` receives the token dict at construction.

---

## UserSettingsDialog (`settings_dialog.py`)

- Edit email, phone → saved to `profile.json`
- Toggle Dark / Light theme → applies immediately to the running app
- Change password → requires current password, validates confirmation match

Writes via `user_manager.save_user_profile()`.
