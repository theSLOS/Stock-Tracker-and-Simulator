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

- **Ticker universe** — full S&P 500 (~503 tickers) fetched from Wikipedia at runtime; falls back to a hardcoded 58-ticker curated list if the fetch fails (status label notes when fallback is in use)
- **Daily cache** — results stored in `Users/explore_cache.json` keyed by date; served instantly on the same calendar day without re-downloading
- **Four sub-tabs** — Top Gainers (% change desc), Top Losers (% change asc), Most Active (volume desc), Biggest Movers (absolute % change desc); each shows top 20
- **Table columns** — `#` rank, Symbol, Name, Price, Change % (▲/▼ arrows + green/red color), Volume, "+ Add" button
- **Market overview bar** — strip below the header showing total stock count, gainers count (green), losers count (red), and average move (colored by sign); hidden until first load, updated by `_on_data_loaded()`; stored as `_ov_total/gainers/losers/avg` labels; `_update_overview(data)` computes and styles them; re-colored on `set_theme()`
- **Real-time search filter** — `QLineEdit` above the tabs; `textChanged` → `_apply_filter(text)` calls `setRowHidden()` on the active table for rows not matching the query in symbol (col 1) or name (col 2); `_tabs.currentChanged` re-applies the filter so switching tabs respects the current query
- **Load flow** — `start_background_load()` called by `MainWindow.__init__` at login (`force=False`, cache-aware); `refresh_if_empty()` is the tab-switch fallback; manual Refresh button uses `force=True` to always re-download and overwrite the cache; status label shows `"Loaded N stocks · HH:MM AM"` timestamp after load
- **Add flow** — "+ Add" button per row emits `add_to_portfolio(symbol)`; double-clicking any row also emits it; both route to `MainWindow.add_stock_from_explore()` → `StockFetchWorker` → switches to Portfolio tab
- **Theme** — `set_theme(theme)` updates `_tokens` and rebuilds stylesheets for the status label, search bar, overview bar labels, and all four table widgets (background, alternating rows, header); gain/loss colours use `tokens["buy_color"]` / `tokens["sell_color"]`

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

Constructed as `UserSettingsDialog(user_profile: dict, theme: str = "dark", parent=None)`. Fixed 680 × 500 px card-style dialog with a left sidebar and a `QStackedWidget` content area. Fully token-driven via `_build_style(t)` — no hardcoded colours.

**Layout:**
- Outer `QDialog` background: `base`. Inner `QFrame#card` (`window`, 14 px radius, separator border).
- Left `QFrame#sidebar` (155 px, `alternate_base`, right separator) holds the "SETTINGS" header and four checkable `QPushButton#nav_btn` items. Checked nav button fills with `highlight`; unchecked hover uses `separator`.
- Right area: `QStackedWidget` for page content + global Save / Cancel `QDialogButtonBox` pinned at the bottom.

**Pages (nav order):**

1. **Profile** — username read-only chip (`QLabel#username_chip`, `alternate_base` background), EMAIL and PHONE `QLineEdit` fields pre-filled from `user_profile`. Saved by the global Save button.

2. **Appearance** — pill-style Dark / Light toggle: two joined `QPushButton` (`#btn_theme_l` / `#btn_theme_r`) with shared borders and matching checked/unchecked states. Saved by the global Save button.

3. **Security** — CURRENT PASSWORD / NEW PASSWORD / CONFIRM NEW PASSWORD fields + a blue "Change Password" `QPushButton#btn_save_pw`. Clicking it validates inline (warns on incomplete fields, wrong current password, or mismatch) via `user_manager.verify_password()` + `hash_password()` + `save_user_profile()`, then clears the fields and flashes a "✓ Password changed" label for 3 s via `QTimer.singleShot`. The global Save button does **not** touch password fields.

4. **API Keys** — one `QFrame#key_row` card per key (Anthropic, Finnhub). Each row shows: icon (highlight color), display name, a status chip ("✓ Set" in `buy_color` / "✗ Not set" in `sell_color`), an "Update" `QPushButton#btn_key_update` (opens `ApiKeyDialog`; refreshes chip on accept), and a "Delete" `QPushButton#btn_key_delete` (calls `key_manager.delete_key()`; refreshes chip; hidden when key is not set). All API key actions save immediately — the global Save button does **not** affect them.

**Save logic (`_save()`):** copies `user_profile`, updates email + phone + theme preference, calls `user_manager.save_user_profile()`, updates `self.user_profile` in-place, then `self.accept()`. `MainWindow.open_settings()` reads the updated theme and triggers `apply_palette()` + `set_theme()` on all persistent panels — no changes needed in `main_window.py`.
