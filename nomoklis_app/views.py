from django.http import HttpResponse
from django.core import signing
import logging
from fpdf import FPDF
from django.http import HttpResponse
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.password_validation import password_validators_help_texts
from django.contrib import messages, admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import ChatRoom,UtilityBill,Profile, Invoice, MeterReading, ChatMessage, Property, ProblemUpdate, PropertyImage, Lease, TenantReview, PropertyReview, RentalRequest, ProblemReport, ProblemImage, SupportTicket, SupportTicketUpdate, SystemSettings
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Max, Q, F
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth import logout
from itertools import chain
from operator import attrgetter
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_POST
from decimal import Decimal
import os
from django.db.models import Q
from django.conf import settings
from django.db.models import Avg
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from .forms import (
    CustomUserCreationForm, MeterReadingForm, UtilitiesPaymentForm,
    PrepareContractForm, RentalRequestForm, TenantTerminationForm,
    TenantCommentForm, PropertyForm, PropertyCreateForm, AssignTenantForm, LandlordProblemUpdateForm, SupportTicketForm,
    SupportTicketUpdateForm, AdminSupportTicketUpdateForm, AdminSupportTicketMessageForm, SystemSettingsForm,
    TerminateLeaseForm, PropertyReviewForm, ProblemReportForm, UtilityBillFormSet,
    UserUpdateForm, ProfileEditForm, ConfirmLeaseForm, UserTypeForm
)
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import Notification, ProblemUpdate
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.core.files.base import ContentFile
import calendar
from django.urls import reverse
from django.utils.safestring import mark_safe
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt, requires_csrf_token
from .models import Property, PropertyImage

def index(request):
    latest_properties = Property.objects.filter(status='paruostas').order_by('-created_at')[:3]
    # Skaičiuojame visas aktyvias ir pasibaigusias sutartis
    successful_deals_count = Lease.objects.filter(status__in=['active', 'terminated']).count()
    context = {
        'latest_properties': latest_properties,
        'active_listings_count': Property.objects.filter(status='paruostas').count(),
        'landlord_count': User.objects.filter(profile__user_type='nuomotojas').count(),
        'tenant_count': User.objects.filter(profile__user_type='nuomininkas').count(),
        'successful_deals_count': successful_deals_count,
    }
    return render(request, 'nomoklis_app/index.html', context)

# def register(request):
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, f'Paskyra sukurta sėkmingai! Dabar galite prisijungti.')
#             return redirect('login')
#     else:
#         form = CustomUserCreationForm()
#     return render(request, 'nomoklis_app/register.html', {'form': form})

@login_required
def dashboard_redirect(request):
    try:
        # Bandome gauti vartotojo profilį
        user_type = request.user.profile.user_type
        if user_type == 'nuomotojas':
            return redirect('nuomotojas_dashboard')
        elif user_type == 'nuomininkas':
            return redirect('nuomininkas_dashboard')
        else:
            # Jei vartotojo tipas yra nežinomas, siunčiame pasirinkti rolę
            return redirect('choose_role')
    except Profile.DoesNotExist:
        # ★★★ SVARBIAUSIA DALIS ★★★
        # Jei profilio nėra, nukreipiame vartotoją į rolės pasirinkimo puslapį
        return redirect('choose_role')

def for_landlords_view(request):
    """Atvaizduoja informacinį puslapį nuomotojams."""
    return render(request, 'nomoklis_app/for_landlords.html')

def for_tenants_view(request):
    """Atvaizduoja informacinį puslapį nuomininkams."""
    return render(request, 'nomoklis_app/for_tenants.html')

def help_center_view(request):
    """Atvaizduoja pagalbos centro puslapį."""
    return render(request, 'nomoklis_app/help_center.html')

def terms_and_conditions_view(request):
    """Atvaizduoja taisyklių ir sąlygų puslapį."""
    return render(request, 'nomoklis_app/terms_and_conditions.html')

def privacy_policy_view(request):
    """Atvaizduoja privatumo politikos puslapį."""
    return render(request, 'nomoklis_app/privacy_policy.html')

@login_required
def nuomotojas_dashboard(request):
    all_properties = Property.objects.filter(owner=request.user)
    
    # Surandame išnuomotus objektus
    rented_properties_qs = all_properties.filter(status='isnuomotas')

    for prop in rented_properties_qs:
        prop.active_lease = prop.leases.filter(status='active').first()

    available_properties = all_properties.filter(status='paruostas')
    monthly_income = Lease.objects.filter(property__in=rented_properties_qs, status='active').aggregate(total=Sum('rent_price'))['total'] or 0
    
    # --- PRIDĖTA DALIS: Gauname laukiančias užklausas ---
    pending_requests = RentalRequest.objects.filter(property__owner=request.user, status='pending').order_by('-created_at')
    # --- PABAIGA ---
    
    context = {
        'active_page': 'dashboard',
        'total_properties': all_properties.count(),
        'rented_count': rented_properties_qs.count(),
        'available_count': available_properties.count(),
        'monthly_income': monthly_income,
        'rented_properties': rented_properties_qs,
        'available_properties': available_properties,
        'pending_requests': pending_requests, # <-- Perduodame užklausas į šabloną
    }
    return render(request, 'nomoklis_app/nuomotojas_dashboard.html', context)

@login_required
def nuomininkas_dashboard(request):
    active_lease = Lease.objects.filter(tenant=request.user, status='active').first()
    pending_leases = Lease.objects.filter(tenant=request.user, status='pending')
    sent_requests = RentalRequest.objects.filter(tenant=request.user, status='pending').order_by('-created_at')

    # Gauname visas pasibaigusias sutartis
    past_leases_qs = Lease.objects.filter(
        Q(tenant=request.user) &
        (Q(status='terminated') | Q(end_date__lt=timezone.now().date()))
    ).order_by('-end_date').distinct()

    # Gauname ID tų sutarčių, kurioms jau paliktas atsiliepimas
    reviewed_lease_ids = set(PropertyReview.objects.filter(lease__in=past_leases_qs).values_list('lease_id', flat=True))

    # Atrenkame sutartis, kurioms dar reikia palikti atsiliepimą
    leases_to_review = [lease for lease in past_leases_qs if lease.id not in reviewed_lease_ids]
    
    # Suskaičiuojame, kiek yra archyvuotų sutarčių (tos, kurios turi atsiliepimą)
    archived_leases_count = len(reviewed_lease_ids)

    unpaid_invoice = None
    next_payment_date = None
    if active_lease:
        unpaid_invoice = Invoice.objects.filter(lease=active_lease, is_paid=False).order_by('-invoice_date').first()
        if not unpaid_invoice:
            # ... (sekančios mokėjimo datos skaičiavimo logika lieka ta pati)
            pass

    context = {
        'active_lease': active_lease,
        'pending_leases': pending_leases,
        'sent_requests': sent_requests,
        'leases_to_review': leases_to_review,
        'archived_leases_count': archived_leases_count,
        'unpaid_invoice': unpaid_invoice,
        'next_payment_date': next_payment_date,
        'active_page': 'dashboard',
    }
    return render(request, 'nomoklis_app/nuomininkas_dashboard.html', context)

@login_required
def add_property(request):
    if request.method == 'POST':
        print(request.POST)
        print(request.FILES)
        form = PropertyCreateForm(request.POST, request.FILES)
        if form.is_valid():
            property_instance = form.save(commit=False)
            property_instance.owner = request.user
            property_instance.status = 'nuoma_pasibaigusi'  # Set the status here
            property_instance.save()
            images = request.FILES.getlist('images')
            for image in images:
                PropertyImage.objects.create(property=property_instance, image=image)
            messages.success(request, 'NT objektas sėkmingai pridėtas!')
            return redirect('my_properties')
        else:
            messages.error(request, f'Forma neteisinga: {form.errors.as_json()}')
    else:
        form = PropertyCreateForm()
    context = {'form': form, 'active_page': 'properties'}
    return render(request, 'nomoklis_app/add_property.html', context)

