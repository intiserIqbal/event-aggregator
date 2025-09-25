# events/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Return dictionary.get(key) safely from templates."""
    try:
        return dictionary.get(key)
    except Exception:
        return None
