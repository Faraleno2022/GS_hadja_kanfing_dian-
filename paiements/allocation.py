"""Règles communes d'affectation des paiements sur un échéancier."""

from decimal import Decimal
import unicodedata

from .models import Paiement


ALLOCATION_COMPONENTS = (
    ("inscription", "frais_inscription_du", "frais_inscription_paye"),
    ("tranche_1", "tranche_1_due", "tranche_1_payee"),
    ("tranche_2", "tranche_2_due", "tranche_2_payee"),
    ("tranche_3", "tranche_3_due", "tranche_3_payee"),
)


def _decimal(value):
    return Decimal(str(value or 0))


def normalize_payment_type(value):
    """Normalise un libellé pour reconnaître inscription/réinscription."""
    if not isinstance(value, str):
        value = getattr(value, "nom", "") or ""
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in normalized if not unicodedata.combining(char))


def registration_kind_for_type(value):
    """Retourne le tarif d'inscription explicitement demandé par le type."""
    normalized = normalize_payment_type(value)
    if "reinscription" in normalized:
        return "reinscription"
    if "inscription" in normalized:
        return "inscription"
    return None


def allocate_amount_sequentially(echeancier, amount, initial_paid=None):
    """Affecte un montant: inscription, T1, T2 puis T3.

    La fonction ne sauvegarde rien. Elle retourne l'affectation du montant,
    les nouveaux cumuls payés et l'éventuel reliquat au-delà du total dû.
    """
    remaining = max(Decimal("0"), _decimal(amount))
    paid = {
        key: _decimal((initial_paid or {}).get(key, getattr(echeancier, paid_field, 0)))
        for key, _due_field, paid_field in ALLOCATION_COMPONENTS
    }
    allocation = {key: Decimal("0") for key, _due, _paid in ALLOCATION_COMPONENTS}

    for key, due_field, _paid_field in ALLOCATION_COMPONENTS:
        if remaining <= 0:
            break
        due = _decimal(getattr(echeancier, due_field, 0))
        available = max(Decimal("0"), due - paid[key])
        applied = min(remaining, available)
        if applied > 0:
            allocation[key] = applied
            paid[key] += applied
            remaining -= applied

    return allocation, paid, remaining


def get_payment_allocation(paiement, echeancier=None):
    """Reconstruit l'affectation exacte d'un paiement validé pour les reçus."""
    if echeancier is None:
        try:
            echeancier = paiement.eleve.echeancier
        except Exception:
            return None

    running_paid = {key: Decimal("0") for key, _due, _paid in ALLOCATION_COMPONENTS}
    target_allocation = None
    validated = (
        Paiement.objects
        .filter(eleve=paiement.eleve, statut="VALIDE")
        .order_by("date_paiement", "date_creation", "pk")
    )

    for current in validated.iterator():
        allocation, running_paid, unapplied = allocate_amount_sequentially(
            echeancier,
            current.montant,
            initial_paid=running_paid,
        )
        allocation["non_affecte"] = unapplied
        if current.pk == paiement.pk:
            target_allocation = allocation

    return target_allocation
