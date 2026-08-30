"""Indicateurs financiers synthétiques du tableau de bord des paiements."""

from datetime import date, timedelta
from decimal import Decimal
import unicodedata

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from bus.models import AbonnementBus, AbonnementCantine
from abonnements.models import (
    AbonnementBus as AbonnementBusHistorique,
    AbonnementCantine as AbonnementCantineHistorique,
)
from utilisateurs.utils import filter_by_user_school

from .allocation import (
    ALLOCATION_COMPONENTS,
    allocate_amount_sequentially,
    allocate_discounts,
    payment_type_plan,
    registration_kind_for_type,
)
from .models import EcheancierPaiement, Paiement, PaiementRemise


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


def _empty_period_values():
    return {
        key: {"amount": 0, "count": 0}
        for key, _label in PERIOD_LABELS
    }


def _payment_service_category(payment_type):
    """Classe les paiements de services qui ne relèvent pas de la scolarité."""
    name = unicodedata.normalize(
        "NFKD", getattr(payment_type, "nom", "") or ""
    ).encode("ascii", "ignore").decode("ascii").lower()
    if "cantine" in name:
        return "cantine"
    if any(token in name for token in ("bus", "transport", "abonnement")):
        return "bus"
    return None


def _merge_period_values(*value_sets):
    merged = _empty_period_values()
    for values in value_sets:
        for key, _label in PERIOD_LABELS:
            merged[key]["amount"] += int(values[key]["amount"] or 0)
            merged[key]["count"] += int(values[key]["count"] or 0)
    return merged


def _ordered_period_values(values):
    return [
        {
            "key": key,
            "label": label,
            "amount": values[key]["amount"],
            "count": values[key]["count"],
        }
        for key, label in PERIOD_LABELS
    ]


def _record_period_amount(values, starts, payment_date, amount, today):
    amount = int(Decimal(str(amount or 0)))
    if amount <= 0 or not payment_date or payment_date > today:
        return
    for key, start in starts.items():
        if payment_date >= start:
            values[key]["amount"] += amount
            values[key]["count"] += 1


def _payment_period_metrics(user, today, starts):
    """Ventile les encaissements entre admission et tranches de scolarité."""
    categories = {
        "scolarite": _empty_period_values(),
        "bus": _empty_period_values(),
        "cantine": _empty_period_values(),
        "inscription": _empty_period_values(),
        "reinscription": _empty_period_values(),
    }
    target_qs = Paiement.objects.filter(
        statut="VALIDE",
        date_paiement__gte=starts["year"],
        date_paiement__lte=today,
    )
    target_qs = filter_by_user_school(
        target_qs, user, "eleve__classe__ecole"
    ).select_related("eleve", "type_paiement")
    targets = list(target_qs)
    if not targets:
        return categories

    target_ids = {payment.pk for payment in targets}
    student_ids = {payment.eleve_id for payment in targets}
    school_years = {payment.annee_scolaire for payment in targets}

    schedules = EcheancierPaiement.objects.filter(
        eleve_id__in=student_ids,
        annee_scolaire__in=school_years,
    )
    schedules = filter_by_user_school(
        schedules, user, "eleve__classe__ecole"
    )
    schedules_by_key = {
        (schedule.eleve_id, schedule.annee_scolaire): schedule
        for schedule in schedules
    }

    history = Paiement.objects.filter(
        statut="VALIDE",
        eleve_id__in=student_ids,
        annee_scolaire__in=school_years,
        date_paiement__lte=today,
    ).select_related("type_paiement")
    history = filter_by_user_school(
        history, user, "eleve__classe__ecole"
    ).order_by(
        "eleve_id", "annee_scolaire", "date_paiement", "date_creation", "pk"
    )

    running_paid = {}
    for payment in history.iterator():
        service_category = _payment_service_category(payment.type_paiement)
        if service_category:
            if payment.pk in target_ids:
                _record_period_amount(
                    categories[service_category], starts,
                    payment.date_paiement, payment.montant, today,
                )
            continue

        payment_key = (payment.eleve_id, payment.annee_scolaire)
        schedule = schedules_by_key.get(payment_key)
        admission_amount = Decimal("0")
        tuition_amount = Decimal("0")
        admission_kind = registration_kind_for_type(payment.type_paiement)

        if schedule is not None:
            initial_paid = running_paid.setdefault(
                payment_key,
                {
                    component: Decimal("0")
                    for component, _due_field, _paid_field in ALLOCATION_COMPONENTS
                },
            )
            allocation, paid_after, unapplied = allocate_amount_sequentially(
                schedule, payment.montant, initial_paid=initial_paid
            )
            running_paid[payment_key] = paid_after
            admission_amount = allocation["inscription"]
            tuition_amount = (
                allocation["tranche_1"]
                + allocation["tranche_2"]
                + allocation["tranche_3"]
                + unapplied
            )
            if admission_kind not in {"inscription", "reinscription"}:
                admission_kind = (
                    "reinscription"
                    if schedule.nature_frais == EcheancierPaiement.NATURE_REINSCRIPTION
                    else "inscription"
                )
        else:
            # Données anciennes sans échéancier : un type d'admission seul peut
            # être classé précisément ; les autres encaissements restent en scolarité.
            plan = payment_type_plan(payment.type_paiement)
            if plan["include_registration"] and not plan["tranches"]:
                admission_amount = Decimal(str(payment.montant or 0))
                admission_kind = admission_kind or "inscription"
            else:
                tuition_amount = Decimal(str(payment.montant or 0))

        if payment.pk not in target_ids:
            continue
        _record_period_amount(
            categories["scolarite"], starts, payment.date_paiement,
            tuition_amount, today,
        )
        if admission_amount > 0:
            _record_period_amount(
                categories[admission_kind or "inscription"], starts,
                payment.date_paiement, admission_amount, today,
            )

    return categories


