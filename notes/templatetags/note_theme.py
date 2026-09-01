from django import template

from notes.charte_graphique import get_charte_notes, trouver_ecole


register = template.Library()


@register.simple_tag(takes_context=True)
def charte_notes(context):
    """Expose la charte de l'école sans imposer de changement à chaque vue PDF."""
    for key in ('ecole', 'classe', 'classe_note', 'eleve', 'evaluation', 'bulletin'):
        ecole = trouver_ecole(context.get(key))
        if ecole is not None:
            return get_charte_notes(ecole)

    request = context.get('request')
    if request is not None:
        try:
            profil = getattr(request.user, 'profil', None)
            ecole = getattr(profil, 'ecole', None)
        except Exception:
            ecole = None
        if ecole is not None:
            return get_charte_notes(ecole)
    return get_charte_notes()
