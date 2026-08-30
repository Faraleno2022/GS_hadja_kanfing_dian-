"""Validateurs partages et compatibilite avec les anciennes migrations."""

import re

from django.core.exceptions import ValidationError


FORMAT_ANNEE_SCOLAIRE = re.compile(r"^\d{4}-\d{4}$")
_DEBUT_ANNEE = re.compile(r"^\s*(\d{4})")


def valider_annee_scolaire(value):
    """Valide le format AAAA-AAAA et deux annees consecutives."""
    if value in (None, ""):
        return

    texte = str(value).strip()
    if not FORMAT_ANNEE_SCOLAIRE.match(texte):
        raise ValidationError(
            "Format d'annee scolaire invalide : %(valeur)s. "
            "Attendu : AAAA-AAAA (par exemple 2025-2026).",
            code="annee_scolaire_format",
            params={"valeur": value},
        )

    debut, fin = (int(part) for part in texte.split("-"))
    if fin != debut + 1:
        raise ValidationError(
            "Annee scolaire incoherente : %(valeur)s. L'annee de fin doit "
            "suivre immediatement l'annee de debut (ici %(attendu)s).",
            code="annee_scolaire_intervalle",
            params={"valeur": value, "attendu": f"{debut}-{debut + 1}"},
        )


def annee_scolaire_est_valide(value):
    """Retourne ``True`` si la valeur respecte les regles de validation."""
    try:
        valider_annee_scolaire(value)
    except ValidationError:
        return False
    return True


def normaliser_annee_scolaire(value):
    """Construit la forme canonique AAAA-(AAAA+1) depuis l'annee de debut."""
    match = _DEBUT_ANNEE.match(str(value or ""))
    if not match:
        return ""
    debut = int(match.group(1))
    return f"{debut}-{debut + 1}"