@login_required
def stats_view(request):
    current_year = datetime.now().year
    user = request.user

    # Lietuviškų mėnesių žodynas
    LITHUANIAN_MONTHS = {
        1: "Sausis", 2: "Vasaris", 3: "Kovas", 4: "Balandis", 5: "Gegužė", 6: "Birželis",
        7: "Liepa", 8: "Rugpjūtis", 9: "Rugsėjis", 10: "Spalis", 11: "Lapkritis", 12: "Gruodis"
    }
    
    # Visų vartotojo NT objektų sąrašas filtrui
    all_user_properties = Property.objects.filter(owner=user)

    # ==================================================================
    # FILTRO IR SKIRTUKŲ LOGIKA
    # ==================================================================
    selected_property_id = request.GET.get('property_id')
    #Įsimename, kuris skirtukas turi būti aktyvus
    active_tab = request.GET.get('tab', 'overview')
    
    # Paruošiame QuerySets, kuriuos filtruosime
    properties_to_analyze = all_user_properties
    paid_invoices_qs = Invoice.objects.filter(lease__property__owner=user, is_paid=True, invoice_date__year=current_year)
    problem_reports_qs = ProblemReport.objects.filter(lease__property__owner=user, created_at__year=current_year, resolution_costs__isnull=False)

    if selected_property_id and selected_property_id.isdigit():
        properties_to_analyze = properties_to_analyze.filter(id=selected_property_id)
        paid_invoices_qs = paid_invoices_qs.filter(lease__property_id=selected_property_id)
        problem_reports_qs = problem_reports_qs.filter(lease__property_id=selected_property_id)

    # ==================================================================
    # TAB 1: Bendra apžvalga (lieka nepakitęs)
    # ==================================================================
    total_properties_count = all_user_properties.count()
    rented_properties_count = all_user_properties.filter(status='isnuomotas').count()
    occupancy_rate = (rented_properties_count / total_properties_count * 100) if total_properties_count > 0 else 0
    
    overall_paid_invoices = Invoice.objects.filter(lease__property__owner=user, is_paid=True, invoice_date__year=current_year)
    overall_problems = ProblemReport.objects.filter(lease__property__owner=user, created_at__year=current_year, resolution_costs__isnull=False)
    
    total_gross_income = overall_paid_invoices.aggregate(total=Sum('amount'))['total'] or 0
    landlord_expenses = overall_problems.filter(paid_by='nuomotojas').aggregate(total=Sum('resolution_costs'))['total'] or 0
    total_annual_income = total_gross_income - landlord_expenses
    monthly_average_income = total_annual_income / 12 if total_annual_income > 0 else 0
    total_expenses_for_chart = overall_problems.aggregate(total=Sum('resolution_costs'))['total'] or 0
    
    income_by_month_overall = (
        overall_paid_invoices.annotate(month=TruncMonth('invoice_date')).values('month')
        .annotate(total_income=Sum('amount')).order_by('month')
    )
    # Naudojame lietuviškus mėnesius
    income_labels = [LITHUANIAN_MONTHS[d['month'].month] for d in income_by_month_overall]
    income_data = [float(d['total_income'] or 0) for d in income_by_month_overall]

    expenses_by_type_overall = (
        overall_problems.values('problem_type').annotate(total_costs=Sum('resolution_costs')).order_by('-total_costs')
    )
    problem_type_dict = dict(ProblemReport.PROBLEM_TYPE_CHOICES)
    expenses_labels = [problem_type_dict.get(item['problem_type'], 'Kita') for item in expenses_by_type_overall]
    expenses_data = [float(item['total_costs']) for item in expenses_by_type_overall]
    
    # ==================================================================
    # TAB 2: Pelningumas (ATNAUJINTA LOGIKA)
    # ==================================================================
    months = [date(current_year, m, 1) for m in range(1, 13)]
    monthly_performance = []

    income_by_month = {
        item['month'].strftime('%Y-%m'): item['total']
        for item in paid_invoices_qs.annotate(month=TruncMonth('invoice_date')).values('month').annotate(total=Sum('amount'))
    }
    expenses_by_month = {
        item['month'].strftime('%Y-%m'): item['total']
        for item in problem_reports_qs.annotate(month=TruncMonth('created_at')).values('month').annotate(total=Sum('resolution_costs'))
    }

    for month_date in months:
        month_str = month_date.strftime('%Y-%m')
        income = income_by_month.get(month_str, 0)
        expenses = expenses_by_month.get(month_str, 0)
        profit = income - expenses
        monthly_performance.append({
            'month': LITHUANIAN_MONTHS[month_date.month], # Naudojame lietuviškus mėnesius
            'income': float(income),
            'expenses': float(expenses),
            'profit': float(profit)
        })
        
    profitability_labels = json.dumps([m['month'] for m in monthly_performance])
    profitability_profit_data = json.dumps([m['profit'] for m in monthly_performance])
    profitability_expenses_data = json.dumps([m['expenses'] for m in monthly_performance])

    # ==================================================================
    # TAB 3: Sutarčių Analizė (ATNAUJINTA LOGIKA)
    # ==================================================================
    lease_analysis_by_property = []
    for prop in all_user_properties:
        completed_leases = Lease.objects.filter(
            property=prop, status='terminated', end_date__isnull=False, start_date__isnull=False
        ).annotate(duration=F('end_date') - F('start_date'))
        avg_duration_data = completed_leases.aggregate(avg_duration=Avg('duration'))
        avg_lease_duration_days = avg_duration_data['avg_duration'].days if avg_duration_data['avg_duration'] else 0

        vacancy_periods = []
        leases = prop.leases.filter(end_date__isnull=False).order_by('start_date')
        if leases.count() > 1:
            for i in range(len(leases) - 1):
                vacancy_periods.append((leases[i+1].end_date - leases[i].end_date).days)
        avg_vacancy_days = sum(vacancy_periods) / len(vacancy_periods) if vacancy_periods else 0

        total_requests = RentalRequest.objects.filter(property=prop, created_at__year=current_year).count()
        accepted_requests = RentalRequest.objects.filter(property=prop, created_at__year=current_year, status='accepted').count()
        conversion_rate = (accepted_requests / total_requests * 100) if total_requests > 0 else 0
        
        lease_analysis_by_property.append({
            'name': str(prop),
            'avg_duration': avg_lease_duration_days,
            'avg_vacancy': round(avg_vacancy_days),
            'conversion_rate': round(conversion_rate, 1)
        })

    # ==================================================================
    # TAB 4: Priežiūra (lieka nepakitęs)
    # ==================================================================
    problematic_properties = all_user_properties.annotate(
        problem_count=Count('leases__problems', filter=Q(leases__problems__created_at__year=current_year))
    ).filter(problem_count__gt=0).order_by('-problem_count')

    # ==================================================================
    # CONTEXT
    # ==================================================================
    context = {
        'active_page': 'stats',
        'all_user_properties': all_user_properties,
        'selected_property_id': selected_property_id,
        'active_tab': active_tab, # Perduodame aktyvų skirtuką
        # Tab 1
        'total_annual_income': total_annual_income, 'monthly_average_income': monthly_average_income,
        'occupancy_rate': occupancy_rate, 'rented_properties_count': rented_properties_count,
        'total_properties_count': total_properties_count, 'total_expenses': total_expenses_for_chart,
        'income_labels': json.dumps(income_labels), 'income_data': json.dumps(income_data),
        'expenses_labels': json.dumps(expenses_labels), 'expenses_data': json.dumps(expenses_data),
        # Tab 2
        'profitability_labels': profitability_labels, 'profitability_profit_data': profitability_profit_data,
        'profitability_expenses_data': profitability_expenses_data,
        # Tab 3
        'lease_analysis_by_property': lease_analysis_by_property,
        # Tab 4
        'problematic_properties': problematic_properties,
    }
    return render(request, 'nomoklis_app/stats.html', context)

from .utils import encode_room_name, decode_room_name

@login_required
def landlord_contracts_page(request):
    """
    Vienintelė funkcija, apdorojanti nuomotojo sutarčių puslapį.
    Atvaizduoja aktyvias ir archyvuotas sutartis.
    """
    user = request.user

    # 1. Gauname aktyvias sutartis
    active_leases = Lease.objects.filter(
        property__owner=user,
        status='active'
    ).order_by('-start_date')

    for lease in active_leases:
        if lease.utilities_paid_by == 'landlord':
            lease.latest_reading = MeterReading.objects.filter(lease=lease).order_by('-reading_date').first()

    # 2. Gauname archyvuotas sutartis
    archived_leases = Lease.objects.filter(
        Q(property__owner=user) &
        (Q(status='terminated') | Q(status='expired'))
    ).order_by('-end_date').distinct()

    # 3. Papildomi duomenys
    pending_requests_count = RentalRequest.objects.filter(property__owner=user, status='pending').count()
    
    # --- ŠTAI PATAISYTA EILUTĖ ---
    # Pakeistas 'user=user' į 'recipient=user'
    notifications = Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')
    # --- PATAISYMO PABAIGA ---

    context = {
        'active_leases': active_leases,
        'archived_leases': archived_leases,
        'pending_requests': pending_requests_count,
        'notifications': notifications,
        'active_page': 'tenants',
    }
    
    return render(request, 'nomoklis_app/contracts.html', context)

@login_required
def start_chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    # Prevent users from starting a chat with themselves
    if request.user == other_user:
        messages.error(request, "Negalite pradėti pokalbio su pačiu savimi.")
        return redirect('dashboard_redirect')

    # Generate a unique room name for the pair of users
    # We sort the user IDs to ensure the room name is always the same for the same two users
    if request.user.id < other_user.id:
        room_name = f"chat_{request.user.id}_{other_user.id}"
    else:
        room_name = f"chat_{other_user.id}_{request.user.id}"

    # Find or create the chat room
    chat_room, created = ChatRoom.objects.get_or_create(name=room_name)

    if created:
        chat_room.participants.add(request.user, other_user)

    # Encode the room name for the URL
    encoded_room_name = encode_room_name(request.user.id, other_user.id)

    return redirect('chat_room', room_name=encoded_room_name)

@login_required
def chat_room_view(request, room_name):
    # Decode the room name
    decoded_room_name = decode_room_name(room_name)
    if not decoded_room_name:
        messages.error(request, "Neteisingas pokalbio kambario adresas.")
        return redirect('dashboard_redirect')

    chat_room = get_object_or_404(ChatRoom, name=decoded_room_name)

    # Patikriname, ar vartotojas yra šio kambario dalyvis
    if request.user not in chat_room.participants.all():
        messages.error(request, "Jūs neturite prieigos prie šio pokalbio.")
        return redirect('dashboard_redirect')

    # Surandame kitą pokalbio dalyvį
    other_user = chat_room.participants.exclude(id=request.user.id).first()

    # Pažymime gautas žinutes kaip perskaitytas
    chat_room.messages.filter(Q(sender=other_user) & Q(is_read=False)).update(is_read=True)
    previous_messages = chat_room.messages.order_by('timestamp')
    user_type = request.user.profile.user_type

    context = {
        'room_name': room_name, # Pass the encoded room name to the template
        'other_user': other_user,
        'previous_messages': previous_messages,
        'active_page': 'messages',
        'user_type': user_type,
    }
    return render(request, 'nomoklis_app/chat_room.html', context)


@login_required
def my_properties_view(request):
    properties = Property.objects.filter(owner=request.user).order_by('-created_at')
    context = {'active_page': 'properties', 'properties': properties}
    return render(request, 'nomoklis_app/my_properties.html', context)

@login_required
def assign_tenant_view(request, property_id):
    prop = get_object_or_404(Property, id=property_id, owner=request.user)
    if request.method == 'POST':
        form = AssignTenantForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                tenant_user = User.objects.get(email=email)
                lease = form.save(commit=False)
                lease.property = prop
                lease.tenant = tenant_user
                lease.status = 'pending'
                lease.save()
                messages.success(request, f'Pasiūlymas išsiųstas nuomininkui {tenant_user.first_name}.')
                return redirect('nuomotojas_dashboard')
            except User.DoesNotExist:
                form.add_error('email', 'Vartotojas su tokiu el. paštu nerastas.')
    else:
        form = AssignTenantForm()
    context = {'form': form, 'property': prop}
    return render(request, 'nomoklis_app/assign_tenant.html', context)

@login_required
def edit_property_view(request, property_id):
    prop = get_object_or_404(Property, id=property_id, owner=request.user)
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=prop)
        if form.is_valid():
            property_instance = form.save(commit=False)
            
            # Patikriname mokamo skelbimo logiką, jei keičiama būsena
            settings = SystemSettings.objects.first()
            requires_payment = (
                settings and settings.paid_listing_enabled and
                property_instance.status == 'paruostas' and not property_instance.is_paid_listing
            )

            if requires_payment:
                # Neišsaugome pakeitimų, o įrašome juos į sesiją
                request.session['property_edit_data'] = form.cleaned_data
                # Konvertuojame Decimal į string, kad būtų galima serializuoti į JSON
                request.session['property_edit_data']['rent_price'] = str(form.cleaned_data['rent_price'])
                request.session['property_edit_data']['area'] = str(form.cleaned_data['area'])
                # Nukreipiame į mokėjimą
                request.session['property_id_for_payment'] = prop.id
                return redirect('activate_property_payment', property_id=prop.id)

            property_instance.save() # Išsaugome, jei mokėjimas nereikalingas
            images = request.FILES.getlist('images')
            for image in images:
                PropertyImage.objects.create(property=prop, image=image)
            messages.success(request, 'NT objekto duomenys sėkmingai atnaujinti!')
            return redirect('my_properties')
    else:
        form = PropertyForm(instance=prop)
    context = {'form': form, 'property': prop, 'active_page': 'properties'}
    return render(request, 'nomoklis_app/edit_property.html', context)

@login_required
def activate_property_payment(request, property_id):
    prop = get_object_or_404(Property, id=property_id, owner=request.user)
    system_settings = SystemSettings.objects.first()

    if not system_settings or not system_settings.paid_listing_enabled or prop.is_paid_listing:
        messages.error(request, 'Šiam objektui nereikalingas aktyvavimas arba jis jau aktyvuotas.')
        return redirect('my_properties')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'Skelbimo aktyvavimas: {prop}',
                        },
                        'unit_amount': int(system_settings.listing_price * 100),
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            metadata={
                'payment_type': 'property_activation',
                'property_id': prop.id
            },
            success_url=request.build_absolute_uri(reverse('payment_success')),
            cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Apmokėjimo klaida: {e}")
        return redirect('my_properties')

