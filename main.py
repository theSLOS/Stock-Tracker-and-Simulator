import pandas as pd
from dotenv import load_dotenv
import os
import pandasModel
import stock_handler
import QWindowModel


import sys
import pandas as pd
import caching

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor

load_dotenv()
path = os.getenv('CSV_PATH')

def main():
    cache = caching.CacheManager(os.getenv('CACHE_PATH', 'cache/main_cache'))   
    app = QApplication(sys.argv)
    QWindowModel.apply_dark_theme(app)

    print("startingWindow")
    window = QWindowModel.MainWindow(cache, path)
    window.show()

    sys.exit(app.exec())

def load_dataframe():
    return stock_handler.get_data()


if __name__ == "__main__":
    main()
    