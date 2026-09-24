"""Lecture unifiée des corrections et suppressions de paiements.

Les modifications annulables sont stockées dans ``ElementCorbeille`` tandis
que les suppressions restaurables utilisent ``CorbeilleElement``. Ce module
présente les deux journaux sous une forme comptable unique, sans dupliquer les
données ni introduire une troisième source d'audit.
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from administration.models import CorbeilleElement, ElementCorbeille
from utilisateurs.utils import user_school


PERIOD_LABELS = (
    ("today", "Aujourd'hui"),
    ("week", "Cette semaine"),
    ("month", "Ce mois"),
    ("year", "Cette année"),
)


def _decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _local_date(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def _school_scoped(queryset, user, field):
    if getattr(user, "is_superuser", False):
        return queryset
    ecole = user_school(user)
    if ecole is None:
        return queryset.none()
    if field == "ecole":
        return queryset.filter(ecole=ecole)
    return queryset.filter(ecole_nom=ecole.nom)


def _student_label(value, fallback=""):
    if isinstance(value, dict):
        return value.get("text") or fallback
    return fallback


def _modification_records(user, start=None, end=None):
    queryset = ElementCorbeille.objects.filter(
        model_label="paiements.Paiement",
        type_operation=ElementCorbeille.MODIFICATION,
    ).select_related("ecole", "utilisateur")
    queryset = _school_scoped(queryset, user, "ecole")
    if start:
        queryset = queryset.filter(date__date__gte=start)
    if end:
        queryset = queryset.filter(date__date__lte=end)

    records = []
    for item in queryset.iterator():
        before = item.donnees_avant or {}
        after = item.donnees_apres or {}
        old_amount = _decimal(before.get("montant"))
        new_amount = _decimal(after.get("montant"))
        receipt = (
            after.get("numero_recu")
            or before.get("numero_recu")
            or item.libelle
        )
        student = _student_label(
            after.get("eleve"),
            _student_label(before.get("eleve"), item.libelle),
        )
        changed_fields = list(item.champs_modifies or [])
        records.append({
            "key": f"modification-{item.pk}",
            "operation": "modification",
            "operation_label": "Modification",
            "date": item.date,
            "numero_recu": str(receipt or ""),
            "eleve": student,
            "ancien_montant": old_amount,
            "nouveau_montant": new_amount,
            "ecart": new_amount - old_amount,
            "montant_modifie": "montant" in changed_fields,
            "champs_modifies": changed_fields,
            "motif": item.motif or "Motif non renseigné",
            "utilisateur": item.utilisateur,
            "restaure": item.restaure,
        })
    return records


def _deletion_records(user, start=None, end=None):
    queryset = CorbeilleElement.objects.filter(
        app_label="paiements",
        model_name="Paiement",
    ).select_related("supprime_par")
    queryset = _school_scoped(queryset, user, "ecole_nom")
    if start:
        queryset = queryset.filter(date_suppression__date__gte=start)
    if end:
        queryset = queryset.filter(date_suppression__date__lte=end)

    records = []
    for item in queryset.iterator():
        snapshot = item.donnees or {}
        principal = snapshot.get("principal") or {}
        receipt = (
            (snapshot.get("recu") or {}).get("numero")
            or principal.get("numero_recu")
            or item.objet_repr
        )
        old_amount = _decimal(principal.get("montant"))
        records.append({
            "key": f"suppression-{item.pk}",
            "operation": "suppression",
            "operation_label": "Suppression",
            "date": item.date_suppression,
            "numero_recu": str(receipt or ""),
            "eleve": item.contexte or item.objet_repr,
            "ancien_montant": old_amount,
            "nouveau_montant": None,
            "ecart": -old_amount,
            "montant_modifie": False,
            "champs_modifies": [],
            "motif": item.motif or "Motif non renseigné",
            "utilisateur": item.supprime_par,
            "restaure": item.restaure,
        })
    return records


def payment_mutation_records(
    user, *, start=None, end=None, operation="", search=""
):
    """Retourne l'historique filtré, du plus récent au plus ancien."""
    operation = (operation or "").lower()
    records = []
    if operation in ("", "modification"):
        records.extend(_modification_records(user, start=start, end=end))
    if operation in ("", "suppression"):
        records.extend(_deletion_records(user, start=start, end=end))

    term = (search or "").strip().casefold()
    if term:
        records = [
            record
            for record in records
            if term
            in " ".join(
                [
                    record["numero_recu"],
                    record["eleve"],
                    record["motif"],
                    record["operation_label"],
                ]
            ).casefold()
        ]
    return sorted(records, key=lambda record: record["date"], reverse=True)


def mutation_period_starts(today):
    return {
        "today": today,
        "week": today - timedelta(days=today.weekday()),
        "month": today.replace(day=1),
        "year": date(today.year, 1, 1),
    }


def payment_mutation_metrics(user, today=None):
    """Montants corrigés/supprimés par date réelle d'opération."""
    today = today or timezone.localdate()
    starts = mutation_period_starts(today)
    records = payment_mutation_records(
        user, start=starts["year"], end=today
    )
    values = {
        "modification": {
            key: {"amount": 0, "count": 0} for key, _ in PERIOD_LABELS
        },
        "suppression": {
            key: {"amount": 0, "count": 0} for key, _ in PERIOD_LABELS
        },
    }

    for record in records:
        record_date = _local_date(record["date"])
        if not record_date or record_date > today:
            continue
        if record["operation"] == "modification":
            if not record["montant_modifie"]:
                continue
            amount = record["nouveau_montant"]
        else:
            amount = record["ancien_montant"]
        for key, start in starts.items():
            if record_date >= start:
                values[record["operation"]][key]["amount"] += int(amount or 0)
                values[record["operation"]][key]["count"] += 1
    return values

