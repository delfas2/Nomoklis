import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nomoklis.settings')
django.setup()

from django.contrib.auth.models import User
from nomoklis_app.models import Notification

print("Checking notifications...")
for user in User.objects.all():
    count = Notification.objects.filter(recipient=user).count()
    print(f"User: {user.username}, Notifications: {count}")
    if count > 0:
        last_5 = Notification.objects.filter(recipient=user).order_by('-created_at')[:5]
        for n in last_5:
            print(f"  - {n.message} (Read: {n.is_read}, Created: {n.created_at})")