@login_required
def confirm_lease(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, tenant=request.user)
    lease.status = 'active'
    lease.save()
    lease.property.status = 'isnuomotas'
    lease.property.save()
    messages.success(request, 'Sėkmingai patvirtinote nuomos sutartį!')
    return redirect('nuomininkas_dashboard')

@login_required
def reject_lease(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, tenant=request.user)
    lease.delete()
    messages.info(request, 'Jūs atmetėte nuomos pasiūlymą.')
    return redirect('nuomininkas_dashboard')

@login_required
def landlord_chat_list(request):
    chat_rooms = ChatRoom.objects.filter(participants=request.user).annotate(
        last_message_time=Max('messages__timestamp'),
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-last_message_time')
    for room in chat_rooms:
        room.latest_message = room.messages.order_by('-timestamp').first()
        # Surandame kitą dalyvį
        other_participant = room.participants.exclude(id=request.user.id).first()
        room.other_participant = other_participant
        if other_participant:
            room.encoded_name = encode_room_name(request.user.id, other_participant.id)
    context = {
        'active_page': 'messages',
        'chat_rooms_data': chat_rooms
    }
    return render(request, 'nomoklis_app/landlord_chat_list.html', context)

@login_required
def tenant_chat_list(request):
    chat_rooms = ChatRoom.objects.filter(participants=request.user).annotate(
        last_message_time=Max('messages__timestamp'),
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-last_message_time')
    for room in chat_rooms:
        room.latest_message = room.messages.order_by('-timestamp').first()
        # Surandame kitą dalyvį
        other_participant = room.participants.exclude(id=request.user.id).first()
        room.other_participant = other_participant
        if other_participant:
            room.encoded_name = encode_room_name(request.user.id, other_participant.id)
    context = {
        'active_page': 'messages',
        'chat_rooms_data': chat_rooms
    }
    return render(request, 'nomoklis_app/tenant_chat_list.html', context)

def property_search_view(request):
    properties = Property.objects.filter(status='paruostas').order_by('-created_at')
    saved_property_ids = []
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        saved_property_ids = list(request.user.profile.saved_properties.values_list('id', flat=True))

    if request.method == 'GET':
        # Pagrindiniai filtrai
        city = request.GET.get('city')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        
        # Papildomi filtrai iš modalinio lango
        min_rooms = request.GET.get('min_rooms')
        max_rooms = request.GET.get('max_rooms')
        min_area = request.GET.get('min_area')
        max_area = request.GET.get('max_area')
        min_floor = request.GET.get('min_floor')
        max_floor = request.GET.get('max_floor')
        
        # Patogumų filtrai (checkboxes)
        has_balcony = request.GET.get('has_balcony')
        has_parking = request.GET.get('has_parking')
        pets_allowed = request.GET.get('pets_allowed')
        is_furnished = request.GET.get('is_furnished')
        has_appliances = request.GET.get('has_appliances')
        residence_declaration_allowed = request.GET.get('residence_declaration_allowed')

        # Filtravimo logika
        if city:
            properties = properties.filter(city__icontains=city)
        if min_price:
            properties = properties.filter(rent_price__gte=min_price)
        if max_price:
            properties = properties.filter(rent_price__lte=max_price)
            
        if min_rooms:
            properties = properties.filter(rooms__gte=min_rooms)
        if max_rooms:
            properties = properties.filter(rooms__lte=max_rooms)
            
        if min_area:
            properties = properties.filter(area__gte=min_area)
        if max_area:
            properties = properties.filter(area__lte=max_area)

        if min_floor:
            properties = properties.filter(floor__gte=min_floor)
        if max_floor:
            properties = properties.filter(floor__lte=max_floor)
            
        if has_balcony:
            properties = properties.filter(has_balcony=True)
        if has_parking:
            properties = properties.filter(has_parking=True)
        if pets_allowed:
            properties = properties.filter(pets_allowed=True)
        if is_furnished:
            properties = properties.filter(is_furnished=True)
        if has_appliances:
            properties = properties.filter(has_appliances=True)
        if residence_declaration_allowed:
            properties = properties.filter(residence_declaration_allowed=True)


    context = {
        'properties': properties,
        'property_types': Property.PROPERTY_TYPE_CHOICES,
        'request': request,
        'saved_property_ids': saved_property_ids,
    }

    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.user_type == 'nuomininkas':
        context['active_page'] = 'property_search'
        context['base_template'] = 'nomoklis_app/_tenant_base.html'
        return render(request, 'nomoklis_app/property_search.html', context)
    else:
        return render(request, 'nomoklis_app/public_property_search.html', context)

def property_detail_view(request, property_id):
    prop = get_object_or_404(Property, id=property_id)
    property_specific_reviews = PropertyReview.objects.filter(lease__property=prop)
    landlord_reviews = PropertyReview.objects.filter(lease__property__owner=prop.owner)
    avg_property_rating = property_specific_reviews.aggregate(avg_rating=Avg('property_rating'))['avg_rating']
    avg_landlord_rating = landlord_reviews.aggregate(avg_rating=Avg('landlord_rating'))['avg_rating']
    context = {
        'property': prop,
        'avg_property_rating': avg_property_rating,
        'avg_landlord_rating': avg_landlord_rating
    }
    return render(request, 'nomoklis_app/_property_detail_popup.html', context)


@login_required
def terminate_lease_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, property__owner=request.user)
    if request.method == 'POST':
        form = TerminateLeaseForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.lease = lease
            review.save()
            lease.status = 'terminated'
            lease.end_date = form.cleaned_data['termination_date']
            lease.save()
            lease.property.status = 'nuoma_pasibaigusi'
            lease.property.save()
            messages.success(request, f'Sutartis su nuomininku {lease.tenant.get_full_name()} sėkmingai nutraukta.')
            return redirect('my_properties')
    else:
        form = TerminateLeaseForm()
    return render(request, 'nomoklis_app/_terminate_lease_popup.html', {'form': form, 'lease': lease})

def submit_rental_request_view(request, property_id):
    if not request.user.is_authenticated:
        messages.info(request, 'Norėdami pateikti užklausą, pirmiausia turite prisijungti arba užsiregistruoti.')
        return redirect('account_signup')

    prop = get_object_or_404(Property, id=property_id)
    
    if request.user.profile.user_type != 'nuomininkas':
        messages.error(request, 'Tik nuomininkai gali teikti nuomos užklausas.')
        return redirect('property_search')

    if request.method == 'POST':
        form = RentalRequestForm(request.POST)
        if form.is_valid():
            # Išsaugome užklausos duomenis
            rental_request = form.save(commit=False)
            rental_request.property = prop
            rental_request.tenant = request.user
            rental_request.save()

            # Sukuriame pokalbių kambarį ir išsiunčiame pirmą žinutę
            room_name = f"chat_{min(request.user.id, prop.owner.id)}_{max(request.user.id, prop.owner.id)}"
            chat_room, created = ChatRoom.objects.get_or_create(name=room_name)
            if created:
                chat_room.participants.add(request.user, prop.owner)
            
            ChatMessage.objects.create(
                room=chat_room,
                sender=request.user,
                content=form.cleaned_data['message']
            )

            messages.success(request, f'Jūsų užklausa dėl "{prop.street}" buvo sėkmingai išsiųsta.')
            
            # Encode the room name for the URL
            encoded_room_name = encode_room_name(request.user.id, prop.owner.id)
            return redirect('chat_room', room_name=encoded_room_name)
    else: # GET metodas
        form = RentalRequestForm(initial={'offered_price': prop.rent_price})
    
    return render(request, 'nomoklis_app/_submit_request_popup.html', {'form': form, 'property': prop})


@login_required
def confirm_rental_request_view(request, request_id):
    rental_request = get_object_or_404(RentalRequest, id=request_id, property__owner=request.user)
    if request.method == 'POST':
        form = ConfirmLeaseForm(request.POST)
        if form.is_valid():
            lease = form.save(commit=False)
            lease.property = rental_request.property
            lease.tenant = rental_request.tenant
            lease.status = 'active'
            lease.save()
            rental_request.property.status = 'isnuomotas'
            rental_request.property.save()
            rental_request.status = 'accepted'
            rental_request.save()
            messages.success(request, f"Nuomos sutartis su {lease.tenant.get_full_name()} sėkmingai sudaryta.")
            return redirect('rental_requests')
    else:
        form = ConfirmLeaseForm(initial={'rent_price': rental_request.property.rent_price})
    return render(request, 'nomoklis_app/_confirm_lease_popup.html', {'form': form, 'rental_request': rental_request})

@login_required
def property_reviews_view(request, property_id):
    prop = get_object_or_404(Property, id=property_id)
    reviews = PropertyReview.objects.filter(lease__property=prop).order_by('-created_at')
    return render(request, 'nomoklis_app/_property_reviews_popup.html', {'property': prop, 'reviews': reviews})

@login_required
def landlord_reviews_view(request, landlord_id):
    landlord = get_object_or_404(User, id=landlord_id)
    reviews = PropertyReview.objects.filter(lease__property__owner=landlord).order_by('-created_at')
    return render(request, 'nomoklis_app/_landlord_reviews_popup.html', {'landlord': landlord, 'reviews': reviews})

@login_required
def tenant_reviews_view(request, tenant_id):
    tenant = get_object_or_404(User, id=tenant_id)
    reviews = TenantReview.objects.filter(lease__tenant=tenant).order_by('-created_at')
    return render(request, 'nomoklis_app/_tenant_reviews_popup.html', {'tenant': tenant, 'reviews': reviews})

@login_required
def tenant_requests_view(request):
    pending_requests = RentalRequest.objects.filter(
        tenant=request.user,
        status='pending'
    ).order_by('-created_at')
    archived_requests = RentalRequest.objects.filter(
        tenant=request.user,
        status__in=['accepted', 'rejected']
    ).order_by('-created_at')
    context = {
        'active_page': 'tenant_requests',
        'pending_requests': pending_requests,
        'archived_requests': archived_requests,
    }
    return render(request, 'nomoklis_app/tenant_rental_requests.html', context)

@login_required
def reject_rental_request_view(request, request_id):
    if request.method == 'GET':
        rental_request = get_object_or_404(RentalRequest, id=request_id, property__owner=request.user)
        rental_request.status = 'rejected'
        rental_request.save()
    return redirect('contracts')

@login_required
def landlord_profile_view(request):
    user = request.user
    properties = Property.objects.filter(owner=user)
    context = {
        'user': user,
        'active_properties_count': properties.filter(status='paruostas').count(),
        'all_reviews': PropertyReview.objects.filter(lease__property__owner=user).order_by('-created_at'),
        'active_page': 'profile',
    }
    return render(request, 'nomoklis_app/landlord_profile.html', context)

@login_required
def landlord_profile_edit_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Jūsų profilis sėkmingai atnaujintas!')
            return redirect('landlord_profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'active_page': 'profile',
        'base_template': 'nomoklis_app/_sidebar.html',
    }
    return render(request, 'nomoklis_app/landlord_profile_edit.html', context)

@login_required
def tenant_profile_view(request):
    user = request.user
    
    # Paliekame tik atsiliepimus, paliktus APIE šį nuomininką (rašė nuomotojai)
    reviews_about_tenant = TenantReview.objects.filter(lease__tenant=user).order_by('-created_at')
    
    # Apskaičiuojame nuomininko reitingo vidurkį
    avg_rating = reviews_about_tenant.aggregate(avg=Avg('rating'))['avg']

    context = {
        'user': user,
        'reviews': reviews_about_tenant, # Pakeistas pavadinimas į bendrinį "reviews"
        'avg_rating': avg_rating,
        'active_page': 'profile',
    }
    return render(request, 'nomoklis_app/tenant_profile.html', context)

@login_required
def tenant_profile_edit_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Jūsų profilis sėkmingai atnaujintas!')
            return redirect('tenant_profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'active_page': 'profile',
        'base_template': 'nomoklis_app/_tenant_sidebar.html',
    }
    return render(request, 'nomoklis_app/tenant_profile_edit.html', context)

def landlord_preview_popup(request, landlord_id):
    landlord = get_object_or_404(User, id=landlord_id)
    context = {
        'landlord': landlord
    }
    return render(request, 'nomoklis_app/_landlord_preview_popup.html', context)

# GALUTINIS PATAISYMAS: `report_problem_view` atnaujinta, kad veiktų su paprasta forma
@login_required
def report_problem_view(request):
    active_lease = Lease.objects.filter(tenant=request.user, status='active').first()
    if not active_lease:
        messages.error(request, "Jūs neturite aktyvios nuomos sutarties, todėl negalite registruoti problemos.")
        return redirect('nuomininkas_dashboard')

    if request.method == 'POST':
        # Perduodame ir request.FILES, kad forma galėtų apdoroti failus
        form = ProblemReportForm(request.POST, request.FILES)
        if form.is_valid():
            problem = form.save(commit=False)
            problem.lease = active_lease
            problem.save()
            
            # Apdorojame ir išsaugome visas įkeltas nuotraukas
            images = request.FILES.getlist('images')
            for image in images:
                ProblemImage.objects.create(problem=problem, image=image)
                
            messages.success(request, "Problema sėkmingai užregistruota!")
            return redirect('problem_list')
    else: # GET metodas
        form = ProblemReportForm()

    context = {
        'form': form, 
        'active_page': 'report_problem',
        'base_template': 'nomoklis_app/_tenant_base.html'
    }
    return render(request, 'nomoklis_app/report_problem.html', context)

@login_required
def problem_list_view(request):
    problems = ProblemReport.objects.filter(lease__tenant=request.user).order_by('-created_at')
    context = {
        'problems': problems, 
        'active_page': 'report_problem',
        'base_template': 'nomoklis_app/_tenant_base.html'
    }
    return render(request, 'nomoklis_app/problem_list.html', context)

@login_required
def landlord_problem_list_view(request):
    problems = ProblemReport.objects.filter(lease__property__owner=request.user).order_by('-created_at')
    context = {'problems': problems, 'active_page': 'problems_landlord', 'base_template': 'nomoklis_app/_landlord_base.html'}
    return render(request, 'nomoklis_app/landlord_problem_list.html', context)

@login_required
def landlord_problem_detail_view(request, problem_id):
    problem = get_object_or_404(ProblemReport, id=problem_id, lease__property__owner=request.user)
    updates = problem.updates.all()

    if request.method == 'POST':
        form = LandlordProblemUpdateForm(request.POST, instance=problem)
        if form.is_valid():
            # Išsaugome problemos atnaujinimus (statusą, kainą ir t.t.)
            form.save()

            # Jei buvo įvestas komentaras, sukuriame naują ProblemUpdate įrašą
            comment_text = form.cleaned_data.get('comment')
            if comment_text:
                ProblemUpdate.objects.create(
                    problem=problem,
                    author=request.user,
                    comment=comment_text
                )

            messages.success(request, "Problemos informacija atnaujinta.")
            return redirect('landlord_problem_detail', problem_id=problem.id)
    else: # GET metodas
        # Formą užpildome esamomis problemos reikšmėmis
        form = LandlordProblemUpdateForm(instance=problem)

    context = {
        'problem': problem,
        'updates': updates,
        'form': form,
        'active_page': 'problems_landlord',
        'base_template': 'nomoklis_app/_landlord_base.html'
    }
    return render(request, 'nomoklis_app/landlord_problem_detail.html', context)

@login_required
def tenant_problem_detail_view(request, problem_id):
    problem = get_object_or_404(ProblemReport, id=problem_id, lease__tenant=request.user)
    updates = problem.updates.all()

    if request.method == 'POST':
        form = TenantCommentForm(request.POST)
        if form.is_valid():
            new_update = form.save(commit=False)
            new_update.problem = problem
            new_update.author = request.user
            new_update.save()
            messages.success(request, "Jūsų komentaras pridėtas.")
            return redirect('tenant_problem_detail', problem_id=problem.id)
    else: # GET metodas
        form = TenantCommentForm()

    context = {
        'problem': problem,
        'updates': updates,
        'form': form,
        'active_page': 'report_problem',
        'base_template': 'nomoklis_app/_tenant_base.html'
    }

    return render(request, 'nomoklis_app/tenant_problem_detail.html', context)

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

@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(recipient=request.user)
    return render(request, 'nomoklis_app/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    # Nustatome, kur nukreipti vartotoją
    if isinstance(notification.content_object, ProblemReport):
        if request.user.profile.user_type == 'nuomotojas':
            return redirect('landlord_problem_detail', problem_id=notification.object_id)
        else:
            return redirect('tenant_problem_detail', problem_id=notification.object_id)
            
    # --- PAKEISTA DALIS ---
    elif isinstance(notification.content_object, RentalRequest):
        # Nukreipiame į naująjį sutarčių puslapį, nes užklausų puslapio nebėra
        return redirect('contracts')
    # --- PABAIGA ---
    
    # Paliekame numatytąjį nukreipimą, jei pranešimas neturi susijusio objekto
    return redirect('notification_list')

@login_required
def notifications_popup_view(request):
    notifications = Notification.objects.filter(recipient=request.user)[:5] # Paimame tik 5 naujausius
    return render(request, 'nomoklis_app/_notifications_popup.html', {'notifications': notifications})

@login_required
def toggle_save_property(request, property_id):
    if request.method == 'POST':
        prop = get_object_or_404(Property, id=property_id)
        profile = request.user.profile
        
        if prop in profile.saved_properties.all():
            profile.saved_properties.remove(prop)
            is_saved = False
        else:
            profile.saved_properties.add(prop)
            is_saved = True
            
        return JsonResponse({'is_saved': is_saved})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def saved_properties_view(request):
    saved_properties = request.user.profile.saved_properties.all()
    context = {
        'properties': saved_properties,
        'active_page': 'saved_properties'
    }
    return render(request, 'nomoklis_app/saved_properties.html', context)

@login_required
def tenant_terminate_lease_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, tenant=request.user)
    
    if request.method == 'POST':
        form = TenantTerminationForm(request.POST)
        if form.is_valid():
            termination_date = form.cleaned_data['termination_date']
            reason = form.cleaned_data['reason']
            
            # Atnaujiname sutartį
            lease.status = 'terminated'
            lease.end_date = termination_date
            lease.save()
            
            # Atlaisviname turtą
            lease.property.status = 'nuoma_pasibaigusi'
            lease.property.save()
            
            # Sukuriame pranešimą nuomotojui
            Notification.objects.create(
                recipient=lease.property.owner,
                message=f"Nuomininkas {request.user.get_full_name()} nutraukė sutartį objektui {lease.property.street}. Priežastis: {reason}",
                content_object=lease.property
            )
            
            messages.success(request, 'Nuomos sutartis sėkmingai nutraukta.')
            return redirect('nuomininkas_dashboard')
    else: # GET metodas
        form = TenantTerminationForm()

    return render(request, 'nomoklis_app/_tenant_terminate_lease_popup.html', {'form': form, 'lease': lease})

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

@login_required
def delete_rental_request_view(request, request_id):
    # Surandame užklausą, užtikrindami, kad ji priklauso prisijungusiam nuomotojui
    rental_request = get_object_or_404(RentalRequest, id=request_id, property__owner=request.user)
    
    # Ištriname objektą
    rental_request.delete()
    
    messages.success(request, 'Nuomos užklausa buvo sėkmingai ištrinta.')
    return redirect('rental_requests')

def _generate_contract_text(rental_request, lease_details):
    """
    Pagalbinė funkcija, kuri sugeneruoja pradinį sutarties tekstą,
    užpildydama jį maksimaliu kiekiu duomenų iš sistemos.
    """
    sutarties_data = date.today().strftime('%Y m. %m d.')
    
    # Šalių informacija
    landlord = rental_request.property.owner
    tenant = rental_request.tenant
    nuomotojas_vardas = landlord.get_full_name()
    nuomininkas_vardas = tenant.get_full_name()
    nuomotojas_adresas = landlord.profile.city or "(nenurodyta)"
    nuomininkas_adresas = tenant.profile.city or "(nenurodyta)"
    
    # Objekto informacija
    prop = rental_request.property
    buto_adresas = f"{prop.street}, {prop.city}"
    buto_plotas = prop.area
    
    # Nuomos sąlygos
    nuomos_kaina = rental_request.offered_price
    depozito_suma = lease_details.get('deposit_amount', rental_request.offered_price)
    mokejimo_diena = 20
    nuomos_pradzia = rental_request.start_date.strftime('%Y-%m-%d') if rental_request.start_date else "(nenurodyta)"
    nuomos_pabaiga = rental_request.end_date.strftime('%Y-%m-%d') if rental_request.end_date else "(neterminuota)"
    
    # Papildomi, bet dažnai tušti laukai
    nuomotojas_ak = "(nenurodyta)"
    nuomininkas_ak = "(nenurodyta)"
    buto_unikalus_nr = "(nenurodyta)"

    contract_text = f"""
GYVENAMŲJŲ PATALPŲ NUOMOS SUTARTIS
{sutarties_data}, {prop.city or 'Vilnius'}

{nuomotojas_vardas} (toliau sutartyje – Nuomotojas), a.k. {nuomotojas_ak}, gyvenantis (-i) adresu {nuomotojas_adresas} ir {nuomininkas_vardas} (toliau sutartyje – Nuomininkas), a.k. {nuomininkas_ak}, gyvenantis (-i) adresu {nuomininkas_adresas}, toliau kartu vadinami „Šalimis“, o kiekvienas atskirai – „Šalimi“, sudarė šią gyvenamųjų patalpų nuomos sutartį, toliau vadinamą „Sutartimi“:

1. SUTARTIES OBJEKTAS
1.1. Šia sutartimi Nuomotojas suteikia Nuomininkui laikinai, nuomos terminui, naudotis ir valdyti už mokestį gyvenamąsias patalpas – butą, gyvenamosios paskirties, esantį adresu {buto_adresas}, kurio unikalus numeris {buto_unikalus_nr}, plotas {buto_plotas} kv.m. (toliau sutartyje - butas), o Nuomininkas įsipareigoja mokėti nuomos mokestį.
1.2. Nuomininkas moka Nuomotojui už buto nuomą {nuomos_kaina:.2f} Eur (suma žodžiais).
1.3. Nuomininkas kiekvieną mėnesį moka Nuomotojui nuomos, buto komunalinių ir kitų paslaugų mokesčius, pagal pateiktas sąskaitas.

2. MOKĖJIMŲ IR ATSISKAITYMŲ PAGAL SUTARTĮ TVARKA
2.1. Nuomininkas kiekvieną mėnesį, ne vėliau kaip iki einamojo mėnesio {mokejimo_diena} dienos, sumoka Nuomotojui mėnesinį nuomos mokestį.
2.2. Nuomininkas kiekvieną mėnesį apmoka buto komunalinių ir kitų paslaugų mokesčius už praėjusį mėnesį, pagal apskaitos prietaisų parodymus bei pateiktas sąskaitas.
2.3. Pasibaigus šios sutarties terminui ar nutraukus ją prieš terminą, Nuomininkas sumoka visas Nuomotojui pagal šią sutartį mokėtinas sumas per penkias dienas nuo sutarties termino pasibaigimo ar sutarties nutraukimo dienos bei susidariusius įsiskolinimus.
2.4. Sutarties pasirašymo dieną Nuomininkas privalo sumokėti Nuomotojui įmoką už pirmąjį nuomos mėnesį bei {depozito_suma:.2f} Eur dydžio užstatą (depozitą), kuris, jeigu Nuomininkas laikosi visų įsipareigojimų, grąžinamas išsikraustant iš būsto ir esant sumokėjus visus priklausančius mokesčius.

3. ŠALIŲĮSIPAREIGOJIMAI
3.1. Pagal šią sutartį Nuomotojas įsipareigoja:
3.1.1. Perduoti Nuomininkui šios sutarties 1.1. punkte nurodytą butą. Butas perduodamos dalyvaujant abiem šalims ar jų įgaliotiems atstovams, kurie sudaro ir pasirašo buto perdavimo–priėmimo aktą (Priedas Nr1).
3.1.2. Pasibaigus nuomos sutarties terminui arba nutraukus šią sutartį, priimti iš Nuomininko nuomojamą butą sudarant perdavimo–priėmimo aktą;
3.1.3. Atlyginti Nuomininkui jo turėtas būtinąsias (pagrįstas dokumentais) nuomojamų buto pagerinimo išlaidas, padarytas raštišku Nuomotojo leidimu. Kai pagerinimai padaryti be Nuomotojo sutikimo arba šalys susitaria, jog Nuomininko buto pagerinimo išlaidos nebus atlyginamos, Nuomininkas neturi teisės į išlaidų, susijusių su buto pagerinimu, kompensavimą;
3.2. Pagal šią sutartį Nuomininkas įsipareigoja:
3.2.1. Laikytis bute ir visoje Nuomotojo teritorijoje vidaus darbo tvarkos, priešgaisrinės apsaugos, aplinkos apsaugos. Nuomininkas atsako už šių taisyklių bei normų nesilaikymo pasekmes ir atlygina dėl to atsiradusią žalą;
3.2.2. Be Nuomotojo raštiško sutikimo nesubnuomoti buto ar jų dalies.
3.2.3. Be Nuomotojo raštiško leidimo neperleisti šia sutartimi įgytų teisių ir pareigų tretiesiems asmenims, neįkeisti nuomos teisės ar kitaip jos nesuvaržyti;
3.2.4. Be Nuomotojo raštiško leidimo neperplanuoti ir nepertvarkyti buto ar jo dalies;
3.2.5. Suderinus su Nuomotoju, savo lėšomis atlikti buto bei vidaus inžinierinių tinklų priežiūrą ir einamąjį remontą.
3.2.6. Pilnai atlyginti Nuomotojui nuostolius, susijusius su buto pabloginimu, jeigu tai įvyksta dėl Nuomininko kaltės;
3.2.7. Ne vėliau kaip prieš 30 dienų iki šios sutarties galiojimo termino pasibaigimo, raštu pranešti Nuomotojui apie paliekamą butą;
3.2.8. Pasibaigus šios sutarties terminui arba ją nutraukus prieš terminą, per dvi darbo dienas perduoti Nuomotojui butą remiantis perdavimo-priėmimo aktu (Priedas Nr. 1).
3.2.9. Laiku mokėti Nuomotojui nuompinigius už naudojimąsi butu ir komunalinių bei kitų paslaugų mokesčius.
3.3. Šalių susitarimu, Nuomotojas, perspėjęs prieš 24 val. Nuomininką ir geranoriškai suderinęs laiką su Nuomininku, turi teisę aprodyti Nuomininko nuomojamą buto dalį tretiesiems asmenims nuomos ar buto pardavimo tikslais.

4. SUTARTIES GALIOJIMO TERMINAS IR NUTRAUKIMO TVARKA
4.1. Butas išnuomojamas nuo {nuomos_pradzia} iki {nuomos_pabaiga}.
4.2. Kiekviena sutarties šalis turi teisę nutraukti šią sutartį raštu įspėjusi apie tai kitą šalį prieš tris mėnesius.
4.3. Nuomotojui pranešus apie sutarties nutraukimą prieš mėnesį, Nuomotojas sumoka 1 (vieno) mėn. nuomos dydžio baudą.
4.4. Nuomotojas turi teisę vienašališkai ir neatlygintai nutraukti šią sutartį nesilaikant 4.2. punkte nurodyto įspėjimo termino, jeigu: Nuomininkas naudojasi daiktu ne pagal sutartį ar daikto paskirtį; tyčia ar dėl neatsargumo blogina daikto būklę; bent vieną mėnesį pilnai nesumoka nuomos ir kitų mokesčių pagal sutartį.
4.5. Nuomininkas turi teisę nutraukti šią Sutartį nesilaikant 4.2. punkte nurodyto įspėjimo termino, jeigu: Nuomotojas neperduoda buto Nuomininkui arba kliudo naudotis juo pagal jų paskirtį ir šios sutarties sąlygas; perduotas butas yra su trūkumais, kurie Nuomotojo nebuvo aptarti ir Nuomininkui nebuvo žinomi.

5. BAIGIAMOSIOS NUOSTATOS
5.1. Ši sutartis įsigalioja ir teisines pasekmes šalims sukelia nuo jos pasirašymo dienos.
5.2. Jeigu pasibaigus sutarties terminui Nuomininkas daugiau kaip dešimt dienų toliau naudojasi turtu, o Nuomotojas tam neprieštarauja, laikoma, kad sutartis tapo neterminuota.
5.3. Sutartis gali būti pakeista arba papildyta tik raštišku abiejų šalių susitarimu.

6. ŠALIŲ PARAŠAI


Nuomotojas: ____________________
({nuomotojas_vardas})


Nuomininkas: ____________________
({nuomininkas_vardas})
"""
    return contract_text

@login_required
def prepare_and_edit_contract_view(request, request_id):
    rental_request = get_object_or_404(RentalRequest, id=request_id, property__owner=request.user)

    if request.method == 'POST':
        form = PrepareContractForm(request.POST)
        if form.is_valid():
            lease = Lease.objects.create(
                property=rental_request.property,
                tenant=rental_request.tenant,
                status='active',
                rent_price=rental_request.offered_price,
                start_date=rental_request.start_date,
                end_date=rental_request.end_date,
                deposit_amount=form.cleaned_data['deposit_amount']
            )

            edited_contract_text = form.cleaned_data['contract_text']
            try:
                font_path = os.path.join(settings.BASE_DIR, 'DejaVuSans.ttf')
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font('DejaVu', '', font_path, uni=True)
                pdf.set_font('DejaVu', '', 10)
                pdf.multi_cell(0, 5, edited_contract_text)
                
                pdf_output = bytes(pdf.output())
                file_name = f'nuomos_sutartis_{{lease.id}}_{date.today()}.pdf'
                
                lease.contract_file.save(file_name, ContentFile(pdf_output), save=True)
            except Exception as e:
                messages.error(request, f"Įvyko klaida generuojant PDF: {e}")
                lease.delete()
                # Pataisytas nukreipimas klaidos atveju
                return redirect('nuomotojas_dashboard')

            rental_request.property.status = 'isnuomotas'
            rental_request.property.save()
            rental_request.status = 'accepted'
            rental_request.save()
            
            generate_invoice_url = reverse('generate_invoice', args=[lease.id])
            message_text = f"""
Sutartis su {lease.tenant.get_full_name()} sėkmingai sudaryta. 
            <a href="{generate_invoice_url}" class="font-bold text-blue-600 hover:underline">
                Sugeneruoti pirmąją sąskaitą.
            </a>
            """
            messages.success(request, mark_safe(message_text))

            # Pataisytas nukreipimas sėkmės atveju
            return redirect('nuomotojas_dashboard')

    else: # GET metodas
        initial_details = {
            'deposit_amount': rental_request.offered_price
        }
        initial_text = _generate_contract_text(rental_request, initial_details)
        initial_details['contract_text'] = initial_text
        
        form = PrepareContractForm(initial=initial_details)

    context = {
        'form': form,
        'rental_request': rental_request,
        'active_page': 'rental_requests' # Šį galime palikti, jis neįtakoja funkcijos
    }
    return render(request, 'nomoklis_app/prepare_contract.html', context)

@login_required
def generate_invoice_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, property__owner=request.user)
    today = date.today()

    if not lease.invoices.exists(): # Jei tai pirma sąskaita
        pass # Leidžiame generuoti
    elif Invoice.objects.filter(lease=lease, invoice_date__year=today.year, invoice_date__month=today.month).exists():
        messages.warning(request, "Šio mėnesio sąskaita šiai sutarčiai jau buvo sugeneruota.")
        return redirect('contracts') # Grįžtame į sutarčių sąrašą
    
    # --- SĄSKAITOS DUOMENŲ RUOŠIMAS ---
    total_amount = 0
    invoice_items = []
    
    is_first_invoice = not lease.invoices.exists()

    if is_first_invoice:
        # Pirmoji sąskaita generuojama pagal sutarties pradžios datą
        invoice_date_context = lease.start_date
        
        # Neleidžiame generuoti pirmos sąskaitos per anksti
        if today.year < invoice_date_context.year or (today.year == invoice_date_context.year and today.month < invoice_date_context.month):
             messages.error(request, f"Pirmąją sąskaitą už {invoice_date_context.strftime('%B')} mėn. galėsite sugeneruoti tik {invoice_date_context.strftime('%Y-%m')}.")
             return redirect('nuomotojas_dashboard')

        #Įtraukiame depozitą
        total_amount += lease.deposit_amount
        invoice_items.append({
            'name': 'Depozitas',
            'price': f"{lease.deposit_amount:.2f}"
        })
        
        # Skaičiuojame proporcinę nuomą
        if lease.start_date.day != 1:
            days_in_month = calendar.monthrange(invoice_date_context.year, invoice_date_context.month)[1]
            days_to_pay_for = days_in_month - lease.start_date.day + 1
            proportional_rent = (lease.rent_price / days_in_month) * days_to_pay_for
            total_amount += proportional_rent
            invoice_items.append({
                'name': f"Nuoma už {invoice_date_context.strftime('%B')} mėn. ({days_to_pay_for} d.)",
                'price': f"{proportional_rent:.2f}"
            })
        else: # Jei sutartis prasideda 1-ą dieną
            total_amount += lease.rent_price
            invoice_items.append({
                'name': f"Nuoma už {invoice_date_context.strftime('%B')} mėn.",
                'price': f"{lease.rent_price:.2f}"
            })
    else: # Ne pirmo mėnesio logika
        invoice_date_context = today
        # Tikriname, ar šio mėnesio sąskaita jau sugeneruota
        if Invoice.objects.filter(lease=lease, invoice_date__year=today.year, invoice_date__month=today.month).exists():
            messages.warning(request, "Šio mėnesio sąskaita šiai sutarčiai jau buvo sugeneruota.")
            return redirect('nuomotojas_dashboard')

        total_amount = lease.rent_price
        invoice_items.append({
            'name': f"Nuoma už {invoice_date_context.strftime('%B')} mėn.",
            'price': f"{lease.rent_price:.2f}"
        })
        
        last_month = today - timedelta(days=today.day)
        repair_costs = ProblemReport.objects.filter(
            lease=lease,
            status='isspresta',
            paid_by='nuomininkas',
            created_at__month=last_month.month,
            created_at__year=last_month.year
        ).aggregate(total=Sum('resolution_costs'))['total'] or 0

        if repair_costs > 0:
            total_amount += repair_costs
            invoice_items.append({
                'name': 'Remonto išlaidos',
                'price': f"{repair_costs:.2f}"
            })

    # --- PDF GENERAVIMAS ---
    # ... (PDF generavimo kodas lieka toks pat, kaip anksčiau)
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
    pdf.cell(95, 7, "Tiekėjas", 0, 0, 'L')
    pdf.cell(95, 7, "Pirkėjas", 0, 1, 'L')
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
    file_name = f'saskaita_{{invoice.id}}_{today.strftime("%Y_%m")}.pdf'
    
    invoice = Invoice.objects.create(
        lease=lease,
        invoice_date=today, # Sąskaitos data yra šiandienos
        due_date=due_date,
        amount=total_amount
    )
    invoice.invoice_file.save(file_name, ContentFile(pdf_output), save=True)
    
    messages.success(request, f"Sąskaita sėkmingai sugeneruota nuomininkui {lease.tenant.get_full_name()}.")
    return redirect('nuomotojas_dashboard')

