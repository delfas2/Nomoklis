import io
import os
from datetime import date
from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MaxValueValidator, MinValueValidator, ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable


class Property(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ('butas', 'Butas'),
        ('namas', 'Namas'),
        ('kambarys', 'Kambarys bute'),
    ]
    STATUS_CHOICES = [
        ('paruostas', 'Paruoštas nuomai'),
        ('remontas', 'Atliekamas remontas'),
        ('isnuomotas', 'Išnuomotas'),
        ('nepasiekiamas', 'Nepasiekiamas'),
        ('nuoma_pasibaigusi', 'Pasibaigusi nuoma'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    street = models.CharField(max_length=255)
    flat_number = models.CharField("Buto numeris", max_length=10, blank=True)
    house_number = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    district = models.CharField("Rajonas", max_length=100, blank=True)
    area = models.DecimalField(max_digits=8, decimal_places=2)
    rooms = models.PositiveIntegerField(blank=True, null=True)
    floor = models.IntegerField(blank=True, null=True)
    total_floors = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    rent_price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_walkthrough = models.BooleanField(default=False, verbose_name="Ar kambarys pereinamas?")
    has_balcony = models.BooleanField(default=False, verbose_name="Balkonas")
    has_parking = models.BooleanField(default=False, verbose_name="Parkavimo vieta")
    pets_allowed = models.BooleanField(default=False, verbose_name="Leidžiami gyvūnai")
    is_furnished = models.BooleanField(default=False, verbose_name="Su baldais")
    has_appliances = models.BooleanField(default=False, verbose_name="Su buitine technika")
    residence_declaration_allowed = models.BooleanField(default=False, verbose_name="Leidžiama deklaruoti gyvenamąją vietą")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # NAUJI LAUKAI KOORDINATĖMS
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_paid_listing = models.BooleanField(default=False, verbose_name="Apmokėtas skelbimas")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Apmokėjimo data")

    def __str__(self):
        address = f"{self.street} {self.house_number}"
        if self.flat_number:
            address += f"-{self.flat_number}"
        address += f", {self.city}"
        return address

    def save(self, *args, **kwargs):
        # Tikriname, ar adresas pasikeitė, kad be reikalo nekviesti API
        address_changed = True
        if self.pk is not None:
            orig = Property.objects.get(pk=self.pk)
            if orig.street == self.street and orig.house_number == self.house_number and orig.city == self.city:
                address_changed = False
        
        # Geokoduojame adresą tik jei jis pasikeitė arba objektas naujas
        if address_changed:
            try:
                full_address = f"{self.street} {self.house_number}, {self.city}, Lithuania"
                geolocator = Nominatim(user_agent="nomoklis_v1") # Būtina nurodyti unikalų pavadinimą
                location = geolocator.geocode(full_address, timeout=10)
                if location:
                    self.latitude = location.latitude
                    self.longitude = location.longitude
                else:
                    self.latitude = None
                    self.longitude = None
            except (GeocoderTimedOut, GeocoderUnavailable):
                # Jei paslauga nepasiekiama, paliekame koordinates tuščias
                self.latitude = None
                self.longitude = None

        super().save(*args, **kwargs)

class Profile(models.Model):
    USER_TYPE_CHOICES = (
        ('nuomininkas', 'Nuomininkas'),
        ('nuomotojas', 'Nuomotojas'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=12, choices=USER_TYPE_CHOICES, null=True, blank=True, default=None)
    
    profile_image = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg', verbose_name="Profilio nuotrauka")
    about_me = models.TextField(blank=True, null=True, verbose_name="Apie mane")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Miestas")
    is_verified = models.BooleanField(default=False, verbose_name="Patvirtintas")
    
    saved_properties = models.ManyToManyField(Property, blank=True, related_name='saved_by')

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        # Tikriname, ar įkelta nauja profilio nuotrauka
        if self.profile_image and hasattr(self.profile_image.file, 'content_type'):
            img = Image.open(self.profile_image)

            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            img.thumbnail((300, 300), Image.Resampling.LANCZOS)

            thumb_io = io.BytesIO()
            img.save(thumb_io, 'JPEG', quality=85)

            filename, _ = os.path.splitext(os.path.basename(self.profile_image.name))
            new_filename = filename + '.jpg'

            self.profile_image.save(new_filename, ContentFile(thumb_io.getvalue()), save=False)

        super().save(*args, **kwargs)

# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)

# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def save_user_profile(sender, instance, **kwargs):
#     if hasattr(instance, 'profile'):
#         instance.profile.save()

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/')

    def __str__(self):
        return f"Image for {self.property.street}"
    
    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image.file, 'content_type'):
            img = Image.open(self.image)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
            thumb_io = io.BytesIO()
            img.save(thumb_io, 'JPEG', quality=85)
            filename, _ = os.path.splitext(os.path.basename(self.image.name))
            new_filename = filename + '.jpg'
            self.image.save(new_filename, ContentFile(thumb_io.getvalue()), save=False)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Užtikrina, kad ištrinant nuotraukos įrašą iš DB, būtų ištrintas ir failas.
        """
        self.image.delete(save=False) # Ištriname failą iš saugyklos
        super().delete(*args, **kwargs) # Ištriname įrašą iš DB


class ChatRoom(models.Model):
    name = models.CharField(max_length=255, unique=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')

    def __str__(self):
        return self.name

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}"
    
class Lease(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Laukiama patvirtinimo'),
        ('active', 'Aktyvi'),
        ('rejected', 'Atmesta'),
        ('terminated', 'Nutraukta'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='leases')
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True, verbose_name="Sutarties Failas")
    is_signed_by_landlord = models.BooleanField(default=False, verbose_name="Pasirašė nuomotojas")
    is_signed_by_tenant = models.BooleanField(default=False, verbose_name="Pasirašė nuomininkas")
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leases')
    start_date = models.DateField(verbose_name="Nuomos sutarties pradžios data")
    end_date = models.DateField(verbose_name="Nuomos sutarties pabaigos data", null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Depozito suma")

    rent_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Galutinė nuomos kaina (€)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    UTILITIES_PAID_BY_CHOICES = [
        ('tenant', 'Moka pats nuomininkas'),
        ('landlord', 'Sąskaitas apmoka nuomotojas (įtraukiama į sąskaitą)'),
    ]
    utilities_paid_by = models.CharField(
        max_length=10,
        choices=UTILITIES_PAID_BY_CHOICES,
        default='tenant',
        verbose_name="Kas apmoka komunalinius mokesčius?"
    )

    def __str__(self):
        return f"Lease for {self.property} by {self.tenant}"
    
class TenantReview(models.Model):
    lease = models.OneToOneField(Lease, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveIntegerField(
        verbose_name="Įvertinimas (1-10)",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    comment = models.TextField(verbose_name="Komentaras", blank=True, null=True)
    termination_reason = models.TextField(verbose_name="Nutraukimo priežastis")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.lease.tenant} on lease {self.lease.id}"
    
class PropertyReview(models.Model):
    lease = models.OneToOneField(Lease, on_delete=models.CASCADE, related_name='property_review')
    property_rating = models.PositiveIntegerField(
        verbose_name="Būsto įvertinimas (1-10)",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    landlord_rating = models.PositiveIntegerField(
        verbose_name="Nuomotojo įvertinimas (1-10)",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    property_comment = models.TextField(verbose_name="Komentaras apie būstą", blank=True, null=True)
    landlord_comment = models.TextField(verbose_name="Komentaras apie nuomotoją", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for property {self.lease.property.id} by {self.lease.tenant}"
    
class RentalRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Laukiama atsakymo'),
        ('accepted', 'Priimta'),
        ('rejected', 'Atmesta'),
    ]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rental_requests')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rental_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    start_date = models.DateField(verbose_name="Norima nuomos pradžia", default=date.today)
    end_date = models.DateField(verbose_name="Norima nuomos pabaiga", null=True, blank=True)
    offered_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Siūloma kaina (€/mėn.)", null=True, blank=True)
    message = models.TextField(verbose_name="Žinutė nuomotojui", null=True, blank=True)

    def __str__(self):
        return f"Request for {self.property.street} by {self.tenant.username}"

class ProblemReport(models.Model):
    PROBLEM_TYPE_CHOICES = [
        ('santechnika', 'Santechnika'),
        ('elektra', 'Elektra'),
        ('buitine_technika', 'Buitinė technika'),
        ('kita', 'Kita'),
    ]
    STATUS_CHOICES = [
        ('nauja', 'Nauja'),
        ('vykdoma', 'Vykdoma'),
        ('isspresta', 'Išspręsta'),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='problems')
    problem_type = models.CharField(max_length=20, choices=PROBLEM_TYPE_CHOICES, verbose_name="Problemos tipas")
    description = models.TextField(verbose_name="Aprašymas")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='nauja', verbose_name="Būsena")
    created_at = models.DateTimeField(auto_now_add=True)
    resolution_costs = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Išsprendimo išlaidos (€)")
    
    PAID_BY_CHOICES = [
        ('nuomotojas', 'Nuomotojas'),
        ('nuomininkas', 'Nuomininkas'),
    ]
    paid_by = models.CharField(
        max_length=11,
        choices=PAID_BY_CHOICES,
        null=True,
        blank=True,
        verbose_name="Kas apmoka?"
    )
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='problem_reports', verbose_name="Sąskaita")

    def __str__(self):
        return f"Problema objekte {self.lease.property.street}"

class ProblemUpdate(models.Model):
    problem = models.ForeignKey(ProblemReport, on_delete=models.CASCADE, related_name='updates')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField(verbose_name="Komentaras")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Komentaras problemai {self.problem.id}"

class ProblemImage(models.Model):
    problem = models.ForeignKey(ProblemReport, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='problems/')

    def __str__(self):
        return f"Nuotrauka problemai {self.problem.id}"
    
    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image.file, 'content_type'):
            img = Image.open(self.image)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((1024, 768), Image.Resampling.LANCZOS)
            thumb_io = io.BytesIO()
            img.save(thumb_io, 'JPEG', quality=85)
            filename, _ = os.path.splitext(os.path.basename(self.image.name))
            new_filename = filename + '.jpg'
            self.image.save(new_filename, ContentFile(thumb_io.getvalue()), save=False)
        
        super().save(*args, **kwargs)

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Neapmokėta'),
        ('pending', 'Laukiama patvirtinimo'),
        ('paid', 'Apmokėta'),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='invoices')
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Tik nuomos suma, be depozito, remonto ir komunalinių")
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    is_paid = models.BooleanField(default=False) # Šis laukas bus palaipsniui naikinamas
    period_date = models.DateField(null=True, blank=True, help_text="Mėnuo, už kurį išrašyta sąskaita (visada 1-a diena)")

    def __str__(self):
        return f"Invoice for {self.lease} on {self.invoice_date}"

class MeterReading(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='meter_readings')
    reading_date = models.DateField(auto_now_add=True)
    electricity_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Elektros skaitiklio rodmuo")
    hot_water_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Karšto vandens skaitiklio rodmuo")
    cold_water_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Šalto vandens skaitiklio rodmuo")
    gas_reading = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Dujų skaitiklio rodmuo")
    notes = models.TextField(blank=True, null=True, verbose_name="Pastabos")

    def __str__(self):
        return f"Meter reading for {self.lease} on {self.reading_date}"

class UtilityBill(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='utility_bills')
    description = models.CharField(max_length=255, verbose_name="Paslaugos pavadinimas")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Suma")

    def __str__(self):
        return f"{self.description} - {self.amount} for Invoice {self.invoice.id}"

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('new', 'Nauja'),
        ('in_progress', 'Vykdoma'),
        ('resolved', 'Išspręsta'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255, verbose_name="Tema")
    description = models.TextField(verbose_name="Aprašymas")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Būsena")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject

class SupportTicketUpdate(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(verbose_name="Žinutė")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Atsakymas į užklausą #{self.ticket.id}"


class SystemSettings(models.Model):
    paid_listing_enabled = models.BooleanField(default=False, verbose_name="Įjungti mokamus skelbimus")
    listing_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, verbose_name="Skelbimo aktyvavimo kaina")

    def __str__(self):
        return "Sistemos nustatymai"

    class Meta:
        verbose_name_plural = "Sistemos nustatymai"

    def save(self, *args, **kwargs):
        # Užtikriname, kad egzistuotų tik vienas nustatymų įrašas
        if not self.pk and SystemSettings.objects.exists():
            raise ValidationError('Gali būti tik vienas sistemos nustatymų įrašas.')
        super(SystemSettings, self).save(*args, **kwargs)