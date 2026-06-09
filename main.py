import os
import sys
import argparse

from PyQt6.QtWidgets import QApplication, QDialog

from ui.login_page import LoginDialog
from ui.mainwindow.main_window import MainWindow, apply_dark_theme, apply_light_theme
from core import caching, user_manager
import os; print(os.getenv("ANTHROPIC_API_KEY"))

def _auto_login(username, password):
    users = user_manager.load_users()
    profile = users.get(username)
    if profile and profile.get("password") == password:
        return profile
    return None


def main():
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--user", "-u", default=None)
    parser.add_argument("--password", "-p", default=None)
    args, remaining = parser.parse_known_args()

    app = QApplication([sys.argv[0]] + remaining)
    apply_dark_theme(app)

    username = None
    user_profile = None

    if args.user and args.password:
        user_profile = _auto_login(args.user, args.password)
        if user_profile:
            username = args.user
            print(f"Auto-login successful for user: {username}")
        else:
            print("Auto-login failed: invalid username or password.")

    if user_profile is None:
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

    if user_profile.get("preferences", {}).get("theme") == "light":
        apply_light_theme(app)

    cache = caching.CacheManager(user_cache_path)
    window = MainWindow(cache, user_csv_path, user_profile)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
