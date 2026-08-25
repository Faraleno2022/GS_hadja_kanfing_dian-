from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal

from eleves.models import Classe, Ecole
from eleves.utils_annee import get_annee_active
from paiements.models import EcheancierPaiement, Paiement, PaiementRemise
from paiements.allocation import (
    ALLOCATION_COMPONENTS,
    allocate_amount_sequentially,
    registration_kind_for_type,
)
from utilisateurs.utils import user_is_admin, user_is_superadmin, user_school
from rapports.utils import _draw_header_and_watermark

# ReportLab
# ReportLab: fera l'objet d'un import différé dans la vue PDF


def _format_taux_remise(taux):
    """Affiche le taux enregistré sans le recalculer depuis le montant dû."""
    taux = Decimal(str(taux or 0)).quantize(Decimal('0.01'))
    return format(taux.normalize(), 'f')


# Roles qui gerent ou supervisent la scolarite: ils ouvrent l'export depuis la
# page /paiements/ a laquelle ils ont deja acces.
ROLES_EXPORT = {'ADMIN', 'DIRECTEUR', 'COMPTABLE', 'SECRETAIRE'}


def _peut_exporter(user):
    """Qui peut sortir le rapport "Tranches par classe".

    Le rapport ne contient rien de plus que ce que la page /paiements/ affiche
    deja: le reserver aux seuls ADMIN/COMPTABLE renvoyait "Acces refuse" aux
    directions et aux secretariats qui l'ouvrent pourtant depuis cette page.
    Restent exclus les profils sans lien avec la gestion financiere tant qu'ils
    n'ont pas la permission "rapports".
    """
    if not getattr(user, 'is_authenticated', False):
        return False
    if user_is_admin(user):
        return True
    profil = getattr(user, 'profil', None)
    if profil is None:
        return False
    if getattr(profil, 'role', None) in ROLES_EXPORT:
        return True
    return bool(
        getattr(profil, 'peut_consulter_rapports', False)
        or getattr(profil, 'peut_generer_rapports', False)
    )


def _perimetre_export(request):
    """Classes retenues, annee appliquee et ecole de l'entete.

    Partage par les deux formats pour qu'un meme filtre donne exactement le
    meme contenu en PDF et en Excel.
    """
    raw_ecole = (request.GET.get('ecole') or '').strip()
    raw_classe = (request.GET.get('classe') or request.GET.get('classe_id') or '').strip()
    # La page /paiements/ envoie "annee"; les anciens liens "annee_scolaire".
    annee_scolaire = (
        request.GET.get('annee_scolaire') or request.GET.get('annee') or ''
    ).strip()

    def parse_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    ecole_id = parse_int(raw_ecole) if raw_ecole else None
    classe_id = parse_int(raw_classe) if raw_classe else None

    ecole_user = user_school(request.user)
    annee_active = get_annee_active(request, ecole_user) if ecole_user else None

    classes = Classe.objects.select_related('ecole').all()
    # Meme separation que filter_by_user_school: seul le superutilisateur voit
    # plusieurs ecoles, et un compte sans ecole rattachee n'exporte rien plutot
    # que la totalite des etablissements.
    if not user_is_superadmin(request.user):
        if ecole_user is None:
            return [], annee_scolaire, None
        classes = classes.filter(ecole=ecole_user)
    elif ecole_id:
        classes = classes.filter(ecole_id=ecole_id)
    if classe_id:
        classes = classes.filter(id=classe_id)
    if annee_scolaire:
        classes = classes.filter(annee_scolaire=annee_scolaire)
    elif annee_active:
        classes = classes.filter(annee_scolaire=annee_active)

    # Anti-abus: limiter le nombre de classes exportees en une requete
    classes = list(classes.order_by('ecole__nom', 'niveau', 'nom')[:200])

    school_ids = {classe.ecole_id for classe in classes if classe.ecole_id}
    if len(school_ids) == 1:
        ecole_entete = classes[0].ecole
    elif ecole_user:
        ecole_entete = ecole_user
    elif ecole_id:
        ecole_entete = Ecole.objects.filter(pk=ecole_id).first()
    else:
        ecole_entete = None
    return classes, annee_scolaire, ecole_entete


def _taux_couverture(total_du, total_paye, remise):
    """Part du du reellement couverte par les encaissements et les remises."""
    if total_du <= 0:
        return Decimal('0')
    couverture = (total_paye + remise) / total_du * Decimal('100')
    return min(Decimal('100'), couverture)


