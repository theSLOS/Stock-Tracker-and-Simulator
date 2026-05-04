import os
import sys
import caching
import QWindowModel
import login_page
from PyQt6.QtWidgets import QApplication, QDialog

import user_manager


def main():
    app = QApplication(sys.argv)
    QWindowModel.apply_dark_theme(app)

    print("startingWindow")
    dialog = login_page.LoginDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        print("Login failed or cancelled. Exiting application.")
        sys.exit(0)

    username = dialog.username_input.text()
    user_profile = user_manager.get_user_profile(username)
    print(f"Login successful for user: {username}")

    user_dir = os.path.join(os.path.dirname(__file__), 'Users')
    user_dir = os.path.join(user_dir,username)
    user_csv_path = os.path.join(user_dir, 'csvFiles')
    user_cache_path = os.path.join(user_dir, 'cache')
    os.makedirs(user_csv_path, exist_ok=True)

    cache = caching.CacheManager(user_cache_path)
    window = QWindowModel.MainWindow(cache, user_csv_path, user_profile)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    