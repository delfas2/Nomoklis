import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

# Nustatome kelią iki nustatymų failo
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nomoklis.settings')

# ★★★ SVARBIAUSIAS ŽINGSNIS ★★★
# Inicializuojame Django aplikaciją PRIEŠ importuojant routing'ą
django.setup()

# Importuojame routing'ą TIK PO inicializacijos
import nomoklis_app.routing

# Sukuriame pagrindinę ASGI aplikaciją
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            nomoklis_app.routing.websocket_urlpatterns
        )
    ),
})