import math
import os
import traceback

import pandas as pd
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

from ..theme import get_tokens
from core import user_manager

_PIE_COLORS = [
    "#6495ED", "#32CD32", "#FF6347", "#FFD700",
    "#BA55D3", "#1E90FF", "#FF8C00", "#00FA9A",
    "#FF69B4", "#20B2AA",
]


class _AvatarWidget(QWidget):
    def __init__(self, username, size=68, avatar_path=None, parent=None):
        super().__init__(parent)
        self._initial = username[0].upper() if username else "?"
        self.setFixedSize(size, size)
        self._size = size
        self._pixmap = None
        if avatar_path and os.path.exists(avatar_path):
            self._pixmap = QPixmap(avatar_path).scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._pixmap and not self._pixmap.isNull():
            clip = QPainterPath()
            clip.addEllipse(0.0, 0.0, float(self._size), float(self._size))
            p.setClipPath(clip)
            p.drawPixmap(0, 0, self._size, self._size, self._pixmap)
        else:
            p.setBrush(QColor("#2a82da"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(0, 0, self._size, self._size)
            font = QFont()
            font.setPixelSize(int(self._size * 0.40))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#ffffff"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)


def _make_segment_path(cx, cy, outer_r, inner_r, start_angle, span_angle):
    path = QPainterPath()
    outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
    inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
    path.arcMoveTo(outer_rect, start_angle)
    path.arcTo(outer_rect, start_angle, span_angle)
    path.arcTo(inner_rect, start_angle + span_angle, -span_angle)
    path.closeSubpath()
    return path


class DonutChartWidget(QWidget):
    hovered = pyqtSignal(int)

    def __init__(self, positions, colors, tokens, parent=None):
        super().__init__(parent)
        self._positions = positions
        self._qcolors = [QColor(c) for c in colors]
        self._tokens = tokens
        self._hovered_idx = -1
        self._draw_progress = 0.0
        self.setFixedSize(300, 300)
        self.setMouseTracking(True)

        self._anim = QPropertyAnimation(self, b"draw_progress")
        self._anim.setDuration(900)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    @pyqtProperty(float)
    def draw_progress(self):
        return self._draw_progress

    @draw_progress.setter
    def draw_progress(self, val):
        self._draw_progress = val
        self.update()

    def set_hovered(self, idx):
        if idx != self._hovered_idx:
            self._hovered_idx = idx
            self.update()

    def _hit_test(self, pos):
        cx, cy = self.width() / 2, self.height() / 2
        outer_r = min(self.width(), self.height()) / 2 - 12
        inner_r = outer_r * 0.54

        dx = pos.x() - cx
        dy = pos.y() - cy
        r = math.sqrt(dx * dx + dy * dy)

        if r < inner_r - 2 or r > outer_r + 14:
            return -1

        values = [p["current_value"] for p in self._positions]
        total = sum(values)
        if total == 0:
            return -1

        angle = math.degrees(math.atan2(-dy, dx)) % 360

        start = 90.0
        for i, value in enumerate(values):
            span = (value / total) * 360.0
            seg_start = start % 360
            seg_end = (start + span) % 360
            if seg_end >= seg_start:
                if seg_start <= angle < seg_end:
                    return i
            else:
                if angle >= seg_start or angle < seg_end:
                    return i
            start += span

        return -1

    def mouseMoveEvent(self, event):
        idx = self._hit_test(event.position())
        if idx != self._hovered_idx:
            self._hovered_idx = idx
            self.hovered.emit(idx)
            self.update()

    def leaveEvent(self, event):
        if self._hovered_idx != -1:
            self._hovered_idx = -1
            self.hovered.emit(-1)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        outer_r = min(w, h) / 2 - 14
        inner_r = outer_r * 0.54
        explode_dist = 10

        values = [p["current_value"] for p in self._positions]
        total = sum(values)
        if total == 0:
            return

        total_sweep = 360.0 * self._draw_progress
        start = 90.0

        for i, (p, color, value) in enumerate(zip(self._positions, self._qcolors, values)):
            span = (value / total) * 360.0
            actual_span = min(span, max(0.0, total_sweep - (start - 90.0)))
            if actual_span < 0.1:
                start += span
                continue

            is_hovered = i == self._hovered_idx
            mid_rad = math.radians(start + actual_span / 2)
            edx = math.cos(mid_rad) * explode_dist if is_hovered else 0.0
            edy = -math.sin(mid_rad) * explode_dist if is_hovered else 0.0

            # Glow layers drawn behind the segment
            if is_hovered:
                for glow_extra, alpha in [(20, 18), (13, 32), (6, 52)]:
                    gc = QColor(color)
                    gc.setAlpha(alpha)
                    gpath = _make_segment_path(
                        cx + edx, cy + edy,
                        outer_r + glow_extra,
                        max(inner_r - glow_extra // 2, 8),
                        start, actual_span,
                    )
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.fillPath(gpath, QBrush(gc))

            seg_color = QColor(color)
            if is_hovered:
                h_hsl, s_hsl, l_hsl, a_hsl = seg_color.getHsl()
                seg_color.setHsl(h_hsl, min(255, s_hsl + 20), min(255, l_hsl + 22), a_hsl)

            path = _make_segment_path(cx + edx, cy + edy, outer_r, inner_r, start, actual_span)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(path, QBrush(seg_color))

            if is_hovered:
                painter.setPen(QPen(QColor(255, 255, 255, 65), 1.5))
                painter.drawPath(path)

            start += span

        # Inner circle to clear center (matches app background)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(self._tokens["donut_center"])))
        painter.drawEllipse(QRectF(cx - inner_r + 1, cy - inner_r + 1, (inner_r - 1) * 2, (inner_r - 1) * 2))

        # Center text: stock detail on hover, total otherwise
        if 0 <= self._hovered_idx < len(self._positions):
            p = self._positions[self._hovered_idx]
            pct = p["current_value"] / total * 100
            gain_pct = p["gain_pct"]
            gain_color = QColor("#00cc66") if gain_pct >= 0 else QColor("#ff4444")
            sign = "+" if gain_pct >= 0 else ""

            font = QFont()
            font.setPixelSize(15)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(self._tokens["value_text"]))
            painter.drawText(QRectF(cx - 65, cy - 42, 130, 22), Qt.AlignmentFlag.AlignCenter, p["symbol"])

            font.setPixelSize(12)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor(self._tokens["value_text"]))
            painter.drawText(QRectF(cx - 65, cy - 18, 130, 20), Qt.AlignmentFlag.AlignCenter, f"${p['current_value']:,.0f}")

            font.setPixelSize(10)
            painter.setFont(font)
            painter.setPen(QColor(self._tokens["label_muted"]))
            painter.drawText(QRectF(cx - 65, cy + 2, 130, 18), Qt.AlignmentFlag.AlignCenter, f"{pct:.1f}% of portfolio")

            font.setPixelSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(gain_color)
            painter.drawText(QRectF(cx - 65, cy + 20, 130, 20), Qt.AlignmentFlag.AlignCenter, f"{sign}{gain_pct:.1f}%")
        else:
            font = QFont()
            font.setPixelSize(17)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(self._tokens["value_text"]))
            painter.drawText(QRectF(cx - 70, cy - 18, 140, 26), Qt.AlignmentFlag.AlignCenter, f"${total:,.0f}")

            font.setPixelSize(10)
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor(self._tokens["label_faint"]))
            painter.drawText(QRectF(cx - 70, cy + 8, 140, 18), Qt.AlignmentFlag.AlignCenter, "Total Value")


