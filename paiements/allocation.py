"""Règles communes de ventilation des paiements scolaires.

Ce module ne dépend pas des vues afin que la même logique soit utilisée pour
mettre à jour l'échéancier et pour afficher l'affectation sur les reçus.
"""

from decimal import Decimal
import re
import unicodedata


INSCRIPTION = "inscription"
TRANCHE_1 = "tranche_1"
TRANCHE_2 = "tranche_2"
TRANCHE_3 = "tranche_3"

ALL_BUCKETS = (INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3)
TRANCHE_BUCKETS = (TRANCHE_1, TRANCHE_2, TRANCHE_3)


def normalize_payment_type(value):
    """Retourne un libellé minuscule sans accents et aux espaces normalisés."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def is_reinscription_payment(value):
    return "reinscription" in normalize_payment_type(value)


def _mentions_tranche(normalized_value, number):
    patterns = (
        rf"tranche\s*{number}",
        rf"t\s*{number}(?:\b|$)",
    )
    if number == 1:
        patterns += (r"1ere\s+tranche", r"premiere\s+tranche")
    elif number == 2:
        patterns += (r"2eme\s+tranche", r"deuxieme\s+tranche")
    else:
        patterns += (r"3eme\s+tranche", r"troisieme\s+tranche")
    return any(re.search(pattern, normalized_value) for pattern in patterns)


def allocation_order_for_type(value):
    """Détermine le premier poste visé puis les postes suivants autorisés.

    Une tranche simple peut déborder sur toutes les tranches suivantes. Un
    paiement d'inscription ou de réinscription continue lui aussi sur T1, T2
    puis T3 lorsque le montant dépasse les frais d'admission.
    """
    normalized = normalize_payment_type(value)
    has_admission_fee = "inscription" in normalized
    has_t1 = _mentions_tranche(normalized, 1)
    has_t2 = _mentions_tranche(normalized, 2)
    has_t3 = _mentions_tranche(normalized, 3)
    is_annual = "annuel" in normalized

    if has_admission_fee:
        return ALL_BUCKETS
    if has_t1:
        return TRANCHE_BUCKETS
    if has_t2:
        return (TRANCHE_2, TRANCHE_3)
    if has_t3:
        return (TRANCHE_3,)
    if is_annual or "scolarite" in normalized:
        return TRANCHE_BUCKETS

    # Compatibilité avec les anciens types non standardisés.
    return ALL_BUCKETS


def _decimal(value):
    return Decimal(str(value or 0))


def allocate_amount(amount, dues, paid=None, payment_type=""):
    """Ventile ``amount`` et retourne (affectation, nouveaux_payés, reliquat)."""
    paid = paid or {}
    remaining = max(Decimal("0"), _decimal(amount))
    updated_paid = {bucket: _decimal(paid.get(bucket, 0)) for bucket in ALL_BUCKETS}
    allocation = {bucket: Decimal("0") for bucket in ALL_BUCKETS}

    for bucket in allocation_order_for_type(payment_type):
        if remaining <= 0:
            break
        room = max(Decimal("0"), _decimal(dues.get(bucket, 0)) - updated_paid[bucket])
        taken = min(remaining, room)
        if taken > 0:
            allocation[bucket] += taken
            updated_paid[bucket] += taken
            remaining -= taken

    return allocation, updated_paid, remaining


def replay_payment_allocations(payments, dues):
    """Rejoue des paiements ordonnés et retourne leur ventilation individuelle."""
    paid = {bucket: Decimal("0") for bucket in ALL_BUCKETS}
    allocations = {}
    unallocated = {}
    for payment in payments:
        type_name = getattr(getattr(payment, "type_paiement", None), "nom", "")
        allocation, paid, remaining = allocate_amount(
            getattr(payment, "montant", 0),
            dues,
            paid,
            type_name,
        )
        allocations[getattr(payment, "pk", getattr(payment, "id", None))] = allocation
        unallocated[getattr(payment, "pk", getattr(payment, "id", None))] = remaining
    return allocations, paid, unallocated


def echeancier_dues(echeancier):
    return {
        INSCRIPTION: _decimal(echeancier.frais_inscription_du),
        TRANCHE_1: _decimal(echeancier.tranche_1_due),
        TRANCHE_2: _decimal(echeancier.tranche_2_due),
        TRANCHE_3: _decimal(echeancier.tranche_3_due),
    }


def echeancier_paid(echeancier):
    return {
        INSCRIPTION: _decimal(echeancier.frais_inscription_paye),
        TRANCHE_1: _decimal(echeancier.tranche_1_payee),
        TRANCHE_2: _decimal(echeancier.tranche_2_payee),
        TRANCHE_3: _decimal(echeancier.tranche_3_payee),
    }
