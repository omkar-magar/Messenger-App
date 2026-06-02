from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFrame, QTextEdit,QListWidget
from PySide6.QtCore import Qt, Signal, QThread
import sys
import asyncio
import websockets
import json

class WebSocketWorker(QThread):
    """Skeleton for the background thread that will talk to server.py"""
    message_received = Signal(str)

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
        try:
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                
                # Send an announcement to the server that we have arrived!
                join_payload = json.dumps({"type": "join", "username": self.username, "content": "has joined the chat!"})
                await websocket.send(join_payload)
                
                async for message in websocket:
                    self.message_received.emit(message)
        except Exception as e:
            self.message_received.emit(json.dumps({"type": "error", "username": "System", "content": f"Connection error: {e}"}))

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

    def go_to_chat(self, username):
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
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
         
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
        layout.addWidget(self.login_button)
        self.setLayout(layout)

    def validate_passwords(self):
        validation = self.password_input.text() 
        # Enable button only if passwords match and are not empty
        self.login_button.setEnabled(len(validation) > 0 and len(self.username_input.text()) > 0)

    def login(self):
        username = self.username_input.text()
        print(f"Logged in as {username}")
        # Emit a signal that MainWindow can listen to
        self.login_successful.emit(username)

class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Main Vertical Layout
        main_layout = QVBoxLayout()
        
        # 2. Chat History Area (Top)
        self.chat_history = QListWidget()
        
        # 3. Bottom Horizontal Layout
        bottom_layout = QHBoxLayout()
        
        # 4. Message Input Field and Send Button
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type here...")
        self.send_button = QPushButton("Send")
        
        bottom_layout.addWidget(self.message_input)
        bottom_layout.addWidget(self.send_button)
        
        # 5. Assemble everything together
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

    def set_username(self, username):
        self.username = username

    def connect_to_server(self):
        self.worker.username = self.username
        # Start the background QThread
        self.worker.start()

    def display_message(self, message):
        try:
            data = json.loads(message)
            if data.get("type") in ["message", "error"]:
                display_text = f"{data['username']}: {data['content']}"
                self.chat_history.addItem(display_text)
            elif data.get("type") == "join":
                display_text = f"🟢 {data['username']} {data['content']}"
                self.chat_history.addItem(display_text)
        except json.JSONDecodeError:
            self.chat_history.addItem(f"Raw: {message}")

    def send_message(self): 
        # Get the text from the input field
        text = self.message_input.text()
        if text:
            # Format message according to our JSON structure
            payload = json.dumps({
                "type": "message",
                "username": self.username,
                "content": text
            })
            self.worker.send_message(payload)
        self.message_input.clear()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
    