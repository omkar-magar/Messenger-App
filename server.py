import asyncio
import websockets

# This set will remember every client that connects to the server
CONNECTED_CLIENTS = set()

async def handler(websocket):
    # 1. When a client connects, add them to our list
    CONNECTED_CLIENTS.add(websocket)
    print(f"New client connected. Total clients: {len(CONNECTED_CLIENTS)}")
    
    try:
        # 2. Wait indefinitely for this client to send a message
        async for message in websocket:
            print(f"Received message: {message}")
            # 3. Send that message out to everyone else
            websockets.broadcast(CONNECTED_CLIENTS, message)
    finally:
        # 4. If the client disconnects, remove them from the list
        CONNECTED_CLIENTS.remove(websocket)
        print(f"Client disconnected. Total clients: {len(CONNECTED_CLIENTS)}")
 
async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("Server started and listening on ws://localhost:8765")
        await asyncio.Future()  # This keeps the server running forever

if __name__ == "__main__":
    asyncio.run(main())
        