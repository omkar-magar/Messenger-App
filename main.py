from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFrame, QTextEdit, QListWidget, QStyle
from PySide6.QtCore import Qt, Signal, QThread
import sys
import asyncio
import websockets
import re
import json
import requests

class LoginWorker(QThread):
    """Handles HTTP authentication requests to the Django backend."""
    finished = Signal(bool, str, str)  # success, token/error_message, username

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        # Django DRF default token endpoint (adjust URL as needed)
        url = "http://localhost:8000/api-token-auth/"
        try:
            response = requests.post(
                url, 
                data={"username": self.username, "password": self.password},
                timeout=5
            )
            if response.status_code == 200:
                token = response.json().get("token")
                self.finished.emit(True, token, self.username)
            else:
                error_msg = response.json().get("non_field_errors", ["Invalid credentials"])[0]
                self.finished.emit(False, error_msg, "")
        except Exception as e:
            self.finished.emit(False, f"Connection failed: {str(e)}", "")

class RegisterWorker(QThread):
    """Handles HTTP registration requests to the Django backend."""
    finished = Signal(bool, str)  # success, message

    def __init__(self, username, password, email=""):
        super().__init__()
        self.username = username
        self.password = password
        self.email = email

    def run(self):
        url = "http://localhost:8000/api/register/" # Adjust based on your urls.py
        try:
            response = requests.post(
                url,
                json={"username": self.username, "password": self.password, "email": self.email},
                timeout=5
            )
            if response.status_code == 201:
                self.finished.emit(True, "Registration successful! Please log in.")
            else:
                # Extract error message from Django's response
                errors = response.json()
                error_text = str(errors.get("username", errors.get("password", ["Registration failed"])[0]))
                self.finished.emit(False, error_text)
        except Exception as e:
            self.finished.emit(False, f"Connection failed: {str(e)}")

class WebSocketWorker(QThread):
    """Skeleton for the background thread that will talk to server.py"""
    message_received = Signal(str)
    connection_status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop = None
        self.websocket = None
        self.username = ""

    def run(self):
        # Initialize the asyncio loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        uri = "ws://localhost:8765"
        attempt = 0
        max_delay = 30

        while True:
            try:
                self.connection_status_changed.emit("Connecting...")
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    self.connection_status_changed.emit("Connected")
                    attempt = 0  # Reset backoff on successful connection
                    
                    # Send an announcement to the server that we have arrived!
                    join_payload = json.dumps({"type": "join", "username": self.username, "content": "has joined the chat!"})
                    await websocket.send(join_payload)
                    
                    async for message in websocket:
                        self.message_received.emit(message)
            except Exception as e:
                self.websocket = None
                print(f"[ERROR] Connection failed: {e}")  # Added structured logging
                delay = min(1 * (2 ** attempt), max_delay)
                self.connection_status_changed.emit(f"Reconnecting in {delay}s...")
                await asyncio.sleep(delay)
                attempt += 1

    def send_message(self, message):
        # Safely pass the message from the main UI thread to the asyncio event loop thread
        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.send(message), self.loop)

