import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal


class InfoPanel(QWidget):
    predict_requested = pyqtSignal()
    ai_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMaximumWidth(280)
        self._senate_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(4)

        self._symbol_label = QLabel("—")
        self._symbol_label.setStyleSheet("font-size: 26px; font-weight: bold;")

        self._name_label = QLabel("")
        self._name_label.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        self._name_label.setWordWrap(True)

        self._price_label = QLabel("—")
        self._price_label.setStyleSheet("font-size: 32px; font-weight: bold; margin-top: 16px;")

        self._change_label = QLabel("")
        self._change_label.setStyleSheet("font-size: 15px;")

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #555555; margin-top: 8px; margin-bottom: 4px;")

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_info_tab(), "Info")
        tabs.addTab(self._build_analysis_tab(), "Analysis")

        layout.addWidget(self._symbol_label)
        layout.addWidget(self._name_label)
        layout.addWidget(self._price_label)
        layout.addWidget(self._change_label)
        layout.addWidget(separator)
        layout.addWidget(tabs, stretch=1)

    def _stat_row(self, label_text):
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

    def _build_info_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(6)

        stats_title = QLabel("Statistics")
        stats_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        month_high_row, self._stat_month_high = self._stat_row("1M High")
        month_low_row,  self._stat_month_low  = self._stat_row("1M Low")
        w52_high_row,   self._stat_52w_high   = self._stat_row("52W High")
        w52_low_row,    self._stat_52w_low    = self._stat_row("52W Low")
        avg_vol_row,    self._stat_avg_vol    = self._stat_row("Avg Vol (30d)")

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
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 12, 4, 8)
        layout.setSpacing(4)

        pred_title = QLabel("Prediction (30 days)")
        pred_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        self._predict_button = QPushButton("Predict Next Month")
        self._predict_button.clicked.connect(self.predict_requested)
        self._predict_button.setEnabled(False)

        self._pred_price_label = QLabel("")
        self._pred_price_label.setStyleSheet("font-size: 20px; font-weight: bold;")

        self._pred_range_label = QLabel("")
        self._pred_range_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        self._pred_range_label.setWordWrap(True)

        self._pred_signal_label = QLabel("")
        self._pred_signal_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        ai_sep = QFrame()
        ai_sep.setFrameShape(QFrame.Shape.HLine)
        ai_sep.setStyleSheet("color: #555555; margin-top: 10px; margin-bottom: 10px;")

        ai_title = QLabel("AI Analysis")
        ai_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #aaaaaa;")

        self._ai_button = QPushButton("Analyse with AI")
        self._ai_button.clicked.connect(self.ai_requested)
        self._ai_button.setEnabled(False)

        self._ai_score_label = QLabel("")
        self._ai_score_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self._ai_desc_label = QLabel("")
        self._ai_desc_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")

        self._ai_summary_label = QLabel("")
        self._ai_summary_label.setStyleSheet("font-size: 11px; color: #888888; font-style: italic;")
        self._ai_summary_label.setWordWrap(True)

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

    # ------------------------------------------------------------------ public

    def update(self, symbol, df, cache):
        self.clear_prediction()
        if symbol is None or df.empty:
            self._symbol_label.setText("—")
            self._name_label.setText("")
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
            return

        info = cache.get_stock_data(symbol)
        name = info.get("name", symbol) if info else symbol
        self._symbol_label.setText(symbol)
        self._name_label.setText(name)

        current = df["Close"].iloc[-1]
        prev = df["Close"].iloc[-2] if len(df) > 1 else current
        change_pct = ((current - prev) / prev) * 100
        self._price_label.setText(f"${current:.2f}")
        if change_pct >= 0:
            self._change_label.setText(f"▲ +{change_pct:.2f}%")
            self._change_label.setStyleSheet("font-size: 15px; color: #00cc66;")
        else:
            self._change_label.setText(f"▼ {change_pct:.2f}%")
            self._change_label.setStyleSheet("font-size: 15px; color: #ff4444;")

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

        cached_ai = cache.get_ai_analysis(symbol)
        if cached_ai and cache.is_ai_analysis_fresh(symbol):
            self.set_ai_result(cached_ai)
        else:
            self._ai_score_label.setText("")
            self._ai_desc_label.setText("")
            self._ai_summary_label.setText("")

        self._fetch_senate_trades(symbol)

    def set_ai_result(self, result):
        from ui.ai_analysis_dialog import _score_color, _score_description
        score = result.get("score", 0)
        color = _score_color(score)
        self._ai_score_label.setText(f"{score:+d}")
        self._ai_score_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        self._ai_desc_label.setText(_score_description(score))
        self._ai_desc_label.setStyleSheet(f"font-size: 11px; color: {color};")
        self._ai_summary_label.setText(result.get("summary", ""))

    def set_prediction_running(self, running: bool):
        self._predict_button.setEnabled(not running)
        self._predict_button.setText("Running..." if running else "Predict Next Month")

    def set_prediction_result(self, pred, low, high, current_price):
        self._pred_price_label.setText(f"${pred:.2f}")
        self._pred_range_label.setText(f"Range: ${low:.2f} – ${high:.2f}")
        change_pct = ((pred - current_price) / current_price) * 100
        if change_pct >= 5:
            signal, color = "BUY", "#00cc66"
        elif change_pct <= -5:
            signal, color = "SELL", "#ff4444"
        else:
            signal, color = "HOLD", "#ffaa00"
        self._pred_signal_label.setText(f"{signal}  ({change_pct:+.1f}%)")
        self._pred_signal_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")

    def clear_prediction(self):
        self._pred_price_label.setText("")
        self._pred_range_label.setText("")
        self._pred_signal_label.setText("")

    # ------------------------------------------------------------------ internal

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
            name      = t.get("name") or t.get("senator") or "Unknown"
            trade_type = (t.get("type") or t.get("transaction_type") or "Unknown").upper()
            date      = t.get("transaction_date") or t.get("date") or ""
            amount    = t.get("amount", "")
            is_buy    = any(k in trade_type for k in ("BUY", "PURCHASE"))
            is_sell   = any(k in trade_type for k in ("SALE", "SELL"))
            color     = "#00cc66" if is_buy else ("#ff4444" if is_sell else "#888888")
            arrow     = "▲" if is_buy else ("▼" if is_sell else "·")
            detail    = f"{date}" + (f"  ·  {amount}" if amount else "")
            entry = QLabel(
                f'<span style="color:{color};">{arrow} {trade_type}</span>  {name}'
                f'<br><span style="color:#666666; font-size:11px;">{detail}</span>'
            )
            entry.setTextFormat(Qt.TextFormat.RichText)
            entry.setWordWrap(True)
            self._senate_inner_layout.addWidget(entry)