@login_required
def lease_invoices_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id)
    # Patikriname, ar vartotojas yra susijęs su šia sutartimi
    if request.user != lease.tenant and request.user != lease.property.owner:
        messages.error(request, "Jūs neturite teisės peržiūrėti šios informacijos.")
        return redirect('dashboard_redirect')

    invoices = lease.invoices.order_by('-invoice_date')
    
    # --- PRIDĖKITE ŠIĄ DALĮ ---
    if request.user.profile.user_type == 'nuomotojas':
        base_template = 'nomoklis_app/_sidebar.html'
        active_page = 'tenants'
    else:
        base_template = 'nomoklis_app/_tenant_sidebar.html'
        active_page = 'dashboard'
    # --- PABAIGA ---
        
    context = {
        'lease': lease,
        'invoices': invoices,
        'base_template': base_template, # <-- NAUJAS KINTAMASIS
        'active_page': active_page
    }

    return render(request, 'nomoklis_app/lease_invoices.html', context)

@login_required
def rental_request_popup_view(request, request_id):
    rental_request = get_object_or_404(RentalRequest, id=request_id, property__owner=request.user)
    context = {
        'req': rental_request
    }
    return render(request, 'nomoklis_app/_rental_request_popup.html', context)

@login_required
def profile_redirect_view(request):
    """
    Nukreipia vartotoją į teisingą profilio puslapį pagal jo tipą.
    """
    if hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'nuomotojas':
            return redirect('landlord_profile')
        else:
            return redirect('tenant_profile')
    # Jei profilis kažkodėl neegzistuoja, nukreipiame į pagrindinį puslapį
    return redirect('index')

