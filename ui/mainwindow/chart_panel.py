from core import stock_handler
from .stock_chart import StockChart
from ui.theme import get_tokens

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt


def _build_style(t: dict) -> str:
    h = t["highlight"]
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    # Hover: slightly lighter; pressed: slightly darker
    h_r = f"#{min(255,r+20):02x}{min(255,g+20):02x}{min(255,b+20):02x}"
    h_d = f"#{max(0,r-20):02x}{max(0,g-20):02x}{max(0,b-20):02x}"
    return f"""
        QComboBox#stock_combo {{
            background: {t['base']};
            color: {t['text']};
            border: 1px solid {t['separator']};
            border-radius: 6px;
            padding: 0px 10px;
            font-size: {t['font_title']};
        }}
        QComboBox#stock_combo:hover {{
            border-color: {t['highlight']};
        }}
        QComboBox#stock_combo:disabled {{
            color: {t['label_muted']};
        }}
        QComboBox#stock_combo::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox#stock_combo::down-arrow {{
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {t['label_secondary']};
            width: 0;
            height: 0;
        }}
        QComboBox#stock_combo QAbstractItemView {{
            background: {t['base']};
            color: {t['text']};
            border: 1px solid {t['separator']};
            selection-background-color: {t['highlight']};
            selection-color: #ffffff;
            outline: none;
            padding: 2px;
        }}
        QPushButton#btn_add {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            font-size: {t['font_title']};
            font-weight: bold;
            padding: 0px 16px;
        }}
        QPushButton#btn_add:hover {{ background: {h_r}; }}
        QPushButton#btn_add:pressed {{ background: {h_d}; }}
        QPushButton#btn_add:disabled {{
            background: {t['alternate_base']};
            color: {t['label_muted']};
        }}
        QPushButton#btn_delete {{
            background: transparent;
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-radius: 6px;
            font-size: {t['font_small']};
        }}
        QPushButton#btn_delete:hover {{
            color: {t['sell_color']};
            border-color: {t['sell_color']};
        }}
        QPushButton#btn_delete:pressed {{
            color: {t['sell_color']};
        }}
        QPushButton#btn_delete:disabled {{
            color: {t['label_faint']};
            border-color: {t['separator_strong']};
        }}
        QPushButton#btn_range {{
            background: transparent;
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-radius: 5px;
            font-size: {t['font_small']};
            font-weight: bold;
        }}
        QPushButton#btn_range:hover {{
            color: {t['text']};
            border-color: {t['highlight']};
        }}
        QPushButton#btn_range:checked {{
            background: {t['highlight']};
            color: #ffffff;
            border-color: {t['highlight']};
        }}
        QPushButton#btn_range:disabled {{
            color: {t['label_faint']};
            border-color: {t['separator_strong']};
        }}
        QPushButton#btn_indicator {{
            background: transparent;
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-radius: 5px;
            font-size: {t['font_small']};
        }}
        QPushButton#btn_indicator:hover {{
            color: {t['text']};
            border-color: {t['highlight']};
        }}
        QPushButton#btn_indicator:checked {{
            background: rgba({r},{g},{b},45);
            color: {t['highlight']};
            border-color: {t['highlight']};
        }}
        QPushButton#btn_indicator:disabled {{
            color: {t['label_faint']};
            border-color: {t['separator_strong']};
        }}
    """


class ChartPanel(QWidget):
    stock_changed = pyqtSignal(str)
    add_stock_requested = pyqtSignal()
    delete_stock_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = "dark"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # ── Combo row ─────────────────────────────────────────────────────
        combo_row = QHBoxLayout()
        combo_row.setSpacing(8)

        self._add_button = QPushButton("+ Add Stock")
        self._add_button.setObjectName("btn_add")
        self._add_button.setFixedHeight(34)
        self._add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_button.clicked.connect(self.add_stock_requested)

        self._combo = QComboBox()
        self._combo.setObjectName("stock_combo")
        self._combo.setFixedHeight(34)
        self._combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._combo.currentIndexChanged.connect(self._on_combo_changed)

        self._delete_button = QPushButton("Delete")
        self._delete_button.setObjectName("btn_delete")
        self._delete_button.setFixedHeight(34)
        self._delete_button.setFixedWidth(72)
        self._delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_button.clicked.connect(self.delete_stock_requested)
        self._delete_button.setEnabled(False)

        combo_row.addWidget(self._add_button)
        combo_row.addWidget(self._combo)
        combo_row.addWidget(self._delete_button)

        # ── Chart ─────────────────────────────────────────────────────────
        self._chart = StockChart()
        self._chart.register_indicator("SMA 20", lambda df: stock_handler.calculate_SMA(df, 20), (0, 255, 0), "SMA 20")
        self._chart.register_indicator("SMA 50", lambda df: stock_handler.calculate_SMA(df, 50), (0, 0, 255), "SMA 50")
        self._chart.register_indicator("EMA 20", lambda df: stock_handler.calculate_EMA(df, 20), (255, 0, 255), "EMA 20")

        # ── Bottom toolbar: date range (left) + indicators (right) ────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)

        self._date_buttons = [
            {"value": 365,  "label": "1Y",  "button": None},
            {"value": 182,  "label": "6M",  "button": None},
            {"value": 91,   "label": "3M",  "button": None},
            {"value": 30,   "label": "1M",  "button": None},
            {"value": None, "label": "All", "button": None},
        ]
        for db in self._date_buttons:
            btn = QPushButton(db["label"])
            btn.setObjectName("btn_range")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setFixedWidth(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=db["value"], b=btn: self._set_date_range(v, b))
            db["button"] = btn
            bottom_row.addWidget(btn)

        # Default: 1Y selected
        self._date_buttons[0]["button"].setChecked(True)

        bottom_row.addStretch()

        self._indicator_buttons = {
            "SMA 20": QPushButton("SMA 20"),
            "SMA 50": QPushButton("SMA 50"),
            "EMA 20": QPushButton("EMA 20"),
        }
        for key, btn in self._indicator_buttons.items():
            btn.setObjectName("btn_indicator")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setFixedWidth(68)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._on_indicator_toggled)
            bottom_row.addWidget(btn)

        layout.addLayout(combo_row)
        layout.addWidget(self._chart)
        layout.addLayout(bottom_row)

        self._apply_styles()

    # ── Private ───────────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet(_build_style(get_tokens(self._theme)))

    def _set_date_range(self, value, active_btn):
        for db in self._date_buttons:
            db["button"].setChecked(db["button"] is active_btn)
        self._chart.set_date_range(value)

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

    # ── Public ────────────────────────────────────────────────────────────

    def populate_stocks(self, stocks: dict, select_symbol=None):
        self._combo.blockSignals(True)
        self._combo.clear()
        for symbol, data in stocks.items():
            name = data.get("name", symbol)
            self._combo.addItem(f"{symbol} — {name}", userData=symbol)
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
        self._theme = theme_name
        self._chart.apply_theme(theme_name)
        self._apply_styles()

    def set_prediction(self, forecast, last_date):
        return self._chart.set_prediction(forecast, last_date)