class _LegendRow(QWidget):
    hover_enter = pyqtSignal(int)
    hover_leave = pyqtSignal()

    def __init__(self, idx, pos, color, tokens, parent=None):
        super().__init__(parent)
        self._idx = idx
        self._color = QColor(color)
        self._highlighted = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(6, 3, 6, 3)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        dot.setFixedWidth(16)

        sym = QLabel(pos["symbol"])
        sym.setStyleSheet(f"font-size: {tokens['font_body']}; font-weight: bold;")

        shares = pos["shares"]
        shares_text = f"{shares:,.0f}" if shares == int(shares) else f"{shares:,.4g}"
        shares_lbl = QLabel(f"{shares_text} sh")
        shares_lbl.setStyleSheet(f"font-size: {tokens['font_body']}; color: {tokens['label_muted']};")

        gain_color_hex = "#00cc66" if pos["gain_pct"] >= 0 else "#ff4444"
        sign = "+" if pos["gain_pct"] >= 0 else ""
        pct_lbl = QLabel(f"{sign}{pos['gain_pct']:.1f}%")
        pct_lbl.setStyleSheet(f"font-size: {tokens['font_body']}; color: {gain_color_hex};")
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        pct_lbl.setFixedWidth(64)

        val_lbl = QLabel(f"${pos['current_value']:,.0f}")
        val_lbl.setStyleSheet(f"font-size: {tokens['font_body']}; color: {tokens['label_secondary']};")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        val_lbl.setFixedWidth(72)

        layout.addWidget(dot)
        layout.addWidget(sym)
        layout.addWidget(shares_lbl)
        layout.addStretch()
        layout.addWidget(pct_lbl)
        layout.addWidget(val_lbl)

        self._apply_style()

    def set_highlighted(self, highlighted: bool):
        if self._highlighted != highlighted:
            self._highlighted = highlighted
            self._apply_style()

    def _apply_style(self):
        if self._highlighted:
            r, g, b = self._color.red(), self._color.green(), self._color.blue()
            self.setStyleSheet(f"background: rgba({r},{g},{b},35); border-radius: 4px;")
        else:
            self.setStyleSheet("")

    def enterEvent(self, event):
        self.hover_enter.emit(self._idx)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_leave.emit()
        super().leaveEvent(event)