def _totaux_export(rows):
    """Cumuls d'une classe, avec son taux de couverture global."""
    cles = ('inscription', 'reinscription', 'tranche_1', 'tranche_2', 'tranche_3',
            'total_due', 'total_paid', 'discount', 'balance')
    totaux = {cle: sum((row[cle] for row in rows), Decimal('0')) for cle in cles}
    totaux['coverage_rate'] = _taux_couverture(
        totaux['total_due'], totaux['total_paid'], totaux['discount']
    )
    return totaux


def _precision_remise(total_du, reste, total_paye):
    if total_du <= 0:
        return 'Total dû indisponible'
    if reste <= 0:
        return 'Soldé'
    return 'Paiement partiel' if total_paye > 0 else 'À payer'


def _tranche_export_rows(classe, annee_scolaire):
    """Construit une ligne cohérente par élève pour les exports PDF et Excel."""
    eleves_mgr = getattr(classe, 'eleves', None)
    eleves = list(
        eleves_mgr.all().order_by('nom', 'prenom')
        if eleves_mgr is not None else []
    )
    if not eleves:
        return []

    effective_year = annee_scolaire or getattr(classe, 'annee_scolaire', '')
    student_ids = [eleve.pk for eleve in eleves]
    schedules = EcheancierPaiement.objects.filter(eleve_id__in=student_ids)
    if effective_year:
        schedules = schedules.filter(annee_scolaire=effective_year)
    schedules_by_student = {item.eleve_id: item for item in schedules}

    # Les anciens echeanciers peuvent contenir une remise reportee dans le
    # champ *_payee de la tranche suivante. Les colonnes d'encaissement des
    # exports doivent etre reconstruites depuis le cash valide, sur les montants
    # bruts dus, afin qu'une remise ne soit jamais presentee comme un paiement.
    validated_cash = Paiement.objects.filter(
        eleve_id__in=student_ids,
        statut='VALIDE',
    )
    if effective_year:
        validated_cash = validated_cash.filter(annee_scolaire=effective_year)
    validated_cash_by_student = {
        item['eleve_id']: Decimal(str(item['total'] or 0))
        for item in validated_cash.values('eleve_id').annotate(total=Sum('montant'))
    }

    discounts = PaiementRemise.objects.filter(
        paiement__eleve_id__in=student_ids,
        paiement__statut='VALIDE',
    )
    if effective_year:
        discounts = discounts.filter(paiement__annee_scolaire=effective_year)
    discounts_by_student = {}
    for item in discounts.select_related('paiement', 'remise').order_by('pk'):
        detail = discounts_by_student.setdefault(
            item.paiement.eleve_id,
            {'amount': Decimal('0'), 'rates': []},
        )
        detail['amount'] += Decimal(str(item.montant_remise or 0))
        if item.remise.type_remise == 'POURCENTAGE':
            taux = Decimal(str(item.remise.valeur or 0))
            if taux not in detail['rates']:
                detail['rates'].append(taux)

    rows = []
    for eleve in eleves:
        schedule = schedules_by_student.get(eleve.pk)
        insc = reinsc = t1 = t2 = t3 = Decimal('0')
        total_du = total_paye = Decimal('0')

        if schedule is not None:
            validated_total = validated_cash_by_student.get(eleve.pk)
            if validated_total is None:
                # Sans objet Paiement, ces champs peuvent provenir d'un import
                # ou d'une reprise manuelle: leur ventilation reste la source.
                admission_payee = Decimal(str(schedule.frais_inscription_paye or 0))
                t1 = Decimal(str(schedule.tranche_1_payee or 0))
                t2 = Decimal(str(schedule.tranche_2_payee or 0))
                t3 = Decimal(str(schedule.tranche_3_payee or 0))
            else:
                recorded_cash = sum(
                    (
                        Decimal(str(getattr(schedule, paid_field, 0) or 0))
                        for _key, _due_field, paid_field in ALLOCATION_COMPONENTS
                    ),
                    Decimal('0'),
                )
                cash_to_allocate = max(recorded_cash, validated_total)
                _cash_allocation, cash_paid, _unapplied = allocate_amount_sequentially(
                    schedule,
                    cash_to_allocate,
                    initial_paid={
                        key: Decimal('0')
                        for key, _due_field, _paid_field in ALLOCATION_COMPONENTS
                    },
                )
                admission_payee = cash_paid['inscription']
                t1 = cash_paid['tranche_1']
                t2 = cash_paid['tranche_2']
                t3 = cash_paid['tranche_3']
            if schedule.est_reinscription:
                reinsc = admission_payee
            else:
                insc = admission_payee
            total_du = schedule.total_du or Decimal('0')
            total_paye = admission_payee + t1 + t2 + t3
        else:
            paiements = Paiement.objects.filter(eleve=eleve, statut='VALIDE')
            if effective_year:
                paiements = paiements.filter(annee_scolaire=effective_year)
            for paiement in paiements.select_related('type_paiement'):
                nature = registration_kind_for_type(paiement.type_paiement)
                if nature == 'reinscription':
                    reinsc += paiement.montant or Decimal('0')
                elif nature == 'inscription':
                    insc += paiement.montant or Decimal('0')
            t1 = paiements.filter(type_paiement__nom__icontains='tranche 1').aggregate(total=Sum('montant'))['total'] or Decimal('0')
            t2 = paiements.filter(type_paiement__nom__icontains='tranche 2').aggregate(total=Sum('montant'))['total'] or Decimal('0')
            t3 = paiements.filter(type_paiement__nom__icontains='tranche 3').aggregate(total=Sum('montant'))['total'] or Decimal('0')
            total_paye = insc + reinsc + t1 + t2 + t3

        discount_detail = discounts_by_student.get(
            eleve.pk, {'amount': Decimal('0'), 'rates': []}
        )
        remise = max(Decimal('0'), discount_detail['amount'])
        reste = max(Decimal('0'), total_du - total_paye - remise) if total_du > 0 else Decimal('0')
        precision = _precision_remise(total_du, reste, total_paye)
        rows.append({
            'student': getattr(eleve, 'nom_complet', f"{eleve.prenom} {eleve.nom}"),
            'inscription': insc,
            'reinscription': reinsc,
            'tranche_1': t1,
            'tranche_2': t2,
            'tranche_3': t3,
            'total_due': total_du,
            'total_paid': total_paye,
            'discount': remise,
            'discount_rates': tuple(discount_detail['rates']),
            'balance': reste,
            'coverage_rate': _taux_couverture(total_du, total_paye, remise),
            'precision': precision,
        })
    return rows


