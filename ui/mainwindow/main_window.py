import os

import pandas as pd

from core import caching
from core.prediction_worker import PredictionWorker
from .info_panel import InfoPanel
from .chart_panel import ChartPanel

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QMessageBox, QInputDialog
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction

from ui.theme import apply_palette


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
        from core import stock_handler
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

        self.setWindowTitle(f"Stock Viewer - User: {self.username}")
        self.resize(1400, 800)

        central = QWidget()
        main_layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        self.info_panel = InfoPanel()
        self.chart_panel = ChartPanel()

        startup_theme = user_profile.get("preferences", {}).get("theme", "dark")
        if startup_theme != "dark":
            self.chart_panel.apply_theme(startup_theme)

        self.info_panel.predict_requested.connect(self.run_prediction)
        self.info_panel.ai_requested.connect(self.run_ai_analysis)
        self.chart_panel.stock_changed.connect(self.load_stock)
        self.chart_panel.add_stock_requested.connect(self.add_new_stock_dialog)
        self.chart_panel.delete_stock_requested.connect(self.on_delete_stock)

        main_layout.addWidget(self.info_panel)
        main_layout.addWidget(self.chart_panel, stretch=1)

        menu_bar = self.menuBar()
        user_menu = menu_bar.addMenu("User")
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        user_menu.addAction(settings_action)

        self.chart_panel.populate_stocks(self.cache.all_stocks())
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

    def open_settings(self):
        from .settings_dialog import UserSettingsDialog
        old_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
        dialog = UserSettingsDialog(self.user_profile, self)
        if dialog.exec():
            new_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
            if new_theme != old_theme:
                apply_palette(QApplication.instance(), new_theme)
                self.chart_panel.apply_theme(new_theme)

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
        symbol = self.chart_panel.current_symbol()
        if symbol is None:
            return
        confirm = QMessageBox.question(
            self, "Confirm Delete", f"Delete '{symbol}' from your portfolio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.cache.delete_stock(symbol, self.csv_path)
        self.chart_panel.populate_stocks(self.cache.all_stocks())
        if not self.chart_panel.current_symbol():
            self.df = pd.DataFrame()
            self.info_panel.update(None, self.df, self.cache)
            self.chart_panel.clear()

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
        self.chart_panel.clear_prediction()
        self.info_panel.update(symbol, self.df, self.cache)
        self.chart_panel.set_data(self.df)

    def run_ai_analysis(self):
        if self.df.empty:
            return
        from .ai_analysis_dialog import AIAnalysisDialog
        from core.ai_analysis_worker import AIAnalysisWorker
        symbol = self.chart_panel.current_symbol()
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
        self._ai_worker.finished.connect(lambda result, sym=symbol: self._on_ai_finished(sym, result))
        self._ai_worker.error.connect(dialog.show_error)
        self._ai_worker.status.connect(dialog.update_status)
        self._ai_worker.start()
        dialog.exec()

    def _on_ai_finished(self, symbol, result):
        self.cache.set_ai_analysis(symbol, result)
        self.info_panel.set_ai_result(result)

    def run_prediction(self):
        if self.df.empty:
            return
        self.info_panel.set_prediction_running(True)
        self.info_panel.clear_prediction()
        self.chart_panel.clear_prediction()
        self._pred_worker = PredictionWorker(self.df)
        self._pred_worker.finished.connect(self._on_prediction_finished)
        self._pred_worker.error.connect(self._on_prediction_error)
        self._pred_worker.start()

    def _on_prediction_finished(self, forecast):
        self.info_panel.set_prediction_running(False)
        pred, low, high = self.chart_panel.set_prediction(forecast, self.df.index[-1])
        self.info_panel.set_prediction_result(pred, low, high, float(self.df["Close"].iloc[-1]))

    def _on_prediction_error(self, message):
        self.info_panel.set_prediction_running(False)
        QMessageBox.warning(self, "Prediction Error", message)

    def _set_controls_enabled(self, enabled):
        self.chart_panel.set_controls_enabled(enabled)

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
            self.chart_panel.clear_prediction()
            self.info_panel.update(self._worker_symbol, self.df, self.cache)
            self.chart_panel.set_data(self.df)
        elif self._worker_mode == "add":
            self.cache.set_stock_data(result)
            self._worker = None
            self.chart_panel.populate_stocks(self.cache.all_stocks(), select_symbol=self._worker_symbol)
        self._worker = None

    def _on_worker_error(self, message):
        self._set_controls_enabled(True)
        self.statusBar().clearMessage()
        QMessageBox.warning(self, "Fetch Error", message)
        if self._worker_mode == "add":
            self.chart_panel.populate_stocks(self.cache.all_stocks())
        self._worker = None


def apply_dark_theme(app):
    apply_palette(app, "dark")


def apply_light_theme(app):
    apply_palette(app, "light")