class _LegendWidget(QWidget):
    def __init__(self, positions, colors, tokens, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Holdings")
        title.setStyleSheet(f"font-size: {tokens['font_title']}; font-weight: bold; color: {tokens['label_secondary']};")
        layout.addWidget(title)

        self._rows = []
        for i, (pos, color) in enumerate(zip(positions, colors)):
            row = _LegendRow(i, pos, color, tokens)
            self._rows.append(row)
            layout.addWidget(row)

    def set_highlighted(self, idx: int):
        for i, row in enumerate(self._rows):
            row.set_highlighted(i == idx)

    @property
    def rows(self):
        return self._rows


class UserPage(QWidget):
    back_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, cache, csv_path, user_profile, theme="dark", parent=None):
        super().__init__(parent)
        tokens = get_tokens(theme)
        positions = _load_positions(cache, csv_path)
        username = user_profile.get("username", "")
        email = user_profile.get("email", "")
        phone = user_profile.get("phone", "")

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 20, 32, 20)
        root.setSpacing(0)

        # Nav bar
        _btn_style = (
            f"font-size: {tokens['font_title']}; background: transparent; border: none; padding: 2px 0;"
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
        settings_btn.setStyleSheet(_btn_style + f" color: {tokens['label_muted']};")
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
        header_row.addWidget(_AvatarWidget(username, avatar_path=user_manager.get_avatar_path(username)))

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        name_lbl = QLabel(username)
        name_lbl.setStyleSheet(f"font-size: {tokens['font_name']}; font-weight: bold;")
        name_col.addWidget(name_lbl)

        sub_parts = [s for s in [email, phone] if s]
        if sub_parts:
            sub_lbl = QLabel("  ·  ".join(sub_parts))
            sub_lbl.setStyleSheet(f"font-size: {tokens['font_body']}; color: {tokens['label_muted']};")
            name_col.addWidget(sub_lbl)

        header_row.addLayout(name_col)
        header_row.addStretch()
        root.addLayout(header_row)
        root.addSpacing(18)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {tokens['separator']};")
        root.addWidget(sep)
        root.addSpacing(18)

        # Portfolio section title
        port_title = QLabel("Portfolio")
        port_title.setStyleSheet(f"font-size: {tokens['font_subhead']}; font-weight: bold;")
        root.addWidget(port_title)
        root.addSpacing(14)

        if not positions:
            empty = QLabel(
                "No portfolio positions recorded.\n"
                "Use the Portfolio tab to track your holdings."
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"font-size: {tokens['font_title']}; color: {tokens['label_faint']};")
            root.addWidget(empty, stretch=1)
        else:
            colors = [_PIE_COLORS[i % len(_PIE_COLORS)] for i in range(len(positions))]
            chart = DonutChartWidget(positions, colors, tokens)
            legend = _LegendWidget(positions, colors, tokens)

            # Bidirectional hover sync
            chart.hovered.connect(legend.set_highlighted)
            for row in legend.rows:
                row.hover_enter.connect(chart.set_hovered)
                row.hover_leave.connect(lambda: chart.set_hovered(-1))

            body = QHBoxLayout()
            body.setSpacing(36)
            body.setAlignment(Qt.AlignmentFlag.AlignTop)
            body.addWidget(chart)

            right = QVBoxLayout()
            right.setSpacing(22)
            right.addWidget(_build_stats(positions, tokens))
            right.addWidget(legend)
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
            purchase_date = portfolio.get("purchase_date")
            if purchase_date:
                df_since = df[df.index >= pd.Timestamp(purchase_date)]
                daily_pct = df_since["Close"].pct_change().dropna()
            else:
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
        except Exception as e:
            print(f"[Portfolio] Failed to load position for {symbol}: {e}")
            traceback.print_exc()
            continue
    return positions


def _build_stats(positions, tokens):
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
    title.setStyleSheet(f"font-size: {tokens['font_title']}; font-weight: bold; color: {tokens['label_secondary']};")
    layout.addWidget(title)

    def _row(label, value, color=None):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: {tokens['font_body']}; color: {tokens['label_muted']};")
        val = QLabel(value)
        val_color = color if color else tokens["value_text"]
        val.setStyleSheet(f"font-size: {tokens['font_title']}; font-weight: bold; color: {val_color};")
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
