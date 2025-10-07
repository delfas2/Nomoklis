import os
import django
from django.core.asgi import get_asgi_application

# 1. Nurodome kelią iki settings.py failo
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nomoklis.settings')

# 2. Įkeliame Django nustatymus. Tai privaloma padaryti prieš kitus importus.
django.setup()

# 3. Tik dabar, kai nustatymai įkelti, importuojame likusias dalis
from channels.routing import ProtocolTypeRouter, URLRouter
import nomoklis_app.routing

# 4. Apibrėžiame aplikaciją
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        nomoklis_app.routing.websocket_urlpatterns
    ),
})
