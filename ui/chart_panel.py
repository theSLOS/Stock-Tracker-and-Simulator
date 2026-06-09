from core import stock_handler
from ui.stock_chart import StockChart

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox
)
from PyQt6.QtCore import pyqtSignal


class ChartPanel(QWidget):
    stock_changed = pyqtSignal(str)
    add_stock_requested = pyqtSignal()
    delete_stock_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # --- combo row
        combo_row = QHBoxLayout()

        self._add_button = QPushButton("+ Add Stock")
        self._add_button.clicked.connect(self.add_stock_requested)
        self._add_button.setFixedWidth(
            self._add_button.fontMetrics().horizontalAdvance("+ Add Stock") + 24
        )

        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_combo_changed)

        self._delete_button = QPushButton("Delete")
        self._delete_button.clicked.connect(self.delete_stock_requested)
        self._delete_button.setFixedWidth(80)
        font = self._delete_button.font()
        font.setPointSize(9)
        self._delete_button.setFont(font)
        self._delete_button.setEnabled(False)

        combo_row.addWidget(self._add_button)
        combo_row.addWidget(self._combo)
        combo_row.addWidget(self._delete_button)

        # --- chart
        self._chart = StockChart()
        self._chart.register_indicator("SMA 20", lambda df: stock_handler.calculate_SMA(df, 20), (0, 255, 0), "SMA 20")
        self._chart.register_indicator("SMA 50", lambda df: stock_handler.calculate_SMA(df, 50), (0, 0, 255), "SMA 50")
        self._chart.register_indicator("EMA 20", lambda df: stock_handler.calculate_EMA(df, 20), (255, 0, 255), "EMA 20")

        # --- indicator buttons
        indicator_row = QHBoxLayout()
        self._indicator_buttons = {
            "SMA 20": QPushButton("SMA 20"),
            "SMA 50": QPushButton("SMA 50"),
            "EMA 20": QPushButton("EMA 20"),
        }
        for key, btn in self._indicator_buttons.items():
            btn.setCheckable(True)
            btn.setFixedWidth(100)
            btn.clicked.connect(self._on_indicator_toggled)
            indicator_row.addWidget(btn)

        # --- date range buttons
        date_row = QHBoxLayout()
        self._date_buttons = [
            {"value": 365,  "button": QPushButton("1 Year")},
            {"value": 182,  "button": QPushButton("6 Months")},
            {"value": 91,   "button": QPushButton("3 Months")},
            {"value": 30,   "button": QPushButton("1 Month")},
            {"value": None, "button": QPushButton("All")},
        ]
        for db in self._date_buttons:
            btn = db["button"]
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda checked, v=db["value"]: self._chart.set_date_range(v))
            date_row.addWidget(btn)

        layout.addLayout(combo_row)
        layout.addWidget(self._chart)
        layout.addLayout(date_row)
        layout.addLayout(indicator_row)

    # ------------------------------------------------------------------ public

    def populate_stocks(self, stocks: dict, select_symbol=None):
        self._combo.blockSignals(True)
        self._combo.clear()
        for symbol, data in stocks.items():
            name = data.get("name", symbol)
            self._combo.addItem(f"{symbol} - {name}", userData=symbol)
        if select_symbol is not None:
            for i in range(self._combo.count()):
                if self._combo.itemData(i) == select_symbol:
                    self._combo.setCurrentIndex(i)
                    break
        self._combo.blockSignals(False)
        symbol = self._combo.currentData()
        self._delete_button.setEnabled(symbol is not None)
        if symbol:
            self.stock_changed.emit(symbol)

    def current_symbol(self):
        return self._combo.currentData()

    def set_controls_enabled(self, enabled: bool):
        self._combo.setEnabled(enabled)
        for db in self._date_buttons:
            db["button"].setEnabled(enabled)
        self._delete_button.setEnabled(enabled and self._combo.currentData() is not None)

    def set_data(self, df):
        self._chart.set_data(df)

    def clear(self):
        self._chart.clear()

    def clear_prediction(self):
        self._chart.clear_prediction()

    def apply_theme(self, theme_name: str):
        self._chart.apply_theme(theme_name)

    def set_prediction(self, forecast, last_date):
        return self._chart.set_prediction(forecast, last_date)

    # ------------------------------------------------------------------ internal

    def _on_combo_changed(self, index):
        symbol = self._combo.itemData(index)
        self._delete_button.setEnabled(symbol is not None)
        if symbol:
            self.stock_changed.emit(symbol)

    def _on_indicator_toggled(self):
        btn = self.sender()
        key = next((k for k, b in self._indicator_buttons.items() if b == btn), None)
        if key:
            self._chart.toggle_indicator(key, btn.isChecked())
