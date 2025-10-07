# nomoklis_app/adapters.py

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from .models import Profile
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name = form.cleaned_data.get('last_name', '')
        # ★★★ PATAISYMAS: Užpildome username lauką el. pašto adresu ★★★
        if not user.username:
            user.username = user.email

        user.save()

        # Sukuriame profilį be rolės. Rolė bus pasirinkta vėliau, choose_role_view.
        if not hasattr(user, 'profile'):
            Profile.objects.create(user=user)
        return user

    def send_password_reset_mail(self, user, email, context):
        """
        Siunčia slaptažodžio atstatymo laišką naudojant lietuviškus šablonus.
        """
        return self.send_mail("nomoklis_app/password_reset_key", email, context)

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """
        Šis metodas iškviečiamas iškart po sėkmingo prisijungimo per socialinį tinklą,
        prieš sukuriant vietinį vartotoją. Jis leidžia automatiškai sujungti paskyras.
        """
        user = sociallogin.user

        # Jei vartotojas jau yra prisijungęs, leidžiame jam tęsti
        if request.user.is_authenticated:
            return

        # Jei socialinė paskyra jau prijungta prie vartotojo, leidžiame tęsti
        if sociallogin.is_existing:
            return

        # ★★★ PAGRINDINIS PATAISYMAS ★★★
        # Ieškome vartotojo pagal el. paštą, gautą iš socialinio tinklo.
        # Tai svarbiausia dalis, jungianti socialinę paskyrą su jau esančia sistemoje.
        try:
            existing_user = User.objects.get(email__iexact=user.email)
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            # Jei vartotojas su tokiu el. paštu nerastas, leidžiame tęsti standartinį
            # registracijos procesą (bus sukurtas naujas vartotojas).
            pass


    def save_user(self, request, sociallogin, form=None):
        """
        Iškviečiamas, kai kuriamas naujas vartotojas iš socialinės paskyros.
        """
        user = super().save_user(request, sociallogin, form)
        # ★★★ PATAISYMAS: Užpildome username lauką el. pašto adresu ★★★
        if not user.username:
            user.username = user.email
            user.save()
        if not hasattr(user, 'profile'):
            # Sukuriame profilį be rolės. Rolė bus pasirinkta vėliau.
            Profile.objects.create(user=user, user_type=None)
        return user

    def is_open_for_signup(self, request, sociallogin):
        """
        Neleidžiame registruotis per socialinius tinklus, jei el. paštas jau užimtas.
        Vartotojas turėtų pirmiausia prisijungti įprastu būdu ir tada prijungti socialinę paskyrą.
        """
        email = sociallogin.user.email
        if email and User.objects.filter(email__iexact=email).exists():
            # Jei vartotojas su tokiu el. paštu jau egzistuoja,
            # `pre_social_login` turėjo jį prijungti. Jei ne, kažkas negerai.
            # Saugumo sumetimais blokuojame naujos paskyros kūrimą.
            return False
        return True