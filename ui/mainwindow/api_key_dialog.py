from PyQt6.QtWidgets import (
    QDialog, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QLabel, QFrame,
)
from PyQt6.QtCore import Qt

from core import key_manager
from ui.theme import get_tokens

_KEY_INFO = {
    "ANTHROPIC_API_KEY": {
        "icon": "✦",
        "title": "Anthropic API Key",
        "description": "Required for AI stock analysis powered by Claude.\nGet your key at console.anthropic.com.",
    },
    "FINNHUB_API_KEY": {
        "icon": "⬡",
        "title": "Finnhub API Key",
        "description": "Required for insider trading data.\nGet your free key at finnhub.io.",
    },
}

_DEFAULT_INFO = {
    "icon": "⚿",
    "title": "API Key",
    "description": "Enter your API key below.",
}


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
        QLabel#dialog_icon {{
            color: {t['highlight']};
            font-size: 36px;
            font-weight: bold;
        }}
        QLabel#dialog_title {{
            color: {t['text']};
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QLabel#dialog_desc {{
            color: {t['label_secondary']};
            font-size: {t['font_body']};
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
        QPushButton#btn_save {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 7px;
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QPushButton#btn_save:hover {{
            background: #3a92ea;
        }}
        QPushButton#btn_save:pressed {{
            background: #1a6fc0;
        }}
        QPushButton#btn_cancel {{
            background: transparent;
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-radius: 7px;
            font-size: {t['font_heading']};
        }}
        QPushButton#btn_cancel:hover {{
            color: {t['text']};
            border-color: {t['text']};
        }}
        QPushButton#btn_toggle {{
            background: transparent;
            color: {t['label_secondary']};
            border: none;
            font-size: {t['font_small']};
            padding: 0px 6px;
        }}
        QPushButton#btn_toggle:hover {{
            color: {t['text']};
        }}
    """


class ApiKeyDialog(QDialog):
    """Card-style dialog for entering/updating a single API key."""

    def __init__(self, key_name: str, username: str, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._key_name = key_name
        self._username = username
        t = get_tokens(theme)
        info = _KEY_INFO.get(key_name, _DEFAULT_INFO)

        self.setWindowTitle(info["title"])
        self.setFixedWidth(460)
        self.setStyleSheet(_build_style(t))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(0)

        # Icon + title
        icon_lbl = QLabel(info["icon"])
        icon_lbl.setObjectName("dialog_icon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_lbl)
        card_layout.addSpacing(8)

        title_lbl = QLabel(info["title"])
        title_lbl.setObjectName("dialog_title")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)
        card_layout.addSpacing(6)

        desc_lbl = QLabel(info["description"])
        desc_lbl.setObjectName("dialog_desc")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        card_layout.addWidget(desc_lbl)
        card_layout.addSpacing(20)

        sep = QFrame()
        sep.setObjectName("sep")
        card_layout.addWidget(sep)
        card_layout.addSpacing(20)

        # Key input
        field_lbl = QLabel("API KEY")
        field_lbl.setObjectName("field_lbl")
        card_layout.addWidget(field_lbl)
        card_layout.addSpacing(4)

        input_row = QHBoxLayout()
        input_row.setSpacing(4)
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setFixedHeight(42)
        self._key_input.setPlaceholderText("Paste your key here...")
        existing = key_manager.get_all_keys(username).get(key_name, "")
        if existing:
            self._key_input.setText(existing)

        self._toggle_btn = QPushButton("Show")
        self._toggle_btn.setObjectName("btn_toggle")
        self._toggle_btn.setFixedHeight(42)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.toggled.connect(self._toggle_visibility)

        input_row.addWidget(self._key_input)
        input_row.addWidget(self._toggle_btn)
        card_layout.addLayout(input_row)
        card_layout.addSpacing(24)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setFixedHeight(42)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Key")
        save_btn.setObjectName("btn_save")
        save_btn.setFixedHeight(42)
        save_btn.clicked.connect(self._save)
        self._key_input.returnPressed.connect(self._save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        card_layout.addLayout(btn_row)

        outer.addWidget(card)
        self.adjustSize()

    def _toggle_visibility(self, checked: bool):
        self._key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._toggle_btn.setText("Hide" if checked else "Show")

    def _save(self):
        value = self._key_input.text().strip()
        if not value:
            self._key_input.setFocus()
            return
        key_manager.set_key(self._username, self._key_name, value)
        self.accept()

    def get_key(self) -> str:
        return self._key_input.text().strip()