@login_required
def tenant_request_popup_view(request, request_id):
    rental_request = get_object_or_404(RentalRequest, id=request_id, tenant=request.user)
    context = {
        'req': rental_request
    }
    return render(request, 'nomoklis_app/_tenant_request_popup.html', context)

@login_required
def cancel_rental_request_view(request, request_id):
    rental_request = get_object_or_404(RentalRequest, id=request_id, tenant=request.user)
    if rental_request.status == 'pending':
        rental_request.delete()
        messages.success(request, f'Jūsų užklausa dėl "{rental_request.property}" buvo sėkmingai atšaukta.')
    else:
        messages.error(request, 'Šios užklausos atšaukti nebegalima.')
    return redirect('nuomininkas_dashboard')

@login_required
def view_and_sign_contract(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id)
    if request.user != lease.tenant and request.user != lease.property.owner:
        messages.error(request, "Jūs neturite teisės peržiūrėti šios sutarties.")
        return redirect('dashboard_redirect')

    # PATAISYMAS: Teisingai sugeneruojame kambario pavadinimą ir perduodame jį į šabloną
    user1_id = lease.property.owner.id
    user2_id = lease.tenant.id
    encoded_room_name = encode_room_name(user1_id, user2_id)
    # Pataisymo pabaiga

    utilities_form = UtilitiesPaymentForm(instance=lease)

    if request.method == 'POST':
        if 'sign_contract' in request.POST:
            if request.user == lease.tenant:
                lease.is_signed_by_tenant = True
            elif request.user == lease.property.owner:
                lease.is_signed_by_landlord = True
            
            lease.save()

            if lease.is_signed_by_tenant and lease.is_signed_by_landlord:
                lease.status = 'active'
                lease.property.status = 'isnuomotas'
                lease.property.save()
                lease.save()
                messages.success(request, "Sutartis sėkmingai aktyvuota!")
            else:
                messages.success(request, "Sėkmingai patvirtinote sutartį.")
            
            return redirect('view_and_sign_contract', lease_id=lease.id)

        if 'update_utilities' in request.POST and request.user == lease.property.owner:
            utilities_form = UtilitiesPaymentForm(request.POST, instance=lease)
            if utilities_form.is_valid():
                utilities_form.save()
                messages.success(request, "Mokesčių mokėtojo informacija atnaujinta.")
                return redirect('view_and_sign_contract', lease_id=lease.id)

    context = {
        'lease': lease,
        'utilities_form': utilities_form,
        'room_name': encoded_room_name, # <-- Perduodame sugeneruotą pavadinimą
        'active_page': 'dashboard',
    }
    return render(request, 'nomoklis_app/view_contract.html', context)