class MainWindow(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.login_page = LoginPage(self)
        self.login_page.login_successful.connect(self.go_to_chat)
        self.chat_page = ChatPage(self)
        
        self.addWidget(self.login_page)
        self.addWidget(self.chat_page)
        
        self.setCurrentWidget(self.login_page)
        self.setWindowTitle("Chat Application")
        self.resize(400, 300)
        self.show()

    def go_to_chat(self, username, token=None):
        self.chat_page.set_username(username)
        self.chat_page.connect_to_server()
        self.setCurrentWidget(self.chat_page)

class LoginPage(QWidget):
    login_successful = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        
        # Label for validation feedback
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #d32f2f; font-size: 11px;")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Eye button for "hold to reveal" password
        self.eye_button = QPushButton("👁")
        self.eye_button.setFixedWidth(30)
        self.eye_button.setFlat(True)
        self.eye_button.setCursor(Qt.PointingHandCursor)
        self.eye_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.eye_button.setStyleSheet("QPushButton { border: none; background: transparent; color: gray; font-size: 14px; }")

        # Embed the eye button inside the password field
        eye_layout = QHBoxLayout(self.password_input)
        eye_layout.setContentsMargins(0, 0, 5, 0)
        eye_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        eye_layout.addWidget(self.eye_button)
        self.password_input.setTextMargins(0, 0, 30, 0) # Prevent text from overlapping icon

        # Connect signals for hold-to-reveal logic
        self.eye_button.pressed.connect(self._reveal_password)
        self.eye_button.released.connect(self._hide_password)
         
        self.login_button = QPushButton("Login")
        self.login_button.setEnabled(False)
        self.login_button.clicked.connect(self.login)

        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.login_button.click)


        # Connect signals to validate in real-time
        self.username_input.textChanged.connect(self.validate_passwords)
        self.password_input.textChanged.connect(self.validate_passwords)

        layout.addWidget(QLabel("Please log in"))
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_button)
        
        # Add a registration link for better UX
        self.register_button = QPushButton("Don't have an account? Register")
        self.register_button.setFlat(True)
        self.register_button.setStyleSheet("color: blue; text-decoration: underline; border: none;")
        self.register_button.clicked.connect(self.register)
        layout.addWidget(self.register_button)

        self.setLayout(layout)
        self.auth_worker = None
        self.reg_worker = None

    def _reveal_password(self) -> None:
        """Show password text when button is held."""
        self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)

    def _hide_password(self) -> None:
        """Hide password text when button is released."""
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def validate_passwords(self):
        username = self.username_input.text()
        password = self.password_input.text()

        # Regex Requirements:
        # ^(?=.*[A-Z])                -> At least one capital letter
        # (?=.*[!@#$%^&*(),.?":{}|<>]) -> At least one special character
        # .{8,}                       -> At least 8 characters long
        password_re = r"^(?=.*[A-Z])(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,}$"
        is_password_valid = bool(re.match(password_re, password))

        if password and not is_password_valid:
            self.error_label.setText("Password: 8+ chars, 1 uppercase, 1 special char.")
        else:
            self.error_label.setText("")

        self.login_button.setEnabled(is_password_valid and len(username) > 0)

    def login(self):
        """Triggered when the user clicks Login."""
        username = self.username_input.text()
        password = self.password_input.text()
        
        # Visual feedback: disable UI while authenticating
        self.login_button.setEnabled(False)
        self.login_button.setText("Authenticating...")
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

        self.auth_worker = LoginWorker(username, password)
        self.auth_worker.finished.connect(self._handle_auth_result)
        self.auth_worker.start()

    def register(self):
        """Triggered when the user clicks Register."""
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Please enter both username and password to register.")
            return

        self.register_button.setEnabled(False)
        self.reg_worker = RegisterWorker(username, password)
        self.reg_worker.finished.connect(self._handle_reg_result)
        self.reg_worker.start()

    def _handle_reg_result(self, success, message):
        self.error_label.setText(message)
        self.error_label.setStyleSheet(f"color: {'green' if success else 'red'}; font-size: 11px;")
        self.register_button.setEnabled(True)

    def _handle_auth_result(self, success, result, username):
        if success:
            self.login_successful.emit(username)
        else:
            self.error_label.setText(result)
            self.login_button.setEnabled(True)
            self.login_button.setText("Login")
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)

class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Main Vertical Layout
        main_layout = QVBoxLayout()
        
        # 1.5 Status Label at the top
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # 2. Chat History Area (Top)
        self.chat_history = QListWidget()
        
        # 3. Bottom Horizontal Layout
        bottom_layout = QHBoxLayout()
        
        # 4. Message Input Field and Send Button
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type here...")
        self.send_button = QPushButton("Send")
        self.send_button.setEnabled(False)
        
        bottom_layout.addWidget(self.message_input)
        bottom_layout.addWidget(self.send_button)
        
        # 5. Assemble everything together
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.chat_history)
        main_layout.addLayout(bottom_layout)
        
        # 6. Apply the layout to the widget
        self.setLayout(main_layout)


        # Connect the send button to the send_message method
        self.send_button.clicked.connect(self.send_message) 
        # Allow pressing Enter to send message
        self.message_input.returnPressed.connect(self.send_message)

        # Skeleton: Initialize WebSocket worker
        self.username = ""
        self.worker = WebSocketWorker(self)
        self.worker.message_received.connect(self.display_message)
        self.worker.connection_status_changed.connect(self.update_status)

    def set_username(self, username):
        self.username = username

    def connect_to_server(self):
        self.worker.username = self.username
        # Start the background QThread
        self.worker.start()

    def update_status(self, status):
        self.status_label.setText(status)
        if status == "Connected":
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.send_button.setEnabled(True)
        elif "Connecting" in status or "Reconnecting" in status:
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            self.send_button.setEnabled(False)
        else:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.send_button.setEnabled(False)

    def display_message(self, message):
        try:
            data = json.loads(message)
            if data.get("type") == "message":
                display_text = f"{data['username']}: {data['content']}"
                self.chat_history.addItem(display_text)
            elif data.get("type") == "error":
                display_text = f"Error: {data.get('message', data.get('content', 'Unknown error'))}"
                self.chat_history.addItem(display_text)
            elif data.get("type") == "join":
                display_text = f"🟢 {data['username']} {data['content']}"
                self.chat_history.addItem(display_text)
            elif data.get("type") == "leave":
                display_text = f"🔴 {data['username']} {data['content']}"
                self.chat_history.addItem(display_text)
        except json.JSONDecodeError:
            self.chat_history.addItem(f"Raw: {message}")

    def send_message(self):
        text = self.message_input.text().strip()
        if not text:
            return

        payload = json.dumps({
            "type": "message",
            "username": self.username,
            "content": text
        })

        if self.worker.loop is None or self.worker.websocket is None or getattr(self.worker.websocket, 'closed', True):
            self.chat_history.addItem("System: Unable to send message. Not connected.")
            return

        self.worker.send_message(payload)
        self.message_input.clear()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
    