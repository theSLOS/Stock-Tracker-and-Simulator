import os
import sys

from PyQt6.QtWidgets import QApplication, QDialog

from ui.login_page import LoginDialog
from ui.main_window import MainWindow, apply_dark_theme
from core import caching, user_manager


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)

    print("startingWindow")
    dialog = LoginDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        print("Login failed or cancelled. Exiting application.")
        sys.exit(0)

    username = dialog.username_input.text()
    user_profile = user_manager.get_user_profile(username)
    print(f"Login successful for user: {username}")

    user_dir = os.path.join(os.path.dirname(__file__), 'Users', username)
    user_csv_path = os.path.join(user_dir, 'csvFiles')
    user_cache_path = os.path.join(user_dir, 'cache')
    os.makedirs(user_csv_path, exist_ok=True)

    cache = caching.CacheManager(user_cache_path)
    window = MainWindow(cache, user_csv_path, user_profile)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
