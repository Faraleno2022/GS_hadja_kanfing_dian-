"""Rapports professionnels : comptabilité des encaissements et recouvrement.

Deux documents destinés à un usage officiel :

* le rapport comptable retrace l'activité d'encaissement sur une période
  (statuts, modes, types, classes, remises, journal détaillé) ;
* le rapport de recouvrement photographie la situation des créances à une date
  d'arrêt (portefeuille, balance âgée, dossiers prioritaires, relances).

Les deux s'appuient sur le moteur unique :func:`payment_engine.situation_echeancier`
afin d'afficher exactement les mêmes soldes et les mêmes retards que les écrans
de l'application.
"""

import io
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from eleves.models import Classe
from eleves.utils_annee import get_annee_active
from rapports.utils import _draw_logo_watermark, _get_logo_path
from utilisateurs.permissions import can_view_reports
from utilisateurs.utils import filter_by_user_school, user_school

from .allocation import INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3
from .models import EcheancierPaiement, Paiement, PaiementRemise, Relance
from .payment_engine import DEADLINE_FIELDS, situation_echeancier


ZERO = Decimal('0')
BLUE = '#174A6E'
BLUE_LIGHT = '#DCEAF3'
GREEN = '#207A54'
ORANGE = '#C2761C'
RED = '#B53A3A'
GREY = '#5D6973'

BUCKETS = (INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3)
BUCKET_LABELS = {
    INSCRIPTION: "Admission (inscription / réinscription)",
    TRANCHE_1: "1ère tranche",
    TRANCHE_2: "2ème tranche",
    TRANCHE_3: "3ème tranche",
}
AGING_BUCKETS = ('1-30 jours', '31-60 jours', '61-90 jours', 'Plus de 90 jours')


def _money(value):
    return f"{int(value or 0):,}".replace(',', ' ')


def _percentage(part, total):
    part = Decimal(str(part or 0))
    total = Decimal(str(total or 0))
    return (part / total * Decimal('100')) if total > 0 else ZERO


def _discount_precision(discount, due):
    if discount <= 0:
        return ''
    rate = _percentage(discount, due)
    return f"Remise appliquée : {_money(discount)} GNF ({rate:.1f} %)"


def _safe_filename(value):
    return re.sub(r'[^\w-]+', '_', value or '').strip('_') or 'etablissement'


def _display_user(user):
    full_name = (user.get_full_name() or '').strip() if user else ''
    return full_name or getattr(user, 'username', '') or 'Système'


def _aging_bucket(days):
    if days <= 30:
        return '1-30 jours'
    if days <= 60:
        return '31-60 jours'
    if days <= 90:
        return '61-90 jours'
    return 'Plus de 90 jours'


def _parse_filters(request):
    """Valide les filtres de l'URL et fige le périmètre du rapport."""
    def read_date(name):
        raw = (request.GET.get(name) or '').strip()
        if not raw:
            return None
        parsed = parse_date(raw)
        if parsed is None:
            raise ValueError(f"La date « {name} » doit être au format AAAA-MM-JJ.")
        return parsed

    start = read_date('du')
    end = read_date('au')
    if start and end and start > end:
        raise ValueError("La date de début doit précéder la date de fin.")

    classe_id = (request.GET.get('classe_id') or '').strip()
    classes = filter_by_user_school(
        Classe.objects.select_related('ecole').order_by('ecole__nom', 'niveau', 'nom'),
        request.user,
        'ecole',
    )
    if classe_id:
        if not classe_id.isdigit():
            raise ValueError("La classe sélectionnée est invalide.")
        classes = classes.filter(pk=int(classe_id))

    classes = list(classes)
    if classe_id and not classes:
        raise ValueError("La classe sélectionnée est introuvable ou non autorisée.")

    school = classes[0].ecole if classes else user_school(request.user)
    requested_year = (request.GET.get('annee_scolaire') or '').strip()
    if requested_year and not re.fullmatch(r'\d{4}-\d{4}', requested_year):
        raise ValueError("L'année scolaire doit être au format AAAA-AAAA.")
    if requested_year:
        school_year = requested_year
    elif len(classes) == 1:
        school_year = classes[0].annee_scolaire
    elif school:
        school_year = get_annee_active(request, school) or ''
    else:
        school_year = ''

    if school_year:
        classes = [item for item in classes if item.annee_scolaire == school_year]

    school_ids = sorted({item.ecole_id for item in classes})
    if len(school_ids) == 1 and classes:
        scoped_school = classes[0].ecole
    elif not classes:
        scoped_school = user_school(request.user)
    else:
        scoped_school = None
    if len(classes) == 1:
        scope_label = f"Classe : {classes[0].nom}"
    elif len(school_ids) == 1 and school:
        scope_label = "Tout l'établissement"
    elif classes:
        scope_label = "Périmètre multi-établissements autorisé"
    else:
        scope_label = "Aucune classe dans le périmètre"

    today = timezone.localdate()
    # Une situation ne se projette pas dans l'avenir : la date d'arrêt est
    # bornée à aujourd'hui même si l'utilisateur demande une date postérieure.
    cutoff = min(end or today, today)
    generated_at = timezone.localtime()
    return {
        'classes': classes,
        'class_ids': [item.pk for item in classes],
        'school': scoped_school,
        'school_name': (
            scoped_school.nom if scoped_school else 'ÉTABLISSEMENTS AUTORISÉS'
        ),
        'school_year': school_year,
        'scope_label': scope_label,
        'start': start,
        'end': end,
        'cutoff': cutoff,
        'historical_cutoff': cutoff < today,
        'generated_at': generated_at,
        'generated_by': _display_user(request.user),
    }


def _reference(data, prefix):
    """Référence unique du document, à citer dans les échanges internes."""
    scope = 'ETAB'
    if len(data['classes']) == 1:
        scope = _safe_filename(data['classes'][0].nom).upper()[:12]
    return f"{prefix}-{data['generated_at'].strftime('%Y%m%d-%H%M')}-{scope}"


def _period_label(data):
    if data['start'] and data['end']:
        return f"Du {data['start'].strftime('%d/%m/%Y')} au {data['end'].strftime('%d/%m/%Y')}"
    if data['start']:
        return f"Depuis le {data['start'].strftime('%d/%m/%Y')}"
    if data['end']:
        return f"Jusqu'au {data['end'].strftime('%d/%m/%Y')}"
    return "Toutes les opérations disponibles"


def _payments_queryset(scope):
    queryset = (
        Paiement.objects
        .filter(eleve__classe_id__in=scope['class_ids'])
        .select_related(
            'eleve', 'eleve__classe', 'type_paiement', 'mode_paiement',
            'cree_par', 'valide_par',
        )
        .prefetch_related('remises__remise')
        .order_by('date_paiement', 'numero_recu')
    )
    if scope['school_year']:
        queryset = queryset.filter(annee_scolaire=scope['school_year'])
    if scope['start']:
        queryset = queryset.filter(date_paiement__gte=scope['start'])
    if scope['end']:
        queryset = queryset.filter(date_paiement__lte=scope['end'])
    return queryset


# ---------------------------------------------------------------------------
# Collecte comptable
# ---------------------------------------------------------------------------

