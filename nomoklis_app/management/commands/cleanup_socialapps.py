from django.core.management.base import BaseCommand
from django.db.models import Count
from allauth.socialaccount.models import SocialApp

class Command(BaseCommand):
    help = 'Detects and removes duplicate SocialApp entries.'

    def handle(self, *args, **options):
        # Find providers with more than one SocialApp
        duplicate_providers = (
            SocialApp.objects.values('provider')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .values_list('provider', flat=True)
        )

        if not list(duplicate_providers):
            self.stdout.write(self.style.SUCCESS('No duplicate SocialApp entries found.'))
            return

        self.stdout.write(
            self.style.WARNING(
                f"Found duplicate SocialApp entries for providers: {', '.join(duplicate_providers)}"
            )
        )

        for provider in duplicate_providers:
            # Get all apps for the provider, ordered by ID (or creation date)
            apps = SocialApp.objects.filter(provider=provider).order_by('id')
            
            # Keep the first one
            app_to_keep = apps.first()
            self.stdout.write(f"Keeping SocialApp '{app_to_keep.name}' (ID: {app_to_keep.id}) for provider '{provider}'.")
            
            # Delete the rest
            apps_to_delete = apps[1:]
            for app in apps_to_delete:
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleting duplicate SocialApp '{app.name}' (ID: {app.id}) for provider '{provider}'."
                    )
                )
                app.delete()

        self.stdout.write(self.style.SUCCESS('Successfully cleaned up duplicate SocialApp entries.'))
