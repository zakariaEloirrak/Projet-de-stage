from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        if value is None or arg is None:
            return 0
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def currency(value):
    """Format a number as currency."""
    try:
        if value is None:
            return "0.00"
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "0.00"

@register.filter
def percentage(value, total):
    """Calculate percentage."""
    try:
        if value is None or total is None or float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0
