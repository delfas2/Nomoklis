# failas: nomoklis_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage, Notification
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Prisijungimas prie kambario grupės
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Atsijungimas nuo kambario grupės
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # ★★★ PATAISYTA LOGIKA ★★★
    # Gauname žinutę iš WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        username = text_data_json['username']

        # Išsaugome žinutę duomenų bazėje
        await self.save_message(username, self.room_name, message)

        # Siunčiame žinutę kambario grupei
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username
            }
        )

    # Žinutės siuntimas į WebSocket
    async def chat_message(self, event):
        message = event['message']
        username = event['username']

        # Siunčiame žinutę atgal klientui
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))
        
    # ★★★ NAUJAS ASINCHRONINIS METODAS ŽINUTĖS IŠSAUGOJIMUI ★★★
    @database_sync_to_async
    def save_message(self, username, room_name, message):
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(name=room_name)
            
            ChatMessage.objects.create(
                sender=user,
                room=room,
                content=message
            )
        except User.DoesNotExist:
            print(f"KLAIDA: Vartotojas '{username}' nerastas.")
        except ChatRoom.DoesNotExist:
            print(f"KLAIDA: Pokalbių kambarys '{room_name}' nerastas.")


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