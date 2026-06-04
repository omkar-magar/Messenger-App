import json
from urllib.parse import unquote
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message
from django.contrib.auth.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. Decode the URL-encoded room name (e.g., "My%20Room" -> "My Room")
        self.room_name = unquote(self.scope['url_route']['kwargs']['room_name'])
        
        # 2. Fetch the room from the database to ensure it exists
        self.room = await self.get_room(self.room_name)
        if not self.room:
            await self.close()
            return

        # 3. Create a safe group name using the Room's integer ID
        self.room_group_name = f'chat_room_{self.room.id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid message format."}))
            return

        message_content = text_data_json.get('message', '').strip()
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close()
            return

        if not message_content:
            await self.send(text_data=json.dumps({"type": "error", "message": "Cannot send an empty message."}))
            return

        if not await self.is_participant(user.id, self.room.id):
            await self.send(text_data=json.dumps({"type": "error", "message": "Join the room before sending messages."}))
            return

        await self.save_message(user.id, self.room.id, message_content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'username': user.username
            }
        )

    async def chat_message(self, event):
        # Send message to the WebSocket
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def is_participant(self, user_id, room_id):
        return Room.objects.filter(id=room_id, participants__id=user_id).exists()

    @database_sync_to_async
    def get_room(self, room_name):
        try:
            return Room.objects.get(name=room_name)
        except Room.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, user_id, room_id, message_content):
        Message.objects.create(room_id=room_id, sender_id=user_id, content=message_content)
