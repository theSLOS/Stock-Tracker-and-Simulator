from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView, QAbstractItemView,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont

from ..theme import get_tokens


class ExplorePanel(QWidget):
    add_to_portfolio = pyqtSignal(str)

    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self._worker = None
        self._tokens = get_tokens(theme)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_row = QHBoxLayout()

        title = QLabel("Explore Markets")
        title_font = QFont()
        title_font.setPixelSize(int(self._tokens["font_subhead"].replace("px", "")))
        title_font.setBold(True)
        title.setFont(title_font)

        self._status_label = QLabel("Click Refresh to load market data")
        self._status_label.setStyleSheet(
            f"font-size: {self._tokens['font_small']}; color: {self._tokens['label_faint']};"
        )

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedWidth(90)
        self._refresh_btn.clicked.connect(self._on_refresh)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self._status_label)
        header_row.addWidget(self._refresh_btn)

        self._tabs = QTabWidget()

        self._gainers_table = self._make_table()
        self._losers_table = self._make_table()
        self._active_table = self._make_table()
        self._movers_table = self._make_table()

        self._tabs.addTab(self._gainers_table, "Top Gainers")
        self._tabs.addTab(self._losers_table, "Top Losers")
        self._tabs.addTab(self._active_table, "Most Active")
        self._tabs.addTab(self._movers_table, "Biggest Movers")

        layout.addLayout(header_row)
        layout.addWidget(self._tabs)

    # ------------------------------------------------------------------ public

    def set_theme(self, theme):
        self._tokens = get_tokens(theme)
        self._status_label.setStyleSheet(
            f"font-size: {self._tokens['font_small']}; color: {self._tokens['label_faint']};"
        )

    def refresh_if_empty(self):
        if self._gainers_table.rowCount() == 0 and (self._worker is None or not self._worker.isRunning()):
            self._status_label.setText("Loading...")
            self._refresh_btn.setEnabled(False)
            self._start_worker(force=False)

    # ------------------------------------------------------------------ internal

    def _make_table(self):
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Symbol", "Name", "Price", "Change %", "Volume", ""])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return table

    def start_background_load(self):
        if self._worker is not None and self._worker.isRunning():
            return
        if self._gainers_table.rowCount() > 0:
            return
        self._status_label.setText("Loading market data in background...")
        self._refresh_btn.setEnabled(False)
        self._start_worker(force=False)

    def _on_refresh(self):
        self._refresh_btn.setEnabled(False)
        self._status_label.setText("Refreshing...")
        self._start_worker(force=True)

    def _start_worker(self, force):
        from core.explore_worker import ExploreWorker
        self._worker = ExploreWorker(force=force)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self._status_label.setText)
        self._worker.start()

    def _on_data_loaded(self, data):
        self._refresh_btn.setEnabled(True)
        self._status_label.setText(f"Loaded {len(data)} stocks")

        gainers = sorted(data, key=lambda x: x["change_pct"], reverse=True)
        losers  = sorted(data, key=lambda x: x["change_pct"])
        active  = sorted(data, key=lambda x: x["volume"], reverse=True)
        movers  = sorted(data, key=lambda x: abs(x["change_pct"]), reverse=True)

        self._fill_table(self._gainers_table, gainers[:20])
        self._fill_table(self._losers_table,  losers[:20])
        self._fill_table(self._active_table,  active[:20])
        self._fill_table(self._movers_table,  movers[:20])

    def _fill_table(self, table, rows):
        t = self._tokens
        table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            symbol = item["symbol"]
            change = item["change_pct"]

            cells = [
                QTableWidgetItem(symbol),
                QTableWidgetItem(item["name"]),
                QTableWidgetItem(f"${item['price']:.2f}"),
                QTableWidgetItem(f"{change:+.2f}%"),
                QTableWidgetItem(self._fmt_volume(item["volume"])),
            ]
            cells[3].setForeground(
                QColor(t["buy_color"]) if change >= 0 else QColor(t["sell_color"])
            )

            for col, cell in enumerate(cells):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
                table.setItem(row, col, cell)

            btn = QPushButton("+ Add")
            btn.setFixedWidth(60)
            btn.setFixedHeight(22)
            f = btn.font()
            f.setPointSize(8)
            btn.setFont(f)
            btn.clicked.connect(lambda _checked, s=symbol: self.add_to_portfolio.emit(s))
            container = QWidget()
            c_layout = QHBoxLayout(container)
            c_layout.setContentsMargins(4, 1, 4, 1)
            c_layout.addWidget(btn)
            table.setCellWidget(row, 5, container)

    def _fmt_volume(self, vol):
        if vol >= 1_000_000_000:
            return f"{vol / 1_000_000_000:.1f}B"
        if vol >= 1_000_000:
            return f"{vol / 1_000_000:.1f}M"
        if vol >= 1_000:
            return f"{vol / 1_000:.0f}K"
        return str(int(vol))

    def _on_error(self, message):
        self._refresh_btn.setEnabled(True)
        self._status_label.setText(f"Error: {message}")
