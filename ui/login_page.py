import os

from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from core import user_manager
from ui.register_page import RegisterDialog
from ui.theme import get_tokens

_SYMBOL_PATH = os.path.join(os.path.dirname(__file__), 'logo', 'logo-symbol.svg')


def _svg_pixmap(size: int) -> QPixmap:
    renderer = QSvgRenderer(_SYMBOL_PATH)
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    renderer.render(p)
    p.end()
    return px


def _build_style(t: dict) -> str:
    return f"""
        QDialog {{
            background: {t['base']};
        }}
        QFrame#card {{
            background: {t['window']};
            border-radius: 14px;
            border: 1px solid {t['separator']};
        }}
        QLabel#app_name {{
            color: {t['text']};
            font-size: {t['font_name']};
            font-weight: bold;
        }}
        QLabel#app_sub {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
            letter-spacing: 1px;
        }}
        QFrame#sep {{
            background: {t['separator']};
            border: none;
            min-height: 1px;
            max-height: 1px;
        }}
        QLabel#field_lbl {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
            font-weight: bold;
        }}
        QLineEdit {{
            background: {t['base']};
            color: {t['text']};
            border: 1px solid {t['separator']};
            border-radius: 7px;
            padding: 0px 14px;
            font-size: {t['font_title']};
            selection-background-color: {t['highlight']};
        }}
        QLineEdit:focus {{
            border-color: {t['highlight']};
        }}
        QPushButton#btn_login {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 7px;
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QPushButton#btn_login:hover {{
            background: #3a92ea;
        }}
        QPushButton#btn_login:pressed {{
            background: #1a6fc0;
        }}
        QLabel#footer_text {{
            color: {t['label_secondary']};
            font-size: {t['font_body']};
        }}
        QPushButton#btn_register {{
            background: transparent;
            color: {t['highlight']};
            border: none;
            font-size: {t['font_body']};
            font-weight: bold;
            padding: 0px 2px;
        }}
        QPushButton#btn_register:hover {{
            color: #3a92ea;
        }}
    """


def _sep():
    f = QFrame()
    f.setObjectName("sep")
    return f


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Viewer")
        self.setFixedSize(440, 540)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(_build_style(get_tokens("dark")))
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(48, 38, 48, 36)
        layout.setSpacing(0)

        # ── Logo / branding ───────────────────────────────────────────────
        icon_lbl = QLabel()
        icon_lbl.setPixmap(_svg_pixmap(72))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name_lbl = QLabel("Stock Viewer")
        name_lbl.setObjectName("app_name")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_lbl = QLabel("PORTFOLIO  ·  ANALYSIS  ·  PREDICTION")
        sub_lbl.setObjectName("app_sub")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_lbl)
        layout.addSpacing(6)
        layout.addWidget(name_lbl)
        layout.addSpacing(6)
        layout.addWidget(sub_lbl)
        layout.addSpacing(28)
        layout.addWidget(_sep())
        layout.addSpacing(26)

        # ── Username ──────────────────────────────────────────────────────
        user_lbl = QLabel("USERNAME")
        user_lbl.setObjectName("field_lbl")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(42)
        self.username_input.returnPressed.connect(self._focus_password)

        layout.addWidget(user_lbl)
        layout.addSpacing(7)
        layout.addWidget(self.username_input)
        layout.addSpacing(18)

        # ── Password ──────────────────────────────────────────────────────
        pass_lbl = QLabel("PASSWORD")
        pass_lbl.setObjectName("field_lbl")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(42)
        self.password_input.returnPressed.connect(self.try_login)

        layout.addWidget(pass_lbl)
        layout.addSpacing(7)
        layout.addWidget(self.password_input)
        layout.addSpacing(26)

        # ── Sign in button ────────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setObjectName("btn_login")
        self.login_btn.setFixedHeight(44)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.try_login)

        layout.addWidget(self.login_btn)
        layout.addSpacing(26)
        layout.addWidget(_sep())
        layout.addSpacing(18)

        # ── Register footer ───────────────────────────────────────────────
        footer_row = QHBoxLayout()
        footer_row.setSpacing(4)
        footer_text = QLabel("Don't have an account?")
        footer_text.setObjectName("footer_text")
        reg_btn = QPushButton("Register")
        reg_btn.setObjectName("btn_register")
        reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reg_btn.clicked.connect(self.create_new_user)

        footer_row.addStretch()
        footer_row.addWidget(footer_text)
        footer_row.addWidget(reg_btn)
        footer_row.addStretch()
        layout.addLayout(footer_row)

        outer.addWidget(card)

    def _focus_password(self):
        self.password_input.setFocus()

    def try_login(self):
        users = user_manager.load_users()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        user = users.get(username)
        if user and user_manager.verify_password(user["password"], password):
            if not user["password"].startswith("pbkdf2sha256:"):
                user["password"] = user_manager.hash_password(password)
                user_manager.save_user_profile(username, user)
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            self.password_input.clear()
            self.password_input.setFocus()

    def create_new_user(self):
        RegisterDialog().exec()
