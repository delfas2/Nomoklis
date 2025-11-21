from datetime import date
from django.utils import timezone

def get_current_date(request=None):
    """Returns the current date."""
    return date.today()

def get_current_time(request=None):
    """Returns the current time."""
    return timezone.now()
