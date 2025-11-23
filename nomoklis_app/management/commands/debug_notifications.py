from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from nomoklis_app.models import Notification

class Command(BaseCommand):
    help = 'Debug notifications for all users'

    def handle(self, *args, **options):
        self.stdout.write("Checking notifications...")
        for user in User.objects.all():
            count = Notification.objects.filter(recipient=user).count()
            self.stdout.write(f"User: {user.username} (ID: {user.id}), Total Notifications: {count}")
            
            if count > 0:
                last_5 = Notification.objects.filter(recipient=user).order_by('-created_at')[:5]
                for n in last_5:
                    self.stdout.write(f"  - [ID: {n.id}] {n.message} (Read: {n.is_read}, Created: {n.created_at})")
            else:
                self.stdout.write("  No notifications found.")
