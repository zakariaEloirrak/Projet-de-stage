from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def currency(value):
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "0.00"

@register.filter
def percentage(value, total):
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def stock_status(produit):
    if produit.quantite_stock <= 0:
        return 'danger'
    elif produit.quantite_stock <= produit.seuil_alerte:
        return 'warning'
    else:
        return 'success'

@register.filter
def stock_badge(produit):
    if produit.quantite_stock <= 0:
        return 'bg-danger'
    elif produit.quantite_stock <= produit.seuil_alerte:
        return 'bg-warning'
    else:
        return 'bg-success'
