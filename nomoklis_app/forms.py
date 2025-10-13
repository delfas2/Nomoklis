from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.models import User
from .models import (
    Property, Lease, PropertyReview, TenantReview, RentalRequest,
    ProblemReport, ProblemImage, ProblemUpdate, Profile, MeterReading,
    Invoice, UtilityBill, SupportTicket, SupportTicketUpdate
)
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe

class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='Vardas', widget=forms.TextInput(
        attrs={'placeholder': 'Vardas'}
    ))
    last_name = forms.CharField(max_length=30, label='Pavardė', widget=forms.TextInput(
        attrs={'placeholder': 'Pavardė'}
    ))
    password = forms.CharField(widget=forms.PasswordInput, label='Slaptažodis')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Pakartokite slaptažodį')
    terms = forms.BooleanField(
        required=True,
        label=mark_safe('Sutinku su <a href="/terms-and-conditions/" target="_blank" class="font-bold text-blue-600 hover:underline">taisyklėmis ir sąlygomis</a>'),
        error_messages={'required': 'Jūs privalote sutikti su taisyklėmis, kad galėtumėte registruotis.'}
    )
 
    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'placeholder': 'Slaptažodis'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'placeholder': 'Pakartokite slaptažodį'}))
    user_type = forms.ChoiceField(choices=[('nuomotojas', 'Nuomotojas'), ('nuomininkas', 'Nuomininkas')],
                                  widget=forms.RadioSelect,
                                  label="Paskyros tipas")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'password2', 'user_type']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'placeholder': 'Vardas'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'placeholder': 'Pavardė'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border rounded-md', 'placeholder': 'El. paštas'}),
        }

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Slaptažodžiai neatitinka.')
        return cd['password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            Profile.objects.create(user=user, user_type=self.cleaned_data['user_type'])
        return user

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            'street', 'house_number', 'flat_number', 'city', 'district', 
            'rent_price', 'property_type', 'status', 'area', 'rooms', 
            'floor', 'total_floors', 'description', 'has_balcony', 
            'has_parking', 'pets_allowed', 'is_furnished', 'has_appliances', 
            'residence_declaration_allowed'
        ]
        
        # --- PATAISYMAS: 'widgets' žodynas perkeltas į 'Meta' klasės vidų ---
        widgets = {
            'street': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'house_number': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'flat_number': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'city': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'district': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'rent_price': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'status': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'property_type': forms.Select(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'area': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'rooms': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'floor': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'total_floors': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'has_balcony': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
            'has_parking': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
            'pets_allowed': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
            'is_furnished': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
            'has_appliances': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
            'residence_declaration_allowed': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
        }

class PropertyCreateForm(PropertyForm):
    class Meta(PropertyForm.Meta):
        fields = [
            'street', 'house_number', 'flat_number', 'city', 'district', 
            'rent_price', 'property_type', 'area', 'rooms', 
            'floor', 'total_floors', 'description', 'has_balcony', 
            'has_parking', 'pets_allowed', 'is_furnished', 'has_appliances', 
            'residence_declaration_allowed'
        ]



class AssignTenantForm(forms.ModelForm):
    email = forms.EmailField(label="Nuomininko el. paštas", widget=forms.EmailInput(attrs={'class': 'w-full border-gray-300 rounded-md'}))
    
    class Meta:
        model = Lease
        fields = ['email', 'rent_price', 'start_date', 'end_date']
        widgets = {
            'rent_price': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'start_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'type': 'date'}),
        }

class TerminateLeaseForm(forms.ModelForm):
    termination_date = forms.DateField(
        label="Nutraukimo data",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full border-gray-300 rounded-md'}),
        initial=timezone.now().date()
    )
    class Meta:
        model = TenantReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'class': 'w-full'}),
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md'}),
        }
        
class PropertyReviewForm(forms.ModelForm):
    class Meta:
        model = PropertyReview
        fields = ['property_rating', 'landlord_rating', 'property_comment', 'landlord_comment']
        widgets = {
            'property_rating': forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'}),
            'landlord_rating': forms.NumberInput(attrs={'type': 'range', 'min': 1, 'max': 5, 'class': 'w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'}),
            'property_comment': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Jūsų atsiliepimas apie būstą...'}),
            'landlord_comment': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Jūsų atsiliepimas apie nuomotoją...'}),
        }
        
