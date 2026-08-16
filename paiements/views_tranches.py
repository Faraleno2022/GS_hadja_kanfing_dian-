from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal

from eleves.models import Classe, Ecole
from eleves.utils_annee import get_annee_active
from paiements.models import EcheancierPaiement, Paiement, PaiementRemise
from paiements.allocation import registration_kind_for_type
from utilisateurs.utils import user_is_admin, user_school
from rapports.utils import _draw_header_and_watermark

# ReportLab
# ReportLab: fera l'objet d'un import différé dans la vue PDF


def _pourcentage_remise(remise, total_du):
    remise = Decimal(str(remise or 0))
    total_du = Decimal(str(total_du or 0))
    return remise / total_du * Decimal('100') if total_du > 0 else Decimal('0')


def _precision_remise(remise, total_du, reste, total_paye):
    if total_du <= 0:
        return 'Remise appliquée - total dû indisponible' if remise > 0 else 'Total dû indisponible'
    if reste <= 0:
        return 'Soldé - remise appliquée au paiement' if remise > 0 else 'Soldé'
    if remise > 0:
        return 'Remise appliquée - solde restant'
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

    discounts = PaiementRemise.objects.filter(
        paiement__eleve_id__in=student_ids,
        paiement__statut='VALIDE',
    )
    if effective_year:
        discounts = discounts.filter(paiement__annee_scolaire=effective_year)
    discounts_by_student = {
        item['paiement__eleve_id']: item['total'] or Decimal('0')
        for item in discounts.values('paiement__eleve_id').annotate(total=Sum('montant_remise'))
    }

    rows = []
    for eleve in eleves:
        schedule = schedules_by_student.get(eleve.pk)
        insc = reinsc = t1 = t2 = t3 = Decimal('0')
        total_du = total_paye = Decimal('0')

        if schedule is not None:
            admission_payee = schedule.frais_inscription_paye or Decimal('0')
            if schedule.est_reinscription:
                reinsc = admission_payee
            else:
                insc = admission_payee
            t1 = schedule.tranche_1_payee or Decimal('0')
            t2 = schedule.tranche_2_payee or Decimal('0')
            t3 = schedule.tranche_3_payee or Decimal('0')
            total_du = schedule.total_du or Decimal('0')
            total_paye = schedule.total_paye or Decimal('0')
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

        remise = max(Decimal('0'), Decimal(str(discounts_by_student.get(eleve.pk, 0))))
        reste = max(Decimal('0'), total_du - total_paye - remise) if total_du > 0 else Decimal('0')
        taux_remise = _pourcentage_remise(remise, total_du)
        precision = _precision_remise(remise, total_du, reste, total_paye)
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
            'discount_rate': taux_remise,
            'balance': reste,
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
    # Contrôle d'accès: Admin ou Comptable uniquement
    is_admin = user_is_admin(request.user)
    is_comptable = False
    try:
        if hasattr(request.user, 'profil'):
            is_comptable = (getattr(request.user.profil, 'role', None) == 'COMPTABLE')
    except Exception:
        is_comptable = False
    if not (is_admin or is_comptable):
        return HttpResponseForbidden("Accès refusé: vous n'avez pas l'autorisation d'exporter ce rapport.")

    # Lecture et validation des paramètres
    raw_ecole = (request.GET.get('ecole') or '').strip()
    raw_classe = (request.GET.get('classe') or request.GET.get('classe_id') or '').strip()
    annee_scolaire = (request.GET.get('annee_scolaire') or '').strip()

    def parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    ecole_id = parse_int(raw_ecole) if raw_ecole else None
    classe_id = parse_int(raw_classe) if raw_classe else None

    # Scope classes (filtrées par année active)
    classes = Classe.objects.select_related('ecole').all()
    ecole_user = user_school(request.user)
    annee_active = get_annee_active(request, ecole_user) if ecole_user else None
    restreindre = not user_is_admin(request.user) and ecole_user is not None
    if restreindre:
        classes = classes.filter(ecole=ecole_user)
    elif ecole_id:
        classes = classes.filter(ecole_id=ecole_id)
    if classe_id:
        classes = classes.filter(id=classe_id)
    if annee_active and not annee_scolaire:
        classes = classes.filter(annee_scolaire=annee_active)
    elif annee_scolaire:
        classes = classes.filter(annee_scolaire=annee_scolaire)

    # Anti-abus: limiter le nombre de classes exportées en une requête
    classes = list(classes.order_by('ecole__nom', 'niveau', 'nom')[:200])
    school_ids = {classe.ecole_id for classe in classes if classe.ecole_id}
    if len(school_ids) == 1:
        ecole_pdf = classes[0].ecole
    elif ecole_user:
        ecole_pdf = ecole_user
    elif ecole_id:
        ecole_pdf = Ecole.objects.filter(pk=ecole_id).first()
    else:
        ecole_pdf = None

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
        "Le reste est calculé après déduction des paiements validés et des remises. "
        "Le taux de remise est rapporté au total dû.",
        cell,
    ))
    elements.append(Spacer(1, 0.5*cm))

    header_labels = [
        'Élève', 'Inscription payée', 'Réinscription payée',
        'Tranche 1 payée', 'Tranche 2 payée', 'Tranche 3 payée',
        'Total dû', 'Total payé', 'Remise', 'Remise (%)', 'Reste',
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

        for row in _tranche_export_rows(classe, annee_scolaire):
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
                f"{row['discount_rate']:.1f} %",
                f"{row['balance']:,}".replace(',', ' '),
                P(row['precision']),
            ])

        # Construire la table pour la classe
        col_widths = [3.7*cm] + [1.8*cm] * 5 + [2.2*cm, 2.2*cm, 2.2*cm, 1.7*cm, 2.2*cm, 4.5*cm]
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
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
        ]))
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
    # Contrôle d'accès
    is_admin = user_is_admin(request.user)
    is_comptable = False
    try:
        if hasattr(request.user, 'profil'):
            is_comptable = (getattr(request.user.profil, 'role', None) == 'COMPTABLE')
    except Exception:
        is_comptable = False
    if not (is_admin or is_comptable):
        return HttpResponseForbidden("Accès refusé: vous n'avez pas l'autorisation d'exporter ce rapport.")

    # Import openpyxl
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except Exception:
        return HttpResponse("OpenPyXL n'est pas installé. Veuillez exécuter: pip install openpyxl", status=500)

    raw_ecole = (request.GET.get('ecole') or '').strip()
    raw_classe = (request.GET.get('classe') or request.GET.get('classe_id') or '').strip()
    annee_scolaire = (request.GET.get('annee_scolaire') or '').strip()

    def parse_int(value):
        try:
            return int(value)
        except Exception:
            return None

    ecole_id = parse_int(raw_ecole) if raw_ecole else None
    classe_id = parse_int(raw_classe) if raw_classe else None

    classes = Classe.objects.select_related('ecole').all()
    ecole_user = user_school(request.user)
    annee_active_xl = get_annee_active(request, ecole_user) if ecole_user else None
    restreindre = not user_is_admin(request.user) and ecole_user is not None
    if restreindre:
        classes = classes.filter(ecole=ecole_user)
    elif ecole_id:
        classes = classes.filter(ecole_id=ecole_id)
    if classe_id:
        classes = classes.filter(id=classe_id)
    if annee_active_xl and not annee_scolaire:
        classes = classes.filter(annee_scolaire=annee_active_xl)
    elif annee_scolaire:
        classes = classes.filter(annee_scolaire=annee_scolaire)
    classes = classes.order_by('ecole__nom', 'niveau', 'nom')[:200]

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
        'Total dû', 'Total payé', 'Remise', 'Remise (%)', 'Reste',
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

        for row in _tranche_export_rows(classe, annee_scolaire):
            ws.append([
                row['student'], int(row['inscription']), int(row['reinscription']),
                int(row['tranche_1']), int(row['tranche_2']), int(row['tranche_3']),
                int(row['total_due']), int(row['total_paid']), int(row['discount']),
                float(round(row['discount_rate'], 1)), int(row['balance']),
                row['precision'],
            ])

        for row_cells in ws.iter_rows(min_row=3, min_col=2, max_col=11):
            for item in row_cells:
                item.number_format = '0.0' if item.column == 10 else '#,##0'
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
        ws.auto_filter.ref = f"A2:{get_column_letter(len(headers))}{max(ws.max_row, 2)}"
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
