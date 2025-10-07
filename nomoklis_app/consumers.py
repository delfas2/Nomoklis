# failas: nomoklis_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage, Notification
from django.contrib.contenttypes.models import ContentType

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Iš URL gaunamas kambario pavadinimas, pvz., "chat_2_3"
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Grupės pavadinimas turi būti toks pat kaip kambario pavadinimas
        self.room_group_name = self.room_name

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user = self.scope['user']

        # Išsaugome žinutę duomenų bazėje
        chat_message = await self.save_message(user, message)

        # Išsiunčiame žinutę visiems kambario dalyviams
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': user.username,
                'sender_name': user.get_full_name()
            }
        )
        
        # Informuojame gavėją apie naują žinutę per notifikacijų kanalą
        recipient = await self.get_recipient()
        if recipient:
            await self.channel_layer.group_send(
                f"notifications_{recipient.id}",
                {
                    'type': 'send_notification',
                    'message': f'Gavote naują žinutę nuo {user.first_name}',
                    'notification_type': 'chat'
                }
            )
            # Sukuriame pranešimą DB
            await self.create_chat_notification(chat_message, recipient)

    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        sender_name = event['sender_name']

        # Išsiunčiame žinutę atgal į kliento naršyklę
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'sender_name': sender_name
        }))

    @database_sync_to_async
    def save_message(self, user, message_content):
        # Randame kambarį ir išsaugome žinutę
        room, _ = ChatRoom.objects.get_or_create(name=self.room_name)
        return ChatMessage.objects.create(
            room=room,
            sender=user,
            content=message_content
        )

    @database_sync_to_async
    def get_recipient(self):
        """Suranda kitą pokalbio kambario dalyvį."""
        room = ChatRoom.objects.get(name=self.room_name)
        # Gauname visus dalyvius ir išfiltruojame siuntėją
        for participant in room.participants.all():
            if participant != self.scope['user']:
                return participant
        return None

    @database_sync_to_async
    def create_chat_notification(self, chat_message, recipient):
        """Sukuria pranešimą duomenų bazėje."""
        Notification.objects.create(
            recipient=recipient,
            message=f"Gavote naują žinutę nuo {chat_message.sender.get_full_name()}",
            content_object=chat_message
        )

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
        else:
            self.room_group_name = f'notifications_{self.user.id}'
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        """Siunčia pranešimą į kliento naršyklę."""
        await self.send(text_data=json.dumps(event))