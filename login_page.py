from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QMessageBox


import user_manager
import register_page

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        NewUserBtn = QPushButton("New User")
        NewUserBtn.clicked.connect(self.create_new_user)
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
        layout.addWidget(NewUserBtn)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def try_login(self):
        users = user_manager.load_users()
        user = users.get(self.username_input.text())
        if user and user["password"] == self.password_input.text():
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            self.username_input.clear()
            self.password_input.clear()

    def create_new_user(self):
        register_page.RegisterDialog().exec()