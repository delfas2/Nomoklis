from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from allauth.account.signals import user_signed_up
from .models import ProblemReport, ProblemUpdate, RentalRequest, Notification, Lease
from .utils import encrypt_id

@receiver(post_save, sender=ProblemReport)
def create_problem_notification(sender, instance, created, **kwargs):
    """Sukuriamas pranešimas ir išsiunčiamas signalas per WebSocket ir el. laiškas."""
    if created:
        recipient = instance.lease.property.owner
        message = f"Gautas naujas pranešimas apie problemą objekte {instance.lease.property.street}."
        Notification.objects.create(
            recipient=recipient,
            message=message,
            content_object=instance
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{recipient.id}",
            {
                "type": "send_notification", "message": message
            }
        )
        
        # Siųsti el. laišką (visada, nepriklausomai nuo to ar vartotojas prisijungęs)
        try:
            encrypted_id = encrypt_id(instance.id)
            problem_url = f"https://nomoklis.lt/landlord/problems/{encrypted_id}/"
            html_content = render_to_string('nomoklis_app/emails/problem_report_email.html', {
                'user': recipient,
                'problem': instance,
                'problem_url': problem_url,
            })
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject='Naujas gedimo pranešimas - Nomoklis',
                body=text_content,
                from_email='info@nomoklis.lt',
                to=[recipient.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
        except Exception as e:
            print(f"Nepavyko išsiųsti el. laiško: {e}")

# Signalas, kuris sukuria pranešimą, kai paliekamas komentaras
@receiver(post_save, sender=ProblemUpdate)
def create_update_notification(sender, instance, created, **kwargs):
    if created:
        problem = instance.problem
        # Jei autorius yra nuomininkas, siunčiame pranešimą nuomotojui
        if instance.author == problem.lease.tenant:
            recipient = problem.lease.property.owner
            message = f"Gautas naujas komentaras problemai objekte {problem.lease.property.street}."
        # Jei autorius yra nuomotojas, siunčiame pranešimą nuomininkui
        else:
            recipient = problem.lease.tenant
            message = f"Nuomotojas atsakė į jūsų pranešimą apie problemą."
        
        Notification.objects.create(
            recipient=recipient,
            message=message,
            content_object=problem
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{recipient.id}",
            {
                "type": "send_notification", "message": message
            }
        )

@receiver(post_save, sender=RentalRequest)
def create_rental_request_notification(sender, instance, created, **kwargs):
    """Sukuriamas pranešimas apie nuomos užklausą ir siunčiamas signalas."""
    if created:
        recipient = instance.property.owner
        message = f"Gauta nauja nuomos užklausa objektui {instance.property.street}."
        Notification.objects.create(
            recipient=recipient,
            message=message,
            content_object=instance
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{recipient.id}",
            {
                "type": "send_notification", "message": message
            }
        )

# Welcome email when user signs up
@receiver(user_signed_up)
def send_welcome_email(request, user, **kwargs):
    """Siunčiamas pasveikinimo el. laiškas naujiems vartotojams."""
    try:
        login_url = "https://nomoklis.lt/accounts/login/"
        html_content = render_to_string('nomoklis_app/emails/welcome_email.html', {
            'user': user,
            'login_url': login_url,
        })
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject='Sveiki atvykę į Nomoklis!',
            body=text_content,
            from_email='info@nomoklis.lt',
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
    except Exception as e:
        print(f"Nepavyko išsiųsti pasveikinimo el. laiško: {e}")

# Email when lease proposal is created
@receiver(post_save, sender=Lease)
def send_lease_proposal_email(sender, instance, created, **kwargs):
    """Siunčiamas el. laiškas nuomininkui apie naują nuomos pasiūlymą."""
    if created and instance.tenant:
        try:
            dashboard_url = "https://nomoklis.lt/tenant/dashboard/"
            html_content = render_to_string('nomoklis_app/emails/lease_proposal_email.html', {
                'user': instance.tenant,
                'lease': instance,
                'dashboard_url': dashboard_url,
            })
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject='Gavote nuomos pasiūlymą - Nomoklis',
                body=text_content,
                from_email='info@nomoklis.lt',
                to=[instance.tenant.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
        except Exception as e:
            print(f"Nepavyko išsiųsti nuomos pasiūlymo el. laiško: {e}")

# NOTE: Chat message emails are disabled to avoid spam
# Email notifications for chat messages would be too frequent
# @receiver(post_save, sender=ChatMessage)
# def send_message_email(sender, instance, created, **kwargs):
#     """Siunčiamas el. laiškas gavėjui apie naują žinutę."""
#     ...