def collect_accounting_data(request):
    data = _parse_filters(request)
    payments = list(_payments_queryset(data))
    validated = [item for item in payments if item.statut == 'VALIDE']

    by_status = {}
    for code, label in Paiement.STATUT_CHOICES:
        rows = [item for item in payments if item.statut == code]
        by_status[code] = {
            'label': label,
            'count': len(rows),
            'amount': sum((item.montant or ZERO) for item in rows),
        }

    by_mode = defaultdict(lambda: {'count': 0, 'amount': ZERO})
    by_type = defaultdict(lambda: {'count': 0, 'amount': ZERO, 'discount': ZERO})
    by_class = defaultdict(lambda: {'count': 0, 'amount': ZERO, 'discount': ZERO})
    by_reason = defaultdict(lambda: {'count': 0, 'amount': ZERO, 'deducted': ZERO})
    payment_rows = []
    total_cash = total_discount = total_deducted = ZERO

    for payment in validated:
        cash = payment.montant or ZERO
        links = list(payment.remises.all())
        discount = sum(((link.montant_remise or ZERO) for link in links), ZERO)
        deducted = sum(
            ((link.montant_remise or ZERO)
             for link in links if link.deduite_du_paiement),
            ZERO,
        )
        mode = payment.mode_paiement.nom if payment.mode_paiement_id else 'Non précisé'
        payment_type = payment.type_paiement.nom if payment.type_paiement_id else 'Non précisé'
        class_name = payment.eleve.classe.nom

        by_mode[mode]['count'] += 1
        by_mode[mode]['amount'] += cash
        by_type[payment_type]['count'] += 1
        by_type[payment_type]['amount'] += cash
        by_type[payment_type]['discount'] += discount
        by_class[class_name]['count'] += 1
        by_class[class_name]['amount'] += cash
        by_class[class_name]['discount'] += discount
        for link in links:
            reason = by_reason[f"{link.libelle_motif} ({link.libelle_portee})"]
            reason['count'] += 1
            reason['amount'] += link.montant_remise or ZERO
            if link.deduite_du_paiement:
                reason['deducted'] += link.montant_remise or ZERO

        total_cash += cash
        total_discount += discount
        total_deducted += deducted
        payment_rows.append({
            'date': payment.date_paiement,
            'receipt': payment.numero_recu,
            'student': payment.eleve.nom_complet,
            'matricule': payment.eleve.matricule,
            'class': class_name,
            'type': payment_type,
            'mode': mode,
            'gross': cash + deducted,
            'cash': cash,
            'discount': discount,
            'reference': payment.reference_externe or '-',
            'cashier': _display_user(payment.cree_par),
            'validator': _display_user(payment.valide_par),
        })

    data.update({
        'period_label': _period_label(data),
        'reference': _reference(data, 'RC'),
        'payments': payments,
        'payment_rows': payment_rows,
        'by_status': by_status,
        'by_mode': dict(sorted(by_mode.items())),
        'by_type': dict(sorted(by_type.items())),
        'by_class': dict(sorted(by_class.items())),
        'by_reason': dict(sorted(by_reason.items())),
        'payment_count': len(payments),
        'total_all_statuses': sum((item.montant or ZERO) for item in payments),
        'validated_count': len(validated),
        'total_cash': total_cash,
        'total_discount': total_discount,
        'total_deducted': total_deducted,
        'total_gross': total_cash + total_deducted,
        'total_coverage': total_cash + total_discount,
    })
    return data


# ---------------------------------------------------------------------------
# Collecte recouvrement
# ---------------------------------------------------------------------------

def collect_recovery_data(request):
    data = _parse_filters(request)
    cutoff = data['cutoff']
    # Les cumuls stockés sur l'échéancier valent « aujourd'hui » : on ne les
    # utilise jamais pour reconstituer une situation passée.
    use_legacy = not data['historical_cutoff']

    schedules_qs = (
        EcheancierPaiement.objects
        .filter(eleve__classe_id__in=data['class_ids'], eleve__statut='ACTIF')
        .select_related(
            'eleve', 'eleve__classe', 'eleve__responsable_principal',
            'eleve__classe__ecole',
        )
        .order_by('eleve__classe__nom', 'eleve__nom', 'eleve__prenom')
    )
    if data['school_year']:
        schedules_qs = schedules_qs.filter(annee_scolaire=data['school_year'])
    schedules = list(schedules_qs)

    relances_qs = (
        Relance.objects
        .filter(eleve__classe_id__in=data['class_ids'])
        .select_related('eleve', 'eleve__classe', 'cree_par')
        .order_by('eleve_id', '-date_creation')
    )
    all_relances = [
        item for item in relances_qs
        if timezone.localdate(item.date_creation) <= cutoff
    ]
    relances_by_student = defaultdict(list)
    for reminder in all_relances:
        relances_by_student[reminder.eleve_id].append(reminder)

    period_relances = all_relances
    if data['start']:
        period_relances = [
            item for item in period_relances
            if timezone.localdate(item.date_creation) >= data['start']
        ]
    if data['end']:
        period_relances = [
            item for item in period_relances
            if timezone.localdate(item.date_creation) <= data['end']
        ]

    class_summary = defaultdict(lambda: {
        'students': 0, 'due': ZERO, 'cash': ZERO, 'discount': ZERO,
        'balance': ZERO, 'overdue': ZERO, 'upcoming': ZERO, 'reminders': 0,
    })
    bucket_summary = {
        bucket: {'due': ZERO, 'cash': ZERO, 'discount': ZERO,
                 'balance': ZERO, 'overdue': ZERO, 'students': 0}
        for bucket in BUCKETS
    }
    aging = {label: {'count': 0, 'amount': ZERO} for label in AGING_BUCKETS}
    priority_rows = []
    student_rows = []
    inconsistent_rows = []
    settled_count = settled_with_discount_count = 0
    partial_count = unpaid_count = overdue_count = 0
    total_due = total_cash = total_discount = ZERO
    total_balance = total_overdue = total_upcoming = ZERO

    for schedule in schedules:
        situation = situation_echeancier(
            schedule, date_reference=cutoff, utiliser_cumuls_legacy=use_legacy,
        )
        due = situation['total_du']
        cash = situation['total_encaisse']
        discount = situation['total_remises']
        balance = situation['solde_restant']
        overdue = situation['retard_total']

        upcoming = ZERO
        oldest_overdue = None
        for bucket in BUCKETS:
            remaining = situation['restes'][bucket]
            summary = bucket_summary[bucket]
            summary['due'] += situation['dues'][bucket]
            summary['cash'] += situation['payes'][bucket]
            summary['discount'] += situation['remises'][bucket]
            summary['balance'] += remaining
            summary['overdue'] += situation['retards'][bucket]
            if remaining > 0:
                summary['students'] += 1
            if remaining <= 0:
                continue
            deadline = getattr(schedule, DEADLINE_FIELDS[bucket], None)
            if deadline is None:
                continue
            if situation['retards'][bucket] > 0:
                days = (cutoff - deadline).days
                slot = aging[_aging_bucket(days)]
                slot['count'] += 1
                slot['amount'] += remaining
                if oldest_overdue is None or deadline < oldest_overdue:
                    oldest_overdue = deadline
            elif cutoff <= deadline <= cutoff + timedelta(days=30):
                upcoming += remaining

        reminders = relances_by_student[schedule.eleve_id]
        latest = reminders[0] if reminders else None
        class_name = schedule.eleve.classe.nom
        summary = class_summary[class_name]
        summary['students'] += 1
        summary['due'] += due
        summary['cash'] += cash
        summary['discount'] += discount
        summary['balance'] += balance
        summary['overdue'] += overdue
        summary['upcoming'] += upcoming
        summary['reminders'] += len(reminders)

        total_due += due
        total_cash += cash
        total_discount += discount
        total_balance += balance
        total_overdue += overdue
        total_upcoming += upcoming

        if balance <= 0:
            settled_count += 1
            if discount > 0:
                settled_with_discount_count += 1
                recovery_status = 'Soldé avec remise'
            else:
                recovery_status = 'Soldé'
        elif cash + discount > 0:
            partial_count += 1
            recovery_status = 'En retard' if overdue > 0 else 'Paiement partiel'
        else:
            unpaid_count += 1
            recovery_status = 'En retard' if overdue > 0 else 'À payer'

        responsible = schedule.eleve.responsable_principal
        responsible_name = responsible.nom_complet if responsible else '-'
        responsible_phone = responsible.telephone if responsible else '-'
        student_rows.append({
            'matricule': schedule.eleve.matricule,
            'student': schedule.eleve.nom_complet,
            'class': class_name,
            'responsible': responsible_name,
            'phone': responsible_phone,
            'due': due,
            'cash': cash,
            'discount': discount,
            'discount_rate': _percentage(discount, due),
            'balance': balance,
            'overdue': overdue,
            'upcoming': upcoming,
            'status': recovery_status,
            'precision': _discount_precision(discount, due),
            'reminder_count': len(reminders),
            'last_reminder': latest.date_creation if latest else None,
            'last_status': latest.get_statut_display() if latest else 'Jamais relancé',
        })

        if overdue > 0:
            overdue_count += 1
            priority_rows.append({
                'matricule': schedule.eleve.matricule,
                'student': schedule.eleve.nom_complet,
                'class': class_name,
                'responsible': responsible_name,
                'phone': responsible_phone,
                'due': due,
                'cash': cash,
                'discount': discount,
                'discount_rate': _percentage(discount, due),
                'coverage': cash + discount,
                'balance': balance,
                'overdue': overdue,
                'days': (cutoff - oldest_overdue).days if oldest_overdue else 0,
                'reminder_count': len(reminders),
                'last_reminder': latest.date_creation if latest else None,
                'last_status': latest.get_statut_display() if latest else 'Jamais relancé',
            })

        # Garde-fou : des encaissements réels écartés faussent le solde.
        ecartes = situation['paiements_ecartes_annee']
        if ecartes:
            inconsistent_rows.append({
                'matricule': schedule.eleve.matricule,
                'student': schedule.eleve.nom_complet,
                'class': class_name,
                'schedule_year': schedule.annee_scolaire,
                'payment_years': ', '.join(sorted({item.annee_scolaire for item in ecartes})),
                'count': len(ecartes),
                'amount': sum((item.montant or ZERO) for item in ecartes),
            })

    priority_rows.sort(key=lambda item: (-item['overdue'], -item['days'], item['student']))

    reminder_by_channel = defaultdict(lambda: {'count': 0, 'sent': 0, 'failed': 0})
    reminder_by_status = defaultdict(int)
    for reminder in period_relances:
        label = reminder.get_canal_display()
        reminder_by_channel[label]['count'] += 1
        if reminder.statut == 'ENVOYEE':
            reminder_by_channel[label]['sent'] += 1
        if reminder.statut == 'ECHEC':
            reminder_by_channel[label]['failed'] += 1
        reminder_by_status[reminder.get_statut_display()] += 1

    validated_period = [
        item for item in _payments_queryset(data)
        if item.statut == 'VALIDE' and item.date_paiement <= cutoff
    ]
    recovery_rate = (
        (total_cash + total_discount) / total_due * Decimal('100') if total_due else ZERO
    )
    discount_rate = _percentage(total_discount, total_due)
    data.update({
        'period_label': _period_label(data),
        'reference': _reference(data, 'RR'),
        'schedule_count': len(schedules),
        'class_summary': dict(sorted(class_summary.items())),
        'bucket_summary': bucket_summary,
        'aging': aging,
        'priority_rows': priority_rows,
        'student_rows': student_rows,
        'inconsistent_rows': inconsistent_rows,
        'total_due': total_due,
        'total_cash': total_cash,
        'total_discount': total_discount,
        'total_coverage': total_cash + total_discount,
        'total_balance': total_balance,
        'total_overdue': total_overdue,
        'total_upcoming': total_upcoming,
        'recovery_rate': recovery_rate,
        'discount_rate': discount_rate,
        'settled_count': settled_count,
        'settled_with_discount_count': settled_with_discount_count,
        'partial_count': partial_count,
        'unpaid_count': unpaid_count,
        'overdue_count': overdue_count,
        'period_payment_count': len(validated_period),
        'period_cash': sum((item.montant or ZERO) for item in validated_period),
        'period_relances': period_relances,
        'reminder_by_channel': dict(sorted(reminder_by_channel.items())),
        'reminder_by_status': dict(sorted(reminder_by_status.items())),
    })
    return data


