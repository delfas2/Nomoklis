from django.contrib import admin
from .models import Property, SystemSettings

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    """
    Administratoriaus sąsaja NT objektų valdymui.
    """
    # Atvaizduojami laukai sąraše. Įtrauktas pilnas adresas.
    list_display = ('get_full_address', 'owner', 'status', 'city', 'property_type', 'is_paid_listing')
    # Filtravimo parinktys dešinėje.
    list_filter = ('status', 'city', 'property_type', 'is_paid_listing')
    # Paieškos laukai. Leidžia ieškoti pagal savininko vardą/el. paštą ir adreso dalis.
    search_fields = ('owner__username', 'owner__email', 'street', 'house_number', 'city')
    # Leidžia redaguoti 'status' lauką tiesiai sąraše.
    list_editable = ('status',)
    list_per_page = 25
    # Optimizuoja savininko lauko užkrovimą dideliuose sąrašuose.
    raw_id_fields = ('owner',)

    def get_full_address(self, obj):
        # Naudoja modelio __str__ metodą pilnam adresui gauti.
        return str(obj)
    # Stulpelio pavadinimas administratoriaus sąsajoje.
    get_full_address.short_description = 'Adresas'
    # Leidžia rikiuoti pagal gatvės pavadinimą paspaudus ant adreso stulpelio.
    get_full_address.admin_order_field = 'street'

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('paid_listing_enabled', 'listing_price')
    
    def has_add_permission(self, request):
        # Leidžiame sukurti tik vieną įrašą
        return not SystemSettings.objects.exists()