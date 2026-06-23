import pandas as pd

from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTabWidget, QLineEdit, QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ..theme import get_tokens


class _MiniAvatar(QWidget):
    def __init__(self, initial, size=28, parent=None):
        super().__init__(parent)
        self._initial = initial
        self.setFixedSize(size, size)
        self._size = size

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#2a82da"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, self._size, self._size)
        font = QFont()
        font.setPixelSize(int(self._size * 0.42))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)


class _ProfileRow(QWidget):
    clicked = pyqtSignal()

    _THEMES = {
        "dark":  {
            "normal": ("QWidget { background: #4a4a4a; border: 1px solid #5e5e5e; border-radius: 8px; }"
                       " QLabel { background: transparent; border: none; }"),
            "hover":  ("QWidget { background: #575757; border: 1px solid #707070; border-radius: 8px; }"
                       " QLabel { background: transparent; border: none; }"),
        },
        "light": {
            "normal": ("QWidget { background: #e2e2e2; border: 1px solid #cccccc; border-radius: 8px; }"
                       " QLabel { background: transparent; border: none; }"),
            "hover":  ("QWidget { background: #d6d6d6; border: 1px solid #bbbbbb; border-radius: 8px; }"
                       " QLabel { background: transparent; border: none; }"),
        },
    }

    def __init__(self, initial, username, theme="dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._name_box = QWidget()
        self._name_box.setStyleSheet(self._THEMES[theme]["normal"])
        box_row = QHBoxLayout(self._name_box)
        box_row.setContentsMargins(8, 6, 8, 6)
        box_row.setSpacing(8)
        box_row.addWidget(_MiniAvatar(initial))
        name = QLabel(username)
        name.setStyleSheet("font-size: 12px; font-weight: bold;")
        box_row.addWidget(name)
        box_row.addStretch()
        chevron = QLabel("❯")
        chevron.setStyleSheet("font-size: 13px; color: #7aafd4;")
        box_row.addWidget(chevron)
        outer.addWidget(self._name_box)

    def set_theme(self, theme):
        self._theme = theme
        self._name_box.setStyleSheet(self._THEMES[theme]["normal"])

    def enterEvent(self, event):
        self._name_box.setStyleSheet(self._THEMES[self._theme]["hover"])
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._name_box.setStyleSheet(self._THEMES[self._theme]["normal"])
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class InfoPanel(QWidget):
    predict_requested = pyqtSignal()
    ai_requested = pyqtSignal()
    profile_clicked = pyqtSignal()
    stock_renamed = pyqtSignal(str, str)  # symbol, new_name

    def __init__(self, username="", theme="dark", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)
        self._senate_worker = None
        self._current_symbol = None
        self._current_price = None
        self._cache = None

        self._tokens = get_tokens(theme)
        # Each entry is (QLabel, base_style_without_color) — rebuilt cleanly on theme change
        self._labels_secondary = []
        self._labels_muted = []
        self._labels_faint = []
        self._labels_value = []   # primary-color labels that have partial stylesheets
        self._separators = []  # list of (QFrame, margin_style)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 24)
        layout.setSpacing(4)

        initial = username[0].upper() if username else "?"
        self._profile_row = _ProfileRow(initial, username, theme=theme)
        self._profile_row.clicked.connect(self.profile_clicked)
        layout.addWidget(self._profile_row)

        self._profile_sep = QFrame()
        self._profile_sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self._profile_sep)

        t = self._tokens
        self._symbol_label = QLabel("—")
        self._symbol_label.setStyleSheet(f"font-size: {t['font_symbol']}; font-weight: bold;")

        self._name_label = QLabel("")
        self._name_label.setWordWrap(True)

        self._rename_btn = QPushButton("✎")
        self._rename_btn.setObjectName("btn_rename")
        self._rename_btn.setFixedSize(20, 20)
        self._rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rename_btn.setEnabled(False)
        self._rename_btn.hide()
        self._rename_btn.clicked.connect(self._on_rename)

        self._price_label = QLabel("—")
        self._price_label.setStyleSheet(f"font-size: {t['font_price']}; font-weight: bold; margin-top: 16px;")

        self._change_label = QLabel("")

        self._main_sep = QFrame()
        self._main_sep.setFrameShape(QFrame.Shape.HLine)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_info_tab(), "Info")
        self._tabs.addTab(self._build_analysis_tab(), "Analysis")
        self._tabs.addTab(self._build_portfolio_tab(), "Portfolio")

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(4)
        name_row.addWidget(self._name_label, stretch=1)
        name_row.addWidget(self._rename_btn)

        layout.addWidget(self._symbol_label)
        layout.addLayout(name_row)
        layout.addWidget(self._price_label)
        layout.addWidget(self._change_label)
        layout.addWidget(self._main_sep)
        layout.addWidget(self._tabs, stretch=1)

        self._apply_theme_styles(self._tokens)

    def _stat_row(self, label_text):
        t = self._tokens
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        k = QLabel(label_text)
        self._labels_muted.append((k, f"font-size: {t['font_small']};"))
        v = QLabel("—")
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._labels_value.append((v, f"font-size: {t['font_small']}; font-weight: bold;"))
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        return w, v

    def _build_info_tab(self):
        t = self._tokens
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(6)

        stats_title = QLabel("Statistics")
        self._labels_secondary.append((stats_title, f"font-size: {t['font_body']}; font-weight: bold;"))

        month_high_row, self._stat_month_high = self._stat_row("1M High")
        month_low_row,  self._stat_month_low  = self._stat_row("1M Low")
        w52_high_row,   self._stat_52w_high   = self._stat_row("52W High")
        w52_low_row,    self._stat_52w_low    = self._stat_row("52W Low")
        avg_vol_row,    self._stat_avg_vol    = self._stat_row("Avg Vol (30d)")

        stats_sep = QFrame()
        stats_sep.setFrameShape(QFrame.Shape.HLine)
        self._separators.append((stats_sep, "margin-top: 6px; margin-bottom: 6px;"))

        insider_title = QLabel("Insider Trades")
        self._labels_secondary.append((insider_title, f"font-size: {t['font_body']}; font-weight: bold;"))

        self._senate_status = QLabel("—")
        self._senate_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._labels_faint.append((self._senate_status, f"font-size: {t['font_small']};"))

        self._senate_container = QWidget()
        self._senate_container.setStyleSheet("background: transparent;")
        self._senate_inner_layout = QVBoxLayout(self._senate_container)
        self._senate_inner_layout.setContentsMargins(0, 0, 0, 0)
        self._senate_inner_layout.setSpacing(8)

        senate_scroll = QScrollArea()
        senate_scroll.setWidgetResizable(True)
        senate_scroll.setWidget(self._senate_container)
        senate_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        layout.addWidget(stats_title)
        layout.addWidget(month_high_row)
        layout.addWidget(month_low_row)
        layout.addWidget(w52_high_row)
        layout.addWidget(w52_low_row)
        layout.addWidget(avg_vol_row)
        layout.addWidget(stats_sep)
        layout.addWidget(insider_title)
        layout.addWidget(self._senate_status)
        layout.addWidget(senate_scroll, stretch=1)
        return tab

    def _build_analysis_tab(self):
        t = self._tokens
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(4)

        pred_title = QLabel("Prediction (30 days)")
        self._labels_secondary.append((pred_title, f"font-size: {t['font_body']}; font-weight: bold;"))

        self._predict_button = QPushButton("Predict Next Month")
        self._predict_button.clicked.connect(self.predict_requested)
        self._predict_button.setEnabled(False)

        self._pred_price_label = QLabel("")
        self._pred_price_label.setStyleSheet(f"font-size: {t['font_value']}; font-weight: bold;")

        self._pred_range_label = QLabel("")
        self._pred_range_label.setWordWrap(True)
        self._labels_secondary.append((self._pred_range_label, f"font-size: {t['font_small']};"))

        self._pred_signal_label = QLabel("")

        ai_sep = QFrame()
        ai_sep.setFrameShape(QFrame.Shape.HLine)
        self._separators.append((ai_sep, "margin-top: 10px; margin-bottom: 10px;"))

        ai_title = QLabel("AI Analysis")
        self._labels_secondary.append((ai_title, f"font-size: {t['font_body']}; font-weight: bold;"))

        self._ai_button = QPushButton("Analyse with AI")
        self._ai_button.clicked.connect(self.ai_requested)
        self._ai_button.setEnabled(False)

        self._ai_score_label = QLabel("")
        self._ai_desc_label = QLabel("")
        self._ai_summary_label = QLabel("")
        self._ai_summary_label.setWordWrap(True)
        self._labels_muted.append((self._ai_summary_label, f"font-size: {t['font_small']}; font-style: italic;"))

        layout.addWidget(pred_title)
        layout.addSpacing(4)
        layout.addWidget(self._predict_button)
        layout.addWidget(self._pred_price_label)
        layout.addWidget(self._pred_range_label)
        layout.addWidget(self._pred_signal_label)
        layout.addWidget(ai_sep)
        layout.addWidget(ai_title)
        layout.addSpacing(4)
        layout.addWidget(self._ai_button)
        layout.addWidget(self._ai_score_label)
        layout.addWidget(self._ai_desc_label)
        layout.addWidget(self._ai_summary_label)
        layout.addStretch()
        return tab

    def _build_portfolio_tab(self):
        t = self._tokens
        self._port_inputs = []

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(6)

        pos_title = QLabel("My Position")
        self._labels_secondary.append((pos_title, f"font-size: {t['font_body']}; font-weight: bold;"))
        layout.addWidget(pos_title)

        def _input_row(label_text, placeholder=""):
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(74)
            self._labels_muted.append((lbl, f"font-size: {t['font_small']};"))
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            self._port_inputs.append(inp)
            row.addWidget(lbl)
            row.addWidget(inp)
            return w, inp

        shares_row, self._port_shares = _input_row("Shares", "e.g. 10")
        cost_row,   self._port_cost   = _input_row("Cost/Share", "e.g. 150.00")
        date_row,   self._port_date   = _input_row("Date", "YYYY-MM-DD")
        target_row, self._port_target = _input_row("Sell Target", "optional")

        self._port_save_btn = QPushButton("Save Position")
        self._port_save_btn.setEnabled(False)
        self._port_save_btn.clicked.connect(self._on_save_portfolio)

        layout.addWidget(shares_row)
        layout.addWidget(cost_row)
        layout.addWidget(date_row)
        layout.addWidget(target_row)
        layout.addSpacing(6)
        layout.addWidget(self._port_save_btn)
        layout.addSpacing(10)

        # ── Performance card ──────────────────────────────────────────────
        self._port_perf_section = QWidget()
        self._port_perf_section.setObjectName("perf_card")
        perf_inner = QVBoxLayout(self._port_perf_section)
        perf_inner.setContentsMargins(8, 10, 8, 10)
        perf_inner.setSpacing(4)

        perf_header = QHBoxLayout()
        perf_title = QLabel("Performance")
        self._labels_secondary.append((perf_title, f"font-size: {t['font_body']}; font-weight: bold;"))
        self._port_gain_label = QLabel("")
        self._port_gain_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        perf_header.addWidget(perf_title)
        perf_header.addStretch()
        perf_header.addWidget(self._port_gain_label)
        perf_inner.addLayout(perf_header)

        perf_sep = QFrame()
        perf_sep.setFrameShape(QFrame.Shape.HLine)
        self._separators.append((perf_sep, "margin-top: 4px; margin-bottom: 4px;"))
        perf_inner.addWidget(perf_sep)

        purchased_row,   self._port_purchased   = self._stat_row("Purchased")
        curr_row,        self._port_curr_val     = self._stat_row("Current Price")
        cost_total_row,  self._port_cost_total   = self._stat_row("Total Cost")
        value_row,       self._port_value        = self._stat_row("Value Now")
        change_row,      self._port_change       = self._stat_row("Change")
        target_perf_row, self._port_target_perf  = self._stat_row("Sell Target")

        perf_inner.addWidget(purchased_row)
        perf_inner.addWidget(curr_row)
        perf_inner.addWidget(cost_total_row)
        perf_inner.addWidget(value_row)
        perf_inner.addWidget(change_row)
        perf_inner.addWidget(target_perf_row)
        perf_inner.addSpacing(8)

        self._port_clear_btn = QPushButton("Clear Position")
        self._port_clear_btn.clicked.connect(self._on_clear_portfolio)
        perf_inner.addWidget(self._port_clear_btn)

        self._port_perf_section.hide()
        layout.addWidget(self._port_perf_section)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        return scroll

    # ------------------------------------------------------------------ public

    def set_theme(self, theme):
        self._tokens = get_tokens(theme)
        self._profile_row.set_theme(theme)
        self._apply_theme_styles(self._tokens)

    def update(self, symbol, df, cache):
        self.clear_prediction()
        if symbol is None or df.empty:
            self._symbol_label.setText("—")
            self._name_label.setText("")
            self._rename_btn.setEnabled(False)
            self._rename_btn.hide()
            self._price_label.setText("—")
            self._change_label.setText("")
            self._predict_button.setEnabled(False)
            self._ai_button.setEnabled(False)
            self._ai_score_label.setText("")
            self._ai_desc_label.setText("")
            self._ai_summary_label.setText("")
            self._senate_status.setText("—")
            self._senate_status.show()
            for lbl in (self._stat_month_high, self._stat_month_low,
                        self._stat_52w_high, self._stat_52w_low, self._stat_avg_vol):
                lbl.setText("—")
            self._port_save_btn.setEnabled(False)
            self._port_perf_section.hide()
            for inp in (self._port_shares, self._port_cost, self._port_date, self._port_target):
                inp.clear()
            self._port_cost.setPlaceholderText("e.g. 150.00")
            self._port_date.setPlaceholderText("YYYY-MM-DD")
            self._current_symbol = None
            self._current_price = None
            self._cache = None
            return

        info = cache.get_stock_data(symbol)
        name = info.get("name", symbol) if info else symbol
        self._symbol_label.setText(symbol)
        self._name_label.setText(name)
        self._rename_btn.setEnabled(True)
        self._rename_btn.show()

        current = df["Close"].iloc[-1]
        prev = df["Close"].iloc[-2] if len(df) > 1 else current
        change_pct = ((current - prev) / prev) * 100
        self._price_label.setText(f"${current:.2f}")
        t = self._tokens
        if change_pct >= 0:
            self._change_label.setText(f"▲ +{change_pct:.2f}%")
            self._change_label.setStyleSheet(f"font-size: {t['font_subhead']}; color: {t['buy_color']};")
        else:
            self._change_label.setText(f"▼ {change_pct:.2f}%")
            self._change_label.setStyleSheet(f"font-size: {t['font_subhead']}; color: {t['sell_color']};")

        now = pd.Timestamp.now()
        month_df = df[df.index >= now - pd.Timedelta(days=30)]
        year_df  = df[df.index >= now - pd.Timedelta(days=365)]
        if not month_df.empty:
            self._stat_month_high.setText(f"${month_df['High'].max():.2f}")
            self._stat_month_low.setText(f"${month_df['Low'].min():.2f}")
            avg = month_df["Volume"].mean()
            self._stat_avg_vol.setText(f"{avg/1e6:.1f}M" if avg >= 1e6 else f"{avg/1e3:.0f}K")
        else:
            self._stat_month_high.setText("—")
            self._stat_month_low.setText("—")
            self._stat_avg_vol.setText("—")
        self._stat_52w_high.setText(f"${year_df['High'].max():.2f}" if not year_df.empty else "—")
        self._stat_52w_low.setText(f"${year_df['Low'].min():.2f}" if not year_df.empty else "—")

        self._predict_button.setEnabled(True)
        self._ai_button.setEnabled(True)
        self._port_save_btn.setEnabled(True)
        self._current_symbol = symbol
        self._current_price = float(current)
        self._cache = cache
        self._refresh_portfolio_tab(cache.get_portfolio(symbol))

        cached_ai = cache.get_ai_analysis(symbol)
        if cached_ai and cache.is_ai_analysis_fresh(symbol):
            self.set_ai_result(cached_ai)
        else:
            self._ai_score_label.setText("")
            self._ai_desc_label.setText("")
            self._ai_summary_label.setText("")

        self._fetch_senate_trades(symbol)

    def set_ai_result(self, result):
        from .ai_analysis_dialog import _score_color, _score_description
        t = self._tokens
        score = result.get("score", 0)
        color = _score_color(score)
        self._ai_score_label.setText(f"{score:+d}")
        self._ai_score_label.setStyleSheet(f"font-size: {t['font_value']}; font-weight: bold; color: {color};")
        self._ai_desc_label.setText(_score_description(score))
        self._ai_desc_label.setStyleSheet(f"font-size: {t['font_small']}; color: {color};")
        self._ai_summary_label.setText(result.get("summary", ""))

    def set_prediction_running(self, running: bool):
        self._predict_button.setEnabled(not running)
        self._predict_button.setText("Running..." if running else "Predict Next Month")

    def set_prediction_result(self, pred, low, high, current_price):
        t = self._tokens
        self._pred_price_label.setText(f"${pred:.2f}")
        self._pred_range_label.setText(f"Range: ${low:.2f} – ${high:.2f}")
        change_pct = ((pred - current_price) / current_price) * 100
        if change_pct >= 5:
            signal, color = "BUY", t["buy_color"]
        elif change_pct <= -5:
            signal, color = "SELL", t["sell_color"]
        else:
            signal, color = "HOLD", t["hold_color"]
        self._pred_signal_label.setText(f"{signal}  ({change_pct:+.1f}%)")
        self._pred_signal_label.setStyleSheet(f"font-size: {t['font_title']}; font-weight: bold; color: {color};")

    def clear_prediction(self):
        self._pred_price_label.setText("")
        self._pred_range_label.setText("")
        self._pred_signal_label.setText("")

    # ------------------------------------------------------------------ internal

    def _apply_theme_styles(self, tokens):
        t = tokens
        self._symbol_label.setStyleSheet(
            f"font-size: {t['font_symbol']}; font-weight: bold; color: {t['value_text']};"
        )
        self._price_label.setStyleSheet(
            f"font-size: {t['font_price']}; font-weight: bold; margin-top: 16px; color: {t['value_text']};"
        )
        self._pred_price_label.setStyleSheet(
            f"font-size: {t['font_value']}; font-weight: bold; color: {t['value_text']};"
        )
        self._name_label.setStyleSheet(f"font-size: {t['font_title']}; color: {t['label_secondary']};")
        self._profile_sep.setStyleSheet(
            f"color: {t['separator_strong']}; margin-top: 6px; margin-bottom: 10px;"
        )
        self._main_sep.setStyleSheet(
            f"color: {t['separator']}; margin-top: 8px; margin-bottom: 4px;"
        )
        for lbl, base in self._labels_value:
            lbl.setStyleSheet(f"{base} color: {t['value_text']};")
        for lbl, base in self._labels_secondary:
            lbl.setStyleSheet(f"{base} color: {t['label_secondary']};")
        for lbl, base in self._labels_muted:
            lbl.setStyleSheet(f"{base} color: {t['label_muted']};")
        for lbl, base in self._labels_faint:
            lbl.setStyleSheet(f"{base} color: {t['label_faint']};")
        for sep, margins in self._separators:
            sep.setStyleSheet(f"color: {t['separator']}; {margins}")
        input_ss = f"""
            QLineEdit {{
                background: {t['base']};
                color: {t['text']};
                border: 1px solid {t['separator']};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: {t['font_small']};
                selection-background-color: {t['highlight']};
            }}
            QLineEdit:focus {{
                border-color: {t['highlight']};
            }}
            QLineEdit:disabled {{
                color: {t['label_muted']};
                border-color: {t['separator_strong']};
            }}
        """
        for inp in self._port_inputs:
            inp.setStyleSheet(input_ss)
        self._port_save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['highlight']};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: {t['font_small']};
                font-weight: bold;
                padding: 5px 0px;
            }}
            QPushButton:hover {{ background: #3a92ea; }}
            QPushButton:pressed {{ background: #1a6fc0; }}
            QPushButton:disabled {{
                background: {t['alternate_base']};
                color: {t['label_muted']};
            }}
        """)
        self._port_clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {t['label_secondary']};
                border: 1px solid {t['separator']};
                border-radius: 6px;
                font-size: {t['font_small']};
                padding: 4px 0px;
            }}
            QPushButton:hover {{
                color: {t['sell_color']};
                border-color: {t['sell_color']};
            }}
            QPushButton:pressed {{ color: {t['sell_color']}; }}
        """)
        self._port_perf_section.setStyleSheet(
            f"QWidget#perf_card {{ background: {t['alternate_base']}; border-radius: 6px; }}"
        )
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {t['label_secondary']};
                border: 1px solid {t['separator']};
                border-radius: 5px;
                padding: 4px 10px;
                margin-right: 4px;
                font-size: {t['font_small']};
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {t['highlight']};
                color: #ffffff;
                border-color: {t['highlight']};
            }}
            QTabBar::tab:hover:!selected {{
                color: {t['text']};
                border-color: {t['highlight']};
            }}
        """)
        self._rename_btn.setStyleSheet(f"""
            QPushButton#btn_rename {{
                background: transparent;
                color: {t['label_muted']};
                border: none;
                font-size: {t['font_small']};
                border-radius: 4px;
            }}
            QPushButton#btn_rename:hover {{
                color: {t['label_secondary']};
                background: {t['alternate_base']};
            }}
            QPushButton#btn_rename:pressed {{
                color: {t['highlight']};
            }}
        """)

    def _on_rename(self):
        if not self._cache or not self._current_symbol:
            return
        info = self._cache.get_stock_data(self._current_symbol)
        current_name = info.get("name", self._current_symbol) if info else self._current_symbol
        new_name, ok = QInputDialog.getText(
            self, "Rename Stock", "Display name:", text=current_name
        )
        if not ok or not new_name.strip() or new_name.strip() == current_name:
            return
        new_name = new_name.strip()
        self._cache.rename_stock(self._current_symbol, new_name)
        self._name_label.setText(new_name)
        self.stock_renamed.emit(self._current_symbol, new_name)

    def _refresh_portfolio_tab(self, portfolio):
        t = self._tokens
        if portfolio:
            self._port_shares.setText(str(portfolio.get('shares', '')))
            self._port_cost.setText(str(portfolio.get('cost_per_share', '')))
            self._port_date.setText(portfolio.get('purchase_date', ''))
            target = portfolio.get('sell_target')
            self._port_target.setText(str(target) if target is not None else '')

            shares = portfolio.get('shares', 0)
            cost_ps = portfolio.get('cost_per_share', 0)
            total_cost = shares * cost_ps
            value = shares * self._current_price
            gain = value - total_cost
            gain_pct = (gain / total_cost * 100) if total_cost > 0 else 0
            color = t["buy_color"] if gain >= 0 else t["sell_color"]

            self._port_gain_label.setText(f"{gain_pct:+.1f}%")
            self._port_gain_label.setStyleSheet(
                f"font-size: {t['font_subhead']}; font-weight: bold; color: {color};"
            )

            self._port_purchased.setText(portfolio.get('purchase_date', '—'))
            self._port_curr_val.setText(f"${self._current_price:.2f}")
            self._port_cost_total.setText(f"${total_cost:,.2f}")
            self._port_value.setText(f"${value:,.2f}")
            self._port_change.setText(f"{gain_pct:+.1f}%  (${gain:+,.2f})")
            self._port_change.setStyleSheet(
                f"font-size: {t['font_small']}; color: {color}; font-weight: bold;"
            )

            if target is not None:
                dist_pct = ((target - self._current_price) / self._current_price) * 100
                t_color = t["hold_color"] if self._current_price < target else t["sell_color"]
                self._port_target_perf.setText(f"${target:,.2f}  ({dist_pct:+.1f}%)")
                self._port_target_perf.setStyleSheet(
                    f"font-size: {t['font_small']}; color: {t_color}; font-weight: bold;"
                )
            else:
                self._port_target_perf.setText("—")
                self._port_target_perf.setStyleSheet(
                    f"font-size: {t['font_small']}; color: {t['value_text']}; font-weight: bold;"
                )

            self._port_perf_section.show()
        else:
            from datetime import datetime
            self._port_shares.clear()
            self._port_cost.setText(f"{self._current_price:.2f}" if self._current_price else "")
            self._port_date.setText(datetime.now().strftime('%Y-%m-%d'))
            self._port_target.clear()
            self._port_gain_label.setText("")
            self._port_perf_section.hide()

    def _on_save_portfolio(self):
        from PyQt6.QtWidgets import QMessageBox
        from datetime import datetime

        shares_text = self._port_shares.text().strip()
        cost_text = self._port_cost.text().strip().replace('$', '').replace(',', '')
        date_text = self._port_date.text().strip()
        target_text = self._port_target.text().strip().replace('$', '').replace(',', '')

        try:
            shares = float(shares_text)
            if shares <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for shares.")
            return

        try:
            cost = float(cost_text)
            if cost <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid positive number for cost per share.")
            return

        if not date_text:
            date_text = datetime.now().strftime('%Y-%m-%d')
        else:
            try:
                datetime.strptime(date_text, '%Y-%m-%d')
            except ValueError:
                QMessageBox.warning(self, "Invalid Date", "Please enter the date as YYYY-MM-DD.")
                return

        portfolio = {'shares': shares, 'cost_per_share': cost, 'purchase_date': date_text}

        if target_text:
            try:
                target = float(target_text)
                if target > 0:
                    portfolio['sell_target'] = target
                else:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Sell target must be a valid positive number.")
                return

        if self._cache and self._current_symbol:
            self._cache.set_portfolio(self._current_symbol, portfolio)
            self._refresh_portfolio_tab(portfolio)
            self._port_save_btn.setText("Saved ✓")
            self._port_save_btn.setEnabled(False)
            QTimer.singleShot(1500, lambda: (
                self._port_save_btn.setText("Save Position"),
                self._port_save_btn.setEnabled(True),
            ))

    def _on_clear_portfolio(self):
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Clear Position",
            "Remove this position from your portfolio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes and self._cache and self._current_symbol:
            self._cache.clear_portfolio(self._current_symbol)
            self._refresh_portfolio_tab(None)

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
        t = self._tokens
        for trade in trades:
            name       = trade.get("name") or trade.get("senator") or "Unknown"
            trade_type = (trade.get("type") or trade.get("transaction_type") or "Unknown").upper()
            date       = trade.get("transaction_date") or trade.get("date") or ""
            amount     = trade.get("amount", "")
            is_buy     = any(k in trade_type for k in ("BUY", "PURCHASE"))
            is_sell    = any(k in trade_type for k in ("SALE", "SELL"))
            color      = t["buy_color"] if is_buy else (t["sell_color"] if is_sell else t["label_muted"])
            arrow      = "▲" if is_buy else ("▼" if is_sell else "·")
            detail     = f"{date}" + (f"  ·  {amount}" if amount else "")
            entry = QLabel(
                f'<span style="color:{color};">{arrow} {trade_type}</span>'
                f'  <span style="color:{t["label_secondary"]};">{name}</span>'
                f'<br><span style="color:{t["label_muted"]}; font-size:{t["font_small"]};">{detail}</span>'
            )
            entry.setTextFormat(Qt.TextFormat.RichText)
            entry.setWordWrap(True)
            self._senate_inner_layout.addWidget(entry)
