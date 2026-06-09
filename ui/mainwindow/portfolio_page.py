import os

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

_PIE_COLORS = [
    "#6495ED", "#32CD32", "#FF6347", "#FFD700",
    "#BA55D3", "#1E90FF", "#FF8C00", "#00FA9A",
    "#FF69B4", "#20B2AA",
]


class _AvatarWidget(QWidget):
    def __init__(self, username, size=68, parent=None):
        super().__init__(parent)
        self._initial = username[0].upper() if username else "?"
        self.setFixedSize(size, size)
        self._size = size

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#2a82da"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, self._size, self._size)
        font = QFont()
        font.setPixelSize(int(self._size * 0.40))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)


class UserPage(QWidget):
    back_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, cache, csv_path, user_profile, parent=None):
        super().__init__(parent)
        positions = _load_positions(cache, csv_path)
        username = user_profile.get("username", "")
        email = user_profile.get("email", "")
        phone = user_profile.get("phone", "")

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 20, 32, 20)
        root.setSpacing(0)

        # Nav bar
        _btn_style = (
            "font-size: 13px; background: transparent; border: none; padding: 2px 0;"
        )
        nav = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFlat(True)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(_btn_style + " color: #6495ED;")
        back_btn.clicked.connect(self.back_requested)
        settings_btn = QPushButton("Settings")
        settings_btn.setFlat(True)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(_btn_style + " color: #888888;")
        settings_btn.clicked.connect(self.settings_requested)
        nav.addWidget(back_btn)
        nav.addStretch()
        nav.addWidget(settings_btn)
        root.addLayout(nav)
        root.addSpacing(14)

        # Profile header
        header_row = QHBoxLayout()
        header_row.setSpacing(16)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_row.addWidget(_AvatarWidget(username))

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        name_lbl = QLabel(username)
        name_lbl.setStyleSheet("font-size: 24px; font-weight: bold;")
        name_col.addWidget(name_lbl)

        sub_parts = [s for s in [email, phone] if s]
        if sub_parts:
            sub_lbl = QLabel("  ·  ".join(sub_parts))
            sub_lbl.setStyleSheet("font-size: 12px; color: #888888;")
            name_col.addWidget(sub_lbl)

        header_row.addLayout(name_col)
        header_row.addStretch()
        root.addLayout(header_row)
        root.addSpacing(18)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444444;")
        root.addWidget(sep)
        root.addSpacing(18)

        # Portfolio section title
        port_title = QLabel("Portfolio")
        port_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        root.addWidget(port_title)
        root.addSpacing(14)

        if not positions:
            empty = QLabel(
                "No portfolio positions recorded.\n"
                "Use the Portfolio tab to track your holdings."
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("font-size: 13px; color: #666666;")
            root.addWidget(empty, stretch=1)
        else:
            body = QHBoxLayout()
            body.setSpacing(36)
            body.setAlignment(Qt.AlignmentFlag.AlignTop)
            body.addWidget(_build_chart(positions))

            right = QVBoxLayout()
            right.setSpacing(22)
            right.addWidget(_build_stats(positions))
            right.addWidget(_build_legend(positions))
            right.addStretch()
            body.addLayout(right, stretch=1)

            root.addLayout(body, stretch=1)


def _load_positions(cache, csv_path):
    positions = []
    for symbol, data in cache.all_stocks().items():
        portfolio = cache.get_portfolio(symbol)
        if not portfolio:
            continue
        dfpath_name = data.get("dfpath")
        if not dfpath_name:
            continue
        dfpath = os.path.join(csv_path, dfpath_name)
        if not os.path.exists(dfpath):
            continue
        try:
            df = pd.read_csv(dfpath, parse_dates=True, index_col=0)
            if df.empty or "Close" not in df.columns:
                continue
            current_price = float(df["Close"].iloc[-1])
            shares = float(portfolio.get("shares", 0))
            cost_per_share = float(portfolio.get("cost_per_share", 0))
            total_cost = shares * cost_per_share
            current_value = shares * current_price
            daily_pct = df["Close"].pct_change().dropna()
            avg_daily_change = float(daily_pct.mean() * 100) if len(daily_pct) > 0 else 0.0
            positions.append({
                "symbol": symbol,
                "name": data.get("name", symbol),
                "shares": shares,
                "cost_per_share": cost_per_share,
                "current_price": current_price,
                "total_cost": total_cost,
                "current_value": current_value,
                "gain_pct": ((current_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0,
                "avg_daily_change": avg_daily_change,
            })
        except Exception:
            continue
    return positions


def _build_chart(positions):
    values = [p["current_value"] for p in positions]
    colors = [_PIE_COLORS[i % len(_PIE_COLORS)] for i in range(len(positions))]
    total_value = sum(values)

    fig = Figure(figsize=(4.6, 4.6), facecolor="#2a2a2a")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#2a2a2a")
    fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)

    ax.pie(
        values,
        labels=None,
        colors=colors,
        wedgeprops={"width": 0.46, "edgecolor": "#2a2a2a", "linewidth": 2},
        startangle=90,
    )
    ax.text(0, 0.10, f"${total_value:,.0f}",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#dcdcdc")
    ax.text(0, -0.14, "Total Value",
            ha="center", va="center", fontsize=9, color="#888888")

    canvas = FigureCanvas(fig)
    canvas.setFixedSize(300, 300)
    return canvas


def _build_stats(positions):
    total_cost = sum(p["total_cost"] for p in positions)
    total_value = sum(p["current_value"] for p in positions)
    overall_gain = total_value - total_cost
    overall_pct = (overall_gain / total_cost * 100) if total_cost > 0 else 0.0
    total_val = sum(p["current_value"] for p in positions)
    avg_daily = (
        sum(p["avg_daily_change"] * p["current_value"] for p in positions) / total_val
        if total_val > 0 else 0.0
    )

    gain_color = "#00cc66" if overall_gain >= 0 else "#ff4444"
    daily_color = "#00cc66" if avg_daily >= 0 else "#ff4444"
    gain_sign = "+" if overall_gain >= 0 else ""
    daily_sign = "+" if avg_daily >= 0 else ""

    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(8)
    layout.setContentsMargins(0, 0, 0, 0)

    title = QLabel("Summary")
    title.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaaaaa;")
    layout.addWidget(title)

    def _row(label, value, color="#dcdcdc"):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; color: #888888;")
        val = QLabel(value)
        val.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {color};")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)

    _row("Total Cost", f"${total_cost:,.2f}")
    _row("Current Value", f"${total_value:,.2f}")
    _row(
        "Total Gain / Loss",
        f"{gain_sign}${abs(overall_gain):,.2f}  ({gain_sign}{overall_pct:.1f}%)",
        gain_color,
    )
    _row("Avg Daily Change", f"{daily_sign}{abs(avg_daily):.3f}%", daily_color)

    return widget


def _build_legend(positions):
    colors = [_PIE_COLORS[i % len(_PIE_COLORS)] for i in range(len(positions))]

    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(7)
    layout.setContentsMargins(0, 0, 0, 0)

    title = QLabel("Holdings")
    title.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaaaaa;")
    layout.addWidget(title)

    for pos, color in zip(positions, colors):
        row = QHBoxLayout()
        row.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        dot.setFixedWidth(16)

        sym = QLabel(pos["symbol"])
        sym.setStyleSheet("font-size: 12px; font-weight: bold;")

        gain_color = "#00cc66" if pos["gain_pct"] >= 0 else "#ff4444"
        sign = "+" if pos["gain_pct"] >= 0 else ""
        pct = QLabel(f"{sign}{pos['gain_pct']:.1f}%")
        pct.setStyleSheet(f"font-size: 12px; color: {gain_color};")
        pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        pct.setFixedWidth(64)

        val = QLabel(f"${pos['current_value']:,.0f}")
        val.setStyleSheet("font-size: 12px; color: #aaaaaa;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        val.setFixedWidth(72)

        row.addWidget(dot)
        row.addWidget(sym)
        row.addStretch()
        row.addWidget(pct)
        row.addWidget(val)
        layout.addLayout(row)

    return widget