@login_required
def submit_meter_readings_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, tenant=request.user)
    if lease.utilities_paid_by != 'landlord':
        messages.error(request, "Jums nereikia siųsti skaitiklių rodmenų.")
        return redirect('nuomininkas_dashboard')

    if request.method == 'POST':
        form = MeterReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            reading.lease = lease
            reading.save()

            # Sukuriame pranešimą nuomotojui
            Notification.objects.create(
                recipient=lease.property.owner,
                message=f"Nuomininkas {request.user.get_full_name()} pateikė skaitiklių rodmenis objektui {lease.property.street}.",
                content_object=reading.lease
            )

            messages.success(request, "Skaitiklių rodmenys sėkmingai išsiųsti.")
            return redirect('nuomininkas_dashboard')
    else: # GET metodas
        form = MeterReadingForm()

    context = {
        'form': form,
        'lease': lease,
        'active_page': 'dashboard'
    }
    return render(request, 'nomoklis_app/submit_meter_readings.html', context)

@login_required
def latest_readings_popup_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, property__owner=request.user)
    latest_reading = MeterReading.objects.filter(lease=lease).order_by('-reading_date').first()
    context = {
        'reading': latest_reading
    }
    return render(request, 'nomoklis_app/_latest_readings_popup.html', context)

@login_required
def prepare_invoice_popup_view(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id, property__owner=request.user)
    today = date.today()

    # Patikriname, ar šio mėnesio sąskaita jau egzistuoja
    if Invoice.objects.filter(lease=lease, invoice_date__year=today.year, invoice_date__month=today.month).exists():
        return render(request, 'nomoklis_app/_invoice_exists_popup.html')

    if request.method == 'POST':
        formset = UtilityBillFormSet(request.POST, prefix='utilities')
        if formset.is_valid():
            invoice_items = []
            total_utilities = 0
            
            # Įtraukiame nuomą kaip pirmą eilutę
            total_amount = lease.rent_price
            invoice_items.append({
                'name': f"Nuoma už {today.strftime('%B')} mėn.",
                'price': f"{lease.rent_price:.2f}"
            })

            # Pridedame komunalinius mokesčius iš formos
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    description = form.cleaned_data.get('description')
                    amount = form.cleaned_data.get('amount')
                    if description and amount:
                        total_utilities += amount
                        invoice_items.append({'name': description, 'price': f"{amount:.2f}"})
            
            total_amount += total_utilities
            
            # 1. Sukuriame pagrindinį Invoice objektą
            # Assuming lease has payment_day attribute
            due_date = today.replace(day=getattr(lease, 'payment_day', 15))
            invoice = Invoice.objects.create(lease=lease, due_date=due_date, amount=total_amount)

            # 2. Išsaugome detalizuotas komunalinių eilučių sumas
            for item in invoice_items:
                if "Nuoma už" not in item['name']: # Nuomos eilutės nesaugome kaip UtilityBill
                    UtilityBill.objects.create(invoice=invoice, description=item['name'], amount=Decimal(item['price']))
            
            # 3. Generuojame PDF
            pdf = FPDF()
            pdf.add_page()
            
            regular_font_path = os.path.join(settings.BASE_DIR, 'DejaVuSans.ttf')
            pdf.add_font('DejaVu', '', regular_font_path, uni=True)
            bold_font_path = os.path.join(settings.BASE_DIR, 'dejavu-sans', 'DejaVuSans-Bold.ttf')
            pdf.add_font('DejaVu', 'B', bold_font_path, uni=True)

            pdf.set_font('DejaVu', 'B', 20)
            pdf.cell(0, 10, f"Sąskaita Nr. {invoice.id}-{today.strftime('%Y%m')}", 0, 1, 'L')
            pdf.set_font('DejaVu', '', 10)
            pdf.cell(0, 5, f"Išrašymo data: {today.strftime('%Y-%m-%d')}", 0, 1, 'L')
            pdf.ln(10)

            pdf.set_font('DejaVu', 'B', 11)
            pdf.cell(95, 7, "Tiekėjas", 0, 0, 'L')
            pdf.cell(95, 7, "Pirkėjas", 0, 1, 'L')
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
            file_name = f'saskaita_{{invoice.id}}_{today.strftime("%Y_%m")}.pdf'
            invoice.invoice_file.save(file_name, ContentFile(pdf_output), save=True)
            
            messages.success(request, "Sąskaita su komunaliniais mokesčiais sėkmingai sugeneruota.")
            return redirect('contracts')
    else: # GET metodas
        formset = UtilityBillFormSet(prefix='utilities')

    context = {
        'lease': lease,
        'formset': formset
    }
    return render(request, 'nomoklis_app/_generate_invoice_with_utilities_popup.html', context)

@login_required
def delete_invoice_view(request, invoice_id):
    # Surandame sąskaitą ir užtikriname, kad ji priklauso prisijungusiam nuomotojui
    invoice = get_object_or_404(Invoice, id=invoice_id, lease__property__owner=request.user)
    
    # Išsaugome sutarties ID, kad žinotume, kur grįžti
    lease_id = invoice.lease.id

    # Leidžiame trinti tik neapmokėtas sąskaitas
    if not invoice.is_paid:
        # Ištriname ir susijusį PDF failą
        if invoice.invoice_file:
            invoice.invoice_file.delete(save=False)
        
        invoice.delete()
        messages.success(request, "Sąskaita sėkmingai ištrinta.")
    else:
        messages.error(request, "Negalima ištrinti apmokėtos sąskaitos.")
        
    # Paliekame tik vieną teisingą 'return' eilutę
    return redirect('lease_invoices', lease_id=lease_id)

@login_required
def tenant_lease_archive_view(request):
    # Gauname visas pasibaigusias sutartis
    past_leases_qs = Lease.objects.filter(
        Q(tenant=request.user) &
        (Q(status='terminated') | Q(end_date__lt=timezone.now().date()))
    ).order_by('-end_date').distinct()

    # Atrenkame tik tas, kurios jau turi atsiliepimą
    reviewed_lease_ids = set(PropertyReview.objects.filter(lease__in=past_leases_qs).values_list('lease_id', flat=True))
    archived_leases = [lease for lease in past_leases_qs if lease.id in reviewed_lease_ids]

    context = {
        'archived_leases': archived_leases,
        'active_page': 'dashboard', # Paliekame, kad meniu punktas liktų aktyvus
    }
    return render(request, 'nomoklis_app/tenant_lease_archive.html', context)

def property_locations_api(request):
    """
    API prieiga, kuri grąžina NT objektų koordinates ir pagrindinę informaciją
    JSON formatu, kad juos būtų galima atvaizduoti žemėlapyje.
    """
    properties = Property.objects.filter(
        status='paruostas', 
        latitude__isnull=False, 
        longitude__isnull=False
    )

    property_list = []
    for prop in properties:
        # Gauname pirmąją nuotrauką, jei ji yra
        first_image = prop.images.first()
        image_url = first_image.image.url if first_image else None

        prop_data = {
            'lat': float(prop.latitude),
            'lon': float(prop.longitude),
            'title': f"{prop.street} {prop.house_number}, {prop.city}",
            'price': f"{prop.rent_price} €/mėn.",
            'popup_url': reverse('property_detail_view', args=[prop.id]),
            # --- PRIDĖTI LAUKAI ---
            'property_type': prop.get_property_type_display(),
            'image_url': image_url,
            'rooms': prop.rooms,
            'area': prop.area,
        }
        property_list.append(prop_data)

    return JsonResponse(property_list, safe=False)

@login_required
@require_POST
def delete_property_image(request, image_id):
    image = get_object_or_404(PropertyImage, id=image_id)
    # Patikriname, ar vartotojas yra nuotraukos savininkas
    if image.property.owner != request.user:
        return JsonResponse({'status': 'error', 'message': 'Neturite teisės ištrinti šios nuotraukos.'}, status=403)
    
    # Ištriname failą iš media aplanko ir įrašą iš duomenų bazės
    image.image.delete() # Svarbu ištrinti ir patį failą
    image.delete() 
    
    return JsonResponse({'status': 'success', 'message': 'Nuotrauka sėkmingai ištrinta.'})

