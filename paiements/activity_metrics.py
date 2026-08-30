"""Historique financier des montants de paiements modifiés et supprimés."""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone

from administration.models import CorbeilleElement, JournalModification
from utilisateurs.utils import filter_by_user_school, user_is_superadmin, user_school

from .models import Paiement


PERIOD_LABELS = (
    ("today", "Aujourd'hui"),
    ("week", "Cette semaine"),
    ("month", "Ce mois"),
    ("year", "Cette année"),
)


def _period_starts(today):
    return {
        "today": today,
        "week": today - timedelta(days=today.weekday()),
        "month": today.replace(day=1),
        "year": date(today.year, 1, 1),
    }


def _decimal(value):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _event_date(value):
    if value is None:
        return None
    if hasattr(value, "tzinfo"):
        try:
            value = timezone.localtime(value)
        except (ValueError, TypeError):
            pass
    return value.date() if hasattr(value, "date") else value


def _payment_snapshot(entry):
    return dict(((entry.donnees or {}).get("principal") or {}))


def _scoped_sources(user, *, date_from=None):
    deletions = CorbeilleElement.objects.filter(
        app_label="paiements",
        model_name="Paiement",
    ).select_related("supprime_par", "restaure_par")
    modifications = JournalModification.objects.filter(
        app_label="paiements",
        model_name="Paiement",
        action=JournalModification.ACTION_MODIFICATION,
    ).select_related("utilisateur")
    if date_from:
        deletions = deletions.filter(date_suppression__date__gte=date_from)
        modifications = modifications.filter(date_modification__date__gte=date_from)

    active_payments = Paiement.objects.select_related(
        "eleve", "eleve__classe", "eleve__classe__ecole"
    )
    if not user_is_superadmin(user):
        school = user_school(user)
        if school is None:
            return deletions.none(), modifications.none(), active_payments.none()
        deletions = deletions.filter(ecole_nom=school.nom)
        active_payments = filter_by_user_school(
            active_payments, user, "eleve__classe__ecole"
        )
        deleted_ids = list(
            deletions.values_list("objet_id_origine", flat=True)
        )
        modifications = modifications.filter(
            Q(objet_id__in=active_payments.values("pk"))
            | Q(objet_id__in=deleted_ids)
        )
    return deletions, modifications, active_payments


def build_payment_activity_rows(user, *, date_from=None, query=""):
    """Fusionne les modifications de montant et les suppressions de paiement."""
    deletions_qs, modifications_qs, active_qs = _scoped_sources(
        user, date_from=date_from
    )
    deletions = list(deletions_qs.order_by("-date_suppression", "-pk"))
    modifications = list(
        modifications_qs.order_by("-date_modification", "-pk")
    )
    active_by_id = {
        payment.pk: payment
        for payment in active_qs.filter(
            pk__in={entry.objet_id for entry in modifications if entry.objet_id}
        )
    }
    deleted_by_id = {}
    for entry in deletions:
        deleted_by_id.setdefault(entry.objet_id_origine, entry)

    rows = []
    for entry in modifications:
        amount_change = (entry.changements or {}).get("montant")
        if not isinstance(amount_change, dict):
            continue
        before = _decimal(amount_change.get("avant"))
        after = _decimal(amount_change.get("apres"))
        if before == after:
            continue
        payment = active_by_id.get(entry.objet_id)
        deleted_entry = deleted_by_id.get(entry.objet_id)
        snapshot = _payment_snapshot(deleted_entry) if deleted_entry else {}
        rows.append({
            "kind": "MODIFICATION",
            "kind_label": "Modification",
            "event_at": entry.date_modification,
            "payment_id": entry.objet_id,
            "receipt": (
                getattr(payment, "numero_recu", "")
                or snapshot.get("numero_recu")
                or entry.objet_repr.split(" - ", 1)[0]
            ),
            "student": (
                getattr(getattr(payment, "eleve", None), "nom_complet", "")
                or (deleted_entry.contexte if deleted_entry else "")
            ),
            "school": (
                getattr(
                    getattr(
                        getattr(getattr(payment, "eleve", None), "classe", None),
                        "ecole", None,
                    ),
                    "nom", "",
                )
                or (deleted_entry.ecole_nom if deleted_entry else "")
            ),
            "before_amount": int(before),
            "after_amount": int(after),
            "impact": int(after - before),
            "reason": entry.commentaire or "Motif non renseigné",
            "user": entry.utilisateur,
            "restored": False,
            "changed_fields": sorted((entry.changements or {}).keys()),
        })

    for entry in deletions:
        snapshot = _payment_snapshot(entry)
        amount = _decimal(snapshot.get("montant"))
        rows.append({
            "kind": "SUPPRESSION",
            "kind_label": "Suppression",
            "event_at": entry.date_suppression,
            "payment_id": entry.objet_id_origine,
            "receipt": snapshot.get("numero_recu") or entry.objet_repr.split(" - ", 1)[0],
            "student": entry.contexte,
            "school": entry.ecole_nom,
            "before_amount": int(amount),
            "after_amount": 0,
            "impact": -int(amount),
            "reason": entry.motif or "Suppression depuis la gestion des paiements",
            "user": entry.supprime_par,
            "restored": entry.restaure,
            "changed_fields": [],
        })

    query = (query or "").strip().casefold()
    if query:
        rows = [
            row for row in rows
            if query in " ".join([
                str(row.get("receipt") or ""),
                str(row.get("student") or ""),
                str(row.get("school") or ""),
                str(row.get("reason") or ""),
                str(row.get("kind_label") or ""),
                str(row.get("user") or ""),
            ]).casefold()
        ]
    rows.sort(key=lambda row: row["event_at"], reverse=True)
    return rows


def build_payment_activity_metrics(user, today=None):
    """Agrège l'impact des modifications/suppressions pour les quatre périodes."""
    today = today or timezone.localdate()
    starts = _period_starts(today)
    rows = build_payment_activity_rows(user, date_from=starts["year"])
    values = {
        key: {
            "modified_before": 0,
            "modified_after": 0,
            "modified_delta": 0,
            "modified_count": 0,
            "deleted_amount": 0,
            "deleted_count": 0,
            "net_impact": 0,
        }
        for key, _label in PERIOD_LABELS
    }
    for row in rows:
        event_date = _event_date(row["event_at"])
        if event_date is None or event_date > today:
            continue
        for key, start in starts.items():
            if event_date < start:
                continue
            period = values[key]
            if row["kind"] == "MODIFICATION":
                period["modified_before"] += row["before_amount"]
                period["modified_after"] += row["after_amount"]
                period["modified_delta"] += row["impact"]
                period["modified_count"] += 1
            else:
                period["deleted_amount"] += row["before_amount"]
                period["deleted_count"] += 1
            period["net_impact"] += row["impact"]

    return {
        "year": today.year,
        "values": values,
        "period_values": [
            {"key": key, "label": label, **values[key]}
            for key, label in PERIOD_LABELS
        ],
    }
