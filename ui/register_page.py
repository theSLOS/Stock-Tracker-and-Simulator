from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt

from core import user_manager
from ui.theme import get_tokens


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
        QLabel#dialog_title {{
            color: {t['text']};
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QLabel#dialog_sub {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
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
        QPushButton#btn_register {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 7px;
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QPushButton#btn_register:hover {{
            background: #3a92ea;
        }}
        QPushButton#btn_register:pressed {{
            background: #1a6fc0;
        }}
        QPushButton#btn_cancel {{
            background: {t['button']};
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-radius: 7px;
            font-size: {t['font_title']};
        }}
        QPushButton#btn_cancel:hover {{
            color: {t['text']};
            border-color: {t['text']};
        }}
    """


def _sep():
    f = QFrame()
    f.setObjectName("sep")
    return f


def _field(label_text: str, placeholder: str, password: bool = False):
    lbl = QLabel(label_text)
    lbl.setObjectName("field_lbl")
    inp = QLineEdit()
    inp.setPlaceholderText(placeholder)
    inp.setFixedHeight(42)
    if password:
        inp.setEchoMode(QLineEdit.EchoMode.Password)
    return lbl, inp


class RegisterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Account")
        self.setFixedSize(440, 560)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(_build_style(get_tokens("dark")))
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(48, 36, 48, 32)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        title_lbl = QLabel("Create Account")
        title_lbl.setObjectName("dialog_title")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_lbl = QLabel("Join Stock Viewer to start tracking your portfolio")
        sub_lbl.setObjectName("dialog_sub")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)

        layout.addWidget(title_lbl)
        layout.addSpacing(8)
        layout.addWidget(sub_lbl)
        layout.addSpacing(24)
        layout.addWidget(_sep())
        layout.addSpacing(24)

        # ── Fields ────────────────────────────────────────────────────────
        user_lbl, self.username_input = _field("USERNAME", "Choose a username")
        pass_lbl, self.password_input = _field("PASSWORD", "Choose a password", password=True)
        conf_lbl, self.confirm_password_input = _field("CONFIRM PASSWORD", "Repeat your password", password=True)

        self.confirm_password_input.returnPressed.connect(self.register_user)

        layout.addWidget(user_lbl)
        layout.addSpacing(7)
        layout.addWidget(self.username_input)
        layout.addSpacing(16)
        layout.addWidget(pass_lbl)
        layout.addSpacing(7)
        layout.addWidget(self.password_input)
        layout.addSpacing(16)
        layout.addWidget(conf_lbl)
        layout.addSpacing(7)
        layout.addWidget(self.confirm_password_input)
        layout.addSpacing(26)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        register_btn = QPushButton("Create Account")
        register_btn.setObjectName("btn_register")
        register_btn.setFixedHeight(44)
        register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        register_btn.clicked.connect(self.register_user)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(register_btn)
        layout.addLayout(btn_row)

        outer.addWidget(card)

    def register_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not username or not password or not confirm_password:
            QMessageBox.warning(self, "Registration Failed", "All fields are required.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Registration Failed", "Passwords do not match.")
            return

        users = user_manager.load_users()

        if username in users:
            QMessageBox.warning(self, "Registration Failed", "Username already exists.")
            return

        user_manager.create_user(username, password)
        QMessageBox.information(self, "Registration Successful", "Account created successfully.")
        self.accept()
