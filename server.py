import asyncio
import websockets
import json

# Mapping of websocket connection to username
ACTIVE_USERS = {}

async def safe_broadcast(message):
    stale_connections = []
    for websocket in list(ACTIVE_USERS):
        try:
            await websocket.send(message)
        except Exception as e:
            username = ACTIVE_USERS.get(websocket, "Unknown")
            print(f"[ERROR] Failed to send message to {username}: {e}")
            stale_connections.append(websocket)

    for websocket in stale_connections:
        ACTIVE_USERS.pop(websocket, None)

async def handler(websocket):
    username = "Unknown"
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"[ERROR] Failed to decode JSON from {username}")
                continue

            msg_type = data.get("type")
            if msg_type == "join":
                username = data.get("username", "Unknown")
                ACTIVE_USERS[websocket] = username
                print(f"[INFO] {username} joined. Total: {len(ACTIVE_USERS)}")
                await safe_broadcast(message)
            elif msg_type == "message":
                print(f"[MESSAGE] {username}: {data.get('content')}")
                await safe_broadcast(message)
            else:
                print(f"[WARN] Unsupported message type from {username}: {msg_type}")

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[ERROR] Connection closed unexpectedly: {e}")
    finally:
        if websocket in ACTIVE_USERS:
            left_user = ACTIVE_USERS.pop(websocket)
            leave_msg = json.dumps({"type": "leave", "username": left_user, "content": "has left the chat."})
            await safe_broadcast(leave_msg)
            print(f"[INFO] {left_user} disconnected. Total: {len(ACTIVE_USERS)}")
 
async def main():
    # Listen on all interfaces (0.0.0.0) if you want other devices on your WiFi to connect
    async with websockets.serve(handler, "localhost", 8765):
        print("Server started and listening on ws://localhost:8765")
        await asyncio.Future()  # This keeps the server running forever

if __name__ == "__main__":
    asyncio.run(main())
        