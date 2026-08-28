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
ALLOCATION_COMPONENTS = (
    (INSCRIPTION, "frais_inscription_du", "frais_inscription_paye"),
    (TRANCHE_1, "tranche_1_due", "tranche_1_payee"),
    (TRANCHE_2, "tranche_2_due", "tranche_2_payee"),
    (TRANCHE_3, "tranche_3_due", "tranche_3_payee"),
)


def normalize_payment_type(value):
    """Retourne un libellé minuscule sans accents et aux espaces normalisés."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def is_reinscription_payment(value):
    return "reinscription" in normalize_payment_type(value)


def registration_kind_for_type(value):
    """Retourne le tarif d'admission explicitement demandé par un type."""
    normalized = normalize_payment_type(value)
    if "reinscription" in normalized:
        return "reinscription"
    if "inscription" in normalized:
        return "inscription"
    return None


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


def scope_for_type(value):
    """Postes que le libellé du type annonce couvrir.

    À ne pas confondre avec :func:`allocation_order_for_type`, qui dit jusqu'où
    un excédent a le droit de glisser. « Réinscription + Tranche 1 » vise
    l'inscription et T1 ; son excédent peut atteindre T2/T3, mais T2/T3 ne font
    pas partie de ce que le type réclame.

    Retourne un tuple vide pour un libellé non standard (« Scolarité »,
    « Divers »…) : aucun montant de référence ne peut alors être déduit.
    """
    normalized = normalize_payment_type(value)
    tranches = [
        bucket
        for number, bucket in ((1, TRANCHE_1), (2, TRANCHE_2), (3, TRANCHE_3))
        if _mentions_tranche(normalized, number)
    ]
    # « Annuel » / « Scolarité » couvrent les trois tranches, mais seulement
    # quand aucune tranche n'est nommée: « Scolarité - 2ème tranche » ne vise
    # que T2.
    if not tranches and ("annuel" in normalized or "scolarite" in normalized):
        tranches = list(TRANCHE_BUCKETS)
    scope = [INSCRIPTION] if "inscription" in normalized else []
    scope.extend(tranches)
    return tuple(scope)


def montant_attendu_pour_type(value, dues, paid=None):
    """Reste exact à payer pour les postes visés par le type.

    C'est le montant qu'un guichetier devrait saisir: ce qui est déjà couvert
    en est retranché, poste par poste. Retourne ``(total, detail)`` où
    ``detail`` liste ``(poste, reste)`` dans l'ordre des postes visés.
    """
    paid = paid or {}
    detail = []
    total = Decimal("0")
    for bucket in scope_for_type(value):
        reste = max(
            Decimal("0"),
            _decimal(dues.get(bucket, 0)) - _decimal(paid.get(bucket, 0)),
        )
        total += reste
        detail.append((bucket, reste))
    return total, detail


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


def allocate_amount_sequentially(echeancier, amount, initial_paid=None):
    """Ventile un total de l'inscription vers T1, T2 puis T3."""
    initial_paid = initial_paid or {}
    return allocate_amount(
        amount,
        echeancier_dues(echeancier),
        {key: _decimal(initial_paid.get(key, 0)) for key in ALL_BUCKETS},
        payment_type="",
    )


def allocate_discounts(echeancier, discounts, balances=None):
    """Ventile les remises sur les tranches encore dues après encaissement."""
    current_balances = dict(balances or {
        key: max(
            Decimal("0"),
            _decimal(getattr(echeancier, due_field, 0))
            - _decimal(getattr(echeancier, paid_field, 0)),
        )
        for key, due_field, paid_field in ALLOCATION_COMPONENTS
    })
    allocation = {key: Decimal("0") for key in ALL_BUCKETS}

    for discount in discounts:
        numeros = getattr(discount, 'tranches_concernees_liste', None)
        if numeros is None:
            numeros = getattr(discount, 'tranches_appliquees', None)
        numeros = list(numeros or [1, 2, 3])
        selected = [f"tranche_{number}" for number in numeros if number in (1, 2, 3)]
        amount = max(Decimal("0"), _decimal(getattr(discount, 'montant_remise', 0)))
        for key in selected:
            if amount <= 0:
                break
            available = max(Decimal("0"), _decimal(current_balances.get(key, 0)))
            take = min(amount, available)
            allocation[key] += take
            current_balances[key] = available - take
            amount -= take

    return allocation, current_balances


def replay_payment_allocations(payments, dues, amounts_by_payment=None):
    """Rejoue des paiements ordonnés et retourne leur ventilation individuelle.

    ``amounts_by_payment`` permet aux rapports d'utiliser un montant net
    d'affichage sans modifier le montant réellement encaissé du paiement.
    """
    amounts_by_payment = amounts_by_payment or {}
    paid = {bucket: Decimal("0") for bucket in ALL_BUCKETS}
    allocations = {}
    unallocated = {}
    for payment in payments:
        payment_id = getattr(payment, "pk", getattr(payment, "id", None))
        type_name = getattr(getattr(payment, "type_paiement", None), "nom", "")
        allocation, paid, remaining = allocate_amount(
            amounts_by_payment.get(payment_id, getattr(payment, "montant", 0)),
            dues,
            paid,
            type_name,
        )
        allocations[payment_id] = allocation
        unallocated[payment_id] = remaining
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