@login_required
def export_tranches_par_classe_pdf(request):
    """Export PDF des tranches par classe avec logo entête et filigrane.

    Filtres GET:
    - ecole: id de l'école
    - classe: id de la classe
    - annee_scolaire: ex '2024-2025'

    Respecte la séparation par école pour les non-admins.
    """
    if not _peut_exporter(request.user):
        return HttpResponseForbidden(
            "Accès refusé: vous n'avez pas l'autorisation d'exporter ce rapport."
        )

    classes, annee_scolaire, ecole_pdf = _perimetre_export(request)

    # Préparer réponse PDF
    response = HttpResponse(content_type='application/pdf')
    suffix = datetime.now().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="tranches_par_classe_{suffix}.pdf"'

    # Import différé de ReportLab pour éviter les erreurs si non installé
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except Exception:
        return HttpResponse("ReportLab n'est pas installé. Veuillez exécuter: pip install reportlab", status=500)

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=80, bottomMargin=30
    )
    elements = []
    styles = getSampleStyleSheet()
    cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=9)
    header_cell = ParagraphStyle(
        'HeaderCell', parent=cell, fontName='Helvetica-Bold', fontSize=7, leading=8,
    )

    titre = 'Tranches par classe'
    if annee_scolaire:
        titre += f" – Année {annee_scolaire}"
    elements.append(Paragraph(titre, styles['Title']))
    elements.append(Paragraph(
        "Les colonnes de paiement contiennent uniquement les montants encaissés. "
        "La remise et le taux choisi dans le système sont affichés séparément.",
        cell,
    ))
    elements.append(Spacer(1, 0.5*cm))

    header_labels = [
        'Élève', 'Inscription payée', 'Réinscription payée',
        'Tranche 1 payée', 'Tranche 2 payée', 'Tranche 3 payée',
        'Total dû', 'Total payé', 'Remise', 'Remise (%)', 'Reste', '% payé',
        'Situation / précision',
    ]
    header = [Paragraph(label, header_cell) for label in header_labels]

    def P(x):
        return Paragraph(str(x or ''), cell)

    # Parcours des classes
    for classe in classes:
        # Titre de la classe
        titre_classe = f"Classe: {classe.nom} – {getattr(classe.ecole, 'nom', '')}"
        elements.append(Paragraph(titre_classe, styles['Heading2']))
        elements.append(Spacer(1, 0.2*cm))

        data = [header]

        rows = _tranche_export_rows(classe, annee_scolaire)
        for row in rows:
            taux_remise = ' / '.join(
                f"{_format_taux_remise(taux)} %"
                for taux in row['discount_rates']
            )
            data.append([
                P(row['student']),
                f"{row['inscription']:,}".replace(',', ' '),
                f"{row['reinscription']:,}".replace(',', ' '),
                f"{row['tranche_1']:,}".replace(',', ' '),
                f"{row['tranche_2']:,}".replace(',', ' '),
                f"{row['tranche_3']:,}".replace(',', ' '),
                f"{row['total_due']:,}".replace(',', ' '),
                f"{row['total_paid']:,}".replace(',', ' '),
                f"{row['discount']:,}".replace(',', ' '),
                taux_remise,
                f"{row['balance']:,}".replace(',', ' '),
                f"{_format_taux_remise(row['coverage_rate'])} %",
                P(row['precision']),
            ])

        ligne_totaux = None
        if rows:
            totaux = _totaux_export(rows)
            ligne_totaux = len(data)
            data.append([
                P('TOTAL CLASSE'),
                f"{totaux['inscription']:,}".replace(',', ' '),
                f"{totaux['reinscription']:,}".replace(',', ' '),
                f"{totaux['tranche_1']:,}".replace(',', ' '),
                f"{totaux['tranche_2']:,}".replace(',', ' '),
                f"{totaux['tranche_3']:,}".replace(',', ' '),
                f"{totaux['total_due']:,}".replace(',', ' '),
                f"{totaux['total_paid']:,}".replace(',', ' '),
                f"{totaux['discount']:,}".replace(',', ' '),
                '',
                f"{totaux['balance']:,}".replace(',', ' '),
                f"{_format_taux_remise(totaux['coverage_rate'])} %",
                P(''),
            ])

        # Construire la table pour la classe
        col_widths = ([3.7*cm] + [1.8*cm] * 5
                      + [2.2*cm, 2.2*cm, 2.2*cm, 1.7*cm, 2.2*cm, 1.5*cm, 3.5*cm])
        table = Table(data, repeatRows=1, colWidths=col_widths)
        styles_table = [
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 7),
            ('FONTSIZE', (0,1), (-1,-1), 6.5),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]
        if ligne_totaux is not None:
            styles_table += [
                ('BACKGROUND', (0, ligne_totaux), (-1, ligne_totaux), colors.whitesmoke),
                ('FONTNAME', (1, ligne_totaux), (-1, ligne_totaux), 'Helvetica-Bold'),
            ]
        table.setStyle(TableStyle(styles_table))
        elements.append(table)
        elements.append(Spacer(1, 0.6*cm))

    # Construire le document avec le logo de l'école filtrée. La fermeture
    # transmet explicitement l'école au callback ReportLab sur chaque page.
    def dessiner_entete(canvas, document):
        _draw_header_and_watermark(
            canvas,
            document,
            ecole=ecole_pdf,
            titre_override='Tranches par classe',
        )

    doc.build(
        elements,
        onFirstPage=dessiner_entete,
        onLaterPages=dessiner_entete,
    )
    return response

