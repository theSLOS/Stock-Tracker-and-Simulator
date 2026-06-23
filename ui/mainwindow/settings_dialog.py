from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDialogButtonBox,
    QGroupBox, QRadioButton, QButtonGroup, QHBoxLayout, QMessageBox
)
from core import user_manager


class UserSettingsDialog(QDialog):
    def __init__(self, user_profile, parent=None):
        super().__init__(parent)
        self.user_profile = user_profile
        self.username = user_profile["username"]
        self.setWindowTitle("User Settings")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Profile
        profile_group = QGroupBox("Profile")
        profile_form = QFormLayout(profile_group)
        self.email_input = QLineEdit(self.user_profile.get("email", ""))
        self.email_input.setPlaceholderText("Optional")
        self.phone_input = QLineEdit(self.user_profile.get("phone", ""))
        self.phone_input.setPlaceholderText("Optional")
        profile_form.addRow("Email:", self.email_input)
        profile_form.addRow("Phone:", self.phone_input)
        layout.addWidget(profile_group)

        # Appearance
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QHBoxLayout(appearance_group)
        self.dark_radio = QRadioButton("Dark")
        self.light_radio = QRadioButton("Light")
        btn_group = QButtonGroup(self)
        btn_group.addButton(self.dark_radio)
        btn_group.addButton(self.light_radio)
        current_theme = self.user_profile.get("preferences", {}).get("theme", "dark")
        (self.light_radio if current_theme == "light" else self.dark_radio).setChecked(True)
        appearance_layout.addWidget(QLabel("Theme:"))
        appearance_layout.addWidget(self.dark_radio)
        appearance_layout.addWidget(self.light_radio)
        appearance_layout.addStretch()
        layout.addWidget(appearance_group)

        # Password
        password_group = QGroupBox("Change Password")
        password_group.setToolTip("Leave blank to keep current password")
        password_form = QFormLayout(password_group)
        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        password_form.addRow("Current Password:", self.current_pw)
        password_form.addRow("New Password:", self.new_pw)
        password_form.addRow("Confirm New Password:", self.confirm_pw)
        layout.addWidget(password_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        profile = dict(self.user_profile)
        profile["email"] = self.email_input.text().strip()
        profile["phone"] = self.phone_input.text().strip()
        profile.setdefault("preferences", {})["theme"] = "light" if self.light_radio.isChecked() else "dark"

        cur = self.current_pw.text()
        new = self.new_pw.text()
        confirm = self.confirm_pw.text()
        if cur or new or confirm:
            if not user_manager.verify_password(profile.get("password", ""), cur):
                QMessageBox.warning(self, "Error", "Current password is incorrect.")
                return
            if not new:
                QMessageBox.warning(self, "Error", "New password cannot be empty.")
                return
            if new != confirm:
                QMessageBox.warning(self, "Error", "New passwords do not match.")
                return
            profile["password"] = user_manager.hash_password(new)

        user_manager.save_user_profile(self.username, profile)
        self.user_profile.update(profile)
        self.accept()
