# failas: nomoklis_app/context_processors.py

from django.contrib.contenttypes.models import ContentType
from .models import ChatMessage, Notification, ProblemReport, ProblemUpdate, SupportTicket
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

        # Gedimų pranešimų skaičius
        try:
            problem_ct = ContentType.objects.get_for_model(ProblemReport)
            update_ct = ContentType.objects.get_for_model(ProblemUpdate)
            problem_badge_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False,
                content_type__in=[problem_ct, update_ct]
            ).count()
        except:
            problem_badge_count = 0
            
        # Support ticket pranešimų skaičius
        try:
            support_ticket_ct = ContentType.objects.get_for_model(SupportTicket)
            support_ticket_badge_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False,
                content_type=support_ticket_ct
            ).count()
        except:
            support_ticket_badge_count = 0

        return {
            'unread_count': message_count,
            'notification_count': notification_count,
            'problem_badge_count': problem_badge_count,
            'support_ticket_badge_count': support_ticket_badge_count
        }
    return {'unread_count': 0, 'notification_count': 0, 'problem_badge_count': 0, 'support_ticket_badge_count': 0}