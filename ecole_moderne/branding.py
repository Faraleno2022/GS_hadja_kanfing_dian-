"""Résolution centralisée de la charte graphique d'une école.

Ce module ne dépend pas directement des modèles au chargement afin de rester
utilisable par les vues, les context processors et les générateurs PDF.
"""

import re

from django.apps import apps
from django.db.models import Q


HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')

DEFAULT_BRANDING = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'accent': '#e74c3c',
    'text': '#2c3e50',
    'muted': '#7f8c8d',
    'header': '#2c3e50',
    'table': '#ecf0f1',
    'card': '#ffffff',
    'border': '#bdc3c7',
    'card_primary': '#0d6efd',
    'card_success': '#198754',
    'card_warning': '#f59e0b',
    'card_danger': '#dc3545',
    'mention_tb': '#27ae60',
    'mention_bien': '#3498db',
    'mention_ab': '#f39c12',
    'mention_passable': '#e67e22',
    'mention_insuffisant': '#e74c3c',
}

THEME_FIELDS = {
    'primary': 'couleur_primaire',
    'secondary': 'couleur_secondaire',
    'accent': 'couleur_accent',
    'text': 'couleur_texte_principal',
    'muted': 'couleur_texte_secondaire',
    'header': 'couleur_fond_header',
    'table': 'couleur_fond_tableau',
    'card': 'couleur_fond_carte',
    'border': 'couleur_bordure',
    'card_primary': 'couleur_carte_primaire',
    'card_success': 'couleur_carte_succes',
    'card_warning': 'couleur_carte_attention',
    'card_danger': 'couleur_carte_danger',
    'mention_tb': 'couleur_mention_tb',
    'mention_bien': 'couleur_mention_bien',
    'mention_ab': 'couleur_mention_ab',
    'mention_passable': 'couleur_mention_passable',
    'mention_insuffisant': 'couleur_mention_insuffisant',
}


def normalize_hex(value, fallback):
    value = str(value or '').strip()
    return value.lower() if HEX_COLOR_RE.fullmatch(value) else fallback.lower()


def _rgb(value):
    value = normalize_hex(value, '#000000').lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix_hex(value, target='#ffffff', ratio=0.88):
    """Mélange une couleur avec une cible, utile pour les fonds discrets."""
    base = _rgb(value)
    end = _rgb(target)
    ratio = min(1.0, max(0.0, float(ratio)))
    mixed = tuple(round(a * (1 - ratio) + b * ratio) for a, b in zip(base, end))
    return '#{:02x}{:02x}{:02x}'.format(*mixed)


def contrast_text(value):
    """Retourne noir ou blanc selon le contraste WCAG le plus lisible."""
    r, g, b = (_component / 255 for _component in _rgb(value))

    def linear(component):
        return component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
    return '#111827' if luminance > 0.48 else '#ffffff'


def get_active_theme(ecole=None):
    """Retourne la charte active de l'école, ou la charte globale de secours."""
    try:
        ThemeBulletin = apps.get_model('notes', 'ThemeBulletin')
        qs = ThemeBulletin.objects.filter(Q(actif=True) | Q(par_defaut=True))
        if ecole is not None:
            theme = qs.filter(ecole=ecole).order_by('-par_defaut', '-actif', '-date_modification').first()
            if theme:
                return theme
        return qs.filter(ecole__isnull=True).order_by('-par_defaut', '-actif', '-date_modification').first()
    except Exception:
        # La base peut ne pas être encore migrée au démarrage d'une ancienne installation.
        return None


def get_school_branding(ecole=None, theme=None):
    """Construit une palette sérialisable pour le HTML, Excel et ReportLab."""
    theme = theme or get_active_theme(ecole)
    branding = dict(DEFAULT_BRANDING)
    if theme is not None:
        for key, attribute in THEME_FIELDS.items():
            branding[key] = normalize_hex(getattr(theme, attribute, None), branding[key])
        branding['theme_name'] = getattr(theme, 'nom', '') or 'Charte graphique'
        branding['theme_id'] = getattr(theme, 'pk', None)
    else:
        branding['theme_name'] = 'Charte par défaut'
        branding['theme_id'] = None

    for key in (
        'primary', 'secondary', 'accent', 'header',
        'card_primary', 'card_success', 'card_warning', 'card_danger',
        'mention_tb', 'mention_bien', 'mention_ab',
        'mention_passable', 'mention_insuffisant',
    ):
        branding[f'{key}_text'] = contrast_text(branding[key])
        branding[f'{key}_soft'] = mix_hex(branding[key])
    branding['table_alt'] = mix_hex(branding['table'], '#ffffff', 0.55)
    return branding


def get_reportlab_palette(ecole=None, theme=None):
    """Retourne la même charte sous forme de couleurs ReportLab."""
    from reportlab.lib import colors

    branding = get_school_branding(ecole, theme=theme)
    palette = {
        key: colors.HexColor(value)
        for key, value in branding.items()
        if isinstance(value, str) and HEX_COLOR_RE.fullmatch(value)
    }
    palette['branding'] = branding
    return palette
