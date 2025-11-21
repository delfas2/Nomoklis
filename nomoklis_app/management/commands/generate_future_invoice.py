from django.core.management.base import BaseCommand
from django.utils import timezone
from nomoklis_app.models import Lease
from nomoklis_app.services import generate_invoice
from datetime import datetime

class Command(BaseCommand):
    help = 'Generates an invoice for a specific lease and date'

    def add_arguments(self, parser):
        parser.add_argument('lease_id', type=int, help='ID of the lease')
        parser.add_argument('date', type=str, help='Target date in YYYY-MM-DD format')

    def handle(self, *args, **options):
        lease_id = options['lease_id']
        date_str = options['date']

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            self.stdout.write(self.style.ERROR('Invalid date format. Please use YYYY-MM-DD'))
            return

        try:
            lease = Lease.objects.get(id=lease_id)
        except Lease.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Lease with ID {lease_id} does not exist'))
            return

        try:
            invoice = generate_invoice(lease, target_date=target_date)
            if invoice:
                self.stdout.write(self.style.SUCCESS(f'Successfully generated invoice {invoice.id} for date {target_date}'))
                self.stdout.write(f'File path: {invoice.invoice_file.path}')
            else:
                self.stdout.write(self.style.WARNING(f'Invoice for lease {lease_id} and date {target_date} already exists'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating invoice: {str(e)}'))
