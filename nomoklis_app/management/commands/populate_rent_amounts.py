from django.core.management.base import BaseCommand
from nomoklis_app.models import Invoice
from decimal import Decimal
import calendar


class Command(BaseCommand):
    help = 'Populate rent_amount field for existing invoices based on lease rent price'

    def handle(self, *args, **options):
        # Find all invoices where rent_amount is NULL
        invoices_to_update = Invoice.objects.filter(rent_amount__isnull=True).select_related('lease')
        
        total_count = invoices_to_update.count()
        updated_count = 0
        
        self.stdout.write(f"Found {total_count} invoices without rent_amount")
        
        for invoice in invoices_to_update:
            lease = invoice.lease
            
            # Check if this is likely the first invoice (has deposit)
            # First invoice amount is typically: deposit + rent
            # So rent_amount should be: amount - deposit
            if invoice.amount > lease.rent_price * Decimal('1.5'):
                # Likely includes deposit
                rent_amount = invoice.amount - lease.deposit_amount
                self.stdout.write(
                    self.style.WARNING(
                        f"Invoice #{invoice.id}: Detected first invoice (with deposit), "
                        f"setting rent_amount to {rent_amount} EUR"
                    )
                )
            else:
                # Regular monthly invoice - use lease rent price
                rent_amount = lease.rent_price
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Invoice #{invoice.id}: Setting rent_amount to {rent_amount} EUR"
                    )
                )
            
            invoice.rent_amount = rent_amount
            invoice.save(update_fields=['rent_amount'])
            updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted! Updated {updated_count} invoices"
            )
        )

