"""
Template tags personnalisés pour le module de gestion des notes
"""

from django import template
from django.utils.safestring import mark_safe
from decimal import Decimal
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Récupère un élément d'un dictionnaire par sa clé
    Usage: {{ dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def moyenne_color(moyenne):
    """
    Retourne une classe CSS selon la moyenne
    Usage: {{ moyenne|moyenne_color }}
    """
    if moyenne is None:
        return 'text-muted'
    
    moyenne = float(moyenne)
    if moyenne >= 16:
        return 'text-success'
    elif moyenne >= 14:
        return 'text-primary' 
    elif moyenne >= 12:
        return 'text-info'
    elif moyenne >= 10:
        return 'text-warning'
    else:
        return 'text-danger'


@register.filter
def moyenne_badge(moyenne):
    """
    Retourne une classe de badge selon la moyenne
    Usage: {{ moyenne|moyenne_badge }}
    """
    if moyenne is None:
        return 'bg-secondary'
    
    moyenne = float(moyenne)
    if moyenne >= 16:
        return 'bg-success'
    elif moyenne >= 14:
        return 'bg-primary'
    elif moyenne >= 12:
        return 'bg-info'
    elif moyenne >= 10:
        return 'bg-warning'
    else:
        return 'bg-danger'


@register.filter
def appreciation_auto(note):
    """
    Génère une appréciation automatique selon la note
    Usage: {{ note|appreciation_auto }}
    """
    if note is None:
        return "Non évalué"
    
    note = float(note)
    if note >= 18:
        return "Excellent"
    elif note >= 16:
        return "Très bien"
    elif note >= 14:
        return "Bien"
    elif note >= 12:
        return "Assez bien"
    elif note >= 10:
        return "Passable"
    else:
        return "Insuffisant"


@register.filter
def rang_suffix(rang):
    """
    Ajoute le suffixe approprié au rang (1er, 2ème, 3ème, etc.)
    Usage: {{ rang|rang_suffix }}
    """
    if rang == 1:
        return "1er"
    elif rang == 2:
        return "2ème"
    elif rang == 3:
        return "3ème"
    else:
        return f"{rang}ème"


@register.filter
def coefficient_total(matieres):
    """
    Calcule le coefficient total d'une liste de matières
    Usage: {{ matieres|coefficient_total }}
    """
    if not matieres:
        return 0
    
    total = 0
    for matiere in matieres:
        total += matiere.coefficient
    return total


@register.simple_tag
def note_badge(note, show_appreciation=False):
    """
    Génère un badge stylisé pour une note
    Usage: {% note_badge note True %}
    """
    if note is None:
        return mark_safe('<span class="badge bg-secondary">--</span>')
    
    note_value = float(note)
    badge_class = moyenne_badge(note_value)
    appreciation = appreciation_auto(note_value) if show_appreciation else ""
    
    html = f'''
    <span class="badge {badge_class} fs-6">
        {note_value:.2f}/20
        {f"<br><small>{appreciation}</small>" if appreciation else ""}
    </span>
    '''
    return mark_safe(html)


@register.simple_tag
def rang_medal(rang):
    """
    Génère une médaille selon le rang
    Usage: {% rang_medal rang %}
    """
    if rang == 1:
        icon = '<i class="fas fa-trophy text-warning"></i>'
    elif rang == 2:
        icon = '<i class="fas fa-medal text-secondary"></i>'
    elif rang == 3:
        icon = '<i class="fas fa-award text-warning"></i>'
    else:
        icon = f'<span class="badge bg-primary">{rang}</span>'
    
    return mark_safe(icon)


@register.filter
def multiply(value, arg):
    """
    Multiplie une valeur par un argument
    Usage: {{ value|multiply:coefficient }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calcule un pourcentage
    Usage: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def stats_card(title, value, icon, color="primary"):
    """
    Génère une carte de statistiques
    Usage: {% stats_card "Total Notes" total_notes "fas fa-star" "success" %}
    """
    html = f'''
    <div class="card border-0 shadow-sm">
        <div class="card-body text-center">
            <div class="text-{color} mb-2">
                <i class="{icon} fa-2x"></i>
            </div>
            <h4 class="fw-bold">{value}</h4>
            <small class="text-muted">{title}</small>
        </div>
    </div>
    '''
    return mark_safe(html)


@register.filter
def json_encode(value):
    """
    Encode une valeur en JSON pour JavaScript
    Usage: {{ data|json_encode }}
    """
    return mark_safe(json.dumps(value))


@register.simple_tag
def evaluation_type_icon(categorie):
    """
    Retourne l'icône appropriée selon le type d'évaluation
    Usage: {% evaluation_type_icon evaluation.categorie %}
    """
    icons = {
        'COURS': '<i class="fas fa-pencil-alt text-primary"></i>',
        'COMPOSITION': '<i class="fas fa-file-alt text-warning"></i>',
    }
    return mark_safe(icons.get(categorie, '<i class="fas fa-question text-muted"></i>'))


@register.filter
def format_coefficient(coefficient):
    """
    Formate l'affichage du coefficient
    Usage: {{ coefficient|format_coefficient }}
    """
    if coefficient == 1:
        return ""
    return f" (coeff. {coefficient})"


@register.simple_tag
def student_avatar(student, size="40"):
    """
    Génère un avatar pour un élève
    Usage: {% student_avatar eleve "50" %}
    """
    initials = ""
    if student.nom and student.prenom:
        initials = f"{student.nom[0]}{student.prenom[0]}"
    elif student.nom:
        initials = student.nom[:2]
    
    html = f'''
    <div class="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center" 
         style="width: {size}px; height: {size}px; font-size: {int(size)//2}px;">
        {initials.upper()}
    </div>
    '''
    return mark_safe(html)


@register.filter
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire par sa clé"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def mul(value, factor):
    """Multiplie une valeur par un facteur"""
    try:
        return float(value) * float(factor)
    except (ValueError, TypeError):
        return 0
