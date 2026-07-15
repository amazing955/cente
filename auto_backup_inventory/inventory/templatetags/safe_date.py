from django import template
import datetime

register = template.Library()

@register.filter
def format_dt(value):
    """Format a date/datetime safely.

    - If value is falsy, return '-'
    - If datetime, return 'Mon DD, YYYY HH:MM'
    - If date, return 'Mon DD, YYYY'
    - Else, try strftime with datetime format, else str(value)
    """
    if not value:
        return '-'
    try:
        if isinstance(value, datetime.datetime):
            return value.strftime('%b %d, %Y %H:%M')
        if isinstance(value, datetime.date):
            return value.strftime('%b %d, %Y')
        # try common attribute
        if hasattr(value, 'hour'):
            return value.strftime('%b %d, %Y %H:%M')
        return str(value)
    except Exception:
        return str(value)