class RentalRequestForm(forms.ModelForm):
    class Meta:
        model = RentalRequest
        fields = ['start_date', 'end_date', 'offered_price', 'message']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border-gray-300 rounded-md text-sm', 'placeholder': 'Pasirinkite datą'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border-gray-300 rounded-md text-sm', 'placeholder': 'Pasirinkite datą'}),
            'offered_price': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md text-sm', 'placeholder': 'Siūloma kaina, €'}),
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'w-full border-gray-300 rounded-md text-sm', 'placeholder': 'Jūsų žinutė nuomotojui...'}),
        }

class ConfirmLeaseForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ['rent_price', 'start_date', 'end_date']
        widgets = {
            'rent_price': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'start_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'type': 'date'}),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
        }

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_image', 'city', 'about_me']
        widgets = {
            'profile_image': forms.ClearableFileInput(attrs={'class': 'w-full'}),
            'city': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'about_me': forms.Textarea(attrs={'rows': 4, 'class': 'w-full border-gray-300 rounded-md'}),
        }
        
class ProblemReportForm(forms.ModelForm):
    class Meta:
        model = ProblemReport
        fields = ['problem_type', 'description']
        widgets = {
            'problem_type': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Detaliai aprašykite problemą...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        images = self.files.getlist('images')
        if len(images) > 5:
            raise ValidationError("Galima įkelti ne daugiau kaip 5 nuotraukas.")
        return cleaned_data

class LandlordProblemUpdateForm(forms.ModelForm):
    comment = forms.CharField(
        label="Pridėti komentarą/atnaujinimą",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Įveskite komentarą...'})
    )
    class Meta:
        model = ProblemReport
        fields = ['status', 'resolution_costs', 'paid_by']
        widgets = {
            'status': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-md'}),
            'resolution_costs': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': '0.00'}),
            'paid_by': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-md'}),
        }

class TenantCommentForm(forms.ModelForm):
    class Meta:
        model = ProblemUpdate
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Jūsų komentaras...'}),
        }

class TenantTerminationForm(forms.Form):
    termination_date = forms.DateField(
        label="Sutarties nutraukimo data",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full border-gray-300 rounded-md'}),
        initial=timezone.now().date()
    )
    reason = forms.CharField(
        label="Nutraukimo priežastis",
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'w-full border-gray-300 rounded-md'})
    )

class PrepareContractForm(forms.Form):
    deposit_amount = forms.DecimalField(
        label="Depozito suma (€)",
        widget=forms.NumberInput(attrs={
            'class': 'w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500',
            'step': '0.01'
        })
    )
    contract_text = forms.CharField(
        label="Sutarties tekstas",
        widget=forms.Textarea(attrs={
            'class': 'w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500',
            'rows': 25
        })
    )

class UtilitiesPaymentForm(forms.ModelForm):
    class Meta:
        model = Lease
        fields = ['utilities_paid_by']
        widgets = {
            'utilities_paid_by': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-md'})
        }

class MeterReadingForm(forms.ModelForm):
    class Meta:
        model = MeterReading
        fields = ['electricity_reading', 'hot_water_reading', 'cold_water_reading', 'gas_reading', 'notes']
        widgets = {
            'electricity_reading': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Elektra'}),
            'hot_water_reading': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Karštas vanduo'}),
            'cold_water_reading': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Šaltas vanduo'}),
            'gas_reading': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Dujos'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Pastabos...'}),
        }
        
class UtilityBillForm(forms.ModelForm):
    class Meta:
        model = UtilityBill
        fields = ['description', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Pvz., Šildymas'}),
            'amount': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md', 'placeholder': '0.00'}),
        }

UtilityBillFormSet = forms.formset_factory(UtilityBillForm, extra=3)

# nomoklis_app/forms.py

from .models import Profile

class UserTypeForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['user_type']
        labels = {
            'user_type': 'Pasirinkite savo rolę'
        }
        widgets = {
            'user_type': forms.RadioSelect(attrs={'class': 'accent-purple-600'})
        }

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['subject', 'description']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-md bg-white shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'w-full border-gray-300 rounded-md bg-white shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
        }

class SupportTicketUpdateForm(forms.ModelForm):
    class Meta:
        model = SupportTicketUpdate
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Jūsų atsakymas...'}),
        }

class AdminSupportTicketUpdateForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-md'}),
        }

class AdminSupportTicketMessageForm(forms.Form):
    message = forms.CharField(
        label="Pridėti atsakymą",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'w-full border-gray-300 rounded-md', 'placeholder': 'Įveskite atsakymą...'})
    )

from .models import SystemSettings

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = ['paid_listing_enabled', 'listing_price']
        widgets = {
            'listing_price': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-md'}),
        }