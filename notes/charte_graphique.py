"""Palette centralisée des bulletins et documents du module Notes."""

import re
from contextvars import ContextVar
from functools import wraps

from django.db.models import Q


CHAMPS_COULEUR = (
    'couleur_primaire',
    'couleur_secondaire',
    'couleur_accent',
    'couleur_texte_principal',
    'couleur_texte_secondaire',
    'couleur_fond_header',
    'couleur_fond_tableau',
    'couleur_fond_carte',
    'couleur_bordure',
    'couleur_mention_tb',
    'couleur_mention_bien',
    'couleur_mention_ab',
    'couleur_mention_passable',
    'couleur_mention_insuffisant',
)

CHARTE_PAR_DEFAUT = {
    'couleur_primaire': '#2C3E50',
    'couleur_secondaire': '#3498DB',
    'couleur_accent': '#E74C3C',
    'couleur_texte_principal': '#2C3E50',
    'couleur_texte_secondaire': '#7F8C8D',
    'couleur_fond_header': '#2C3E50',
    'couleur_fond_tableau': '#ECF0F1',
    'couleur_fond_carte': '#FFFFFF',
    'couleur_bordure': '#BDC3C7',
    'couleur_mention_tb': '#27AE60',
    'couleur_mention_bien': '#3498DB',
    'couleur_mention_ab': '#F39C12',
    'couleur_mention_passable': '#E67E22',
    'couleur_mention_insuffisant': '#E74C3C',
}

_HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
_CHARTE_DOCUMENT_COURANTE = ContextVar('charte_documents_notes', default=None)


def normaliser_couleur(value, fallback):
    value = str(value or '').strip()
    return value.upper() if _HEX_RE.fullmatch(value) else fallback


def couleur_contraste(value):
    """Retourne noir ou blanc selon la luminosité de la couleur de fond."""
    value = normaliser_couleur(value, '#FFFFFF')
    red, green, blue = (int(value[i:i + 2], 16) for i in (1, 3, 5))
    luminance = (red * 299 + green * 587 + blue * 114) / 1000
    return '#111827' if luminance >= 150 else '#FFFFFF'


def melanger_couleurs(value, cible='#FFFFFF', proportion=0.88):
    """Crée une nuance claire stable, utile pour les fonds des documents."""
    value = normaliser_couleur(value, '#2C3E50')
    cible = normaliser_couleur(cible, '#FFFFFF')
    proportion = max(0, min(1, float(proportion)))
    rgb = []
    for index in (1, 3, 5):
        source = int(value[index:index + 2], 16)
        destination = int(cible[index:index + 2], 16)
        rgb.append(round(source + (destination - source) * proportion))
    return '#{:02X}{:02X}{:02X}'.format(*rgb)


def trouver_ecole(source):
    """Déduit l'école depuis les objets habituellement placés dans un contexte PDF."""
    if source is None:
        return None
    if source.__class__.__name__ == 'Ecole':
        return source
    try:
        user = getattr(source, 'user', None)
        profil = getattr(user, 'profil', None)
        ecole = getattr(profil, 'ecole', None)
        if ecole is not None:
            return ecole
    except Exception:
        pass
    for attribute in ('ecole', 'classe', 'classe_note', 'eleve', 'evaluation'):
        try:
            related = getattr(source, attribute, None)
        except Exception:
            related = None
        if related is not None and related is not source:
            found = trouver_ecole(related)
            if found is not None:
                return found
    return None


def obtenir_theme_actif(ecole=None):
    """Retourne le thème prioritaire de l'école, puis le thème global éventuel."""
    from .models import ThemeBulletin

    def premier(queryset):
        return queryset.filter(Q(actif=True) | Q(par_defaut=True)).order_by(
            '-par_defaut', '-actif', '-date_modification', '-pk'
        ).first()

    try:
        if ecole is not None and getattr(ecole, 'pk', None):
            theme = premier(ThemeBulletin.objects.filter(ecole=ecole))
            if theme:
                return theme
        return premier(ThemeBulletin.objects.filter(ecole__isnull=True))
    except Exception:
        # Les PDF restent générables pendant une migration ou sur une base ancienne.
        return None


def get_charte_notes(ecole=None):
    """Retourne une palette prête pour Django templates et ReportLab."""
    ecole = trouver_ecole(ecole) or ecole
    palette = dict(CHARTE_PAR_DEFAUT)
    theme = obtenir_theme_actif(ecole)
    if theme:
        for field in CHAMPS_COULEUR:
            palette[field] = normaliser_couleur(
                getattr(theme, field, None), CHARTE_PAR_DEFAUT[field]
            )

    palette.update({
        'texte_sur_primaire': couleur_contraste(palette['couleur_primaire']),
        'texte_sur_secondaire': couleur_contraste(palette['couleur_secondaire']),
        'texte_sur_accent': couleur_contraste(palette['couleur_accent']),
        'texte_sur_header': couleur_contraste(palette['couleur_fond_header']),
        'primaire_clair': melanger_couleurs(palette['couleur_primaire']),
        'secondaire_clair': melanger_couleurs(palette['couleur_secondaire']),
        'accent_clair': melanger_couleurs(palette['couleur_accent'], proportion=0.9),
        'theme': theme,
    })
    return palette


def get_charte_reportlab(ecole=None):
    """Même palette, convertie en couleurs ReportLab."""
    from reportlab.lib import colors

    palette = get_charte_notes(ecole)
    return {
        key: colors.HexColor(value) if isinstance(value, str) and _HEX_RE.fullmatch(value) else value
        for key, value in palette.items()
        if key != 'theme'
    }


def couleur_document(key):
    """Couleur ReportLab de la génération courante (compatible concurrence)."""
    palette = _CHARTE_DOCUMENT_COURANTE.get()
    if palette is None:
        palette = get_charte_reportlab()
    return palette[key]


def document_avec_charte(ecole_position=0):
    """Isole la palette pendant toute la génération d'un document ReportLab."""
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            source = args[ecole_position] if len(args) > ecole_position else None
            ecole = trouver_ecole(source)
            token = _CHARTE_DOCUMENT_COURANTE.set(get_charte_reportlab(ecole))
            try:
                return function(*args, **kwargs)
            finally:
                _CHARTE_DOCUMENT_COURANTE.reset(token)
        return wrapper
    return decorator
