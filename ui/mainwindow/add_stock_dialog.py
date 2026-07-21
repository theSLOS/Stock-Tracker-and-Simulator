import json
import os
from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from ui.theme import get_tokens

_SYMBOL_PATH = os.path.join(os.path.dirname(__file__), '..', 'logo', 'logo-symbol.svg')


def _svg_pixmap(size: int) -> QPixmap:
    renderer = QSvgRenderer(_SYMBOL_PATH)
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    renderer.render(p)
    p.end()
    return px


def _load_explore_cache():
    try:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, "Users", "explore_cache.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") == str(date.today()):
            return data.get("results", [])
    except Exception:
        pass
    return None


def _build_style(t: dict) -> str:
    return f"""
        QDialog {{
            background: {t['base']};
        }}
        QFrame#card {{
            background: {t['window']};
            border-radius: 14px;
            border: 1px solid {t['separator']};
        }}
        QLabel#dialog_title {{
            color: {t['text']};
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QFrame#sep {{
            background: {t['separator']};
            border: none;
            min-height: 1px;
            max-height: 1px;
        }}
        QLabel#field_lbl {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
            font-weight: bold;
        }}
        QLabel#section_lbl {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QLabel#cat_lbl {{
            color: {t['label_muted']};
            font-size: {t['font_small']};
        }}
        QLineEdit {{
            background: {t['base']};
            color: {t['text']};
            border: 1px solid {t['separator']};
            border-radius: 7px;
            padding: 0px 14px;
            font-size: {t['font_title']};
            selection-background-color: {t['highlight']};
        }}
        QLineEdit:focus {{
            border-color: {t['highlight']};
        }}
        QPushButton#btn_add {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 7px;
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QPushButton#btn_add:hover {{
            background: #3a92ea;
        }}
        QPushButton#btn_add:pressed {{
            background: #1a6fc0;
        }}
        QPushButton#btn_cancel {{
            background: transparent;
            color: {t['label_secondary']};
            border: none;
            font-size: {t['font_body']};
        }}
        QPushButton#btn_cancel:hover {{
            color: {t['text']};
        }}
    """


def _sep():
    f = QFrame()
    f.setObjectName("sep")
    return f


class AddStockDialog(QDialog):
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._tokens = get_tokens(theme)
        self._symbol = ""
        self._explore_data = _load_explore_cache()

        self.setWindowTitle("Add Stock")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(_build_style(self._tokens))
        self._build_ui()

    def _build_ui(self):
        t = self._tokens
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(_svg_pixmap(28))
        title_lbl = QLabel("Add Stock")
        title_lbl.setObjectName("dialog_title")
        header_row.addWidget(icon_lbl)
        header_row.addSpacing(10)
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        layout.addLayout(header_row)
        layout.addSpacing(18)
        layout.addWidget(_sep())
        layout.addSpacing(22)

        # ── Symbol input ──────────────────────────────────────────────────
        sym_lbl = QLabel("SYMBOL")
        sym_lbl.setObjectName("field_lbl")
        self._sym_input = QLineEdit()
        self._sym_input.setPlaceholderText("Enter ticker  (e.g. AAPL)")
        self._sym_input.setFixedHeight(42)
        self._sym_input.returnPressed.connect(self._on_add)

        layout.addWidget(sym_lbl)
        layout.addSpacing(7)
        layout.addWidget(self._sym_input)

        # ── Market highlights ─────────────────────────────────────────────
        if self._explore_data:
            layout.addSpacing(22)
            layout.addWidget(_sep())
            layout.addSpacing(18)

            section_lbl = QLabel("MARKET HIGHLIGHTS")
            section_lbl.setObjectName("section_lbl")
            layout.addWidget(section_lbl)
            layout.addSpacing(14)

            gainers = sorted(self._explore_data, key=lambda x: x["change_pct"], reverse=True)
            losers  = sorted(self._explore_data, key=lambda x: x["change_pct"])
            active  = sorted(self._explore_data, key=lambda x: x["volume"], reverse=True)

            self._add_chip_row(layout, "▲  TOP GAINERS",  gainers[:4], t["buy_color"])
            layout.addSpacing(10)
            self._add_chip_row(layout, "▼  TOP LOSERS",   losers[:4],  t["sell_color"])
            layout.addSpacing(10)
            self._add_chip_row(layout, "⚡  MOST ACTIVE",  active[:4],  t["highlight"])
        else:
            layout.addSpacing(14)
            hint = QLabel("Open the Explore tab to load market highlights")
            hint.setStyleSheet(
                f"color: {t['label_faint']}; font-size: {t['font_small']};"
            )
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)

        # ── Add button ────────────────────────────────────────────────────
        layout.addSpacing(26)
        add_btn = QPushButton("Add to Portfolio")
        add_btn.setObjectName("btn_add")
        add_btn.setFixedHeight(44)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add)
        layout.addWidget(add_btn)

        layout.addSpacing(14)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setFixedHeight(24)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        outer.addWidget(card)
        self.setFixedWidth(480)
        self.adjustSize()

    def _add_chip_row(self, layout, label: str, stocks: list, color: str):
        t = self._tokens

        cat_lbl = QLabel(label)
        cat_lbl.setObjectName("cat_lbl")
        layout.addWidget(cat_lbl)
        layout.addSpacing(5)

        row = QHBoxLayout()
        row.setSpacing(6)
        for stock in stocks:
            symbol = stock["symbol"]
            change = stock["change_pct"]
            pct = f"{change:+.1f}%"
            btn = QPushButton(f"{symbol}  {pct}")
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {color};
                    border: 1px solid {color};
                    border-radius: 13px;
                    font-size: {t['font_small']};
                    padding: 0px 10px;
                }}
                QPushButton:hover {{
                    background: {color}28;
                }}
                QPushButton:pressed {{
                    background: {color}44;
                }}
            """)
            btn.clicked.connect(lambda _checked, s=symbol: self._fill(s))
            row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)

    def _fill(self, symbol: str):
        self._sym_input.setText(symbol)
        self._sym_input.setFocus()

    def _on_add(self):
        symbol = self._sym_input.text().strip().upper()
        if not symbol:
            self._sym_input.setFocus()
            return
        self._symbol = symbol
        self.accept()

    def get_symbol(self) -> str:
        return self._symbol
