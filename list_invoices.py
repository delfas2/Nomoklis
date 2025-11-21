import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/justinaszamarys/Library/Mobile Documents/com~apple~CloudDocs/_Python_duomenys/docker_Nomoklis/Nomoklis')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nomoklis.settings')
django.setup()

from nomoklis_app.models import Invoice, Lease

print("Existing Invoices:")
for invoice in Invoice.objects.all().order_by('-created_at'):
    print(f"ID: {invoice.id}, Lease: {invoice.lease.id}, Date: {invoice.invoice_date}, Period: {invoice.period_date}, Amount: {invoice.amount}")

print("\nActive Leases:")
for lease in Lease.objects.filter(status='active'):
    print(f"ID: {lease.id}, Tenant: {lease.tenant}, Property: {lease.property}")