# ---------------------------------------------------------------------------
# Rendu PDF
# ---------------------------------------------------------------------------

def _numbered_canvas(footer_text, page_width):
    """Canvas à deux passes : la pagination « Page X/Y » exige le total final."""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as pdf_canvas

    class NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self.saveState()
                self.setFont('Helvetica', 6.5)
                self.setFillColor(colors.HexColor(GREY))
                self.drawString(0.8 * cm, 0.48 * cm, footer_text)
                self.drawRightString(
                    page_width - 0.8 * cm, 0.48 * cm,
                    f"Page {self._pageNumber}/{total}",
                )
                self.restoreState()
                super().showPage()
            super().save()

    return NumberedCanvas


def _pdf_primitives(data, title):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportTitle', parent=styles['Title'], fontName='Helvetica-Bold',
        fontSize=18, leading=21, textColor=colors.HexColor(BLUE), alignment=TA_LEFT,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name='ReportSubTitle', parent=styles['Normal'], fontSize=9, leading=12,
        textColor=colors.HexColor(GREY), spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=12, leading=15, textColor=colors.HexColor(BLUE),
        spaceBefore=9, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name='SmallCell', parent=styles['Normal'], fontSize=6.8, leading=8.2,
        textColor=colors.HexColor('#202B33'),
    ))
    styles.add(ParagraphStyle(
        name='SmallCellCenter', parent=styles['SmallCell'], alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='HeaderCell', parent=styles['SmallCellCenter'],
        textColor=colors.white, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        name='SmallCellRight', parent=styles['SmallCell'], alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name='Note', parent=styles['Normal'], fontSize=7.2, leading=9,
        textColor=colors.HexColor(GREY),
    ))

    def paragraph(value, style='SmallCell'):
        safe_value = escape(str(value if value is not None else '')).replace('\n', '<br/>')
        return Paragraph(safe_value, styles[style])

    def table(rows, widths=None, numeric_from=None, numeric_columns=None, total_row=False):
        rendered = [
            [
                paragraph(value, 'HeaderCell' if row_index == 0 else 'SmallCell')
                for value in row
            ]
            for row_index, row in enumerate(rows)
        ]
        commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#AEBBC4')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F7FA')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        if numeric_from is not None:
            commands.append(('ALIGN', (numeric_from, 1), (-1, -1), 'RIGHT'))
        for column in numeric_columns or ():
            commands.append(('ALIGN', (column, 1), (column, -1), 'RIGHT'))
        if total_row and len(rows) > 1:
            commands.extend([
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(BLUE_LIGHT)),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ])
        return Table(rendered, colWidths=widths, repeatRows=1, style=TableStyle(commands))

    def kpis(items):
        cells = []
        for label, value, color in items:
            cells.append([
                [paragraph(label, 'SmallCellCenter')],
                [Paragraph(f"<b>{escape(str(value))}</b>", ParagraphStyle(
                    f'Kpi{len(cells)}', parent=styles['Normal'], fontSize=13,
                    leading=15, alignment=TA_CENTER, textColor=colors.HexColor(color),
                ))],
            ])
        return Table(
            [[Table(cell, colWidths=[4.15 * cm], style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
                ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#C7D4DD')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ])) for cell in cells]],
            colWidths=[4.35 * cm] * len(cells),
        )

    page_width, page_height = landscape(A4)
    logo_path = _get_logo_path(data['school']) if data.get('school') else ''

    def on_page(canvas, doc):
        _draw_logo_watermark(canvas, logo_path, page_width, page_height)
        canvas.saveState()
        canvas.setTitle(title)
        canvas.setAuthor(data['generated_by'])
        canvas.setSubject(
            f"{data['reference']} | {data['scope_label']} | "
            f"{data.get('school_year') or 'année non précisée'}"
        )
        if logo_path:
            try:
                canvas.drawImage(
                    logo_path, 0.8 * cm, page_height - 1.25 * cm,
                    width=1.4 * cm, height=0.75 * cm,
                    preserveAspectRatio=True, mask='auto',
                )
            except Exception:
                pass
        canvas.setFillColor(colors.HexColor(BLUE))
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(2.4 * cm, page_height - 0.9 * cm, data['school_name'])
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor(GREY))
        canvas.drawRightString(
            page_width - 0.8 * cm, page_height - 0.9 * cm,
            f"{title} — réf. {data['reference']}",
        )
        canvas.setStrokeColor(colors.HexColor('#9DB4C5'))
        canvas.line(0.8 * cm, page_height - 1.35 * cm, page_width - 0.8 * cm, page_height - 1.35 * cm)
        canvas.line(0.8 * cm, 0.8 * cm, page_width - 0.8 * cm, 0.8 * cm)
        canvas.restoreState()

    return styles, paragraph, table, kpis, on_page


def _document(data, title):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        topMargin=1.55 * cm, bottomMargin=1.05 * cm,
        leftMargin=0.8 * cm, rightMargin=0.8 * cm,
        title=title, author=data['generated_by'],
    )
    return buffer, doc


def _title_elements(data, styles, title, subtitle):
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer

    details = [f"Réf. {data['reference']}", data['scope_label']]
    if data.get('school_year'):
        details.append(f"Année scolaire : {data['school_year']}")
    details.append(subtitle)
    return [
        Spacer(1, 0.1 * cm),
        Paragraph(escape(title), styles['ReportTitle']),
        Paragraph(escape(' | '.join(details)), styles['ReportSubTitle']),
    ]


def _signature_block(table, columns):
    from reportlab.lib.units import cm

    return table(
        [[label for label, _value in columns], [value for _label, value in columns]],
        widths=[8.8 * cm] * len(columns),
    )


def _build(doc, buffer, elements, data, title, on_page):
    footer = (
        f"Document confidentiel — {data['reference']} — généré par "
        f"{data['generated_by']} le {data['generated_at'].strftime('%d/%m/%Y à %H:%M')}"
    )
    from reportlab.lib.pagesizes import A4, landscape

    page_width, _height = landscape(A4)
    doc.build(
        elements, onFirstPage=on_page, onLaterPages=on_page,
        canvasmaker=_numbered_canvas(footer, page_width),
    )
    buffer.seek(0)
    return buffer


def build_accounting_pdf(data):
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, Spacer, Table

    title = 'RAPPORT COMPTABLE DES ENCAISSEMENTS'
    styles, _p, table, kpis, on_page = _pdf_primitives(data, title)
    buffer, doc = _document(data, title)

    elements = _title_elements(data, styles, title, data['period_label'])
    elements.append(kpis([
        ('Encaissé (net)', f"{_money(data['total_cash'])} GNF", GREEN),
        ('Facturé (brut)', f"{_money(data['total_gross'])} GNF", BLUE),
        ('Remises accordées', f"{_money(data['total_discount'])} GNF", ORANGE),
        ('Couverture élèves', f"{_money(data['total_coverage'])} GNF", BLUE),
        ('Paiements validés', str(data['validated_count']), GREEN),
        ('En attente / rejetés', (
            f"{data['by_status']['EN_ATTENTE']['count']} / "
            f"{data['by_status']['REJETE']['count']}"
        ), ORANGE),
    ]))

    elements.append(Paragraph('1. SYNTHÈSE PAR STATUT', styles['SectionTitle']))
    status_rows = [['Statut', 'Nombre', 'Montant (GNF)', 'Part des opérations']]
    for code, _label in Paiement.STATUT_CHOICES:
        item = data['by_status'][code]
        share = (item['count'] / data['payment_count'] * 100) if data['payment_count'] else 0
        status_rows.append([item['label'], item['count'], _money(item['amount']), f"{share:.1f} %"])
    status_rows.append([
        'TOTAL', data['payment_count'], _money(data['total_all_statuses']),
        '100 %' if data['payment_count'] else '0 %',
    ])
    elements.append(table(
        status_rows, widths=[7 * cm, 4 * cm, 6 * cm, 5 * cm],
        numeric_from=1, total_row=True,
    ))

    elements.append(Paragraph(
        '2. RAPPROCHEMENT DE CAISSE (opérations validées)', styles['SectionTitle'],
    ))
    mode_rows = [['Mode de règlement', 'Opérations', 'Encaissé (GNF)', '% du total']]
    for label, item in data['by_mode'].items():
        pct = item['amount'] / data['total_cash'] * 100 if data['total_cash'] else ZERO
        mode_rows.append([label, item['count'], _money(item['amount']), f"{pct:.1f} %"])
    if len(mode_rows) == 1:
        mode_rows.append(['Aucun encaissement validé', 0, '0', '0 %'])
    else:
        mode_rows.append([
            'TOTAL', data['validated_count'], _money(data['total_cash']), '100 %',
        ])

    type_rows = [['Type de paiement', 'Opérations', 'Encaissé (GNF)', 'Remises (GNF)']]
    for label, item in data['by_type'].items():
        type_rows.append([label, item['count'], _money(item['amount']), _money(item['discount'])])
    if len(type_rows) == 1:
        type_rows.append(['Aucun encaissement validé', 0, '0', '0'])
    else:
        type_rows.append([
            'TOTAL', data['validated_count'], _money(data['total_cash']),
            _money(data['total_discount']),
        ])
    elements.append(Table(
        [[
            table(mode_rows, widths=[4.6 * cm, 2.4 * cm, 3.6 * cm, 2.4 * cm],
                  numeric_from=1, total_row=len(data['by_mode']) > 0),
            table(type_rows, widths=[5.4 * cm, 2.2 * cm, 3.4 * cm, 2.8 * cm],
                  numeric_from=1, total_row=len(data['by_type']) > 0),
        ]],
        colWidths=[13.5 * cm, 14 * cm],
    ))

    elements.append(Paragraph('3. SYNTHÈSE PAR CLASSE', styles['SectionTitle']))
    class_rows = [['Classe', 'Paiements', 'Encaissé (GNF)', 'Remises (GNF)', 'Couverture (GNF)']]
    for label, item in data['by_class'].items():
        class_rows.append([
            label, item['count'], _money(item['amount']), _money(item['discount']),
            _money(item['amount'] + item['discount']),
        ])
    if len(class_rows) == 1:
        class_rows.append(['Aucune classe avec encaissement', 0, '0', '0', '0'])
    class_rows.append([
        'TOTAL', data['validated_count'], _money(data['total_cash']),
        _money(data['total_discount']), _money(data['total_coverage']),
    ])
    elements.append(table(
        class_rows, widths=[8 * cm, 3 * cm, 5 * cm, 5 * cm, 5 * cm],
        numeric_from=1, total_row=True,
    ))

    elements.append(Paragraph('4. REMISES ET RÉDUCTIONS', styles['SectionTitle']))
    discount_rows = [['Motif et portée', 'Lignes', 'Remise (GNF)', 'dont déduite du reçu (GNF)']]
    for label, item in data['by_reason'].items():
        discount_rows.append([label, item['count'], _money(item['amount']), _money(item['deducted'])])
    if len(discount_rows) == 1:
        discount_rows.append(['Aucune remise sur les paiements validés', 0, '0', '0'])
    discount_rows.append([
        'TOTAL', sum(item['count'] for item in data['by_reason'].values()),
        _money(data['total_discount']), _money(data['total_deducted']),
    ])
    elements.append(table(
        discount_rows, widths=[11 * cm, 3 * cm, 6 * cm, 6 * cm],
        numeric_from=1, total_row=True,
    ))
    elements.append(Paragraph(
        "Lecture : « déduite du reçu » signifie que la remise a déjà été retirée du "
        "montant encaissé ; le montant facturé brut vaut alors encaissé + remise déduite.",
        styles['Note'],
    ))

    if data['payment_rows']:
        elements.append(PageBreak())
        elements.append(Paragraph(
            '5. JOURNAL DÉTAILLÉ DES ENCAISSEMENTS VALIDÉS', styles['SectionTitle'],
        ))
        elements.append(Paragraph(
            escape(f"{data['scope_label']} | {data['period_label']}"),
            styles['ReportSubTitle'],
        ))
        detail_rows = [[
            'Date', 'Reçu', 'Matricule / Élève', 'Classe', 'Type', 'Mode',
            'Brut', 'Remise', 'Encaissé', 'Référence', 'Caissier / Validateur',
        ]]
        for item in data['payment_rows']:
            detail_rows.append([
                item['date'].strftime('%d/%m/%Y'), item['receipt'],
                f"{item['matricule']}\n{item['student']}", item['class'],
                item['type'], item['mode'], _money(item['gross']),
                _money(item['discount']), _money(item['cash']), item['reference'],
                f"{item['cashier']}\n{item['validator']}",
            ])
        detail_rows.append([
            'TOTAL', f"{data['validated_count']} reçus", '', '', '', '',
            _money(data['total_gross']), _money(data['total_discount']),
            _money(data['total_cash']), '', '',
        ])
        elements.append(table(
            detail_rows,
            widths=[1.7 * cm, 2.1 * cm, 3.9 * cm, 2.5 * cm, 3.1 * cm, 2.2 * cm,
                    2.3 * cm, 2.1 * cm, 2.3 * cm, 2.6 * cm, 3 * cm],
            numeric_columns=(6, 7, 8), total_row=True,
        ))
    else:
        elements.append(Paragraph(
            "Aucune opération validée pour les filtres sélectionnés : le rapport se "
            "limite volontairement à la page de synthèse.",
            styles['Note'],
        ))

    elements.extend([
        Spacer(1, 0.35 * cm),
        Paragraph(
            "Contrôle recommandé : rapprocher les montants par mode avec les bordereaux "
            "de caisse, les relevés Mobile Money, les chèques et les relevés bancaires.",
            styles['Note'],
        ),
        Spacer(1, 0.35 * cm),
        _signature_block(table, [
            ('Établi par', data['generated_by']),
            ('Contrôlé par (comptabilité)', 'Nom / Date / Signature'),
            ('Approuvé par (direction)', 'Nom / Date / Signature'),
        ]),
    ])
    return _build(doc, buffer, elements, data, title, on_page)


def build_recovery_pdf(data):
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, Spacer, Table

    title = 'RAPPORT PROFESSIONNEL DE RECOUVREMENT'
    styles, _p, table, kpis, on_page = _pdf_primitives(data, title)
    buffer, doc = _document(data, title)

    subtitle = (
        f"Situation arrêtée au {data['cutoff'].strftime('%d/%m/%Y')} | "
        f"Activité : {data['period_label']}"
    )
    elements = _title_elements(data, styles, title, subtitle)
    elements.append(kpis([
        ('Créances totales', f"{_money(data['total_due'])} GNF", BLUE),
        ('Couverture', f"{_money(data['total_coverage'])} GNF", GREEN),
        ('Solde à recouvrer', f"{_money(data['total_balance'])} GNF", ORANGE),
        ('Retard exigible', f"{_money(data['total_overdue'])} GNF", RED),
        ('Taux de recouvrement', f"{data['recovery_rate']:.1f} %", GREEN),
        ('Élèves en retard', str(data['overdue_count']), RED),
    ]))

    elements.append(Paragraph('1. PORTEFEUILLE DE RECOUVREMENT', styles['SectionTitle']))
    elements.append(table([
        ['Indicateur', 'Élèves', 'Montant (GNF)', 'Observation'],
        ['Créances brutes', data['schedule_count'], _money(data['total_due']),
         'Échéanciers actifs suivis'],
        ['Encaissements cumulés', '-', _money(data['total_cash']),
         "Paiements validés affectés poste par poste"],
        ['Remises imputées', '-', _money(data['total_discount']),
         f"Réductions validées — {data['discount_rate']:.1f} % des créances"],
        ['Solde à recouvrer', data['schedule_count'] - data['settled_count'],
         _money(data['total_balance']), 'Après paiements et remises'],
        ['Élèves soldés', data['settled_count'], '-', 'Aucun solde restant'],
        ['Dont soldés avec remise', data['settled_with_discount_count'], '-',
         'Le paiement et la remise couvrent toute la scolarité'],
        ['Paiement partiel', data['partial_count'], '-', 'Couverture incomplète'],
        ['Sans aucun règlement', data['unpaid_count'], '-', 'Aucune couverture enregistrée'],
        ['Dont en retard', data['overdue_count'], _money(data['total_overdue']),
         f"Échéances dépassées au {data['cutoff'].strftime('%d/%m/%Y')}"],
        ['Échéances sous 30 jours', '-', _money(data['total_upcoming']),
         'Prévention à organiser'],
        ['Encaissements sur la période', data['period_payment_count'],
         _money(data['period_cash']), data['period_label']],
    ], widths=[6.5 * cm, 3 * cm, 5.5 * cm, 11 * cm], numeric_from=1))

    elements.append(Paragraph('2. PERFORMANCE PAR CLASSE', styles['SectionTitle']))
    class_rows = [[
        'Classe', 'Élèves', 'Dû', 'Encaissé', 'Remises', 'Remise %', 'Solde',
        'Retard', 'À 30 jours', 'Relances', 'Recouvrement %',
    ]]
    for label, item in data['class_summary'].items():
        rate = ((item['cash'] + item['discount']) / item['due'] * 100) if item['due'] else ZERO
        discount_rate = _percentage(item['discount'], item['due'])
        class_rows.append([
            label, item['students'], _money(item['due']), _money(item['cash']),
            _money(item['discount']), f"{discount_rate:.1f} %", _money(item['balance']),
            _money(item['overdue']), _money(item['upcoming']), item['reminders'],
            f"{rate:.1f} %",
        ])
    if len(class_rows) == 1:
        class_rows.append([
            'Aucun échéancier actif', 0, '0', '0', '0', '0 %', '0', '0', '0', 0, '0 %',
        ])
    class_rows.append([
        'TOTAL', data['schedule_count'], _money(data['total_due']),
        _money(data['total_cash']), _money(data['total_discount']),
        f"{data['discount_rate']:.1f} %",
        _money(data['total_balance']), _money(data['total_overdue']),
        _money(data['total_upcoming']),
        sum(item['reminders'] for item in data['class_summary'].values()),
        f"{data['recovery_rate']:.1f} %",
    ])
    elements.append(table(
        class_rows,
        widths=[4.1 * cm, 1.5 * cm, 2.55 * cm, 2.55 * cm, 2.4 * cm, 1.7 * cm,
                2.55 * cm, 2.55 * cm, 2.3 * cm, 1.6 * cm, 1.9 * cm],
        numeric_from=1, total_row=True,
    ))

    elements.append(Paragraph(
        '3. VENTILATION PAR POSTE (inscription et tranches)', styles['SectionTitle'],
    ))
    bucket_rows = [[
        'Poste', 'Dû (GNF)', 'Encaissé (GNF)', 'Remises (GNF)', 'Remise %',
        'Reste (GNF)', 'Dont exigible (GNF)', 'Élèves concernés', 'Couverture %',
    ]]
    for bucket in BUCKETS:
        item = data['bucket_summary'][bucket]
        rate = ((item['cash'] + item['discount']) / item['due'] * 100) if item['due'] else ZERO
        discount_rate = _percentage(item['discount'], item['due'])
        bucket_rows.append([
            BUCKET_LABELS[bucket], _money(item['due']), _money(item['cash']),
            _money(item['discount']), f"{discount_rate:.1f} %", _money(item['balance']),
            _money(item['overdue']), item['students'], f"{rate:.1f} %",
        ])
    bucket_rows.append([
        'TOTAL', _money(data['total_due']), _money(data['total_cash']),
        _money(data['total_discount']), f"{data['discount_rate']:.1f} %",
        _money(data['total_balance']), _money(data['total_overdue']), '-',
        f"{data['recovery_rate']:.1f} %",
    ])
    elements.append(table(
        bucket_rows,
        widths=[5 * cm, 3 * cm, 3 * cm, 2.7 * cm, 1.8 * cm, 3 * cm, 3.2 * cm,
                2.3 * cm, 2.4 * cm],
        numeric_from=1, total_row=True,
    ))

    elements.append(PageBreak())
    elements.append(Paragraph(
        '4. REMISES ET SITUATION DÉTAILLÉE DES ÉLÈVES', styles['SectionTitle'],
    ))
    student_rows = [[
        'Matricule / Élève', 'Classe', 'Dû', 'Encaissé', 'Remise', 'Remise %',
        'Solde', 'Situation / précision',
    ]]
    for item in data['student_rows']:
        situation = item['status']
        if item['precision']:
            situation = f"{situation}\n{item['precision']}"
        student_rows.append([
            f"{item['matricule']}\n{item['student']}", item['class'], _money(item['due']),
            _money(item['cash']), _money(item['discount']),
            f"{item['discount_rate']:.1f} %", _money(item['balance']), situation,
        ])
    if len(student_rows) == 1:
        student_rows.append(['Aucun échéancier actif', '', '0', '0', '0', '0 %', '0', '-'])
    elements.append(table(
        student_rows,
        widths=[4.1 * cm, 2.5 * cm, 2.7 * cm, 2.7 * cm, 2.5 * cm, 1.8 * cm,
                2.7 * cm, 8 * cm],
        numeric_columns=(2, 3, 4, 5, 6),
    ))

    elements.append(Paragraph('5. BALANCE ÂGÉE DES IMPAYÉS', styles['SectionTitle']))
    aging_rows = [['Ancienneté du retard', 'Échéances', 'Montant en retard (GNF)', 'Part du retard']]
    for label in AGING_BUCKETS:
        item = data['aging'][label]
        share = item['amount'] / data['total_overdue'] * 100 if data['total_overdue'] else ZERO
        aging_rows.append([label, item['count'], _money(item['amount']), f"{share:.1f} %"])
    aging_rows.append([
        'TOTAL', sum(item['count'] for item in data['aging'].values()),
        _money(data['total_overdue']), '100 %' if data['total_overdue'] else '0 %',
    ])
    elements.append(table(
        aging_rows, widths=[8 * cm, 3 * cm, 6 * cm, 4 * cm],
        numeric_from=1, total_row=True,
    ))

    if data['priority_rows']:
        elements.append(PageBreak())
        elements.append(Paragraph(
            '6. DOSSIERS PRIORITAIRES DE RECOUVREMENT', styles['SectionTitle'],
        ))
        elements.append(Paragraph(
            escape(
                f"Situation arrêtée au {data['cutoff'].strftime('%d/%m/%Y')} | "
                "Classement par montant en retard décroissant"
            ),
            styles['ReportSubTitle'],
        ))
        priority = [[
            'Matricule / Élève', 'Classe', 'Responsable / Téléphone', 'Dû',
            'Encaissé / Remise', 'Solde', 'Retard', 'Jours', 'Relances', 'Dernière action',
        ]]
        for item in data['priority_rows']:
            last = item['last_reminder'].strftime('%d/%m/%Y') if item['last_reminder'] else '-'
            priority.append([
                f"{item['matricule']}\n{item['student']}", item['class'],
                f"{item['responsible']}\n{item['phone']}", _money(item['due']),
                f"{_money(item['cash'])}\nRemise : {_money(item['discount'])} ({item['discount_rate']:.1f} %)",
                _money(item['balance']), _money(item['overdue']),
                item['days'], item['reminder_count'], f"{last}\n{item['last_status']}",
            ])
        priority.append([
            'TOTAL', f"{len(data['priority_rows'])} dossiers", '', '', '', '',
            _money(data['total_overdue']), '', '', '',
        ])
        elements.append(table(
            priority,
            widths=[3.9 * cm, 2.5 * cm, 4.2 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm,
                    2.5 * cm, 1.5 * cm, 1.6 * cm, 3.2 * cm],
            numeric_columns=(3, 4, 5, 6, 7, 8), total_row=True,
        ))
    else:
        elements.append(Paragraph(
            "Aucun dossier en retard à la date d'arrêt : le portefeuille est à jour.",
            styles['Note'],
        ))

    elements.append(Paragraph('7. PILOTAGE DES RELANCES', styles['SectionTitle']))
    channel_rows = [['Canal', 'Actions', 'Envoyées', 'Échecs', 'Taux de succès']]
    for label, item in data['reminder_by_channel'].items():
        success = item['sent'] / item['count'] * 100 if item['count'] else 0
        channel_rows.append([label, item['count'], item['sent'], item['failed'], f"{success:.1f} %"])
    if len(channel_rows) == 1:
        channel_rows.append(['Aucune relance sur la période', 0, 0, 0, '0 %'])
    status_rows = [['Statut de relance', 'Nombre']]
    for label, count in data['reminder_by_status'].items():
        status_rows.append([label, count])
    if len(status_rows) == 1:
        status_rows.append(['Aucune relance', 0])
    elements.append(Table(
        [[
            table(channel_rows, widths=[4 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 3 * cm],
                  numeric_from=1),
            table(status_rows, widths=[7 * cm, 3 * cm], numeric_from=1),
        ]],
        colWidths=[15 * cm, 11 * cm],
    ))

    if data['inconsistent_rows']:
        elements.append(Paragraph(
            '8. CONTRÔLE QUALITÉ — SOLDES NON FIABLES', styles['SectionTitle'],
        ))
        control_rows = [[
            'Matricule / Élève', 'Classe', 'Année de l\'échéancier',
            'Année des paiements écartés', 'Paiements', 'Montant écarté (GNF)',
        ]]
        for item in data['inconsistent_rows']:
            control_rows.append([
                f"{item['matricule']}\n{item['student']}", item['class'],
                item['schedule_year'], item['payment_years'], item['count'],
                _money(item['amount']),
            ])
        elements.append(table(
            control_rows,
            widths=[5.5 * cm, 3.5 * cm, 4 * cm, 5 * cm, 3 * cm, 5 * cm],
            numeric_from=4,
        ))
        elements.append(Paragraph(
            "Ces élèves ont des paiements validés tombant dans la période de leur "
            "échéancier mais étiquetés sur une autre année scolaire : leur solde est "
            "surévalué tant que l'année n'est pas corrigée.",
            styles['Note'],
        ))

    elements.extend([
        Spacer(1, 0.35 * cm),
        Paragraph(
            (
                "Méthode : la situation historique est reconstruite à partir des seuls "
                "paiements et remises validés jusqu'à la date d'arrêt."
                if data['historical_cutoff']
                else "Méthode : la situation courante rapproche les paiements validés, "
                     "les remises imputées et les cumuls de l'échéancier. Une échéance "
                     "n'est exigible qu'à partir du lendemain de sa date."
            ),
            styles['Note'],
        ),
        Spacer(1, 0.15 * cm),
        Paragraph(
            "Plan d'action recommandé : traiter d'abord les retards les plus anciens et "
            "les montants les plus élevés, puis prévenir les échéances attendues dans "
            "les 30 prochains jours.",
            styles['Note'],
        ),
        Spacer(1, 0.35 * cm),
        _signature_block(table, [
            ('Responsable recouvrement', data['generated_by']),
            ('Comptabilité', 'Nom / Date / Signature'),
            ('Direction', 'Visa / Date / Signature'),
        ]),
    ])
    return _build(doc, buffer, elements, data, title, on_page)


# ---------------------------------------------------------------------------
# Rendu Excel
# ---------------------------------------------------------------------------

def _excel_workbook(data, report_kind):
    import openpyxl
    from openpyxl.drawing.image import Image as ExcelImage
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    dark_fill = PatternFill('solid', fgColor=BLUE.replace('#', ''))
    light_fill = PatternFill('solid', fgColor=BLUE_LIGHT.replace('#', ''))
    white_font = Font(color='FFFFFF', bold=True)
    bold_font = Font(bold=True)
    side = Side(style='thin', color='B7C4CC')
    border = Border(left=side, right=side, top=side, bottom=side)
    logo_path = _get_logo_path(data.get('school')) if data.get('school') else ''

    def sheet(name, title, headers):
        ws = wb.create_sheet(name[:31])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        cell = ws.cell(1, 1, f"{data['school_name']} — {title}")
        cell.font = Font(bold=True, size=14, color=BLUE.replace('#', ''))
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
        ws.cell(
            2, 1,
            f"{data['scope_label']} | Année {data.get('school_year') or '-'} | "
            f"{data.get('period_label', '')}",
        ).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=len(headers))
        ws.cell(
            3, 1,
            f"Réf. {data['reference']} | Généré par {data['generated_by']} le "
            f"{data['generated_at'].strftime('%d/%m/%Y à %H:%M')} | "
            f"Situation au {data['cutoff'].strftime('%d/%m/%Y')}",
        ).alignment = Alignment(horizontal='center')
        ws.row_dimensions[1].height = 34
        ws.row_dimensions[2].height = 30
        ws.row_dimensions[3].height = 22
        if logo_path:
            try:
                logo = ExcelImage(logo_path)
                ratio = (logo.width / logo.height) if logo.height else 1
                logo.height = 30
                logo.width = 30 * ratio
                ws.add_image(logo, 'A1')
            except Exception:
                pass
        for col, label in enumerate(headers, 1):
            item = ws.cell(5, col, label)
            item.fill = dark_fill
            item.font = white_font
            item.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            item.border = border
        ws.freeze_panes = 'A6'
        ws.auto_filter.ref = f"A5:{get_column_letter(len(headers))}5"
        return ws

    def append(ws, values, total=False):
        ws.append(values)
        row = ws.max_row
        for cell in ws[row]:
            cell.border = border
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            if total:
                cell.fill = light_fill
                cell.font = bold_font
            if isinstance(cell.value, int) and not isinstance(cell.value, bool) and cell.column > 1:
                cell.number_format = '#,##0'

    def local(value):
        return timezone.localtime(value).replace(tzinfo=None) if value else None

    if report_kind == 'accounting':
        ws = sheet('Synthèse', 'RAPPORT COMPTABLE DES ENCAISSEMENTS',
                   ['Indicateur', 'Nombre', 'Montant (GNF)'])
        append(ws, ['Opérations enregistrées', data['payment_count'], int(data['total_all_statuses'])])
        append(ws, ['Paiements validés', data['validated_count'], int(data['total_cash'])])
        append(ws, ['Montant facturé brut', data['validated_count'], int(data['total_gross'])])
        append(ws, ['Remises accordées', sum(i['count'] for i in data['by_reason'].values()),
                    int(data['total_discount'])])
        append(ws, ['dont déduites du reçu', None, int(data['total_deducted'])])
        append(ws, ['Couverture élèves (encaissé + remises)', data['validated_count'],
                    int(data['total_coverage'])], total=True)

        ws = sheet('Statuts', 'PAIEMENTS PAR STATUT', ['Statut', 'Nombre', 'Montant (GNF)'])
        for code, _label in Paiement.STATUT_CHOICES:
            item = data['by_status'][code]
            append(ws, [item['label'], item['count'], int(item['amount'])])
        append(ws, ['TOTAL', data['payment_count'], int(data['total_all_statuses'])], total=True)

        ws = sheet('Rapprochements', 'RAPPROCHEMENTS ANALYTIQUES',
                   ['Dimension', 'Libellé', 'Opérations', 'Encaissé (GNF)', 'Remises (GNF)'])
        for label, item in data['by_mode'].items():
            append(ws, ['Mode', label, item['count'], int(item['amount']), 0])
        for label, item in data['by_type'].items():
            append(ws, ['Type', label, item['count'], int(item['amount']), int(item['discount'])])
        for label, item in data['by_class'].items():
            append(ws, ['Classe', label, item['count'], int(item['amount']), int(item['discount'])])
        append(ws, ['TOTAL', '-', data['validated_count'], int(data['total_cash']),
                    int(data['total_discount'])], total=True)

        ws = sheet('Remises', 'REMISES ET RÉDUCTIONS',
                   ['Motif et portée', 'Lignes', 'Remise (GNF)', 'Dont déduite du reçu (GNF)'])
        for label, item in data['by_reason'].items():
            append(ws, [label, item['count'], int(item['amount']), int(item['deducted'])])
        append(ws, ['TOTAL', sum(i['count'] for i in data['by_reason'].values()),
                    int(data['total_discount']), int(data['total_deducted'])], total=True)

        ws = sheet('Journal validé', 'JOURNAL DES ENCAISSEMENTS VALIDÉS',
                   ['Date', 'Reçu', 'Matricule', 'Élève', 'Classe', 'Type', 'Mode',
                    'Brut (GNF)', 'Remise (GNF)', 'Encaissé (GNF)', 'Référence',
                    'Caissier', 'Validateur'])
        for item in data['payment_rows']:
            append(ws, [
                item['date'], item['receipt'], item['matricule'], item['student'],
                item['class'], item['type'], item['mode'], int(item['gross']),
                int(item['discount']), int(item['cash']), item['reference'],
                item['cashier'], item['validator'],
            ])
        append(ws, ['TOTAL', data['validated_count'], '', '', '', '', '',
                    int(data['total_gross']), int(data['total_discount']),
                    int(data['total_cash']), '', '', ''], total=True)
    else:
        ws = sheet('Synthèse', 'RAPPORT PROFESSIONNEL DE RECOUVREMENT',
                   ['Indicateur', 'Élèves', 'Montant (GNF)', 'Observation'])
        for label, count, amount, observation in [
            ('Créances brutes', data['schedule_count'], data['total_due'],
             'Échéanciers actifs suivis'),
            ('Encaissements cumulés', None, data['total_cash'], 'Paiements validés affectés'),
            ('Remises imputées', None, data['total_discount'], 'Réductions validées'),
            ('Solde à recouvrer', data['schedule_count'] - data['settled_count'],
             data['total_balance'], 'Après paiements et remises'),
            ('Élèves soldés', data['settled_count'], None, 'Aucun solde restant'),
            ('Dont soldés avec remise', data['settled_with_discount_count'], None,
             'Paiement + remise couvrent toute la scolarité'),
            ('Paiement partiel', data['partial_count'], None, 'Couverture incomplète'),
            ('Sans aucun règlement', data['unpaid_count'], None, 'Aucune couverture'),
            ('Élèves en retard', data['overdue_count'], data['total_overdue'],
             f"Situation au {data['cutoff'].strftime('%d/%m/%Y')}"),
            ('Échéances sous 30 jours', None, data['total_upcoming'], 'Prévention à organiser'),
            ('Encaissements sur la période', data['period_payment_count'],
             data['period_cash'], data['period_label']),
            ('Taux de recouvrement', None, None, f"{data['recovery_rate']:.1f} %"),
            ('Taux moyen de remise', None, None, f"{data['discount_rate']:.1f} %"),
        ]:
            append(ws, [label, count, int(amount) if amount is not None else None, observation])

        ws = sheet('Classes', 'PERFORMANCE PAR CLASSE',
                   ['Classe', 'Élèves', 'Dû', 'Encaissé', 'Remises', 'Remise (%)',
                    'Solde', 'Retard', 'À 30 jours', 'Relances', 'Recouvrement (%)'])
        for label, item in data['class_summary'].items():
            rate = ((item['cash'] + item['discount']) / item['due'] * 100) if item['due'] else ZERO
            append(ws, [
                label, item['students'], int(item['due']), int(item['cash']),
                int(item['discount']), float(round(_percentage(item['discount'], item['due']), 1)),
                int(item['balance']), int(item['overdue']), int(item['upcoming']),
                item['reminders'], float(round(rate, 1)),
            ])
        append(ws, [
            'TOTAL', data['schedule_count'], int(data['total_due']), int(data['total_cash']),
            int(data['total_discount']), float(round(data['discount_rate'], 1)),
            int(data['total_balance']), int(data['total_overdue']), int(data['total_upcoming']),
            sum(item['reminders'] for item in data['class_summary'].values()),
            float(round(data['recovery_rate'], 1)),
        ], total=True)

        ws = sheet('Postes', 'VENTILATION PAR POSTE',
                   ['Poste', 'Dû', 'Encaissé', 'Remises', 'Remise (%)', 'Reste',
                    'Dont exigible', 'Élèves concernés', 'Couverture (%)'])
        for bucket in BUCKETS:
            item = data['bucket_summary'][bucket]
            rate = ((item['cash'] + item['discount']) / item['due'] * 100) if item['due'] else ZERO
            append(ws, [
                BUCKET_LABELS[bucket], int(item['due']), int(item['cash']),
                int(item['discount']),
                float(round(_percentage(item['discount'], item['due']), 1)),
                int(item['balance']), int(item['overdue']), item['students'],
                float(round(rate, 1)),
            ])
        append(ws, [
            'TOTAL', int(data['total_due']), int(data['total_cash']),
            int(data['total_discount']), float(round(data['discount_rate'], 1)),
            int(data['total_balance']), int(data['total_overdue']), None,
            float(round(data['recovery_rate'], 1)),
        ], total=True)

        ws = sheet('Balance âgée', 'BALANCE ÂGÉE DES IMPAYÉS',
                   ['Ancienneté', 'Échéances', 'Montant (GNF)'])
        for label in AGING_BUCKETS:
            item = data['aging'][label]
            append(ws, [label, item['count'], int(item['amount'])])
        append(ws, ['TOTAL', sum(item['count'] for item in data['aging'].values()),
                    int(data['total_overdue'])], total=True)

        ws = sheet('Portefeuille élèves', 'PORTEFEUILLE DÉTAILLÉ DU RECOUVREMENT',
                   ['Matricule', 'Élève', 'Classe', 'Responsable', 'Téléphone', 'Dû',
                    'Encaissé', 'Remises', 'Remise (%)', 'Solde', 'Retard', 'À 30 jours',
                    'Situation', 'Précision remise', 'Relances', 'Dernière relance',
                    'Statut relance'])
        for item in data['student_rows']:
            append(ws, [
                item['matricule'], item['student'], item['class'], item['responsible'],
                item['phone'], int(item['due']), int(item['cash']), int(item['discount']),
                float(round(item['discount_rate'], 1)), int(item['balance']),
                int(item['overdue']), int(item['upcoming']), item['status'],
                item['precision'], item['reminder_count'], local(item['last_reminder']),
                item['last_status'],
            ])

        ws = sheet('Priorités', 'DOSSIERS PRIORITAIRES',
                   ['Matricule', 'Élève', 'Classe', 'Responsable', 'Téléphone', 'Dû',
                    'Encaissé', 'Remises', 'Remise (%)', 'Couvert', 'Solde', 'Retard',
                    'Jours', 'Relances', 'Dernière relance', 'Statut'])
        for item in data['priority_rows']:
            append(ws, [
                item['matricule'], item['student'], item['class'], item['responsible'],
                item['phone'], int(item['due']), int(item['cash']), int(item['discount']),
                float(round(item['discount_rate'], 1)), int(item['coverage']),
                int(item['balance']), int(item['overdue']), item['days'], item['reminder_count'],
                local(item['last_reminder']), item['last_status'],
            ])

        ws = sheet('Relances', 'PILOTAGE DES RELANCES',
                   ['Dimension', 'Libellé', 'Actions', 'Envoyées', 'Échecs', 'Taux succès (%)'])
        for label, item in data['reminder_by_channel'].items():
            success = item['sent'] / item['count'] * 100 if item['count'] else 0
            append(ws, ['Canal', label, item['count'], item['sent'], item['failed'],
                        float(round(success, 1))])
        for label, count in data['reminder_by_status'].items():
            append(ws, ['Statut', label, count, None, None, None])

        ws = sheet('Journal relances', 'JOURNAL DÉTAILLÉ DES RELANCES',
                   ['Date', 'Matricule', 'Élève', 'Classe', 'Canal', 'Statut',
                    'Solde estimé (GNF)', 'Message', 'Créé par'])
        for item in data['period_relances']:
            append(ws, [
                local(item.date_creation), item.eleve.matricule, item.eleve.nom_complet,
                item.eleve.classe.nom, item.get_canal_display(), item.get_statut_display(),
                int(item.solde_estime or 0), item.message, _display_user(item.cree_par),
            ])

        if data['inconsistent_rows']:
            ws = sheet('Contrôle qualité', 'SOLDES NON FIABLES À CORRIGER',
                       ['Matricule', 'Élève', 'Classe', "Année de l'échéancier",
                        'Année des paiements écartés', 'Paiements', 'Montant écarté (GNF)'])
            for item in data['inconsistent_rows']:
                append(ws, [
                    item['matricule'], item['student'], item['class'],
                    item['schedule_year'], item['payment_years'], item['count'],
                    int(item['amount']),
                ])

    for ws in wb.worksheets:
        for column in ws.columns:
            letter = get_column_letter(column[0].column)
            max_len = max((len(str(cell.value or '')) for cell in column), default=12)
            ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 34)
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = '1:5'
    return wb


