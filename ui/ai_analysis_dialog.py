from datetime import datetime as dt

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen


def _score_color(score):
    if score >= 5:
        return "#00cc66"
    elif score >= 1:
        return "#66dd88"
    elif score <= -5:
        return "#ff4444"
    elif score <= -1:
        return "#ff8866"
    return "#aaaaaa"


def _score_description(score):
    if score >= 7:
        return "Strongly Bullish"
    elif score >= 4:
        return "Bullish"
    elif score >= 1:
        return "Mildly Bullish"
    elif score <= -7:
        return "Strongly Bearish"
    elif score <= -4:
        return "Bearish"
    elif score <= -1:
        return "Mildly Bearish"
    return "Neutral"


class ScoreBar(QWidget):
    def __init__(self, score, parent=None):
        super().__init__(parent)
        self.score = max(-10, min(10, score))
        self.setFixedHeight(16)
        self.setMinimumWidth(280)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        painter.setBrush(QColor(55, 55, 55))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 4, 4)

        center = w // 2
        fill = int((abs(self.score) / 10) * (w // 2))
        painter.setBrush(QColor(_score_color(self.score)))
        if self.score >= 0:
            painter.drawRoundedRect(center, 2, fill, h - 4, 3, 3)
        else:
            painter.drawRoundedRect(center - fill, 2, fill, h - 4, 3, 3)

        painter.setPen(QPen(QColor(160, 160, 160), 1))
        painter.drawLine(center, 0, center, h)


class AIAnalysisDialog(QDialog):
    def __init__(self, symbol, name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"AI Analysis — {symbol}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(420)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(24, 20, 24, 20)

        header = QLabel("AI Market Analysis")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        sub = QLabel(f"{symbol}  ·  {name}")
        sub.setStyleSheet("font-size: 12px; color: #aaaaaa;")
        root.addWidget(header)
        root.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #555555;")
        root.addWidget(sep)

        self._status_label = QLabel("Analyzing...")
        self._status_label.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._results_widget = QWidget()
        self._results_widget.hide()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(10)
        root.addWidget(self._results_widget)

        root.addStretch()

        disclaimer = QLabel("AI-generated analysis. Not financial advice.")
        disclaimer.setStyleSheet("font-size: 10px; color: #666666;")
        disclaimer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(disclaimer)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    def update_status(self, message):
        self._status_label.setText(message)

    def show_results(self, result):
        self._status_label.hide()

        score = result.get("score", 0)
        pros = result.get("pros", [])
        cons = result.get("cons", [])

        color = _score_color(score)
        desc = _score_description(score)

        score_label = QLabel(f"{score:+d}")
        score_label.setStyleSheet(f"font-size: 52px; font-weight: bold; color: {color};")
        score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bar = ScoreBar(score)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"font-size: 14px; color: {color};")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        score_section = QVBoxLayout()
        score_section.setSpacing(6)
        score_section.addWidget(score_label)
        score_section.addWidget(bar)
        score_section.addWidget(desc_label)

        summary_text = result.get("summary", "")
        if summary_text:
            summary_label = QLabel(summary_text)
            summary_label.setStyleSheet("font-size: 12px; color: #bbbbbb; font-style: italic;")
            summary_label.setWordWrap(True)
            summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            score_section.addWidget(summary_label)

        score_widget = QWidget()
        score_widget.setLayout(score_section)
        self._results_layout.addWidget(score_widget)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #555555;")
        self._results_layout.addWidget(sep)

        pc_layout = QHBoxLayout()
        pc_layout.setSpacing(16)

        pros_col = QVBoxLayout()
        pros_col.setSpacing(6)
        pros_title = QLabel("Pros")
        pros_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #00cc66;")
        pros_col.addWidget(pros_title)
        for p in pros:
            lbl = QLabel(f"▲  {p}")
            lbl.setStyleSheet("font-size: 12px; color: #cccccc;")
            lbl.setWordWrap(True)
            pros_col.addWidget(lbl)
        pros_col.addStretch()

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setStyleSheet("color: #555555;")

        cons_col = QVBoxLayout()
        cons_col.setSpacing(6)
        cons_title = QLabel("Cons")
        cons_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff4444;")
        cons_col.addWidget(cons_title)
        for c in cons:
            lbl = QLabel(f"▼  {c}")
            lbl.setStyleSheet("font-size: 12px; color: #cccccc;")
            lbl.setWordWrap(True)
            cons_col.addWidget(lbl)
        cons_col.addStretch()

        pc_layout.addLayout(pros_col)
        pc_layout.addWidget(vline)
        pc_layout.addLayout(cons_col)
        self._results_layout.addLayout(pc_layout)

        timestamp_str = result.get("timestamp")
        if timestamp_str:
            try:
                ts = dt.fromisoformat(timestamp_str)
                ts_label = QLabel(f"Cached · {ts.strftime('%b %d, %Y  %H:%M')}")
            except ValueError:
                ts_label = QLabel("Cached result")
            ts_label.setStyleSheet("font-size: 10px; color: #555555;")
            ts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.addWidget(ts_label)

        price_text = result.get("price_summary", "")
        senate_text = result.get("senate_summary") or ""
        if price_text or senate_text:
            self._build_data_section(price_text, senate_text)

        self._results_widget.show()

    def _build_data_section(self, price_text, senate_text):
        toggle_btn = QPushButton("▶  Show data used")
        toggle_btn.setStyleSheet(
            "font-size: 11px; color: #666666; background: transparent; border: none; text-align: left; padding: 0;"
        )
        toggle_btn.setFlat(True)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(8, 4, 8, 4)
        data_layout.setSpacing(6)

        if price_text:
            price_title = QLabel("30-day price data")
            price_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #777777;")
            data_layout.addWidget(price_title)
            price_lbl = QLabel(price_text)
            price_lbl.setStyleSheet("font-size: 11px; color: #666666; font-family: monospace;")
            data_layout.addWidget(price_lbl)

        senate_display = senate_text if senate_text else "No Senate trading data was available."
        senate_title = QLabel("Senate trades used")
        senate_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #777777;")
        data_layout.addWidget(senate_title)
        senate_lbl = QLabel(senate_display)
        senate_lbl.setStyleSheet("font-size: 11px; color: #666666;")
        senate_lbl.setWordWrap(True)
        data_layout.addWidget(senate_lbl)

        data_widget.hide()

        def _toggle():
            if data_widget.isVisible():
                data_widget.hide()
                toggle_btn.setText("▶  Show data used")
            else:
                data_widget.show()
                toggle_btn.setText("▼  Hide data used")
            self.adjustSize()

        toggle_btn.clicked.connect(_toggle)
        self._results_layout.addWidget(toggle_btn)
        self._results_layout.addWidget(data_widget)

    def show_error(self, message):
        self._status_label.setText(f"Error: {message}")
        self._status_label.setStyleSheet("font-size: 12px; color: #ff4444;")