@login_required(login_url='/login/')
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    """
    Atvaizduoja administratoriaus panelės puslapį su realiais duomenimis.
    Prieinamas tik prisijungusiems supervartotojams.
    """
    now = timezone.now()
    current_month = now.month
    current_year = now.year

    # 1. Pajamos iš sąskaitų apmokėjimo
    invoice_income = Invoice.objects.filter(
        is_paid=True,
        invoice_date__month=current_month,
        invoice_date__year=current_year
    ).aggregate(total=Sum('amount'))['total'] or 0

    # 2. Pajamos iš skelbimų aktyvavimo
    system_settings = SystemSettings.objects.first()
    listing_price = system_settings.listing_price if system_settings else Decimal('0.00')
    paid_listings_count = Property.objects.filter(
        is_paid_listing=True,
        paid_at__month=current_month,
        paid_at__year=current_year
    ).count()
    listing_income = paid_listings_count * listing_price

    total_monthly_income = (invoice_income + listing_income)

    """
    Atvaizduoja administratoriaus panelės puslapį su realiais duomenimis.
    Prieinamas tik prisijungusiems supervartotojams.
    """
    # --- Duomenys statistikoms ir grafikams (šis kodas lieka toks pat) ---
    six_months_ago = timezone.now() - timedelta(days=180)
    user_growth_data = User.objects.filter(date_joined__gte=six_months_ago) \
        .annotate(month=TruncMonth('date_joined')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')
    revenue_data = Invoice.objects.filter(is_paid=True, invoice_date__gte=six_months_ago) \
        .annotate(month=TruncMonth('invoice_date')) \
        .values('month') \
        .annotate(total=Sum('amount')) \
        .order_by('month')
    
    months_labels = []
    current_date = timezone.now().replace(day=1)
    for i in range(5, -1, -1):
        month_date = current_date - timedelta(days=i*30)
        months_labels.append(month_date.strftime("%B"))
    
    user_chart_data = [0] * 6
    for entry in user_growth_data:
        month_name = entry['month'].strftime("%B")
        if month_name in months_labels:
            index = months_labels.index(month_name)
            user_chart_data[index] = entry['count']
    
    revenue_chart_data = [0.0] * 6
    for entry in revenue_data:
        month_name = entry['month'].strftime("%B")
        if month_name in months_labels:
            index = months_labels.index(month_name)
            revenue_chart_data[index] = float(entry['total'])

    # --- NAUJA DALIS: Duomenys "Naujausiems įvykiams" ---
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_properties = Property.objects.order_by('-created_at')[:5]

    # Sujungiame vartotojus ir NT objektus į vieną sąrašą
    # Kiekvienam elementui priskiriame tipą ir laiko žymą
    combined_events = []
    for user in recent_users:
        combined_events.append({'type': 'user', 'timestamp': user.date_joined, 'object': user})
    for prop in recent_properties:
        combined_events.append({'type': 'property', 'timestamp': prop.created_at, 'object': prop})

    # Surūšiuojame bendrą sąrašą pagal laiko žymą (nuo naujausio)
    sorted_events = sorted(combined_events, key=lambda x: x['timestamp'], reverse=True)

    # --- NAUJA DALIS: Duomenys "Reikalinga peržiūra" ---
    # Tarkime, kad naujai sukurti objektai turi statusą 'draft', kurį adminas turi patvirtinti
    pending_properties = Property.objects.filter(status='draft').order_by('-created_at')


    context = {
        # Statistikos kortelės
        'total_users': User.objects.count(),
        'total_properties': Property.objects.count(),
        'active_leases': Lease.objects.filter(status='active').count(),
        'monthly_income': total_monthly_income,
        'active_page': 'dashboard',
        # Duomenys grafikams
        'user_growth_labels': json.dumps(months_labels),
        'user_growth_data': json.dumps(user_chart_data),
        'revenue_labels': json.dumps(months_labels),
        'revenue_data': json.dumps(revenue_chart_data),
        
        # Duomenys įvykių blokams
        'recent_events': sorted_events[:5], # Paimame 5 naujausius įvykius
        'pending_properties': pending_properties,
    }
    return render(request, 'nomoklis_app/admin_dashboard.html', context)

@login_required(login_url='/login/')
@user_passes_test(lambda u: u.is_superuser)
def admin_users_list(request):
    # Naudojame .select_related('profile'), kad išvengtume papildomų užklausų į DB cikle
    all_users = User.objects.all().select_related('profile').order_by('-date_joined')
    context = {
        'users': all_users,
        'active_page': 'users', # Kad sidebar'e būtų aktyvuota teisinga nuoroda
    }
    return render(request, 'nomoklis_app/admin_users_list.html', context)

@login_required(login_url='/login/')
@user_passes_test(lambda u: u.is_superuser)
def admin_properties_list(request):
    """
    Atvaizduoja NT objektų sąrašą administratoriaus panelėje su paieška ir filtrais.
    """
    all_properties = Property.objects.all().select_related('owner').order_by('-created_at')

    # Paieškos logika
    query = request.GET.get('q')
    if query:
        all_properties = all_properties.filter(
            Q(street__icontains=query) | Q(city__icontains=query) |
            Q(owner__first_name__icontains=query) | Q(owner__last_name__icontains=query) |
            Q(owner__email__icontains=query)
        )

    # Filtravimo pagal būseną logika
    status_filter = request.GET.get('status')
    if status_filter:
        all_properties = all_properties.filter(status=status_filter)

    context = {
        'properties': all_properties,
        'active_page': 'properties',
        'property_statuses': Property.STATUS_CHOICES, # Perduodame būsenų sąrašą į šabloną
    }
    return render(request, 'nomoklis_app/admin_properties_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def admin_update_property_status(request, property_id):
    """
    Apdoroja NT objekto būsenos atnaujinimą iš administratoriaus panelės.
    """
    prop = get_object_or_404(Property, id=property_id)
    new_status = request.POST.get('status')

    # Patikriname, ar gauta būsena yra leistina
    valid_statuses = [choice[0] for choice in Property.STATUS_CHOICES]
    if new_status in valid_statuses:
        prop.status = new_status
        prop.save(update_fields=['status'])
        messages.success(request, f'Objekto "{prop}" būsena sėkmingai atnaujinta.')
    else:
        messages.error(request, 'Pateikta negalima būsenos reikšmė.')

    return redirect('admin_properties_list')

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def admin_delete_property(request, property_id):
    """
    Apdoroja NT objekto ištrynimą iš administratoriaus panelės.
    """
    prop = get_object_or_404(Property, id=property_id)
    prop_address = str(prop)
    prop.delete()
    messages.success(request, f'Objektas "{prop_address}" buvo sėkmingai ištrintas.')
    return redirect('admin_properties_list')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_system_settings_view(request):
    # Gauname vienintelį nustatymų objektą arba sukuriame naują, jei jo nėra
    settings, created = SystemSettings.objects.get_or_create()

    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sistemos nustatymai sėkmingai atnaujinti.')
            return redirect('admin_system_settings')
    else:
        form = SystemSettingsForm(instance=settings)

    context = {
        'form': form,
        'active_page': 'settings',
    }
    return render(request, 'nomoklis_app/admin_system_settings.html', context)



@login_required
def create_checkout_session(request, invoice_id):
    """
    Inicijuoja Stripe Checkout sesiją konkrečiai sąskaitai.
    """
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        # Saugumo patikra, ar vartotojas bando apmokėti savo sąskaitą
        if invoice.lease.tenant != request.user:
            return JsonResponse({'error': 'Neturite teisės apmokėti šios sąskaitos.'}, status=403)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'Sąskaita Nr. {invoice.id} už {invoice.invoice_date.strftime("%Y-%m")}',
                        },
                        # Suma turi būti nurodyta centais
                        'unit_amount': int(invoice.amount * 100),
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            # Svarbu: perduodame sąskaitos ID, kad webhook'as žinotų, ką pažymėti kaip apmokėtą
            client_reference_id=invoice.id,
            success_url=request.build_absolute_uri(reverse('payment_success')),
            cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def payment_success_view(request):
    """
    Puslapis, kurį vartotojas pamato po sėkmingo apmokėjimo.
    """
    # Patikriname, ar sesijoje yra duomenų apie NT objekto redagavimą
    property_edit_data = request.session.get('property_edit_data')
    property_id_from_session = request.session.get('property_id_for_payment')

    if property_edit_data and property_id_from_session:
        prop = get_object_or_404(Property, id=property_id_from_session)
        # Atkuriame Decimal laukus
        property_edit_data['rent_price'] = Decimal(property_edit_data['rent_price'])
        property_edit_data['area'] = Decimal(property_edit_data['area'])
        
        form = PropertyForm(property_edit_data, instance=prop)
        if form.is_valid():
            form.save() # Išsaugome pakeitimus po sėkmingo mokėjimo
            messages.success(request, "Apmokėjimas sėkmingas! Jūsų NT objekto būsena atnaujinta.")
        
        # Išvalome sesijos duomenis
        del request.session['property_edit_data']
        del request.session['property_id_for_payment']
    else:
        messages.success(request, "Apmokėjimas sėkmingas! Jūsų sąskaitos būsena bus greitai atnaujinta.")
    
    # Patikriname vartotojo tipą ir nukreipiame į teisingą panelę
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'nuomotojas':
            return redirect('nuomotojas_dashboard')
    
    # Numatytasis nukreipimas nuomininkui arba neprisijungusiam vartotojui
    return redirect('nuomininkas_dashboard')


def payment_cancel_view(request):
    """
    Puslapis, kurį vartotojas pamato atšaukęs apmokėjimą.
    """
    messages.warning(request, "Apmokėjimas buvo atšauktas.")
    
    # Išvalome sesijos duomenis, jei jie buvo nustatyti
    if 'property_edit_data' in request.session:
        del request.session['property_edit_data']
    if 'property_id_for_payment' in request.session:
        del request.session['property_id_for_payment']
    
    # Patikriname vartotojo tipą ir nukreipiame į teisingą panelę
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'nuomotojas':
            return redirect('nuomotojas_dashboard')
    
    # Numatytasis nukreipimas nuomininkui arba neprisijungusiam vartotojui
    return redirect('nuomininkas_dashboard')


@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    # Sukuriame logger'į, kad galėtume matyti klaidas
    logger = logging.getLogger(__name__)

    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Neteisingas payload
        logger.error(f"Stripe webhook ValueError: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Neteisingas signature
        logger.error(f"Stripe webhook SignatureVerificationError: {e}")
        return HttpResponse(status=400)

    # Apdorojame 'checkout.session.completed' įvykį
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        payment_type = metadata.get('payment_type')

        if payment_type == 'property_activation':
            property_id = metadata.get('property_id')
            if property_id is not None:
                # Konvertuojame property_id į integer, nes iš Stripe metaduomenų jis ateina kaip string
                property_id_int = int(property_id)
                logger.info(f"Gautas property_activation webhook'as. Konvertuotas Property ID: {property_id_int}")
                try:
                    prop = Property.objects.get(id=property_id_int)
                    # Atnaujiname tik jei dar neatnaujinta, kad išvengti pasikartojančių webhook'ų
                    if not prop.is_paid_listing:
                        prop.is_paid_listing = True
                        prop.paid_at = timezone.now() # Išsaugome apmokėjimo datą
                        # Būsena 'paruostas' jau turėtų būti nustatyta prieš mokėjimą
                        prop.save(update_fields=['is_paid_listing', 'paid_at'])
                        logger.info(f"Objektas {prop.id} sėkmingai pažymėtas kaip apmokėtas.")

                    # Sukuriame pranešimą nuomotojui
                    Notification.objects.create(
                        recipient=prop.owner,
                        message=f'Jūsų skelbimas "{prop}" sėkmingai aktyvuotas!',
                        content_object=prop
                    )
                except Property.DoesNotExist: # Jei objektas su tokiu ID nerastas
                    logger.error(f"Stripe webhook klaida: bandyta aktyvuoti neegzistuojantį objektą. Property ID: {property_id_int}")
                    pass # Objektas nerastas
        else:
            # Esama sąskaitų apmokėjimo logika
            invoice_id = session.get('client_reference_id')
            if invoice_id:
                try:
                    invoice = Invoice.objects.get(id=invoice_id)
                    invoice.is_paid = True
                    invoice.save()
                except Invoice.DoesNotExist:
                    # Jei sąskaita nerasta, loguojame įvykį
                    logger.error(f"Stripe webhook klaida: nepavyko rasti sąskaitos su ID: {invoice_id}")
                    pass

    return HttpResponse(status=200)

@login_required
def mark_invoice_as_paid(request, invoice_id):
    """
    Pažymi sąskaitą kaip apmokėtą.
    Tik turto savininkas (nuomotojas) gali atlikti šį veiksmą.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Patikriname, ar vartotojas yra nuomos sutarties savininkas
    if request.user != invoice.lease.property.owner:
        messages.error(request, 'Jūs neturite teisės atlikti šio veiksmo.')
        return redirect('lease_invoices', lease_id=invoice.lease.id)

    # Pakeičiame būseną ir išsaugome
    invoice.is_paid = True
    invoice.save()

    messages.success(request, f'Sąskaita sėkmingai pažymėta kaip apmokėta.')
    return redirect('lease_invoices', lease_id=invoice.lease.id)

@login_required
def choose_role_view(request):
    # Bandome gauti profilį. Jei jo nėra, sukuriame naują.
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Jei profilis jau turėjo rolę, nukreipiame į panelę
    if not created and profile.user_type:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = UserTypeForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Jūsų rolė sėkmingai pasirinkta!')
            return redirect('dashboard_redirect')
    else: # GET metodas
        form = UserTypeForm(instance=profile)
    
    return render(request, 'nomoklis_app/choose_role.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Jūs sėkmingai atsijungėte.")
    return redirect('index')

@login_required
def delete_account_view(request):
    """
    Atvaizduoja paskyros trynimo patvirtinimo puslapį ir apdoroja trynimą.
    """
    # Nustatome bazinį šabloną pagal vartotojo tipą
    base_template_name = 'nomoklis_app/_tenant_base.html' # Numatytasis
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'nuomotojas':
            base_template_name = 'nomoklis_app/_landlord_base.html'

    if request.method == 'POST':
        user_to_delete = request.user
        user_to_delete.delete()    # Ištriname vartotoją
        logout(request)  # Atjungiame vartotoją po ištrynimo
        messages.success(request, 'Jūsų paskyra buvo sėkmingai ir negrįžtamai ištrinta.')
        return redirect('index') # Nukreipiame į pradinį puslapį

    context = {
        'base_template': base_template_name
    }
    return render(request, 'nomoklis_app/delete_account_confirm.html', context)

@login_required
def change_password_view(request):
    """
    Atvaizduoja ir apdoroja slaptažodžio keitimo formą.
    Parenka tinkamą formą priklausomai nuo to, ar vartotojas turi nustatytą slaptažodį.
    """
    if request.user.has_usable_password():
        form_class = PasswordChangeForm
    else:
        form_class = SetPasswordForm

    if request.method == 'POST':
        form = form_class(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Svarbu atnaujinti sesiją, kad vartotojas nebūtų atjungtas
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Jūsų slaptažodis sėkmingai pakeistas!')
            # Nukreipiame į profilio redagavimo puslapį
            if request.user.profile.user_type == 'nuomotojas':
                return redirect('landlord_profile_edit')
            else:
                return redirect('tenant_profile_edit')
    else:
        form = form_class(user=request.user)

    # Nustatome bazinį šabloną pagal vartotojo tipą
    base_template = 'nomoklis_app/_tenant_base.html' if request.user.profile.user_type == 'nuomininkas' else 'nomoklis_app/_landlord_base.html'

    context = {
        'form': form,
        'base_template': base_template,
        'active_page': 'profile',
        'password_help_texts': password_validators_help_texts(),
    }
    return render(request, 'nomoklis_app/change_password.html', context)


@login_required
def create_support_ticket_view(request):
    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            messages.success(request, 'Jūsų užklausa sėkmingai išsiųsta administracijai.')
            return redirect('support_ticket_list')
    else: # GET metodas
        form = SupportTicketForm()

    base_template = 'nomoklis_app/_tenant_base.html'
    if request.user.profile.user_type == 'nuomotojas':
        base_template = 'nomoklis_app/_landlord_base.html'

    context = {
        'form': form,
        'active_page': 'support',
        'base_template': base_template,
    }
    return render(request, 'nomoklis_app/create_support_ticket.html', context)

@login_required
def support_ticket_list_view(request):
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    base_template = 'nomoklis_app/_tenant_base.html'
    if request.user.profile.user_type == 'nuomotojas':
        base_template = 'nomoklis_app/_landlord_base.html'

    context = {
        'tickets': tickets,
        'active_page': 'support',
        'base_template': base_template,
    }
    return render(request, 'nomoklis_app/support_ticket_list.html', context)

@login_required
def delete_property_view(request, property_id):
    prop = get_object_or_404(Property, id=property_id, owner=request.user)
    if request.method == 'POST':
        prop.delete()
        messages.success(request, 'NT objektas sėkmingai ištrintas!')
        return redirect('my_properties')
    return redirect('my_properties')

@login_required
def support_ticket_detail_view(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id, user=request.user)
    updates = ticket.updates.all()
    if request.method == 'POST':
        form = SupportTicketUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.ticket = ticket
            update.user = request.user
            update.save()
            messages.success(request, 'Jūsų atsakymas išsiųstas.')
            return redirect('support_ticket_detail', ticket_id=ticket.id)
    else:
        form = SupportTicketUpdateForm()

    base_template = 'nomoklis_app/_tenant_base.html'
    if request.user.profile.user_type == 'nuomotojas':
        base_template = 'nomoklis_app/_landlord_base.html'

    context = {
        'ticket': ticket,
        'updates': updates,
        'form': form,
        'active_page': 'support',
        'base_template': base_template,
    }
    return render(request, 'nomoklis_app/support_ticket_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_support_ticket_list_view(request):
    tickets = SupportTicket.objects.all().order_by('-created_at')
    context = {
        'tickets': tickets,
        'active_page': 'support_tickets',
    }
    return render(request, 'nomoklis_app/admin_support_ticket_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_support_ticket_detail_view(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    updates = ticket.updates.all()
    if request.method == 'POST':
        form = AdminSupportTicketMessageForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.ticket = ticket
            update.user = request.user # Admin user
            update.save()
            
            # Pakeičiame statusą, jei adminas pasirinko
            new_status = request.POST.get('status')
            if new_status and new_status != ticket.status:
                ticket.status = new_status
                ticket.save()
                # Pranešimas vartotojui apie statuso pasikeitimą
                SupportTicketUpdate.objects.create(
                    ticket=ticket, 
                    user=request.user, 
                    comment=f"Būsena pakeista į '{ticket.get_status_display()}'",
                    is_internal=True # Vartotojas nemato šio įrašo
                )

            messages.success(request, 'Atsakymas išsiųstas vartotojui.')
            return redirect('admin_support_ticket_detail', ticket_id=ticket.id)
    else: # GET metodas
        form = AdminSupportTicketMessageForm()

    status_form = AdminSupportTicketUpdateForm(instance=ticket)

    context = {
        'ticket': ticket,
        'updates': updates,
        'form': form,
        'status_form': status_form,
        'active_page': 'support_tickets',
    }
    return render(request, 'nomoklis_app/admin_support_ticket_detail.html', context)
