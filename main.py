import pandas as pd
from dotenv import load_dotenv
import os
import pandasModel
import stock_handler
import QWindowModel
import login_page


import sys
import pandas as pd
import caching

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QPalette, QColor

load_dotenv()
path = os.getenv('CSV_PATH')

def main():
    cache = caching.CacheManager(os.getenv('CACHE_PATH', 'cache/main_cache'))   
    app = QApplication(sys.argv)
    QWindowModel.apply_dark_theme(app)

    print("startingWindow")
    dialog = login_page.LoginDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        print("Login failed or cancelled. Exiting application.")
        sys.exit(0)
    username = dialog.username_input.text()
    print(f"Login successful for user: {username}")

    user_path = os.path.join(path, username)
    os.makedirs(user_path, exist_ok=True)

    cache_base = os.path.join(os.getenv('CACHE_PATH', 'cache/main_cache'))
    user_cache_path = f"{cache_base}_{username}"
    cache = caching.CacheManager(user_cache_path)

    window = QWindowModel.MainWindow(cache, user_path, username)
    window.show()

    sys.exit(app.exec())

def load_dataframe():
    return stock_handler.get_data()


if __name__ == "__main__":
    main()
    