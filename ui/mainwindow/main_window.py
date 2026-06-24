import os
import traceback

import pandas as pd

from core import caching
from core.prediction_worker import PredictionWorker
from .info_panel import InfoPanel
from .chart_panel import ChartPanel
from .explore_panel import ExplorePanel

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QTabWidget, QStackedWidget, QMessageBox,
)
from PyQt6.QtCore import QThread, pyqtSignal

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
            print(f"[StockFetch] Failed to fetch {self.symbol}: {e}")
            traceback.print_exc()
            self.error.emit("Failed to fetch stock data. Check the console for details.")


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

        # Top-level tab widget: Portfolio | Explore
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # --- Portfolio tab: QStackedWidget for stock view ↔ portfolio page navigation
        self._stack = QStackedWidget()

        stock_widget = QWidget()
        main_layout = QHBoxLayout(stock_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        startup_theme = user_profile.get("preferences", {}).get("theme", "dark")
        self.info_panel = InfoPanel(username=self.username, theme=startup_theme)
        self.chart_panel = ChartPanel()

        if startup_theme != "dark":
            self.chart_panel.apply_theme(startup_theme)

        self.info_panel.predict_requested.connect(self.run_prediction)
        self.info_panel.ai_requested.connect(self.run_ai_analysis)
        self.info_panel.profile_clicked.connect(self.open_portfolio)
        self.info_panel.stock_renamed.connect(self._on_stock_renamed)
        self.chart_panel.stock_changed.connect(self.load_stock)
        self.chart_panel.add_stock_requested.connect(self.add_new_stock_dialog)
        self.chart_panel.delete_stock_requested.connect(self.on_delete_stock)

        main_layout.addWidget(self.info_panel)
        main_layout.addWidget(self.chart_panel, stretch=1)
        self._stack.addWidget(stock_widget)

        # --- Explore tab
        self.explore_panel = ExplorePanel(theme=startup_theme)
        self.explore_panel.add_to_portfolio.connect(self.add_stock_from_explore)

        self._tabs.addTab(self._stack, "Portfolio")
        self._tabs.addTab(self.explore_panel, "Explore")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self.explore_panel.start_background_load()

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

    def open_portfolio(self):
        from .portfolio_page import UserPage
        if self._stack.count() > 1:
            old = self._stack.widget(1)
            self._stack.removeWidget(old)
            old.deleteLater()
        current_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
        page = UserPage(self.cache, self.csv_path, self.user_profile, theme=current_theme, parent=self)
        page.back_requested.connect(lambda: self._stack.setCurrentIndex(0))
        page.settings_requested.connect(self.open_settings)
        self._stack.addWidget(page)
        self._stack.setCurrentIndex(1)

    def open_settings(self):
        from .settings_dialog import UserSettingsDialog
        old_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
        dialog = UserSettingsDialog(self.user_profile, theme=old_theme, parent=self)
        dialog.username_changed.connect(self._on_username_changed)
        dialog.avatar_changed.connect(self._on_avatar_changed)
        if dialog.exec():
            new_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
            if new_theme != old_theme:
                apply_palette(QApplication.instance(), new_theme)
                self.chart_panel.apply_theme(new_theme)
                self.info_panel.set_theme(new_theme)
                self.explore_panel.set_theme(new_theme)

    def _on_username_changed(self, new_username: str):
        from core.user_manager import get_user_dir
        self.username = new_username
        self.setWindowTitle(f"Stock Viewer - User: {new_username}")
        self.cache.path = os.path.join(get_user_dir(new_username), "cache")
        self.csv_path = os.path.join(get_user_dir(new_username), "csvFiles")
        self.info_panel.set_username(new_username)

    def _on_avatar_changed(self):
        self.info_panel.refresh_avatar()

    def _on_tab_changed(self, index):
        if index == 1:
            self.explore_panel.refresh_if_empty()

    def add_stock_from_explore(self, symbol):
        if self.cache.has_stock(symbol):
            QMessageBox.information(self, "Already in Portfolio", f"'{symbol}' is already in your portfolio.")
            self._tabs.setCurrentIndex(0)
            return
        if not os.path.exists(self.csv_path):
            os.makedirs(self.csv_path)
        self._worker_symbol = symbol
        self._worker_mode = "add"
        self._worker = StockFetchWorker("add", symbol, self.csv_path, name=symbol)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._set_controls_enabled(False)
        self.statusBar().showMessage(f"Adding {symbol} to portfolio...")
        self._worker.start()
        self._tabs.setCurrentIndex(0)

    def add_new_stock_dialog(self):
        from .add_stock_dialog import AddStockDialog
        current_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
        dialog = AddStockDialog(theme=current_theme, parent=self)
        if not dialog.exec():
            return
        symbol = dialog.get_symbol()
        if not symbol:
            return
        if self.cache.has_stock(symbol):
            QMessageBox.information(self, "Stock Exists", f"'{symbol}' is already in your portfolio.")
            return
        if not os.path.exists(self.csv_path):
            os.makedirs(self.csv_path)
        self._worker_symbol = symbol
        self._worker_mode = "add"
        self._worker = StockFetchWorker("add", symbol, self.csv_path, name=symbol)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._set_controls_enabled(False)
        self.statusBar().showMessage(f"Fetching data for {symbol}...")
        self._worker.start()

    def _on_stock_renamed(self, symbol, new_name):
        self.chart_panel.populate_stocks(self.cache.all_stocks(), select_symbol=symbol)

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
        from .api_key_dialog import ApiKeyDialog
        from core.ai_analysis_worker import AIAnalysisWorker
        from core import key_manager
        symbol = self.chart_panel.current_symbol()
        info = self.cache.get_stock_data(symbol)
        name = info.get("name", symbol) if info else symbol

        current_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
        if self.cache.is_ai_analysis_fresh(symbol):
            cached = self.cache.get_ai_analysis(symbol)
            dialog = AIAnalysisDialog(symbol, name, theme=current_theme, parent=self)
            dialog.show_results(cached)
            dialog.exec()
            return

        anthropic_key = key_manager.get_key(self.username, "ANTHROPIC_API_KEY")
        if not anthropic_key:
            dlg = ApiKeyDialog("ANTHROPIC_API_KEY", self.username, theme=current_theme, parent=self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            anthropic_key = key_manager.get_key(self.username, "ANTHROPIC_API_KEY")

        finnhub_key = key_manager.get_key(self.username, "FINNHUB_API_KEY")
        self._ai_worker = AIAnalysisWorker(symbol, name, self.df,
                                           anthropic_key=anthropic_key,
                                           finnhub_key=finnhub_key)
        dialog = AIAnalysisDialog(symbol, name, theme=current_theme, parent=self)
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
