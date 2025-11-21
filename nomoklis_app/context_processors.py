# failas: nomoklis_app/context_processors.py

from .models import ChatMessage, Notification 
from django.db.models import Q

def unread_messages_count(request):
    if request.user.is_authenticated:
        # Žinučių skaičius
        message_count = ChatMessage.objects.filter(
            Q(room__participants=request.user) & 
            Q(is_read=False) & 
            ~Q(sender=request.user)
        ).count()
        
        # Pranešimų skaičius
        notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        return {
            'unread_count': message_count,
            'notification_count': notification_count
        }
    return {'unread_count': 0, 'notification_count': 0}

def simulated_date_context(request):
    return {
        'simulated_date': request.session.get('simulated_date')
    }