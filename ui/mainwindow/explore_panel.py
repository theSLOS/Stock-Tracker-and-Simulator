from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QTabWidget, QHeaderView, QAbstractItemView,
    QSizePolicy, QLineEdit, QFrame,
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
        self._all_data = []
        self._table_data = {}
        self._load_time = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # -- Header row --
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

        # -- Market overview bar --
        self._overview_frame = QFrame()
        self._overview_frame.setVisible(False)
        ov_layout = QHBoxLayout(self._overview_frame)
        ov_layout.setContentsMargins(0, 2, 0, 2)
        ov_layout.setSpacing(10)

        self._ov_total = QLabel()
        self._ov_div1 = QLabel("|")
        self._ov_gainers = QLabel()
        self._ov_div2 = QLabel("|")
        self._ov_losers = QLabel()
        self._ov_div3 = QLabel("|")
        self._ov_avg = QLabel()

        for w in (self._ov_total, self._ov_div1, self._ov_gainers, self._ov_div2,
                  self._ov_losers, self._ov_div3, self._ov_avg):
            ov_layout.addWidget(w)
        ov_layout.addStretch()

        # -- Search / filter bar --
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Search by symbol or name…")
        self._search_bar.setFixedHeight(30)
        self._search_bar.setClearButtonEnabled(True)
        self._search_bar.textChanged.connect(self._apply_filter)

        # -- Tabs --
        self._tabs = QTabWidget()

        self._gainers_table = self._make_table()
        self._losers_table = self._make_table()
        self._active_table = self._make_table()
        self._movers_table = self._make_table()

        self._tabs.addTab(self._gainers_table, "Top Gainers")
        self._tabs.addTab(self._losers_table, "Top Losers")
        self._tabs.addTab(self._active_table, "Most Active")
        self._tabs.addTab(self._movers_table, "Biggest Movers")
        self._tabs.currentChanged.connect(lambda _: self._apply_filter(self._search_bar.text()))

        layout.addLayout(header_row)
        layout.addWidget(self._overview_frame)
        layout.addWidget(self._search_bar)
        layout.addWidget(self._tabs)

        self._apply_search_style()
        self._apply_overview_style()
        self._apply_table_styles()

    # ------------------------------------------------------------------ public

    def set_theme(self, theme):
        self._tokens = get_tokens(theme)
        self._status_label.setStyleSheet(
            f"font-size: {self._tokens['font_small']}; color: {self._tokens['label_faint']};"
        )
        self._apply_search_style()
        self._apply_overview_style()
        self._apply_table_styles()
        if self._all_data:
            self._update_overview(self._all_data)

    def refresh_if_empty(self):
        if self._gainers_table.rowCount() == 0 and (self._worker is None or not self._worker.isRunning()):
            self._status_label.setText("Loading…")
            self._refresh_btn.setEnabled(False)
            self._start_worker(force=False)

    # ------------------------------------------------------------------ styling helpers

    def _apply_search_style(self):
        t = self._tokens
        self._search_bar.setStyleSheet(f"""
            QLineEdit {{
                background: {t['base']};
                color: {t['text']};
                border: 1px solid {t['separator']};
                border-radius: 4px;
                padding: 3px 8px;
                font-size: {t['font_body']};
            }}
            QLineEdit:focus {{
                border: 1px solid {t['highlight']};
            }}
        """)

    def _apply_overview_style(self):
        t = self._tokens
        small = f"font-size: {t['font_small']};"
        for div in (self._ov_div1, self._ov_div2, self._ov_div3):
            div.setStyleSheet(f"{small} color: {t['label_muted']};")
        self._ov_total.setStyleSheet(f"{small} color: {t['label_secondary']};")

    def _apply_table_styles(self):
        t = self._tokens
        stylesheet = f"""
            QTableWidget {{
                background: {t['base']};
                alternate-background-color: {t['alternate_base']};
                color: {t['text']};
                gridline-color: {t['separator_strong']};
                font-size: {t['font_body']};
                border: none;
            }}
            QHeaderView::section {{
                background: {t['window']};
                color: {t['label_secondary']};
                padding: 4px 8px;
                border: none;
                border-bottom: 1px solid {t['separator']};
                font-size: {t['font_small']};
                font-weight: bold;
            }}
        """
        for table in (self._gainers_table, self._losers_table,
                      self._active_table, self._movers_table):
            table.setStyleSheet(stylesheet)

    # ------------------------------------------------------------------ table factory

    def _make_table(self):
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["#", "Symbol", "Name", "Price", "Change %", "Volume", ""])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.cellDoubleClicked.connect(
            lambda row, col, t=table: self._on_row_double_clicked(t, row)
        )
        return table

    def _on_row_double_clicked(self, table, row):
        item = table.item(row, 1)
        if item:
            self.add_to_portfolio.emit(item.text())

    # ------------------------------------------------------------------ load flow

    def start_background_load(self):
        if self._worker is not None and self._worker.isRunning():
            return
        if self._gainers_table.rowCount() > 0:
            return
        self._status_label.setText("Loading market data in background…")
        self._refresh_btn.setEnabled(False)
        self._start_worker(force=False)

    def _on_refresh(self):
        self._refresh_btn.setEnabled(False)
        self._status_label.setText("Refreshing…")
        self._start_worker(force=True)

    def _start_worker(self, force):
        from core.explore_worker import ExploreWorker
        self._worker = ExploreWorker(force=force)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self._status_label.setText)
        self._worker.start()

    def _on_data_loaded(self, data):
        self._all_data = data
        self._load_time = datetime.now().strftime("%I:%M %p").lstrip("0")
        self._refresh_btn.setEnabled(True)
        self._status_label.setText(f"Loaded {len(data)} stocks · {self._load_time}")

        gainers = sorted(data, key=lambda x: x["change_pct"], reverse=True)
        losers  = sorted(data, key=lambda x: x["change_pct"])
        active  = sorted(data, key=lambda x: x["volume"], reverse=True)
        movers  = sorted(data, key=lambda x: abs(x["change_pct"]), reverse=True)

        self._fill_table(self._gainers_table, gainers[:20])
        self._fill_table(self._losers_table,  losers[:20])
        self._fill_table(self._active_table,  active[:20])
        self._fill_table(self._movers_table,  movers[:20])

        self._update_overview(data)
        self._overview_frame.setVisible(True)
        self._apply_filter(self._search_bar.text())

    def _update_overview(self, data):
        t = self._tokens
        n_gainers = sum(1 for d in data if d["change_pct"] >= 0)
        n_losers = len(data) - n_gainers
        avg = sum(d["change_pct"] for d in data) / len(data) if data else 0.0

        bold_small = f"font-size: {t['font_small']}; font-weight: bold;"
        self._ov_total.setText(f"{len(data)} stocks")
        self._ov_total.setStyleSheet(f"font-size: {t['font_small']}; color: {t['label_secondary']};")
        self._ov_gainers.setText(f"▲ {n_gainers} gainers")
        self._ov_gainers.setStyleSheet(f"{bold_small} color: {t['buy_color']};")
        self._ov_losers.setText(f"▼ {n_losers} losers")
        self._ov_losers.setStyleSheet(f"{bold_small} color: {t['sell_color']};")
        avg_color = t["buy_color"] if avg >= 0 else t["sell_color"]
        avg_arrow = "▲" if avg >= 0 else "▼"
        self._ov_avg.setText(f"Avg {avg_arrow} {abs(avg):.2f}%")
        self._ov_avg.setStyleSheet(f"{bold_small} color: {avg_color};")

    def _fill_table(self, table, rows):
        t = self._tokens
        self._table_data[table] = rows
        table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            symbol = item["symbol"]
            change = item["change_pct"]
            arrow = "▲" if change >= 0 else "▼"
            change_color = t["buy_color"] if change >= 0 else t["sell_color"]

            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setForeground(QColor(t["label_muted"]))

            cells = [
                rank_item,
                QTableWidgetItem(symbol),
                QTableWidgetItem(item["name"]),
                QTableWidgetItem(f"${item['price']:.2f}"),
                QTableWidgetItem(f"{arrow} {abs(change):.2f}%"),
                QTableWidgetItem(self._fmt_volume(item["volume"])),
            ]
            cells[4].setForeground(QColor(change_color))

            for col, cell in enumerate(cells):
                cell.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
                table.setItem(row, col, cell)

            btn = QPushButton("+ Add")
            btn.setFixedWidth(72)
            btn.setFixedHeight(26)
            f = btn.font()
            f.setPixelSize(int(t["font_body"].replace("px", "")))
            btn.setFont(f)
            btn.clicked.connect(lambda _checked, s=symbol: self.add_to_portfolio.emit(s))
            container = QWidget()
            c_layout = QHBoxLayout(container)
            c_layout.setContentsMargins(4, 2, 4, 2)
            c_layout.addWidget(btn)
            table.setCellWidget(row, 6, container)

    def _apply_filter(self, text):
        current_table = self._tabs.currentWidget()
        if not isinstance(current_table, QTableWidget):
            return
        query = text.strip().lower()
        for row in range(current_table.rowCount()):
            if not query:
                current_table.setRowHidden(row, False)
                continue
            symbol_item = current_table.item(row, 1)
            name_item = current_table.item(row, 2)
            symbol = symbol_item.text().lower() if symbol_item else ""
            name = name_item.text().lower() if name_item else ""
            current_table.setRowHidden(row, query not in symbol and query not in name)

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
