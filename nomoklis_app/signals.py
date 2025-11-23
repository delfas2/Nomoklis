from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ProblemReport, ProblemUpdate, RentalRequest, Notification

@receiver(post_save, sender=ProblemReport)
def create_problem_notification(sender, instance, created, **kwargs):
    """Sukuriamas pranešimas ir išsiunčiamas signalas per WebSocket."""
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
