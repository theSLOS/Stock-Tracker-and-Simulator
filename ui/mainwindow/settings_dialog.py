import os
import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QMessageBox, QPushButton, QFrame,
    QStackedWidget, QWidget, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap, QImage

from core import user_manager, key_manager
from ui.theme import get_tokens


_KEYS = [
    ("ANTHROPIC_API_KEY", "✦", "Anthropic API Key"),
    ("FINNHUB_API_KEY",   "⬡", "Finnhub API Key"),
]

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,20}$')


class _AvatarPreview(QWidget):
    SIZE = 60

    def __init__(self, username: str, avatar_path: str | None = None, parent=None):
        super().__init__(parent)
        self._initial = username[0].upper() if username else "?"
        self.setFixedSize(self.SIZE, self.SIZE)
        self._avatar_path = avatar_path
        self._pixmap = self._load_pixmap()

    def _load_pixmap(self):
        if self._avatar_path and os.path.exists(self._avatar_path):
            return QPixmap(self._avatar_path).scaled(
                self.SIZE, self.SIZE,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        return None

    def refresh(self, avatar_path: str | None = None):
        if avatar_path is not None:
            self._avatar_path = avatar_path
        self._pixmap = self._load_pixmap()
        self.update()

    def set_initial(self, username: str):
        self._initial = username[0].upper() if username else "?"
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._pixmap and not self._pixmap.isNull():
            clip = QPainterPath()
            clip.addEllipse(0.0, 0.0, float(self.SIZE), float(self.SIZE))
            p.setClipPath(clip)
            p.drawPixmap(0, 0, self.SIZE, self.SIZE, self._pixmap)
        else:
            p.setBrush(QColor("#2a82da"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(0, 0, self.SIZE, self.SIZE)
            font = QFont()
            font.setPixelSize(int(self.SIZE * 0.42))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#ffffff"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initial)


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
        QFrame#sidebar {{
            background: {t['alternate_base']};
            border-top-left-radius: 14px;
            border-bottom-left-radius: 14px;
            border-right: 1px solid {t['separator']};
        }}
        QLabel#sidebar_header {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QPushButton#nav_btn {{
            background: transparent;
            color: {t['label_secondary']};
            border: none;
            text-align: left;
            padding: 10px 16px;
            font-size: {t['font_body']};
            border-radius: 8px;
            margin: 1px 8px;
        }}
        QPushButton#nav_btn:checked {{
            background: {t['highlight']};
            color: #ffffff;
        }}
        QPushButton#nav_btn:hover:!checked {{
            background: {t['separator']};
            color: {t['text']};
        }}
        QLabel#section_title {{
            color: {t['text']};
            font-size: {t['font_heading']};
            font-weight: bold;
        }}
        QLabel#field_lbl {{
            color: {t['label_secondary']};
            font-size: {t['font_small']};
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QLabel#username_chip {{
            background: {t['alternate_base']};
            color: {t['label_muted']};
            border-radius: 10px;
            padding: 4px 14px;
            font-size: {t['font_body']};
        }}
        QLineEdit {{
            background: {t['base']};
            color: {t['text']};
            border: 1px solid {t['separator']};
            border-radius: 7px;
            padding: 0px 12px;
            font-size: {t['font_title']};
            min-height: 38px;
        }}
        QLineEdit:focus {{
            border-color: {t['highlight']};
        }}
        QPushButton#btn_theme_l {{
            background: {t['window']};
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-right: none;
            border-top-left-radius: 7px;
            border-bottom-left-radius: 7px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 0px;
            padding: 8px 24px;
            font-size: {t['font_body']};
        }}
        QPushButton#btn_theme_r {{
            background: {t['window']};
            color: {t['label_secondary']};
            border: 1px solid {t['separator']};
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            padding: 8px 24px;
            font-size: {t['font_body']};
        }}
        QPushButton#btn_theme_l:checked, QPushButton#btn_theme_r:checked {{
            background: {t['highlight']};
            color: #ffffff;
            border-color: {t['highlight']};
        }}
        QPushButton#btn_theme_l:hover:!checked, QPushButton#btn_theme_r:hover:!checked {{
            background: {t['separator']};
            color: {t['text']};
        }}
        QPushButton#btn_apply_username {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 6px 14px;
            font-size: {t['font_small']};
            font-weight: bold;
        }}
        QPushButton#btn_apply_username:hover {{
            background: {t['highlight']}cc;
        }}
        QPushButton#btn_change_photo {{
            background: transparent;
            color: {t['highlight']};
            border: 1px solid {t['highlight']};
            border-radius: 6px;
            padding: 5px 12px;
            font-size: {t['font_small']};
        }}
        QPushButton#btn_change_photo:hover {{
            background: {t['highlight']}22;
        }}
        QPushButton#btn_save_pw {{
            background: {t['highlight']};
            color: #ffffff;
            border: none;
            border-radius: 7px;
            padding: 9px 20px;
            font-size: {t['font_body']};
            font-weight: bold;
            min-width: 140px;
        }}
        QPushButton#btn_save_pw:hover {{
            background: {t['highlight']}cc;
        }}
        QPushButton#btn_key_update {{
            background: transparent;
            color: {t['highlight']};
            border: 1px solid {t['highlight']};
            border-radius: 6px;
            padding: 5px 14px;
            font-size: {t['font_small']};
            min-width: 60px;
        }}
        QPushButton#btn_key_update:hover {{
            background: {t['highlight']}22;
        }}
        QPushButton#btn_key_delete {{
            background: transparent;
            color: {t['sell_color']};
            border: 1px solid {t['sell_color']};
            border-radius: 6px;
            padding: 5px 14px;
            font-size: {t['font_small']};
            min-width: 60px;
        }}
        QPushButton#btn_key_delete:hover {{
            background: {t['sell_color']}22;
        }}
        QFrame#key_row {{
            background: {t['alternate_base']};
            border-radius: 10px;
            border: 1px solid {t['separator']};
        }}
        QFrame#sep_h {{
            background: {t['separator']};
            min-height: 1px;
            max-height: 1px;
            border: none;
        }}
        QDialogButtonBox QPushButton {{
            min-width: 80px;
            min-height: 34px;
            border-radius: 7px;
            font-size: {t['font_body']};
            background: {t['button']};
            color: {t['button_text']};
            border: 1px solid {t['separator']};
            padding: 6px 14px;
        }}
        QDialogButtonBox QPushButton:hover {{
            background: {t['separator']};
        }}
    """


class UserSettingsDialog(QDialog):
    username_changed = pyqtSignal(str)
    avatar_changed   = pyqtSignal()

    def __init__(self, user_profile: dict, theme: str = "dark", parent=None):
        super().__init__(parent)
        self.user_profile = user_profile
        self.username = user_profile["username"]
        self._theme = theme
        self._tokens = get_tokens(theme)
        self.setWindowTitle("Settings")
        self.setFixedSize(680, 500)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        card_layout.addWidget(self._make_sidebar())
        card_layout.addWidget(self._make_content_area())

        outer.addWidget(card)
        self.setStyleSheet(_build_style(self._tokens))

    def _make_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(155)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 16)
        layout.setSpacing(0)

        header = QLabel("SETTINGS")
        header.setObjectName("sidebar_header")
        header.setContentsMargins(24, 0, 0, 0)
        layout.addWidget(header)

        sep = QFrame()
        sep.setObjectName("sep_h")
        layout.addSpacing(12)
        layout.addWidget(sep)
        layout.addSpacing(8)

        self._nav_btns = []
        for label, idx in [
            ("  👤   Profile",    0),
            ("  🎨   Appearance", 1),
            ("  🔒   Security",   2),
            ("  🔑   API Keys",   3),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            layout.addWidget(btn)
            self._nav_btns.append(btn)

        layout.addStretch()
        return sidebar

    def _make_content_area(self) -> QWidget:
        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_profile_page())
        self._stack.addWidget(self._make_appearance_page())
        self._stack.addWidget(self._make_security_page())
        self._stack.addWidget(self._make_keys_page())
        layout.addWidget(self._stack)

        layout.addSpacing(16)
        sep = QFrame()
        sep.setObjectName("sep_h")
        layout.addWidget(sep)
        layout.addSpacing(12)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box, alignment=Qt.AlignmentFlag.AlignRight)

        return right

    # ── Pages ──

    def _make_profile_page(self) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Profile")
        title.setObjectName("section_title")
        layout.addWidget(title)
        layout.addSpacing(16)

        # Avatar row
        avatar_row = QHBoxLayout()
        avatar_row.setContentsMargins(0, 0, 0, 0)
        avatar_row.setSpacing(14)
        self._avatar_preview = _AvatarPreview(
            self.username,
            avatar_path=user_manager.get_avatar_path(self.username),
        )
        avatar_row.addWidget(self._avatar_preview)
        change_photo_btn = QPushButton("Change Photo")
        change_photo_btn.setObjectName("btn_change_photo")
        change_photo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_photo_btn.clicked.connect(self._pick_avatar)
        photo_col = QVBoxLayout()
        photo_col.setSpacing(4)
        photo_col.addWidget(change_photo_btn)
        photo_hint = QLabel("JPG, PNG, WEBP")
        photo_hint.setStyleSheet(f"color: {t['label_muted']}; font-size: {t['font_micro']};")
        photo_col.addWidget(photo_hint)
        photo_col.addStretch()
        avatar_row.addLayout(photo_col)
        avatar_row.addStretch()
        layout.addLayout(avatar_row)
        layout.addSpacing(16)

        # Username row
        uname_lbl = QLabel("USERNAME")
        uname_lbl.setObjectName("field_lbl")
        layout.addWidget(uname_lbl)
        layout.addSpacing(4)
        uname_row = QHBoxLayout()
        uname_row.setSpacing(8)
        self._username_input = QLineEdit(self.username)
        uname_row.addWidget(self._username_input)
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("btn_apply_username")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._change_username)
        uname_row.addWidget(apply_btn)
        layout.addLayout(uname_row)
        layout.addSpacing(4)
        self._uname_status = QLabel("")
        self._uname_status.setObjectName("field_lbl")
        layout.addWidget(self._uname_status)
        layout.addSpacing(12)

        email_lbl = QLabel("EMAIL")
        email_lbl.setObjectName("field_lbl")
        layout.addWidget(email_lbl)
        layout.addSpacing(4)
        self.email_input = QLineEdit(self.user_profile.get("email", ""))
        self.email_input.setPlaceholderText("Optional")
        layout.addWidget(self.email_input)
        layout.addSpacing(14)

        phone_lbl = QLabel("PHONE")
        phone_lbl.setObjectName("field_lbl")
        layout.addWidget(phone_lbl)
        layout.addSpacing(4)
        self.phone_input = QLineEdit(self.user_profile.get("phone", ""))
        self.phone_input.setPlaceholderText("Optional")
        layout.addWidget(self.phone_input)

        layout.addStretch()
        return page

    def _make_appearance_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Appearance")
        title.setObjectName("section_title")
        layout.addWidget(title)
        layout.addSpacing(24)

        theme_lbl = QLabel("THEME")
        theme_lbl.setObjectName("field_lbl")
        layout.addWidget(theme_lbl)
        layout.addSpacing(10)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(0)
        toggle_row.setContentsMargins(0, 0, 0, 0)

        self._dark_btn = QPushButton("Dark")
        self._dark_btn.setObjectName("btn_theme_l")
        self._dark_btn.setCheckable(True)

        self._light_btn = QPushButton("Light")
        self._light_btn.setObjectName("btn_theme_r")
        self._light_btn.setCheckable(True)

        current = self.user_profile.get("preferences", {}).get("theme", "dark")
        self._dark_btn.setChecked(current == "dark")
        self._light_btn.setChecked(current == "light")

        self._dark_btn.clicked.connect(lambda: self._select_theme("dark"))
        self._light_btn.clicked.connect(lambda: self._select_theme("light"))

        toggle_row.addWidget(self._dark_btn)
        toggle_row.addWidget(self._light_btn)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        layout.addStretch()
        return page

    def _make_security_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Security")
        title.setObjectName("section_title")
        layout.addWidget(title)
        layout.addSpacing(16)

        for attr, label_text in [
            ("current_pw", "CURRENT PASSWORD"),
            ("new_pw",     "NEW PASSWORD"),
            ("confirm_pw", "CONFIRM NEW PASSWORD"),
        ]:
            lbl = QLabel(label_text)
            lbl.setObjectName("field_lbl")
            layout.addWidget(lbl)
            layout.addSpacing(4)
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            setattr(self, attr, field)
            layout.addWidget(field)
            layout.addSpacing(12)

        pw_btn_row = QHBoxLayout()
        self._pw_status = QLabel("")
        self._pw_status.setObjectName("field_lbl")
        pw_btn_row.addWidget(self._pw_status)
        pw_btn_row.addStretch()
        change_btn = QPushButton("Change Password")
        change_btn.setObjectName("btn_save_pw")
        change_btn.clicked.connect(self._change_password)
        pw_btn_row.addWidget(change_btn)
        layout.addLayout(pw_btn_row)

        layout.addStretch()
        return page

    def _make_keys_page(self) -> QWidget:
        t = self._tokens
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("API Keys")
        title.setObjectName("section_title")
        layout.addWidget(title)
        layout.addSpacing(16)

        self._key_rows: dict[str, dict] = {}
        existing = key_manager.get_all_keys(self.username)

        for key_name, icon, display_name in _KEYS:
            row_frame = QFrame()
            row_frame.setObjectName("key_row")
            row_inner = QHBoxLayout(row_frame)
            row_inner.setContentsMargins(14, 12, 14, 12)
            row_inner.setSpacing(10)

            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"color: {t['highlight']}; font-size: 18px;")
            row_inner.addWidget(icon_lbl)

            name_lbl = QLabel(display_name)
            name_lbl.setStyleSheet(f"color: {t['text']}; font-size: {t['font_body']};")
            row_inner.addWidget(name_lbl)
            row_inner.addStretch()

            has_key = bool(existing.get(key_name))
            status_lbl = QLabel("✓ Set" if has_key else "✗ Not set")
            status_lbl.setStyleSheet(self._key_status_style(has_key))
            row_inner.addWidget(status_lbl)

            update_btn = QPushButton("Update")
            update_btn.setObjectName("btn_key_update")
            update_btn.clicked.connect(lambda _, kn=key_name: self._update_key(kn))
            row_inner.addWidget(update_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("btn_key_delete")
            delete_btn.setVisible(has_key)
            delete_btn.clicked.connect(lambda _, kn=key_name: self._delete_key(kn))
            row_inner.addWidget(delete_btn)

            self._key_rows[key_name] = {"status_lbl": status_lbl, "delete_btn": delete_btn}
            layout.addWidget(row_frame)
            layout.addSpacing(10)

        layout.addStretch()
        return page

    # ── Helpers ──

    def _key_status_style(self, has_key: bool) -> str:
        t = self._tokens
        color = t["buy_color"] if has_key else t["sell_color"]
        return f"color: {color}; font-size: {t['font_small']}; font-weight: bold;"

    def _switch_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)

    def _select_theme(self, theme: str):
        self._dark_btn.setChecked(theme == "dark")
        self._light_btn.setChecked(theme == "light")

    # ── Actions ──

    def _pick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Photo", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            return
        img = img.scaled(
            256, 256,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Crop to centered 256×256
        x = (img.width() - 256) // 2
        y = (img.height() - 256) // 2
        img = img.copy(x, y, 256, 256)
        dest = user_manager.get_avatar_path(self.username)
        img.save(dest, "PNG")
        self._avatar_preview.refresh(dest)
        self.avatar_changed.emit()

    def _change_username(self):
        t = self._tokens
        new_name = self._username_input.text().strip()
        if not new_name or new_name == self.username:
            return
        if not _USERNAME_RE.match(new_name):
            self._show_uname_status(
                "3–20 chars: letters, numbers, underscore only",
                t["sell_color"],
            )
            return
        try:
            user_manager.rename_user(self.username, new_name)
        except ValueError as e:
            self._show_uname_status(str(e), t["sell_color"])
            return
        self.username = new_name
        self.user_profile["username"] = new_name
        self._avatar_preview.set_initial(new_name)
        self._show_uname_status("Username changed", t["buy_color"])
        self.username_changed.emit(new_name)

    def _show_uname_status(self, msg: str, color: str):
        t = self._tokens
        self._uname_status.setText(msg)
        self._uname_status.setStyleSheet(
            f"color: {color}; font-size: {t['font_small']}; font-weight: bold;"
        )
        QTimer.singleShot(3000, lambda: (
            self._uname_status.setText(""),
            self._uname_status.setStyleSheet(""),
        ))

    def _change_password(self):
        cur = self.current_pw.text()
        new = self.new_pw.text()
        confirm = self.confirm_pw.text()
        if not cur or not new or not confirm:
            QMessageBox.warning(self, "Error", "Please fill in all password fields.")
            return
        if not user_manager.verify_password(self.user_profile.get("password", ""), cur):
            QMessageBox.warning(self, "Error", "Current password is incorrect.")
            return
        if new != confirm:
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            return
        profile = dict(self.user_profile)
        profile["password"] = user_manager.hash_password(new)
        user_manager.save_user_profile(self.username, profile)
        self.user_profile.update(profile)
        self.current_pw.clear()
        self.new_pw.clear()
        self.confirm_pw.clear()
        t = self._tokens
        self._pw_status.setText("✓ Password changed")
        self._pw_status.setStyleSheet(
            f"color: {t['buy_color']}; font-size: {t['font_small']}; font-weight: bold;"
        )
        QTimer.singleShot(3000, lambda: (
            self._pw_status.setText(""),
            self._pw_status.setStyleSheet(""),
        ))

    def _update_key(self, key_name: str):
        from .api_key_dialog import ApiKeyDialog
        dlg = ApiKeyDialog(key_name, self.username, self._theme, parent=self)
        if dlg.exec():
            self._refresh_key_row(key_name)

    def _delete_key(self, key_name: str):
        key_manager.delete_key(self.username, key_name)
        self._refresh_key_row(key_name)

    def _refresh_key_row(self, key_name: str):
        has_key = bool(key_manager.get_all_keys(self.username).get(key_name))
        row = self._key_rows[key_name]
        row["status_lbl"].setText("✓ Set" if has_key else "✗ Not set")
        row["status_lbl"].setStyleSheet(self._key_status_style(has_key))
        row["delete_btn"].setVisible(has_key)

    def _save(self):
        profile = dict(self.user_profile)
        profile["email"] = self.email_input.text().strip()
        profile["phone"] = self.phone_input.text().strip()
        profile.setdefault("preferences", {})["theme"] = (
            "light" if self._light_btn.isChecked() else "dark"
        )
        user_manager.save_user_profile(self.username, profile)
        self.user_profile.update(profile)
        self.accept()