@login_required
def export_tranches_par_classe_excel(request):
    """Export Excel (XLSX) des tranches par classe avec inscription et réinscription séparées.

    Filtres GET facultatifs: ecole, classe/classe_id, annee_scolaire.
    Respecte la séparation par école pour non-admin.
    """
    if not _peut_exporter(request.user):
        return HttpResponseForbidden(
            "Accès refusé: vous n'avez pas l'autorisation d'exporter ce rapport."
        )

    # Import openpyxl
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except Exception:
        return HttpResponse("OpenPyXL n'est pas installé. Veuillez exécuter: pip install openpyxl", status=500)

    classes, annee_scolaire, _ecole_entete = _perimetre_export(request)

    wb = Workbook()
    ws_index = wb.active
    ws_index.title = 'Index'
    index_title = 'Tranches par classe'
    if annee_scolaire:
        index_title += f" - Année {annee_scolaire}"
    ws_index.append([index_title])
    ws_index.merge_cells('A1:C1')
    ws_index.cell(1, 1).font = Font(bold=True, size=14, color='174A6E')
    ws_index.cell(1, 1).alignment = Alignment(horizontal='center')
    ws_index.append(['École', 'Classe', 'Feuille'])
    for cell_header in ws_index[2]:
        cell_header.fill = PatternFill('solid', fgColor='174A6E')
        cell_header.font = Font(bold=True, color='FFFFFF')
        cell_header.alignment = Alignment(horizontal='center')
    ws_index.column_dimensions['A'].width = 36
    ws_index.column_dimensions['B'].width = 24
    ws_index.column_dimensions['C'].width = 24
    ws_index.freeze_panes = 'A3'
    ws_index.sheet_view.showGridLines = False

    headers = [
        'Élève', 'Inscription payée', 'Réinscription payée',
        'Tranche 1 payée', 'Tranche 2 payée', 'Tranche 3 payée',
        'Total dû', 'Total payé', 'Remise', 'Remise (%)', 'Reste', '% payé',
        'Situation / précision',
    ]

    for idx, classe in enumerate(classes, start=1):
        sheet_name = f"{classe.nom[:25]}"  # Limite Excel <=31
        ws = wb.create_sheet(title=sheet_name)
        ws.append([f"Classe: {classe.nom} – {getattr(classe.ecole, 'nom', '')}"])
        ws.append(headers)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        ws.cell(1, 1).font = Font(bold=True, size=13, color='174A6E')
        ws.cell(1, 1).alignment = Alignment(horizontal='center')
        for cell_header in ws[2]:
            cell_header.fill = PatternFill('solid', fgColor='174A6E')
            cell_header.font = Font(bold=True, color='FFFFFF')
            cell_header.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        rows = _tranche_export_rows(classe, annee_scolaire)
        for row in rows:
            if len(row['discount_rates']) == 1:
                taux_remise = float(row['discount_rates'][0])
            elif row['discount_rates']:
                taux_remise = ' / '.join(
                    f"{_format_taux_remise(taux)} %"
                    for taux in row['discount_rates']
                )
            else:
                taux_remise = None
            ws.append([
                row['student'], int(row['inscription']), int(row['reinscription']),
                int(row['tranche_1']), int(row['tranche_2']), int(row['tranche_3']),
                int(row['total_due']), int(row['total_paid']), int(row['discount']),
                taux_remise, int(row['balance']),
                float(round(row['coverage_rate'], 2)),
                row['precision'],
            ])

        # La ligne de total reste hors du filtre automatique pour ne jamais
        # etre masquee par un tri ou un filtre pose sur les eleves.
        derniere_ligne_donnees = max(ws.max_row, 2)
        if rows:
            totaux = _totaux_export(rows)
            ws.append([
                'TOTAL CLASSE',
                int(totaux['inscription']), int(totaux['reinscription']),
                int(totaux['tranche_1']), int(totaux['tranche_2']), int(totaux['tranche_3']),
                int(totaux['total_due']), int(totaux['total_paid']), int(totaux['discount']),
                None, int(totaux['balance']),
                float(round(totaux['coverage_rate'], 2)),
                '',
            ])
            for cellule in ws[ws.max_row]:
                cellule.font = Font(bold=True)

        for row_cells in ws.iter_rows(min_row=3, min_col=2, max_col=12):
            for item in row_cells:
                item.number_format = '0.##' if item.column in (10, 12) else '#,##0'
        for row_cells in ws.iter_rows(min_row=3, max_col=len(headers)):
            for item in row_cells:
                item.alignment = Alignment(vertical='top', wrap_text=True)
                item.border = Border(bottom=Side(style='thin', color='D6E0E6'))
        for col in range(1, len(headers) + 1):
            if col == 1:
                width = 24
            elif col == len(headers):
                width = 34
            else:
                width = 16
            ws.column_dimensions[get_column_letter(col)].width = width
        ws.freeze_panes = 'A3'
        ws.auto_filter.ref = f"A2:{get_column_letter(len(headers))}{derniere_ligne_donnees}"
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True

        # Index line
        ws_index.append([getattr(classe.ecole, 'nom', ''), classe.nom, sheet_name])
        ws_index.cell(ws_index.max_row, 3).hyperlink = f"#'{sheet_name}'!A1"
        ws_index.cell(ws_index.max_row, 3).style = 'Hyperlink'

    # Supprimer la feuille par défaut si vide
    if ws_index.max_row == 2:
        ws_index.append(['Aucune classe'])

    from io import BytesIO
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    resp = HttpResponse(stream.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    suffix = datetime.now().strftime('%Y%m%d')
    filename = f'tranches_par_classe_{suffix}.xlsx'
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp
