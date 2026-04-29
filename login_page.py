from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QMessageBox

import os
import json

def load_users():
    path = os.path.join(os.path.dirname(__file__), 'users.json')
    if  not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Username: "))   
        layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password: "))
        layout.addWidget(self.password_input)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def try_login(self):
        users = load_users()
        user = users.get(self.username_input.text())
        if user and user["password"] == self.password_input.text():
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            self.username_input.clear()
            self.password_input.clear()