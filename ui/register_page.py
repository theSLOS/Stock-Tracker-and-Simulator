from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QMessageBox

from core import user_manager


class RegisterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Register")
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.confirm_password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.register_user)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Username: "))
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password: "))
        layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Confirm Password: "))
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def register_user(self):
        username = self.username_input.text()
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
        QMessageBox.information(self, "Registration Successful", "User registered successfully.")
        self.accept()