# ---------------------------------------------------------------------------
# Vues
# ---------------------------------------------------------------------------

def _bad_request(exc):
    return HttpResponse(str(exc), status=400, content_type='text/plain; charset=utf-8')


def _filename_suffix(data):
    if len(data['classes']) == 1:
        return _safe_filename(data['classes'][0].nom)
    return 'etablissement'


def _pdf_response(buffer, prefix, data):
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{prefix}_{_filename_suffix(data)}_{date.today().isoformat()}.pdf"'
    )
    return response


def _excel_response(workbook, prefix, data):
    buffer = io.BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{prefix}_{_filename_suffix(data)}_{date.today().isoformat()}.xlsx"'
    )
    return response


@can_view_reports
def export_comptabilite_pdf(request):
    try:
        data = collect_accounting_data(request)
    except ValueError as exc:
        return _bad_request(exc)
    return _pdf_response(build_accounting_pdf(data), 'rapport_comptable', data)


@can_view_reports
def export_comptabilite_excel(request):
    try:
        data = collect_accounting_data(request)
    except ValueError as exc:
        return _bad_request(exc)
    return _excel_response(_excel_workbook(data, 'accounting'), 'rapport_comptable', data)


@can_view_reports
def export_recouvrement_pdf(request):
    try:
        data = collect_recovery_data(request)
    except ValueError as exc:
        return _bad_request(exc)
    return _pdf_response(build_recovery_pdf(data), 'rapport_recouvrement', data)


@can_view_reports
def export_recouvrement_excel(request):
    try:
        data = collect_recovery_data(request)
    except ValueError as exc:
        return _bad_request(exc)
    return _excel_response(_excel_workbook(data, 'recovery'), 'rapport_recouvrement', data)
