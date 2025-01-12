# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Verify user has access to this room
        if not await self.can_access_room():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    @database_sync_to_async
    def can_access_room(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return self.user == room.client or self.user == room.admin
        except ChatRoom.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')

        if message_type == 'message':
            await self.handle_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)

    async def handle_message(self, data):
        message = data['message']
        
        # Save message to database
        message_obj = await self.save_message(message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': self.user.id,
                'sender_email': self.user.email,
                'timestamp': str(message_obj.timestamp)
            }
        )

    async def handle_typing(self, data):
        # Broadcast typing status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_typing',
                'user_id': self.user.id,
                'is_typing': data.get('is_typing', False)
            }
        )

    async def chat_message(self, event):
        # Send chat message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_email': event['sender_email'],
            'timestamp': event['timestamp']
        }))

    async def user_typing(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def save_message(self, content):
        # Save message to the database
        room = ChatRoom.objects.get(id=self.room_id)
        message = Message.objects.create(
            room=room,
            sender=self.user,
            content=content
        )
        
        # Update room's updated_at timestamp
        room.updated_at = timezone.now()
        room.save()
        
        return message
