from django.core.management.base import BaseCommand
from nomoklis_app.models import Property
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from django.db.models import Q

class Command(BaseCommand):
    help = 'Perrinks ir geokoduoja visus NT objektus, kurie neturi koordinačių.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--silent',
            action='store_true',
            help='Vykdyti tyliuoju režimu, spausdinti tik galutinę ataskaitą.',
        )
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Priverstinai atnaujinti visų NT objektų koordinates, net jei jos jau egzistuoja.',
        )

    def handle(self, *args, **options):
        if options['force_all']:
            self.stdout.write(self.style.WARNING('Vykdomas priverstinis visų NT objektų koordinačių atnaujinimas...'))
            properties_to_geocode = Property.objects.all()
        else:
            # Gauname visus objektus, kuriems trūksta platumos arba ilgumos
            properties_to_geocode = Property.objects.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        
        if not properties_to_geocode.exists():
            self.stdout.write(self.style.SUCCESS('Visi NT objektai jau turi koordinates. Nėra ką atnaujinti.'))
            return

        self.stdout.write(f'Rasta {properties_to_geocode.count()} NT objektų be koordinačių. Pradedamas atnaujinimas...')
        
        updated_count = 0
        failed_count = 0

        for prop in properties_to_geocode:
            try:
                # Išsaugant objektą, automatiškai pasileis geokodavimo funkcija modelyje
                # Naudojame update_fields, kad išvengtume kitų laukų atnaujinimo ir signalų
                prop.save(update_fields=['latitude', 'longitude', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'Sėkmingai atnaujintas adresas: {prop.street}, {prop.city}'))
                updated_count += 1
            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                self.stdout.write(self.style.ERROR(f'Nepavyko gauti koordinačių {prop.street}: {e}'))
                failed_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Įvyko netikėta klaida atnaujinant {prop.street}: {e}'))
                failed_count += 1
        
        self.stdout.write('--------------------')
        self.stdout.write(self.style.SUCCESS(f'Geokodavimas baigtas. Sėkmingai atnaujinta: {updated_count} įrašų.'))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'Nepavyko atnaujinti: {failed_count} įrašų.'))