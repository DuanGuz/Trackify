from django import template
from core.utils import format_rut

register = template.Library()

@register.filter
def rut(value):
    return format_rut(value or "")