def _tuition_late_metrics(user, today):
    schedules = (
        EcheancierPaiement.objects
        .filter(
            eleve__statut="ACTIF",
            annee_scolaire=F("eleve__classe__annee_scolaire"),
        )
    )
    schedules = filter_by_user_school(
        schedules, user, "eleve__classe__ecole"
    )
    schedule_rows = list(schedules)
    discounts_by_key = {}
    if schedule_rows:
        student_ids = {schedule.eleve_id for schedule in schedule_rows}
        school_years = {schedule.annee_scolaire for schedule in schedule_rows}
        discounts = (
            PaiementRemise.objects
            .filter(
                paiement__statut="VALIDE",
                paiement__eleve_id__in=student_ids,
                paiement__annee_scolaire__in=school_years,
            )
            .select_related("paiement")
            .order_by("paiement__date_paiement", "paiement_id", "id")
        )
        discounts = filter_by_user_school(
            discounts, user, "paiement__eleve__classe__ecole"
        )
        for discount in discounts:
            key = (
                discount.paiement.eleve_id,
                discount.paiement.annee_scolaire,
            )
            discounts_by_key.setdefault(key, []).append(discount)

    late_amount = Decimal("0")
    late_count = 0
    for schedule in schedule_rows:
        balances_after_cash = {
            key: max(
                Decimal("0"),
                Decimal(str(getattr(schedule, due_field, 0) or 0))
                - Decimal(str(getattr(schedule, paid_field, 0) or 0)),
            )
            for key, due_field, paid_field in ALLOCATION_COMPONENTS
        }
        discount_allocation, _remaining_balances = allocate_discounts(
            schedule,
            discounts_by_key.get(
                (schedule.eleve_id, schedule.annee_scolaire), []
            ),
            balances=balances_after_cash,
        )
        outstanding = Decimal("0")
        for key, due_field, paid_field, due_date_field in (
            ("tranche_1", "tranche_1_due", "tranche_1_payee", "date_echeance_tranche_1"),
            ("tranche_2", "tranche_2_due", "tranche_2_payee", "date_echeance_tranche_2"),
            ("tranche_3", "tranche_3_due", "tranche_3_payee", "date_echeance_tranche_3"),
        ):
            due_date = getattr(schedule, due_date_field, None)
            if due_date and due_date < today:
                outstanding += max(
                    Decimal("0"),
                    Decimal(str(getattr(schedule, due_field, 0) or 0))
                    - Decimal(str(getattr(schedule, paid_field, 0) or 0))
                    - discount_allocation[key],
                )
        if outstanding > 0:
            late_count += 1
            late_amount += outstanding

    return {"amount": int(late_amount), "count": late_count}


