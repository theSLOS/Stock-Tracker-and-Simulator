import sys
import os
import pandas as pd
import pandasModel
import caching
import stock_handler
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QTableView, QLabel, QComboBox,QMessageBox, 
    QFileDialog, QInputDialog, QPushButton
)
from PyQt6.QtCore import (Qt, QSize)
from PyQt6.QtGui import QIcon
import pyqtgraph as pg

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor

from PyQt6.QtCore import QAbstractTableModel, QVariant

ADD_NEW_SENTINEL = "__add_new_stock__"

class MainWindow(QMainWindow):
    def __init__(self, cache: caching.CacheManager, csv_path):
        super().__init__()
        self.cache = cache
        self.df = pd.DataFrame()
        self.csv_path = csv_path

        self.setWindowTitle("Stock Viewer")
        self.resize(1400, 800)

        # --- central widget + main layout
        central = QWidget()
        main_layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        # --- LEFT: table view
        self.table = QTableView()
        self.model = pandasModel.PandasModel(self.df)
        self.table.setModel(self.model)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(False)  # you can implement sorting later

        # --- RIGHT: chart area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)

        self.vline = pg.InfiniteLine(angle=90, movable=False)
        self.plot_widget.addItem(self.vline, ignoreBounds=True)

        self.hover_marker = pg.ScatterPlotItem(size=8, brush=pg.mkBrush(255, 0, 0), pen=pg.mkPen(None))
        self.plot_widget.addItem(self.hover_marker)

        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
        
        
        # --- top row: stock dropdown + delete button
        combo_row = QHBoxLayout()
        
        self.stock_combo = QComboBox()
        
        self.stock_combo.currentIndexChanged.connect(self.on_stock_changed)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.on_delete_stock)

        self.delete_button.setFixedWidth(80)

        font = self.delete_button.font()
        font.setPointSize(9)
        self.delete_button.setFont(font)

        if self.stock_combo.count() == 0:
            self.delete_button.setEnabled(False)

        combo_row.addWidget(self.stock_combo)
        combo_row.addWidget(self.delete_button)

        self.populate_stock_combo()

        right_layout.addLayout(combo_row)

        title_label = QLabel("Price Chart")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.stock_combo.count() > 0:
            self.load_stock(self.stock_combo.itemData(0))

        right_layout.addWidget(title_label)
        right_layout.addWidget(self.plot_widget)

        # --- add both sides to main layout
        main_layout.addWidget(self.table, stretch=1)
        main_layout.addWidget(right_panel, stretch=2)


        # e.g., later you might make selection filter date range, etc.

    def plot_price(self):
        df = self.df.copy()

        if "Date" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
                df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")
            x = df["Date"].astype("int64") // 10**9
        else:
            if not pd.api.types.is_datetime64_any_dtype(df.index):
                df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            x = df.index.astype("int64") // 10**9

        y = df["Close"]

        self.x_data = np.array(x)
        self.y_data = np.array(y)

        # Set axis
        axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation="bottom")
        self.plot_widget.setAxisItems({"bottom": axis})

        # If curve exists, update it
        if hasattr(self, "curve"):
            self.curve.setData(self.x_data, self.y_data)
        else:
            # First-time creation
            self.curve = self.plot_widget.plot(self.x_data, self.y_data, pen=pg.mkPen(width=2))

        self.plot_widget.setLabel("bottom", "Date (YYYY-MM-DD)")
        self.plot_widget.setLabel("left", "Price $(USD)")

    def populate_stock_combo(self, select_symbol: str | None = None):
        """Fill the dropdown with stocks from the cache."""
        self.stock_combo.blockSignals(True)
        self.stock_combo.clear()

        stocks = self.cache.all_stocks()  # dict: symbol -> entry

        # Add normal stock items
        for symbol, data in stocks.items():
            name = data.get("name", symbol)
            label = f"{symbol} - {name}"
            self.stock_combo.addItem(label, userData=symbol)

        # Add the special 'Add new stock...' item at the bottom
        self.stock_combo.addItem("Add new stock...", userData=ADD_NEW_SENTINEL)

        # Optionally auto-select a given symbol (e.g. after adding)
        if select_symbol is not None:
            for i in range(self.stock_combo.count()):
                if self.stock_combo.itemData(i) == select_symbol:
                    self.stock_combo.setCurrentIndex(i)
                    break

        self.stock_combo.blockSignals(False)
        current_index = self.stock_combo.currentIndex()
        if current_index >= 0:
            self.on_stock_changed(current_index)


    def on_stock_changed(self, index):
        """used when user selects different stock from dropdown"""
        if index < 0:
            return
        
        data = self.stock_combo.itemData(index)

        # Enable delete only for real stocks
        is_real_stock = data not in (None, ADD_NEW_SENTINEL)
        self.delete_button.setEnabled(is_real_stock)

        if data == ADD_NEW_SENTINEL:
                # Handle adding a new stock
                self.add_new_stock_dialog()
                return
        
        if data is None:
            return
        
        self.load_stock(data)
    
    def add_new_stock_dialog(self):
        """ask user for new stock symbol and add it to cache"""
        symbol, ok = QInputDialog.getText(self, "Add New Stock", "Enter stock symbol (e.g., AAPL):")
        if not ok or not symbol.strip():
            return
        symbol = symbol.strip().upper()

        if self.cache.has_stock(symbol):
            QMessageBox.information(self, "Stock Exists", f"The stock '{symbol}' is already in the cache.")
            return
        
        name, ok = QInputDialog.getText(self, "Add New Stock", "Enter stock name (optional):")
        if not ok or not name.strip():
            name = symbol
        name = name.strip()

        
        if not os.path.exists(self.csv_path):
            os.makedirs(self.csv_path)
        
        stock_package = stock_handler.add_new_stock(symbol, self.csv_path, name=name)
        if stock_package is None:
            QMessageBox.warning(self, "Error", f"Failed to retrieve data for stock '{symbol}'.")
            return
        
        self.cache.set_stock_data(stock_package)
        self.populate_stock_combo(select_symbol=symbol)

    def on_delete_stock(self):
        """delete stock currently selected in dropdown"""
        index = self.stock_combo.currentIndex()
        if index < 0:
            return  
        
        data = self.stock_combo.itemData(index)
        if data == ADD_NEW_SENTINEL:
            return      
        
        symbol = data
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete stock '{symbol}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.cache.delete_stock(symbol)
        
        self.populate_stock_combo()

        real_symbols = [self.stock_combo.itemData(i) for i in range(self.stock_combo.count()) 
                        if self.stock_combo.itemData(i) != ADD_NEW_SENTINEL]
        if not real_symbols:
            self.df = pd.DataFrame()
            self.model = pandasModel.PandasModel(self.df)
            self.table.setModel(self.model)
            self.plot_widget.clear()
            self.delete_button.setEnabled(False)


    def load_stock(self, symbol):
        """load stocks csv data into dataframe and update table/chart"""
        info = self.cache.get_stock_data(symbol)
        if info is None:
            print(f"No cache entry for {symbol}")
            return
        dfpath = info.get("dfpath", None)
        if dfpath is None:
            print(f"No dfpath for {symbol} in cache")
            return
        if(not self.cache.is_stock_fresh(symbol)):
            stock_handler.get_stock_data(symbol, stock_handler.path)
            self.cache.update_stock_timestamp(symbol)
            self.cache.save_cache()

        df = pd.read_csv(dfpath, parse_dates=True, index_col=0)
        self.df = df

        self.model = pandasModel.PandasModel(self.df)
        self.table.setModel(self.model)
        self.plot_price()

    def on_mouse_moved(self, pos):
        """update hover marker position based on mouse movement."""
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return
        
        vb = self.plot_widget.getPlotItem().vb
        mouse_point = vb.mapSceneToView(pos)

        x = mouse_point.x()

        if not hasattr(self, 'df') or self.x_data.size == 0:
            return
        
        #find index of closest x value 
        idx = (np.abs(self.x_data - x)).argmin()    
        x_closet = self.x_data[idx]
        y_closet = self.y_data[idx]

        self.vline.setPos(x_closet)

        self.hover_marker.setData([x_closet], [y_closet])


def apply_dark_theme(app):
    app.setStyle("Fusion")
    dark = QPalette()

    dark.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.ToolTipBase, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    dark.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

    app.setPalette(dark)