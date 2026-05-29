import os

import pandas as pd

from core import caching, stock_handler
from core.prediction_worker import PredictionWorker
from ui.stock_chart import StockChart

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QMessageBox,
    QInputDialog, QPushButton, QFrame, QScrollArea, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPalette, QColor


class StockFetchWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, mode, symbol, path, name=""):
        super().__init__()
        self.mode = mode
        self.symbol = symbol
        self.path = path
        self.name = name

    def run(self):
        try:
            if self.mode == "add":
                result = stock_handler.add_new_stock(self.symbol, self.path, name=self.name)
                if result is None:
                    self.error.emit(f"Failed to retrieve data for '{self.symbol}'.")
                else:
                    self.finished.emit(result)
            else:
                stock_handler.get_stock_data(self.symbol, self.path)
                self.finished.emit(None)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, cache: caching.CacheManager, csv_path, user_profile):
        super().__init__()
        self.user_profile = user_profile
        self.username = user_profile["username"]
        self.cache = cache
        self.df = pd.DataFrame()
        self.csv_path = csv_path

        self._worker = None
        self._worker_symbol = None
        self._worker_mode = None
        self._pred_worker = None
        self._ai_worker = None
        self._senate_worker = None

        self.setWindowTitle(f"Stock Viewer - User: {self.username}")
        self.resize(1400, 800)

        # --- central widget
        central = QWidget()
        main_layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        # --- LEFT: info panel
        info_panel = QWidget()
        info_panel.setMinimumWidth(200)
        info_panel.setMaximumWidth(280)
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(20, 24, 20, 24)
        info_layout.setSpacing(4)

        self.symbol_label = QLabel("—")
        self.symbol_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        self.name_label = QLabel("")
        self.name_label.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        self.name_label.setWordWrap(True)

        self.price_label = QLabel("—")
        self.price_label.setStyleSheet("font-size: 32px; font-weight: bold; margin-top: 16px;")

        self.change_label = QLabel("")
        self.change_label.setStyleSheet("font-size: 15px;")

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #555555; margin-top: 8px; margin-bottom: 4px;")

        # --- Tabs ---
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # helper: a key/value stat row
        def stat_row(label_text):
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            k = QLabel(label_text)
            k.setStyleSheet("font-size: 11px; color: #888888;")
            v = QLabel("—")
            v.setStyleSheet("font-size: 11px; color: #dddddd; font-weight: bold;")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(k)
            row.addStretch()
            row.addWidget(v)
            return w, v

        # ---- Info tab ----
        info_tab = QWidget()
        info_tab_layout = QVBoxLayout(info_tab)
        info_tab_layout.setContentsMargins(4, 12, 4, 8)
        info_tab_layout.setSpacing(6)

        stats_title = QLabel("Statistics")
        stats_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        month_high_row, self.stat_month_high = stat_row("1M High")
        month_low_row,  self.stat_month_low  = stat_row("1M Low")
        w52_high_row,   self.stat_52w_high   = stat_row("52W High")
        w52_low_row,    self.stat_52w_low    = stat_row("52W Low")
        avg_vol_row,    self.stat_avg_vol    = stat_row("Avg Vol (30d)")

        stats_sep = QFrame()
        stats_sep.setFrameShape(QFrame.Shape.HLine)
        stats_sep.setStyleSheet("color: #555555; margin-top: 6px; margin-bottom: 6px;")

        insider_title = QLabel("Insider Trades")
        insider_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        self._senate_status = QLabel("—")
        self._senate_status.setStyleSheet("font-size: 11px; color: #666666;")
        self._senate_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._senate_container = QWidget()
        self._senate_container.setStyleSheet("background: transparent;")
        self._senate_inner_layout = QVBoxLayout(self._senate_container)
        self._senate_inner_layout.setContentsMargins(0, 0, 0, 0)
        self._senate_inner_layout.setSpacing(8)

        senate_scroll = QScrollArea()
        senate_scroll.setWidgetResizable(True)
        senate_scroll.setWidget(self._senate_container)
        senate_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        info_tab_layout.addWidget(stats_title)
        info_tab_layout.addWidget(month_high_row)
        info_tab_layout.addWidget(month_low_row)
        info_tab_layout.addWidget(w52_high_row)
        info_tab_layout.addWidget(w52_low_row)
        info_tab_layout.addWidget(avg_vol_row)
        info_tab_layout.addWidget(stats_sep)
        info_tab_layout.addWidget(insider_title)
        info_tab_layout.addWidget(self._senate_status)
        info_tab_layout.addWidget(senate_scroll, stretch=1)

        # ---- Analysis tab ----
        analysis_tab = QWidget()
        analysis_tab_layout = QVBoxLayout(analysis_tab)
        analysis_tab_layout.setContentsMargins(4, 12, 4, 8)
        analysis_tab_layout.setSpacing(4)

        pred_title = QLabel("Prediction (30 days)")
        pred_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        self.predict_button = QPushButton("Predict Next Month")
        self.predict_button.clicked.connect(self.run_prediction)
        self.predict_button.setEnabled(False)

        self.pred_price_label = QLabel("")
        self.pred_price_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.pred_range_label = QLabel("")
        self.pred_range_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        self.pred_range_label.setWordWrap(True)

        self.pred_signal_label = QLabel("")
        self.pred_signal_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        ai_separator = QFrame()
        ai_separator.setFrameShape(QFrame.Shape.HLine)
        ai_separator.setStyleSheet("color: #555555; margin-top: 10px; margin-bottom: 10px;")

        ai_title = QLabel("AI Analysis")
        ai_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        self.ai_button = QPushButton("Analyse with AI")
        self.ai_button.clicked.connect(self.run_ai_analysis)
        self.ai_button.setEnabled(False)

        self.ai_score_label = QLabel("")
        self.ai_score_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.ai_desc_label = QLabel("")
        self.ai_desc_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")

        self.ai_summary_label = QLabel("")
        self.ai_summary_label.setStyleSheet("font-size: 11px; color: #888888; font-style: italic;")
        self.ai_summary_label.setWordWrap(True)

        analysis_tab_layout.addWidget(pred_title)
        analysis_tab_layout.addSpacing(4)
        analysis_tab_layout.addWidget(self.predict_button)
        analysis_tab_layout.addWidget(self.pred_price_label)
        analysis_tab_layout.addWidget(self.pred_range_label)
        analysis_tab_layout.addWidget(self.pred_signal_label)
        analysis_tab_layout.addWidget(ai_separator)
        analysis_tab_layout.addWidget(ai_title)
        analysis_tab_layout.addSpacing(4)
        analysis_tab_layout.addWidget(self.ai_button)
        analysis_tab_layout.addWidget(self.ai_score_label)
        analysis_tab_layout.addWidget(self.ai_desc_label)
        analysis_tab_layout.addWidget(self.ai_summary_label)
        analysis_tab_layout.addStretch()

        tabs.addTab(info_tab, "Info")
        tabs.addTab(analysis_tab, "Analysis")

        info_layout.addWidget(self.symbol_label)
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.price_label)
        info_layout.addWidget(self.change_label)
        info_layout.addWidget(separator)
        info_layout.addWidget(tabs, stretch=1)

        # --- RIGHT: chart + controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        combo_row = QHBoxLayout()
        self.stock_combo = QComboBox()
        self.stock_combo.currentIndexChanged.connect(self.on_stock_changed)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.on_delete_stock)
        self.delete_button.setFixedWidth(80)
        font = self.delete_button.font()
        font.setPointSize(9)
        self.delete_button.setFont(font)

        self.add_button = QPushButton("+ Add Stock")
        self.add_button.clicked.connect(self.add_new_stock_dialog)
        self.add_button.setFixedWidth(self.add_button.fontMetrics().horizontalAdvance("+ Add Stock") + 24)

        if self.stock_combo.count() == 0:
            self.delete_button.setEnabled(False)

        combo_row.addWidget(self.add_button)
        combo_row.addWidget(self.stock_combo)
        combo_row.addWidget(self.delete_button)

        # chart
        self.chart = StockChart()
        self.chart.register_indicator("SMA 20", lambda df: stock_handler.calculate_SMA(df, 20), (0, 255, 0), "SMA 20")
        self.chart.register_indicator("SMA 50", lambda df: stock_handler.calculate_SMA(df, 50), (0, 0, 255), "SMA 50")
        self.chart.register_indicator("EMA 20", lambda df: stock_handler.calculate_EMA(df, 20), (255, 0, 255), "EMA 20")

        # indicator buttons
        self.indicator_row = QHBoxLayout()
        self.indicator_buttons = {
            "SMA 20": QPushButton("SMA 20"),
            "SMA 50": QPushButton("SMA 50"),
            "EMA 20": QPushButton("EMA 20"),
        }
        for key, btn in self.indicator_buttons.items():
            btn.setCheckable(True)
            btn.setFixedWidth(100)
            btn.clicked.connect(self.on_indicator_toggled)
            self.indicator_row.addWidget(btn)

        # date range buttons
        self.date_range_row = QHBoxLayout()
        self.date_buttons = [
            {"value": 365,  "button": QPushButton("1 Year")},
            {"value": 182,  "button": QPushButton("6 Months")},
            {"value": 91,   "button": QPushButton("3 Months")},
            {"value": 30,   "button": QPushButton("1 Month")},
            {"value": None, "button": QPushButton("All")},
        ]
        for db in self.date_buttons:
            btn = db["button"]
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda checked, v=db["value"]: self.chart.set_date_range(v))
            self.date_range_row.addWidget(btn)

        self.populate_stock_combo()
        if len(self.cache.list_stocks()) == 0:
            default = self.user_profile["preferences"].get("default_stock", "")
            if default:
                QMessageBox.information(self, "Welcome", f"No stocks found. Loading default stock: {default}")
                self._worker_mode = "add"
                self._worker_symbol = default
                self._worker = StockFetchWorker("add", default, self.csv_path, name=default)
                self._worker.finished.connect(self._on_worker_finished)
                self._worker.error.connect(self._on_worker_error)
                self._worker.start()

        right_layout.addLayout(combo_row)
        right_layout.addWidget(self.chart)
        right_layout.addLayout(self.date_range_row)
        right_layout.addLayout(self.indicator_row)

        main_layout.addWidget(info_panel)
        main_layout.addWidget(right_panel, stretch=1)

    def populate_stock_combo(self, select_symbol: str | None = None):
        self.stock_combo.blockSignals(True)
        self.stock_combo.clear()
        for symbol, data in self.cache.all_stocks().items():
            name = data.get("name", symbol)
            self.stock_combo.addItem(f"{symbol} - {name}", userData=symbol)
        if select_symbol is not None:
            for i in range(self.stock_combo.count()):
                if self.stock_combo.itemData(i) == select_symbol:
                    self.stock_combo.setCurrentIndex(i)
                    break
        self.stock_combo.blockSignals(False)
        idx = self.stock_combo.currentIndex()
        if idx >= 0:
            self.on_stock_changed(idx)

    def on_stock_changed(self, index):
        if index < 0:
            return
        symbol = self.stock_combo.itemData(index)
        self.delete_button.setEnabled(symbol is not None)
        if symbol is None:
            return
        self.load_stock(symbol)

    def add_new_stock_dialog(self):
        symbol, ok = QInputDialog.getText(self, "Add New Stock", "Enter stock symbol (e.g., AAPL):")
        if not ok or not symbol.strip():
            return
        symbol = symbol.strip().upper()
        if self.cache.has_stock(symbol):
            QMessageBox.information(self, "Stock Exists", f"'{symbol}' is already in your portfolio.")
            return
        name, ok = QInputDialog.getText(self, "Add New Stock", "Enter stock name (optional):")
        name = name.strip() if ok and name.strip() else symbol
        if not os.path.exists(self.csv_path):
            os.makedirs(self.csv_path)
        self._worker_symbol = symbol
        self._worker_mode = "add"
        self._worker = StockFetchWorker("add", symbol, self.csv_path, name=name)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._set_controls_enabled(False)
        self.statusBar().showMessage(f"Fetching data for {symbol}...")
        self._worker.start()

    def on_delete_stock(self):
        index = self.stock_combo.currentIndex()
        if index < 0:
            return
        symbol = self.stock_combo.itemData(index)
        if symbol is None:
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete", f"Delete '{symbol}' from your portfolio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.cache.delete_stock(symbol, self.csv_path)
        self.populate_stock_combo()
        has_stocks = any(
            self.stock_combo.itemData(i) is not None for i in range(self.stock_combo.count())
        )
        if not has_stocks:
            self.df = pd.DataFrame()
            self.update_info_panel(None)
            self.chart.clear()
            self.delete_button.setEnabled(False)

    def load_stock(self, symbol):
        info = self.cache.get_stock_data(symbol)
        if info is None:
            return
        filename = info.get("dfpath")
        if filename is None:
            return
        dfpath = os.path.join(self.csv_path, filename)
        if not os.path.exists(dfpath) or not self.cache.is_stock_fresh(symbol):
            self._worker_symbol = symbol
            self._worker_mode = "refresh"
            self._worker = StockFetchWorker("refresh", symbol, self.csv_path)
            self._worker.finished.connect(self._on_worker_finished)
            self._worker.error.connect(self._on_worker_error)
            self._set_controls_enabled(False)
            self.statusBar().showMessage(f"Refreshing {symbol}...")
            self._worker.start()
            return
        self.df = pd.read_csv(dfpath, parse_dates=True, index_col=0)
        self.update_info_panel(symbol)
        self.chart.set_data(self.df)

    def on_indicator_toggled(self):
        btn = self.sender()
        key = next((k for k, b in self.indicator_buttons.items() if b == btn), None)
        if key:
            self.chart.toggle_indicator(key, btn.isChecked())

    def run_ai_analysis(self):
        if self.df.empty:
            return
        from ui.ai_analysis_dialog import AIAnalysisDialog
        from core.ai_analysis_worker import AIAnalysisWorker
        symbol = self.stock_combo.currentData()
        info = self.cache.get_stock_data(symbol)
        name = info.get("name", symbol) if info else symbol

        if self.cache.is_ai_analysis_fresh(symbol):
            cached = self.cache.get_ai_analysis(symbol)
            dialog = AIAnalysisDialog(symbol, name, self)
            dialog.show_results(cached)
            dialog.exec()
            return

        self._ai_worker = AIAnalysisWorker(symbol, name, self.df)
        dialog = AIAnalysisDialog(symbol, name, self)
        self._ai_worker.finished.connect(dialog.show_results)
        self._ai_worker.finished.connect(lambda result, sym=symbol: self._save_and_display_ai(sym, result))
        self._ai_worker.error.connect(dialog.show_error)
        self._ai_worker.status.connect(dialog.update_status)
        self._ai_worker.start()
        dialog.exec()

    def _save_and_display_ai(self, symbol, result):
        self.cache.set_ai_analysis(symbol, result)
        self._update_ai_score(result)

    def _update_ai_score(self, result):
        from ui.ai_analysis_dialog import _score_color, _score_description
        score = result.get("score", 0)
        color = _score_color(score)
        desc = _score_description(score)
        self.ai_score_label.setText(f"{score:+d}")
        self.ai_score_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        self.ai_desc_label.setText(desc)
        self.ai_desc_label.setStyleSheet(f"font-size: 11px; color: {color};")
        self.ai_summary_label.setText(result.get("summary", ""))

    def _fetch_senate_trades(self, symbol):
        from core.senate_worker import SenateWorker
        self._senate_status.setText("Loading...")
        self._senate_status.show()
        for i in reversed(range(self._senate_inner_layout.count())):
            w = self._senate_inner_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._senate_worker = SenateWorker(symbol)
        self._senate_worker.finished.connect(self._update_senate_trades)
        self._senate_worker.start()

    def _update_senate_trades(self, trades):
        for i in reversed(range(self._senate_inner_layout.count())):
            w = self._senate_inner_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if not trades:
            self._senate_status.setText("No recent insider trades found.")
            return

        self._senate_status.hide()
        for t in trades:
            name = t.get("name") or t.get("senator") or "Unknown"
            trade_type = (t.get("type") or t.get("transaction_type") or "Unknown").upper()
            date = t.get("transaction_date") or t.get("date") or ""
            amount = t.get("amount", "")

            is_buy = any(k in trade_type for k in ("BUY", "PURCHASE"))
            is_sell = any(k in trade_type for k in ("SALE", "SELL"))
            color = "#00cc66" if is_buy else ("#ff4444" if is_sell else "#888888")
            arrow = "▲" if is_buy else ("▼" if is_sell else "·")

            detail = f"{date}" + (f"  ·  {amount}" if amount else "")
            entry = QLabel(
                f'<span style="color:{color};">{arrow} {trade_type}</span>  {name}'
                f'<br><span style="color:#666666; font-size:11px;">{detail}</span>'
            )
            entry.setTextFormat(Qt.TextFormat.RichText)
            entry.setWordWrap(True)
            self._senate_inner_layout.addWidget(entry)

    def run_prediction(self):
        if self.df.empty:
            return
        self.predict_button.setEnabled(False)
        self.predict_button.setText("Running...")
        self._clear_prediction_labels()
        self.chart.clear_prediction()
        self._pred_worker = PredictionWorker(self.df)
        self._pred_worker.finished.connect(self._on_prediction_finished)
        self._pred_worker.error.connect(self._on_prediction_error)
        self._pred_worker.start()

    def _on_prediction_finished(self, forecast):
        self.predict_button.setEnabled(True)
        self.predict_button.setText("Predict Next Month")
        pred, low, high = self.chart.set_prediction(forecast, self.df.index[-1])
        current = float(self.df["Close"].iloc[-1])
        change_pct = ((pred - current) / current) * 100
        self.pred_price_label.setText(f"${pred:.2f}")
        self.pred_range_label.setText(f"Range: ${low:.2f} – ${high:.2f}")
        if change_pct >= 5:
            signal, color = "BUY", "#00cc66"
        elif change_pct <= -5:
            signal, color = "SELL", "#ff4444"
        else:
            signal, color = "HOLD", "#ffaa00"
        self.pred_signal_label.setText(f"{signal}  ({change_pct:+.1f}%)")
        self.pred_signal_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")

    def _on_prediction_error(self, message):
        self.predict_button.setEnabled(True)
        self.predict_button.setText("Predict Next Month")
        QMessageBox.warning(self, "Prediction Error", message)

    def _clear_prediction_labels(self):
        self.pred_price_label.setText("")
        self.pred_range_label.setText("")
        self.pred_signal_label.setText("")

    def update_info_panel(self, symbol):
        self._clear_prediction_labels()
        self.chart.clear_prediction()
        if symbol is None or self.df.empty:
            self.predict_button.setEnabled(False)
            self.ai_button.setEnabled(False)
            self.ai_score_label.setText("")
            self.ai_desc_label.setText("")
            self.ai_summary_label.setText("")
            self._senate_status.setText("—")
            self._senate_status.show()
            self.symbol_label.setText("—")
            self.name_label.setText("")
            self.price_label.setText("—")
            self.change_label.setText("")
            for lbl in (self.stat_month_high, self.stat_month_low,
                        self.stat_52w_high, self.stat_52w_low, self.stat_avg_vol):
                lbl.setText("—")
            return
        info = self.cache.get_stock_data(symbol)
        name = info.get("name", symbol) if info else symbol
        self.symbol_label.setText(symbol)
        self.name_label.setText(name)
        current = self.df["Close"].iloc[-1]
        prev = self.df["Close"].iloc[-2] if len(self.df) > 1 else current
        change_pct = ((current - prev) / prev) * 100
        self.price_label.setText(f"${current:.2f}")
        if change_pct >= 0:
            self.change_label.setText(f"▲ +{change_pct:.2f}%")
            self.change_label.setStyleSheet("font-size: 15px; color: #00cc66;")
        else:
            self.change_label.setText(f"▼ {change_pct:.2f}%")
            self.change_label.setStyleSheet("font-size: 15px; color: #ff4444;")

        # stats
        now = pd.Timestamp.now()
        month_df = self.df[self.df.index >= now - pd.Timedelta(days=30)]
        year_df  = self.df[self.df.index >= now - pd.Timedelta(days=365)]
        if not month_df.empty:
            self.stat_month_high.setText(f"${month_df['High'].max():.2f}")
            self.stat_month_low.setText(f"${month_df['Low'].min():.2f}")
            avg = month_df["Volume"].mean()
            self.stat_avg_vol.setText(f"{avg/1e6:.1f}M" if avg >= 1e6 else f"{avg/1e3:.0f}K")
        else:
            self.stat_month_high.setText("—")
            self.stat_month_low.setText("—")
            self.stat_avg_vol.setText("—")
        self.stat_52w_high.setText(f"${year_df['High'].max():.2f}" if not year_df.empty else "—")
        self.stat_52w_low.setText(f"${year_df['Low'].min():.2f}" if not year_df.empty else "—")

        self.predict_button.setEnabled(True)
        self.ai_button.setEnabled(True)
        cached = self.cache.get_ai_analysis(symbol)
        if cached and self.cache.is_ai_analysis_fresh(symbol):
            self._update_ai_score(cached)
        else:
            self.ai_score_label.setText("")
            self.ai_desc_label.setText("")
            self.ai_summary_label.setText("")
        self._fetch_senate_trades(symbol)

    def _set_controls_enabled(self, enabled):
        self.stock_combo.setEnabled(enabled)
        for db in self.date_buttons:
            db["button"].setEnabled(enabled)
        self.delete_button.setEnabled(enabled and self.stock_combo.currentData() is not None)

    def _on_worker_finished(self, result):
        self._set_controls_enabled(True)
        self.statusBar().clearMessage()
        if self._worker_mode == "refresh":
            self.cache.update_stock_timestamp(self._worker_symbol)
            self.cache.save_cache()
            info = self.cache.get_stock_data(self._worker_symbol)
            self.df = pd.read_csv(
                os.path.join(self.csv_path, info["dfpath"]), parse_dates=True, index_col=0
            )
            self.update_info_panel(self._worker_symbol)
            self.chart.set_data(self.df)
        elif self._worker_mode == "add":
            self.cache.set_stock_data(result)
            self._worker = None
            self.populate_stock_combo(select_symbol=self._worker_symbol)
        self._worker = None

    def _on_worker_error(self, message):
        self._set_controls_enabled(True)
        self.statusBar().clearMessage()
        QMessageBox.warning(self, "Fetch Error", message)
        if self._worker_mode == "add":
            self.populate_stock_combo()
        self._worker = None


def apply_dark_theme(app):
    app.setStyle("Fusion")
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.ToolTipBase, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark)