def _subscription_metrics(models, user, today, starts):
    """Agrège les abonnements des modules courant et historique.

    Le projet possède deux générations de modèles Bus/Cantine. Les écrans
    historiques continuent à créer des données dans ``abonnements`` tandis
    que les écrans principaux utilisent ``bus``. Le tableau financier doit
    donc lire les deux sources.
    """
    amount_field = DecimalField(max_digits=12, decimal_places=0)
    values = {
        key: {"amount": 0, "count": 0}
        for key, _label in PERIOD_LABELS
    }

    # Un élève n'est en retard que si son abonnement le plus récent est expiré.
    # La comparaison couvre également un renouvellement réalisé depuis l'autre
    # génération du module.
    latest_by_student = {}
    for model in models:
        qs = model.objects.select_related(
            "eleve", "eleve__classe", "eleve__classe__ecole"
        )
        qs = filter_by_user_school(qs, user, "eleve__classe__ecole")

        aggregates = {}
        for key, start in starts.items():
            period_filter = Q(date_debut__gte=start, date_debut__lte=today)
            aggregates[f"{key}_amount"] = Coalesce(
                Sum("montant", filter=period_filter),
                Value(0, output_field=amount_field),
                output_field=amount_field,
            )
            aggregates[f"{key}_count"] = Count("id", filter=period_filter)
        totals = qs.aggregate(**aggregates)
        for key, _label in PERIOD_LABELS:
            values[key]["amount"] += int(
                totals.get(f"{key}_amount") or 0
            )
            values[key]["count"] += int(
                totals.get(f"{key}_count") or 0
            )

        end_field = (
            "date_expiration"
            if hasattr(model, "date_expiration")
            else "date_fin"
        )
        for subscription in qs.iterator():
            end_date = getattr(subscription, end_field, None)
            sort_key = (
                end_date or date.min,
                getattr(subscription, "date_debut", None) or date.min,
                subscription.pk or 0,
            )
            current = latest_by_student.get(subscription.eleve_id)
            if current is None or sort_key > current[0]:
                latest_by_student[subscription.eleve_id] = (
                    sort_key, subscription, end_date
                )

    late_subscriptions = [
        (subscription, end_date)
        for _sort_key, subscription, end_date in latest_by_student.values()
        if subscription.statut != "SUSPENDU"
        and (
            (end_date is not None and end_date < today)
            or subscription.statut == "EXPIRE"
        )
    ]
    late = {
        "amount": sum(
            int(subscription.montant or 0)
            for subscription, _end_date in late_subscriptions
        ),
        "count": len(late_subscriptions),
    }
    return values, late


def build_payment_dashboard_metrics(user, today=None):
    """Construit des données prêtes pour le template et l'endpoint AJAX."""
    today = today or timezone.localdate()
    starts = _period_starts(today)
    payment_metrics = _payment_period_metrics(user, today, starts)
    bus_values, bus_late = _subscription_metrics(
        (AbonnementBus, AbonnementBusHistorique), user, today, starts
    )
    cantine_values, cantine_late = _subscription_metrics(
        (AbonnementCantine, AbonnementCantineHistorique), user, today, starts
    )
    bus_values = _merge_period_values(bus_values, payment_metrics["bus"])
    cantine_values = _merge_period_values(
        cantine_values, payment_metrics["cantine"]
    )

    return {
        "periods": [
            {"key": key, "label": label}
            for key, label in PERIOD_LABELS
        ],
        "year": today.year,
        "categories": [
            {
                "key": "scolarite",
                "label": "Scolarité",
                "icon": "fa-graduation-cap",
                "color": "primary",
                "values": payment_metrics["scolarite"],
                "period_values": _ordered_period_values(
                    payment_metrics["scolarite"]
                ),
                "late": _tuition_late_metrics(user, today),
                "late_label": "Élèves en retard de scolarité",
            },
            {
                "key": "bus",
                "label": "Bus scolaire",
                "icon": "fa-bus",
                "color": "info",
                "values": bus_values,
                "period_values": _ordered_period_values(bus_values),
                "late": bus_late,
                "late_label": "Abonnements bus à renouveler",
            },
            {
                "key": "cantine",
                "label": "Cantine",
                "icon": "fa-utensils",
                "color": "success",
                "values": cantine_values,
                "period_values": _ordered_period_values(cantine_values),
                "late": cantine_late,
                "late_label": "Abonnements cantine à renouveler",
            },
        ],
        "admissions": [
            {
                "key": "inscription",
                "label": "Inscriptions",
                "icon": "fa-user-plus",
                "color": "warning",
                "values": payment_metrics["inscription"],
                "period_values": _ordered_period_values(
                    payment_metrics["inscription"]
                ),
            },
            {
                "key": "reinscription",
                "label": "Réinscriptions",
                "icon": "fa-user-check",
                "color": "secondary",
                "values": payment_metrics["reinscription"],
                "period_values": _ordered_period_values(
                    payment_metrics["reinscription"]
                ),
            },
        ],
    }
