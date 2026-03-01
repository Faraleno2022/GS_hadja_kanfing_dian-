"""
Utilitaire pour la gestion de l'année scolaire active.
Centralise la logique de récupération de l'année active depuis la session.
"""
from .models import Classe

SESSION_ANNEE_ACTIVE = 'annee_scolaire_active'


def get_annee_active(request, ecole):
    """Retourne l'année scolaire active (session ou la plus récente).

    L'année est déterminée par :
    1. La valeur stockée en session (si elle correspond à une année existante)
    2. L'année la plus récente pour l'école donnée
    """
    if not ecole:
        return None
    annees = list(
        Classe.objects
        .filter(ecole=ecole)
        .values_list('annee_scolaire', flat=True)
        .distinct()
        .order_by('-annee_scolaire')
    )
    if not annees:
        return None
    annee_session = request.session.get(SESSION_ANNEE_ACTIVE)
    if annee_session and annee_session in annees:
        return annee_session
    return annees[0]
