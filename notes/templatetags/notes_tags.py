from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Permet d'accéder à un élément du dictionnaire avec une clé variable"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def mul(value, arg):
    """Multiplie deux valeurs"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
