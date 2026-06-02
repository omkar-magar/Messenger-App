# Messenger Application Context

## Project Overview

Messenger is a real-time desktop chat application built with Python. The application provides instant messaging capabilities between multiple connected clients through a WebSocket server while maintaining a responsive and modern desktop user interface.

The architecture follows a strict separation of concerns:

* UI Layer → PySide6 Widgets
* Communication Layer → WebSocketWorker
* Networking Layer → WebSocket Server
* Threading Layer → QThread + asyncio

The application must remain responsive at all times, even during network interruptions or reconnection attempts.

---

# Tech Stack

## Frontend

* Python 3.12+
* PySide6 (Qt for Python)

## Backend Communication

* asyncio
* websockets

## Concurrency

* QThread
* Qt Signals & Slots

## Data Format

* JSON messages exchanged through WebSockets

Example:

```json
{
    "type": "message",
    "username": "Omkar",
    "content": "Hello World"
}
```

---

# Project Structure

```text
project/
│
├── server.py
│
├── main.py
│
├── widgets/
│   ├── login_page.py
│   ├── chat_page.py
│   └── message_widget.py
│
├── workers/
│   └── websocket_worker.py
│
├── assets/
│
└── styles/
```

---

# Architecture Rules

## UI Layer

The UI layer must:

* Handle rendering only.
* Handle user interactions only.
* Never contain networking logic.
* Never directly call asyncio functions.
* Never directly manage websocket connections.

Allowed responsibilities:

* Button click handlers
* Form validation
* Screen navigation
* Message rendering
* Status indicators

---

## WebSocketWorker Layer

The WebSocketWorker is the single source of truth for networking.

Responsibilities:

* Manage websocket connections
* Manage reconnection logic
* Send messages
* Receive messages
* Parse incoming JSON
* Emit Qt signals
* Handle connection errors

The worker must never update UI elements directly.

Communication with UI must occur exclusively through Signals and Slots.

---

## Server Layer

The server must:

* Maintain active client connections
* Broadcast messages
* Handle disconnects gracefully
* Prevent crashes caused by individual client failures
* Log connection events

The server should remain stateless whenever possible.

---

# Signal Architecture

## Worker → UI

```python
message_received(str)
connection_status_changed(str)
error_occurred(str)
user_joined(str)
user_left(str)
```

## UI → Worker

```python
connect_to_server(username)
disconnect_from_server()
send_message(message)
```

All communication between threads must use Qt Signals and Slots.

Never access UI widgets from the worker thread.

---

# Message Flow

## Sending

```text
ChatPage
   ↓
send_message signal
   ↓
WebSocketWorker
   ↓
websocket.send()
   ↓
Server
   ↓
Broadcast
```

## Receiving

```text
Server
   ↓
WebSocketWorker
   ↓
message_received signal
   ↓
ChatPage.display_message()
```

---

# Error Handling Requirements

The application must gracefully handle:

* Server unavailable
* Connection timeout
* Internet interruption
* Unexpected disconnect
* Invalid JSON payloads
* Server restart
* Duplicate usernames

Errors should never crash the UI.

Display user-friendly messages instead.

---

# Reconnection Strategy

Requirements:

1. Detect connection loss.
2. Notify UI immediately.
3. Attempt automatic reconnection.
4. Use exponential backoff.

Example:

```text
Attempt 1 → 1 second
Attempt 2 → 2 seconds
Attempt 3 → 4 seconds
Attempt 4 → 8 seconds
```

Maximum delay:

```text
30 seconds
```

---

# Performance Guidelines

* Never block the UI thread.
* Avoid long-running operations inside slots.
* Use asynchronous networking exclusively.
* Keep message rendering lightweight.
* Avoid creating unnecessary QThreads.
* Maintain a single websocket connection per client.

---

# Logging Requirements

Implement structured logging.

Log:

* Client connected
* Client disconnected
* Message sent
* Message received
* Reconnection attempts
* Exceptions

Example:

```text
[INFO] Connected to server
[INFO] Message received from Omkar
[WARNING] Connection lost
[ERROR] Failed to reconnect
```

---

# Security Guidelines

Minimum requirements:

* Validate incoming payloads.
* Sanitize user-generated text.
* Limit maximum message length.
* Reject malformed JSON.
* Never execute received data.
* Escape UI-rendered content when necessary.

Future enhancements:

* Authentication
* User sessions
* TLS (wss://)
* Message encryption

---

# Code Quality Standards

* Follow PEP 8.
* Use type hints everywhere.
* Prefer dataclasses for message models.
* Keep functions small and focused.
* Avoid global state.
* Write descriptive docstrings.
* Use dependency injection where appropriate.

Example:

```python
def send_message(self, content: str) -> None:
    """Send a chat message to the server."""
```

---

# Testing Requirements

Create tests for:

* Connection establishment
* Message sending
* Message receiving
* Reconnection logic
* JSON serialization
* Error handling

Use:

* pytest
* pytest-asyncio

---

# Current Roadmap

## Phase 1

* Implement asyncio loop inside WebSocketWorker.run()
* Connect client to websocket server
* Send messages from ChatPage
* Receive messages from server
* Display incoming messages

## Phase 2

* User join/leave notifications
* Connection status indicator
* Auto reconnect
* Typing indicator

## Phase 3

* Private messaging
* Chat rooms
* User list panel
* Message timestamps

## Phase 4

* Authentication
* Persistent chat history
* File sharing
* Voice messages

---

# AI Assistant Instructions

When generating code for this project:

1. Respect the architecture rules strictly.
2. Never place networking code inside UI widgets.
3. Never manipulate widgets from worker threads.
4. Use Signals and Slots for thread communication.
5. Keep asyncio logic inside WebSocketWorker.
6. Prefer maintainable and production-ready solutions.
7. Generate complete implementations rather than placeholders when possible.
8. Preserve separation of concerns.
9. Add type hints and docstrings.
10. Follow existing project structure and naming conventions.
