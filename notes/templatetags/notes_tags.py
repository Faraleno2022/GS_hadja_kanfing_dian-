from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Récupérer un élément d'un dictionnaire par clé"""
    return dictionary.get(key)
