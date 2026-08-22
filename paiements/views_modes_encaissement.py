"""Vue detaillee des eleves et soldes par mode d'encaissement."""

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from eleves.models import Classe
from utilisateurs.permissions import can_view_reports
from utilisateurs.utils import filter_by_user_school

from .models import EcheancierPaiement, ModePaiement, Paiement
from .payment_engine import situation_echeancier


ZERO = Decimal('0')
SITUATIONS = {'', 'solde', 'reste', 'sans_echeancier'}


def _read_date(request, name, default):
    raw_value = (request.GET.get(name) or '').strip()
    if not raw_value:
        return default
    value = parse_date(raw_value)
    if value is None:
        raise ValueError(f"La date « {name} » doit être au format AAAA-MM-JJ.")
    return value


def _read_id(request, name):
    raw_value = (request.GET.get(name) or '').strip()
    if not raw_value:
        return None
    if not raw_value.isdigit():
        raise ValueError(f"Le filtre « {name} » est invalide.")
    return int(raw_value)


def _bad_request(exc):
    return HttpResponse(str(exc), status=400, content_type='text/plain; charset=utf-8')


def collect_modes_students_data(request):
    """Calcule les lignes eleve/mode et le solde global de chaque eleve."""
    today = timezone.localdate()
    start = _read_date(request, 'du', today.replace(day=1))
    end = _read_date(request, 'au', today)
    if start > end:
        raise ValueError("La date de début doit précéder la date de fin.")

    mode_id = _read_id(request, 'mode_id')
    class_id = _read_id(request, 'classe_id')
    query = (request.GET.get('q') or '').strip()[:100]
    payment_situation = (request.GET.get('situation') or '').strip()
    if payment_situation not in SITUATIONS:
        raise ValueError("La situation de paiement sélectionnée est invalide.")

    classes = filter_by_user_school(
        Classe.objects.select_related('ecole').order_by('ecole__nom', 'nom'),
        request.user,
        'ecole',
    )
    if class_id and not classes.filter(pk=class_id).exists():
        raise ValueError("La classe sélectionnée est introuvable ou non autorisée.")
    if mode_id and not ModePaiement.objects.filter(pk=mode_id).exists():
        raise ValueError("Le mode d'encaissement sélectionné est introuvable.")

    payments = Paiement.objects.filter(
        statut='VALIDE',
        date_paiement__gte=start,
        date_paiement__lte=end,
    )
    payments = filter_by_user_school(
        payments, request.user, 'eleve__classe__ecole'
    )
    if mode_id:
        payments = payments.filter(mode_paiement_id=mode_id)
    if class_id:
        payments = payments.filter(eleve__classe_id=class_id)
    if query:
        payments = payments.filter(
            Q(eleve__matricule__icontains=query)
            | Q(eleve__nom__icontains=query)
            | Q(eleve__prenom__icontains=query)
            | Q(eleve__classe__nom__icontains=query)
            | Q(numero_recu__icontains=query)
            | Q(reference_externe__icontains=query)
        )

    amount_field = DecimalField(max_digits=18, decimal_places=0)
    grouped = list(
        payments
        .values(
            'eleve_id',
            'eleve__matricule',
            'eleve__prenom',
            'eleve__nom',
            'eleve__classe_id',
            'eleve__classe__nom',
            'eleve__classe__ecole__nom',
            'mode_paiement_id',
            'mode_paiement__nom',
        )
        .annotate(
            payment_count=Count('id'),
            period_amount=Coalesce(
                Sum('montant'),
                Value(ZERO, output_field=amount_field),
                output_field=amount_field,
            ),
            last_payment=Max('date_paiement'),
        )
        .order_by(
            'mode_paiement__nom',
            'eleve__nom',
            'eleve__prenom',
            'eleve__matricule',
        )
    )

    student_ids = {item['eleve_id'] for item in grouped}
    schedules = EcheancierPaiement.objects.filter(eleve_id__in=student_ids).select_related(
        'eleve', 'eleve__classe', 'eleve__classe__ecole'
    )
    schedules = filter_by_user_school(
        schedules, request.user, 'eleve__classe__ecole'
    )
    schedules_by_student = {item.eleve_id: item for item in schedules}
    balance_date = min(end, today)
    situations_by_student = {}
    for student_id, schedule in schedules_by_student.items():
        situation = situation_echeancier(schedule, date_reference=balance_date)
        if situation['total_du'] > 0 and situation['solde_restant'] <= 0:
            status = 'solde'
            status_label = 'Soldé'
        elif situation['solde_restant'] > 0:
            status = 'reste'
            status_label = 'Reste à payer'
        else:
            status = 'solde'
            status_label = 'Aucun solde'
        situations_by_student[student_id] = {
            'schedule': schedule,
            'due': situation['total_du'],
            'paid': situation['total_encaisse'],
            'discount': situation['total_remises'],
            'balance': situation['solde_restant'],
            'overdue': situation['retard_total'],
            'status': status,
            'status_label': status_label,
            'reliable': not bool(situation['paiements_ecartes_annee']),
        }

    rows = []
    for item in grouped:
        student_situation = situations_by_student.get(item['eleve_id'])
        status = student_situation['status'] if student_situation else 'sans_echeancier'
        if payment_situation and status != payment_situation:
            continue
        rows.append({
            'student_id': item['eleve_id'],
            'matricule': item['eleve__matricule'],
            'student': f"{item['eleve__prenom']} {item['eleve__nom']}",
            'class_id': item['eleve__classe_id'],
            'class_name': item['eleve__classe__nom'],
            'school_name': item['eleve__classe__ecole__nom'],
            'mode_id': item['mode_paiement_id'],
            'mode': item['mode_paiement__nom'],
            'payment_count': int(item['payment_count'] or 0),
            'period_amount': item['period_amount'] or ZERO,
            'last_payment': item['last_payment'],
            'situation': student_situation,
            'status': status,
            'status_label': (
                student_situation['status_label']
                if student_situation
                else 'Sans échéancier'
            ),
        })

    visible_student_ids = {item['student_id'] for item in rows}
    unique_situations = {
        student_id: situations_by_student.get(student_id)
        for student_id in visible_student_ids
    }
    total_balance = sum(
        (
            item['balance']
            for item in unique_situations.values()
            if item is not None
        ),
        ZERO,
    )
    summary = {
        'mode_count': len({item['mode_id'] for item in rows}),
        'student_count': len(visible_student_ids),
        'payment_count': sum(item['payment_count'] for item in rows),
        'period_amount': sum((item['period_amount'] for item in rows), ZERO),
        'balance': total_balance,
        'settled_count': sum(
            1 for item in unique_situations.values()
            if item is not None and item['status'] == 'solde'
        ),
        'remaining_count': sum(
            1 for item in unique_situations.values()
            if item is not None and item['status'] == 'reste'
        ),
        'without_schedule_count': sum(
            1 for item in unique_situations.values() if item is None
        ),
    }

    paginator = Paginator(rows, 25)
    page_obj = paginator.get_page(request.GET.get('page') or 1)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    return {
        'titre_page': "Élèves et soldes par mode d'encaissement",
        'rows': page_obj.object_list,
        'page_obj': page_obj,
        'summary': summary,
        'classes': classes,
        # Conserver aussi les modes historiques désactivés : leurs anciens
        # encaissements doivent rester filtrables dans un rapport.
        'modes': ModePaiement.objects.order_by('nom'),
        'filters': {
            'q': query,
            'du': start,
            'au': end,
            'mode_id': str(mode_id or ''),
            'classe_id': str(class_id or ''),
            'situation': payment_situation,
        },
        'balance_date': balance_date,
        'querystring': query_params.urlencode(),
    }


@can_view_reports
def modes_encaissement_soldes(request):
    try:
        context = collect_modes_students_data(request)
    except ValueError as exc:
        return _bad_request(exc)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    template = (
        'paiements/_modes_encaissement_soldes_resultats.html'
        if is_ajax
        else 'paiements/modes_encaissement_soldes.html'
    )
    return render(request, template, context)
