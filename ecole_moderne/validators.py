"""Validateurs partagés entre les applications."""
import re

from django.core.exceptions import ValidationError

FORMAT_ANNEE_SCOLAIRE = re.compile(r'^\d{4}-\d{4}$')
_DEBUT_ANNEE = re.compile(r'^\s*(\d{4})')


def valider_annee_scolaire(value):
    """Impose le format AAAA-AAAA dont la fin suit immédiatement le début.

    Une valeur comme "2025-2027" a déjà faussé tous les soldes d'une école :
    les échéanciers portaient cette année alors que les paiements portaient
    "2025-2026", et le moteur de calcul, qui apparie les deux, ne retenait plus
    aucun paiement. Les reçus affichaient donc le dû intégral.
    """
    if value in (None, ''):
        return
    texte = str(value).strip()
    if not FORMAT_ANNEE_SCOLAIRE.match(texte):
        raise ValidationError(
            "Format d'année scolaire invalide : %(valeur)s. "
            "Attendu : AAAA-AAAA (par exemple 2025-2026).",
            code='annee_scolaire_format',
            params={'valeur': value},
        )
    debut, fin = (int(part) for part in texte.split('-'))
    if fin != debut + 1:
        raise ValidationError(
            "Année scolaire incohérente : %(valeur)s. L'année de fin doit "
            "suivre immédiatement l'année de début (ici %(attendu)s).",
            code='annee_scolaire_intervalle',
            params={'valeur': value, 'attendu': f'{debut}-{debut + 1}'},
        )


def annee_scolaire_est_valide(value):
    """Version booléenne du validateur, pour les audits et les diagnostics."""
    try:
        valider_annee_scolaire(value)
    except ValidationError:
        return False
    return True


def normaliser_annee_scolaire(value):
    """Forme canonique AAAA-(AAAA+1) déduite de l'année de début.

    Retourne une chaîne vide si aucune année de début n'est lisible.
    """
    match = _DEBUT_ANNEE.match(str(value or ''))
    if not match:
        return ''
    debut = int(match.group(1))
    return f'{debut}-{debut + 1}'
