# failas: nomoklis_app/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # PATAISYMAS: Pašalintas 'ws/' priešdėlis, kad atitiktų JavaScript pakeitimą.
    re_path(r'chat/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
]