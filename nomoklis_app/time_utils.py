from datetime import date, datetime
from django.utils import timezone
from django.conf import settings

def get_current_date(request):
    """
    Returns the current date.
    If a simulated date is set in the session, returns that date.
    Otherwise, returns the actual current date.
    """
    simulated_date_str = request.session.get('simulated_date')
    if simulated_date_str:
        try:
            return datetime.strptime(simulated_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return date.today()

def get_current_time(request):
    """
    Returns the current time.
    If a simulated date is set in the session, returns the current time but on that date.
    Otherwise, returns the actual current time.
    """
    simulated_date_str = request.session.get('simulated_date')
    now = timezone.now()
    
    if simulated_date_str:
        try:
            simulated_date = datetime.strptime(simulated_date_str, '%Y-%m-%d').date()
            # Combine simulated date with current time
            return now.replace(year=simulated_date.year, month=simulated_date.month, day=simulated_date.day)
        except ValueError:
            pass
            
    return now
