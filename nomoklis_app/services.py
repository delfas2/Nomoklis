import os
import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Sum
from fpdf import FPDF
from .models import Invoice, ProblemReport

def generate_invoice(lease, target_date=None, utility_items=None):
    """
    Generates an invoice for the given lease and target date.
    If target_date is None, uses today's date.
    utility_items: Optional list of dicts [{'name': '...', 'price': '...'}] for extra charges.
    Returns the created Invoice object or raises an exception.
    """
    
    # Lithuanian month names
    LITHUANIAN_MONTHS = {
        1: "Sausis", 2: "Vasaris", 3: "Kovas", 4: "Balandis", 
        5: "Gegužė", 6: "Birželis", 7: "Liepa", 8: "Rugpjūtis",
        9: "Rugsėjis", 10: "Spalis", 11: "Lapkritis", 12: "Gruodis"
    }
    today = target_date if target_date else date.today()
    target_period = today.replace(day=1)
    
    # Check if invoice already exists for this month (period)
    # We check both explicit period_date and legacy invoice_date (for old invoices)
    from django.db.models import Q
    
    existing_invoice = Invoice.objects.filter(
        lease=lease
    ).filter(
        Q(period_date=target_period) | 
        (
            Q(period_date__isnull=True) & 
            Q(invoice_date__year=today.year) & 
            Q(invoice_date__month=today.month)
        )
    ).exists()
    
    if existing_invoice:
        return None

    # Special check for the "First Invoice generated early" edge case
    # If we have exactly one invoice (legacy, no period_date) and lease starts this month,
    # assume that first invoice covers this month.
    if lease.invoices.count() == 1:
        first_inv = lease.invoices.first()
        if first_inv.period_date is None:
             if lease.start_date.year == today.year and lease.start_date.month == today.month:
                 return None

    # --- INVOICE DATA PREPARATION ---
    total_amount = 0
    rent_amount = 0  # Track rent separately for statistics
    invoice_items = []
    
    is_first_invoice = not lease.invoices.exists()
    
    # Determine the period date for the new invoice
    if is_first_invoice:
        current_period_date = lease.start_date.replace(day=1)
    else:
        current_period_date = target_period

    if is_first_invoice:
        # First invoice generated based on lease start date
        invoice_date_context = lease.start_date
        due_date = lease.start_date

        # Include deposit
        total_amount += lease.deposit_amount
        invoice_items.append({
            'name': 'Depozitas',
            'price': f"{lease.deposit_amount:.2f}"
        })
        
        # Calculate proportional rent
        if lease.start_date.day != 1:
            days_in_month = calendar.monthrange(invoice_date_context.year, invoice_date_context.month)[1]
            days_to_pay_for = days_in_month - lease.start_date.day + 1
            proportional_rent = (lease.rent_price / days_in_month) * days_to_pay_for
            total_amount += proportional_rent
            rent_amount = proportional_rent  # For statistics
            invoice_items.append({
                'name': f"Nuoma už {LITHUANIAN_MONTHS[invoice_date_context.month]} mėn. ({days_to_pay_for} d.)",
                'price': f"{proportional_rent:.2f}"
            })
        else: # If lease starts on the 1st
            total_amount += lease.rent_price
            rent_amount = lease.rent_price  # For statistics
            invoice_items.append({
                'name': f"Nuoma už {LITHUANIAN_MONTHS[invoice_date_context.month]} mėn.",
                'price': f"{lease.rent_price:.2f}"
            })
    else: # Subsequent months logic
        invoice_date_context = today
        
        # Standard due date for recurring invoices
        # Handle potential month rollover if payment_day doesn't exist in current month? 
        # For now keeping original logic but using today's month/year
        try:
            due_date = today.replace(day=getattr(lease, 'payment_day', 15))
        except ValueError:
            # Fallback for shorter months if payment day is 31st etc.
            # This is a basic fix, original code didn't handle it explicitly but replace might fail
            last_day = calendar.monthrange(today.year, today.month)[1]
            due_date = today.replace(day=last_day)

        total_amount = lease.rent_price
        rent_amount = lease.rent_price  # For statistics
        invoice_items.append({
            'name': f"Nuoma už {LITHUANIAN_MONTHS[invoice_date_context.month]} mėn.",
            'price': f"{lease.rent_price:.2f}"
        })
        
        # Calculate repair costs
        # We fetch ALL resolved, tenant-paid repairs that are NOT yet billed (invoice is Null)
        unbilled_repairs = ProblemReport.objects.filter(
            lease=lease,
            status='isspresta',
            paid_by='nuomininkas',
            invoice__isnull=True,
            resolution_costs__gt=0
        )
        
        for repair in unbilled_repairs:
            cost = repair.resolution_costs
            total_amount += cost
            # Format date as YYYY-MM-DD
            date_str = repair.created_at.strftime('%Y-%m-%d')
            invoice_items.append({
                'name': f"Remontas: {repair.get_problem_type_display()} ({date_str})",
                'price': f"{cost:.2f}"
            })

    # Add manually entered utility items
    if utility_items:
        for item in utility_items:
            # item is expected to be a dict with 'name' and 'price' (or 'amount')
            # Ensure price is a float/decimal for calculation
            try:
                price = float(item.get('price', item.get('amount', 0)))
                if price > 0:
                    total_amount += Decimal(str(price))
                    invoice_items.append({
                        'name': item.get('name', 'Komunalinės paslaugos'),
                        'price': f"{price:.2f}"
                    })
            except (ValueError, TypeError):
                continue

    # --- PDF GENERATION ---
    pdf = FPDF()
    pdf.add_page()
    
    regular_font_path = os.path.join(settings.BASE_DIR, 'DejaVuSans.ttf')
    pdf.add_font('DejaVu', '', regular_font_path, uni=True)
    bold_font_path = os.path.join(settings.BASE_DIR, 'dejavu-sans', 'DejaVuSans-Bold.ttf')
    pdf.add_font('DejaVu', 'B', bold_font_path, uni=True)

    pdf.set_font('DejaVu', 'B', 20)
    pdf.cell(0, 10, f"Sąskaita Nr. {lease.id}-{invoice_date_context.strftime('%Y%m')}", 0, 1, 'L')
    pdf.set_font('DejaVu', '', 10)
    pdf.cell(0, 5, f"Išrašymo data: {today.strftime('%Y-%m-%d')}", 0, 1, 'L')
    pdf.ln(10)

    pdf.set_font('DejaVu', 'B', 11)
    pdf.cell(95, 7, "Nuomotojas", 0, 0, 'L')
    pdf.cell(95, 7, "Nuomininkas", 0, 1, 'L')
    pdf.set_font('DejaVu', '', 10)
    pdf.cell(95, 6, lease.property.owner.get_full_name(), 0, 0, 'L')
    pdf.cell(95, 6, lease.tenant.get_full_name(), 0, 1, 'L')
    pdf.cell(95, 6, lease.property.owner.email, 0, 0, 'L')
    pdf.cell(95, 6, lease.tenant.email, 0, 1, 'L')
    pdf.ln(10)

    pdf.set_font('DejaVu', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(130, 8, "Paslaugos pavadinimas", 1, 0, 'L', 1)
    pdf.cell(30, 8, "Kiekis", 1, 0, 'C', 1)
    pdf.cell(30, 8, "Suma, Eur", 1, 1, 'R', 1)

    pdf.set_font('DejaVu', '', 10)
    for item in invoice_items:
        pdf.cell(130, 7, item['name'], 1, 0, 'L')
        pdf.cell(30, 7, "1", 1, 0, 'C')
        pdf.cell(30, 7, item['price'], 1, 1, 'R')
    
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(160, 10, "Mokėti iš viso:", 0, 0, 'R')
    pdf.cell(30, 10, f"{total_amount:.2f} Eur", 0, 1, 'R')
    pdf.ln(5)
    
    pdf.set_font('DejaVu', '', 10)
    pdf.cell(0, 7, f"Apmokėti ne vėliau kaip iki {due_date.strftime('%Y-%m-%d')}", 0, 1, 'L')

    pdf_output = bytes(pdf.output())
    
    invoice = Invoice.objects.create(
        lease=lease,
        invoice_date=today,
        due_date=due_date,
        amount=total_amount,
        rent_amount=rent_amount,
        period_date=current_period_date
    )
    
    file_name = f'saskaita_{invoice.id}_{today.strftime("%Y_%m")}.pdf'
    invoice.invoice_file.save(file_name, ContentFile(pdf_output), save=True)
    
    # Link the repairs to this invoice
    if not is_first_invoice and 'unbilled_repairs' in locals() and unbilled_repairs:
        unbilled_repairs.update(invoice=invoice)
    
    return invoice
