import numpy as np
import pandas as pd
from datetime import datetime as dt

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStackedWidget
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QLinearGradient, QColor, QBrush

import pyqtgraph as pg


class _DateAxis(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        return [dt.fromtimestamp(v).strftime('%b %d, %Y') for v in values]


class StockChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.df = pd.DataFrame()
        self.plot_df = pd.DataFrame()
        self.x_data = np.array([])
        self.y_data = np.array([])
        self._date_range = None
        self._indicators = {}   # key -> {func, color, name, curve}
        self._pred_curves = []

        # --- plot widget
        date_axis = _DateAxis(orientation='bottom')
        date_axis.setPen(pg.mkPen('#3a3a5c'))
        date_axis.setTextPen(pg.mkPen('#888'))
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': date_axis})
        self.plot_widget.setBackground('#1a1a2e')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.12)
        left_ax = self.plot_widget.getPlotItem().getAxis('left')
        left_ax.setPen(pg.mkPen('#3a3a5c'))
        left_ax.setTextPen(pg.mkPen('#888'))

        # gradient fill under price line
        gradient = QLinearGradient(0, 0, 0, 1)
        gradient.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
        gradient.setColorAt(0, QColor(100, 149, 237, 120))
        gradient.setColorAt(1, QColor(100, 149, 237, 0))
        self._price_curve = pg.PlotCurveItem(
            pen=pg.mkPen('#6495ED', width=2),
            fillLevel=0,
            brush=QBrush(gradient),
        )
        self.plot_widget.addItem(self._price_curve)

        self._legend = self.plot_widget.addLegend(offset=(10, 10))
        self._legend.addItem(self._price_curve, 'Price')

        # crosshair
        self._vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen('#555', width=1, style=Qt.PenStyle.DashLine),
        )
        self.plot_widget.addItem(self._vline, ignoreBounds=True)

        self._dot = pg.ScatterPlotItem(
            size=9, brush=pg.mkBrush('#6495ED'), pen=pg.mkPen('white', width=1.5)
        )
        self.plot_widget.addItem(self._dot, ignoreBounds=True)

        self.plot_widget.viewport().setMouseTracking(True)
        self.plot_widget.viewport().installEventFilter(self)

        # floating tooltip overlay
        self._tooltip = QLabel(self)
        self._tooltip.setStyleSheet("""
            QLabel {
                background: rgba(20, 20, 35, 210);
                color: #eeeeee;
                border: 1px solid #3a3a5c;
                border-radius: 6px;
                padding: 7px 11px;
                font-size: 12px;
            }
        """)
        self._tooltip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._tooltip.hide()

        # empty state
        empty = QLabel('No stocks — click "+ Add Stock" to get started')
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet('color: #666; font-size: 16px;')
        self._empty_widget = empty

        self._stack = QStackedWidget()
        self._stack.addWidget(empty)
        self._stack.addWidget(self.plot_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

    # ------------------------------------------------------------------ public

    def set_data(self, df: pd.DataFrame):
        self.df = df
        self._redraw()

    def set_date_range(self, days: int | None):
        self._date_range = days
        self._redraw()

    def register_indicator(self, key: str, func, color: tuple, name: str):
        self._indicators[key] = {'func': func, 'color': color, 'name': name, 'curve': None}

    def toggle_indicator(self, key: str, enabled: bool):
        if key not in self._indicators:
            return
        entry = self._indicators[key]
        if enabled:
            self._draw_indicator(key)
        else:
            if entry['curve'] is not None:
                self.plot_widget.removeItem(entry['curve'])
                self._legend.removeItem(entry['name'])
                entry['curve'] = None

    def set_prediction(self, forecast: pd.DataFrame, last_date) -> tuple:
        self.clear_prediction()
        if not isinstance(last_date, pd.Timestamp):
            last_date = pd.Timestamp(last_date)
        future = forecast[forecast['ds'] > last_date].copy()

        x = np.array(future['ds'].astype('int64') // 10 ** 9)
        y_mean = np.array(future['yhat'])
        y_upper = np.array(future['yhat_upper'])
        y_lower = np.array(future['yhat_lower'])

        upper = pg.PlotCurveItem(x, y_upper, pen=pg.mkPen(None))
        lower = pg.PlotCurveItem(x, y_lower, pen=pg.mkPen(None))
        band = pg.FillBetweenItem(upper, lower, brush=pg.mkBrush(100, 149, 237, 50))
        mean_line = self.plot_widget.plot(
            x, y_mean, pen=pg.mkPen((100, 149, 237), width=2, style=Qt.PenStyle.DashLine)
        )
        for item in (upper, lower, band):
            self.plot_widget.addItem(item)
        self._pred_curves = [upper, lower, band, mean_line]

        return (
            float(future['yhat'].iloc[-1]),
            float(future['yhat_lower'].iloc[-1]),
            float(future['yhat_upper'].iloc[-1]),
        )

    def clear_prediction(self):
        for item in self._pred_curves:
            self.plot_widget.removeItem(item)
        self._pred_curves = []

    def clear(self):
        self.df = pd.DataFrame()
        self.plot_df = pd.DataFrame()
        self.x_data = np.array([])
        self.y_data = np.array([])
        self._price_curve.setData([], [])
        for entry in self._indicators.values():
            if entry['curve'] is not None:
                self.plot_widget.removeItem(entry['curve'])
                entry['curve'] = None
        self.clear_prediction()
        self._stack.setCurrentWidget(self._empty_widget)

    # ------------------------------------------------------------------ internal

    def _redraw(self):
        if self.df.empty:
            self._stack.setCurrentWidget(self._empty_widget)
            return

        df = self.df.copy()
        if self._date_range is not None:
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=self._date_range)
            df = df[df.index >= cutoff]
        self.plot_df = df

        if not pd.api.types.is_datetime64_any_dtype(df.index):
            df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        self.x_data = df.index.astype('datetime64[s]').astype('int64').to_numpy()
        self.y_data = np.array(df['Close'])

        self.plot_widget.setLabel('left', 'Price (USD)')

        self._price_curve.setData(self.x_data, self.y_data, fillLevel=float(self.y_data.min()))
        self._stack.setCurrentWidget(self.plot_widget)
        self._redraw_indicators()

    def _draw_indicator(self, key: str):
        entry = self._indicators[key]
        if self.plot_df.empty:
            return
        curve = self.plot_widget.plot(
            pen=pg.mkPen(entry['color'], width=1.5, style=Qt.PenStyle.DashLine)
        )
        entry['curve'] = curve
        values = np.array(entry['func'](self.plot_df))
        curve.setData(self.x_data, values)
        self._legend.addItem(curve, entry['name'])

    def _redraw_indicators(self):
        for entry in self._indicators.values():
            if entry['curve'] is not None:
                values = np.array(entry['func'](self.plot_df))
                entry['curve'].setData(self.x_data, values)

    def eventFilter(self, obj, event):
        if obj is self.plot_widget.viewport() and event.type() == QEvent.Type.MouseMove:
            scene_pos = self.plot_widget.mapToScene(event.pos())
            self._on_mouse_moved(scene_pos)
            return False
        return super().eventFilter(obj, event)

    def _on_mouse_moved(self, pos):
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self._vline.hide()
            self._dot.hide()
            self._tooltip.hide()
            return
        if self.x_data.size == 0:
            return

        vb = self.plot_widget.getPlotItem().vb
        pt = vb.mapSceneToView(pos)
        mx = pt.x()

        if mx < self.x_data[0] or mx > self.x_data[-1]:
            self._vline.hide()
            self._dot.hide()
            self._tooltip.hide()
            return

        self._vline.show()
        self._dot.show()

        idx = int(np.abs(self.x_data - mx).argmin())
        x0, y0 = self.x_data[idx], self.y_data[idx]

        y_interp = float(np.interp(mx, self.x_data, self.y_data))

        self._vline.setPos(mx)
        self._dot.setData([mx], [y_interp])

        date_str = dt.fromtimestamp(x0).strftime('%b %d, %Y')
        change = float(y0 - self.y_data[idx - 1]) if idx > 0 else 0.0
        pct = (change / float(self.y_data[idx - 1]) * 100) if idx > 0 else 0.0
        sign = '+' if change >= 0 else ''
        col = '#00cc66' if change >= 0 else '#ff4444'

        self._tooltip.setText(
            f'<b>{date_str}</b><br>'
            f'Price: <b>${y0:.2f}</b><br>'
            f"<span style='color:{col}'>{sign}{change:.2f} ({sign}{pct:.2f}%)</span>"
        )
        self._tooltip.adjustSize()

        pw_pt = self.plot_widget.mapFromScene(pos)
        w_pt = self.plot_widget.mapTo(self, pw_pt)
        tx = w_pt.x() + 16
        ty = w_pt.y() - self._tooltip.height() // 2
        tx = min(tx, self.width() - self._tooltip.width() - 4)
        ty = max(4, min(ty, self.height() - self._tooltip.height() - 4))
        self._tooltip.move(tx, ty)
        self._tooltip.show()
        self._tooltip.raise_()
