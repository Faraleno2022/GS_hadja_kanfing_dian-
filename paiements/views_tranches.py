"""Exports « Tranches par classe » (PDF et Excel).

Une seule source de vérité pour les deux formats: ``_lignes_tranches``
construit les lignes élève par élève, avec les remises réellement accordées et
le pourcentage effectivement choisi par l'utilisateur au moment de la remise.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal

from eleves.models import Classe
from eleves.utils_annee import get_annee_active
from paiements.models import EcheancierPaiement, Paiement, PaiementRemise
from paiements.allocation import registration_kind_for_type
from utilisateurs.utils import user_is_admin, user_is_superadmin, user_school
from rapports.utils import _draw_header_and_watermark

# ReportLab / OpenPyXL: import différé dans chaque vue

ZERO = Decimal('0')

# Rôles qui gèrent ou supervisent la scolarité: ils ouvrent l'export depuis la
# page /paiements/ à laquelle ils ont déjà accès.
ROLES_EXPORT = {'ADMIN', 'DIRECTEUR', 'COMPTABLE', 'SECRETAIRE'}

# En-têtes partagés par le PDF et l'Excel: chaque pourcentage a sa propre
# colonne, jamais mélangé avec un montant.
ENTETES = [
    'Élève', 'Inscription payée', 'Réinscription payée',
    'Tranche 1 payée', 'Tranche 2 payée', 'Tranche 3 payée',
    'Total dû', 'Total payé', 'Remise (GNF)', 'Remise (%)',
    'Reste', '% payé',
]


def _fmt_gnf(valeur):
    try:
        return f"{int(valeur or 0):,}".replace(',', ' ')
    except (TypeError, ValueError):
        return '0'


def _fmt_pct(valeur):
    """2 décimales au plus, sans zéro inutile: 12.50 -> « 12,5 % », 50 -> « 50 % »."""
    try:
        val = Decimal(str(valeur or 0))
    except Exception:
        return '0 %'
    txt = f"{val:.2f}".rstrip('0').rstrip('.')
    return f"{(txt or '0').replace('.', ',')} %"


def _peut_exporter(user):
    """Qui peut sortir le rapport « Tranches par classe ».

    Le rapport ne contient rien de plus que ce que la page /paiements/ affiche
    déjà: le réserver aux seuls ADMIN/COMPTABLE bloquait les directions et les
    secrétariats qui ouvrent pourtant l'export depuis cette même page. Restent
    exclus les profils sans lien avec la gestion financière (enseignants,
    surveillants) tant qu'ils n'ont pas la permission « rapports ».
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


def _classes_du_perimetre(request):
    """Classes visibles par l'utilisateur, filtrées par les paramètres GET."""
    raw_ecole = (request.GET.get('ecole') or '').strip()
    raw_classe = (request.GET.get('classe') or request.GET.get('classe_id') or '').strip()
    # La page /paiements/ envoie « annee »; les anciens liens « annee_scolaire ».
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

    classes = Classe.objects.select_related('ecole').all()
    ecole_user = user_school(request.user)
    annee_active = get_annee_active(request, ecole_user) if ecole_user else None
    # Même séparation par école que filter_by_user_school: seul le
    # superutilisateur voit plusieurs écoles, et un compte sans école
    # rattachée n'exporte rien plutôt que tout.
    if not user_is_superadmin(request.user):
        if ecole_user is None:
            return [], annee_scolaire
        classes = classes.filter(ecole=ecole_user)
    elif ecole_id:
        classes = classes.filter(ecole_id=ecole_id)
    if classe_id:
        classes = classes.filter(id=classe_id)
    if annee_scolaire:
        classes = classes.filter(annee_scolaire=annee_scolaire)
    elif annee_active:
        classes = classes.filter(annee_scolaire=annee_active)

    # Anti-abus: limiter le nombre de classes exportées en une requête
    classes = classes.order_by('ecole__nom', 'niveau', 'nom')[:200]
    return list(classes), annee_scolaire


def _remises_par_eleve(student_ids, annee_scolaire):
    """Remises validées par élève: montant total + pourcentages choisis.

    Le pourcentage retourné est celui que l'utilisateur a sélectionné en
    appliquant la remise (``RemiseReduction.valeur`` d'une remise de type
    POURCENTAGE), et non un ratio recalculé après coup.
    """
    lignes = (
        PaiementRemise.objects
        .filter(paiement__eleve_id__in=student_ids, paiement__statut='VALIDE')
    )
    if annee_scolaire:
        lignes = lignes.filter(paiement__annee_scolaire=annee_scolaire)

    resultat = {}
    for ligne in lignes.values(
        'paiement__eleve_id', 'montant_remise',
        'remise__type_remise', 'remise__valeur',
    ):
        eleve_id = ligne['paiement__eleve_id']
        infos = resultat.setdefault(eleve_id, {'montant': ZERO, 'pourcentages': []})
        infos['montant'] += Decimal(str(ligne['montant_remise'] or 0))
        if ligne['remise__type_remise'] == 'POURCENTAGE':
            valeur = Decimal(str(ligne['remise__valeur'] or 0))
            if valeur > 0 and valeur not in infos['pourcentages']:
                infos['pourcentages'].append(valeur)
    for infos in resultat.values():
        infos['pourcentages'].sort(reverse=True)
    return resultat


def _lignes_tranches(classe, annee_scolaire):
    """Construit une ligne cohérente par élève pour les exports PDF et Excel."""
    eleves_mgr = getattr(classe, 'eleves', None)
    eleves = list(
        eleves_mgr.all().order_by('nom', 'prenom') if eleves_mgr is not None else []
    )
    if not eleves:
        return []

    annee_effective = annee_scolaire or getattr(classe, 'annee_scolaire', '')
    student_ids = [eleve.pk for eleve in eleves]

    echeanciers = EcheancierPaiement.objects.filter(eleve_id__in=student_ids)
    if annee_effective:
        echeanciers = echeanciers.filter(annee_scolaire=annee_effective)
    echeanciers_par_eleve = {item.eleve_id: item for item in echeanciers}

    remises_par_eleve = _remises_par_eleve(student_ids, annee_effective)

    lignes = []
    for eleve in eleves:
        echeancier = echeanciers_par_eleve.get(eleve.pk)
        insc = reinsc = t1 = t2 = t3 = ZERO
        total_du = total_paye = ZERO

        if echeancier is not None:
            admission_payee = echeancier.frais_inscription_paye or ZERO
            if echeancier.est_reinscription:
                reinsc = admission_payee
            else:
                insc = admission_payee
            t1 = echeancier.tranche_1_payee or ZERO
            t2 = echeancier.tranche_2_payee or ZERO
            t3 = echeancier.tranche_3_payee or ZERO
            total_du = echeancier.total_du or ZERO
            total_paye = echeancier.total_paye or ZERO
        else:
            # Sans échéancier, le montant dû est inconnu: seuls les
            # encaissements validés sont restituables.
            paiements = Paiement.objects.filter(eleve=eleve, statut='VALIDE')
            if annee_effective:
                paiements = paiements.filter(annee_scolaire=annee_effective)
            for paiement in paiements.select_related('type_paiement'):
                nature = registration_kind_for_type(paiement.type_paiement)
                if nature == 'reinscription':
                    reinsc += paiement.montant or ZERO
                elif nature == 'inscription':
                    insc += paiement.montant or ZERO
            t1 = paiements.filter(type_paiement__nom__icontains='tranche 1').aggregate(
                total=Sum('montant'))['total'] or ZERO
            t2 = paiements.filter(type_paiement__nom__icontains='tranche 2').aggregate(
                total=Sum('montant'))['total'] or ZERO
            t3 = paiements.filter(type_paiement__nom__icontains='tranche 3').aggregate(
                total=Sum('montant'))['total'] or ZERO
            total_paye = insc + reinsc + t1 + t2 + t3

        infos_remise = remises_par_eleve.get(eleve.pk) or {}
        remise = max(ZERO, Decimal(str(infos_remise.get('montant', 0) or 0)))
        pourcentages = infos_remise.get('pourcentages') or []

        if total_du > 0:
            reste = max(ZERO, total_du - total_paye - remise)
            pct_paye = min(
                Decimal('100'), (total_paye + remise) / total_du * Decimal('100')
            )
        else:
            reste = ZERO
            pct_paye = ZERO

        lignes.append({
            'eleve': getattr(eleve, 'nom_complet', f"{eleve.prenom} {eleve.nom}"),
            'inscription': insc,
            'reinscription': reinsc,
            'tranche_1': t1,
            'tranche_2': t2,
            'tranche_3': t3,
            'total_du': total_du,
            'total_paye': total_paye,
            'remise': remise,
            'remise_pourcentages': pourcentages,
            'reste': reste,
            'pourcentage_paye': pct_paye,
        })
    return lignes


def _totaux(lignes):
    cles = ('inscription', 'reinscription', 'tranche_1', 'tranche_2', 'tranche_3',
            'total_du', 'total_paye', 'remise', 'reste')
    totaux = {cle: sum((ligne[cle] for ligne in lignes), ZERO) for cle in cles}
    if totaux['total_du'] > 0:
        totaux['pourcentage_paye'] = min(
            Decimal('100'),
            (totaux['total_paye'] + totaux['remise']) / totaux['total_du'] * Decimal('100'),
        )
    else:
        totaux['pourcentage_paye'] = ZERO
    return totaux


def _libelle_pourcentages(pourcentages):
    """« 50 % » ou « 50 % + 10 % » — les taux réellement choisis."""
    if not pourcentages:
        return ''
    return ' + '.join(_fmt_pct(p) for p in pourcentages)


@login_required
def export_tranches_par_classe_pdf(request):
    """Export PDF des tranches par classe avec logo entête et filigrane.

    Filtres GET: ecole, classe (ou classe_id), annee_scolaire (ou annee).
    Respecte la séparation par école pour les non-admins.
    """
    if not _peut_exporter(request.user):
        return HttpResponse(
            "Accès refusé: vous n'avez pas l'autorisation d'exporter ce rapport.",
            status=403,
        )

    classes, annee_scolaire = _classes_du_perimetre(request)

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
        return HttpResponse(
            "ReportLab n'est pas installé. Veuillez exécuter: pip install reportlab",
            status=500,
        )

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20, leftMargin=20, topMargin=60, bottomMargin=30
    )
    elements = []
    styles = getSampleStyleSheet()
    cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7, leading=8.5)
    cell_head = ParagraphStyle(
        'CellHead', parent=styles['Normal'], fontSize=7, leading=8.5,
        fontName='Helvetica-Bold', alignment=1,
    )

    titre = 'Tranches par classe'
    if annee_scolaire:
        titre += f" – Année {annee_scolaire}"
    elements.append(Paragraph(titre, styles['Title']))
    elements.append(Spacer(1, 0.4 * cm))

    def P(x):
        return Paragraph(str(x if x is not None else ''), cell)

    entetes = [Paragraph(h, cell_head) for h in ENTETES]
    col_widths = [4.2 * cm, 2.2 * cm, 2.2 * cm, 2.1 * cm, 2.1 * cm, 2.1 * cm,
                  2.4 * cm, 2.4 * cm, 2.2 * cm, 1.6 * cm, 2.4 * cm, 1.5 * cm]

    if not classes:
        elements.append(Paragraph("Aucune classe ne correspond aux filtres.", styles['Normal']))

    for classe in classes:
        titre_classe = f"Classe: {classe.nom} – {getattr(classe.ecole, 'nom', '')}"
        elements.append(Paragraph(titre_classe, styles['Heading2']))
        elements.append(Spacer(1, 0.2 * cm))

        lignes = _lignes_tranches(classe, annee_scolaire)
        data = [entetes]
        for ligne in lignes:
            data.append([
                P(ligne['eleve']),
                _fmt_gnf(ligne['inscription']),
                _fmt_gnf(ligne['reinscription']),
                _fmt_gnf(ligne['tranche_1']),
                _fmt_gnf(ligne['tranche_2']),
                _fmt_gnf(ligne['tranche_3']),
                _fmt_gnf(ligne['total_du']),
                _fmt_gnf(ligne['total_paye']),
                _fmt_gnf(ligne['remise']),
                _libelle_pourcentages(ligne['remise_pourcentages']),
                _fmt_gnf(ligne['reste']),
                _fmt_pct(ligne['pourcentage_paye']),
            ])

        ligne_totaux = None
        if lignes:
            totaux = _totaux(lignes)
            ligne_totaux = len(data)
            data.append([
                P('TOTAL CLASSE'),
                _fmt_gnf(totaux['inscription']),
                _fmt_gnf(totaux['reinscription']),
                _fmt_gnf(totaux['tranche_1']),
                _fmt_gnf(totaux['tranche_2']),
                _fmt_gnf(totaux['tranche_3']),
                _fmt_gnf(totaux['total_du']),
                _fmt_gnf(totaux['total_paye']),
                _fmt_gnf(totaux['remise']),
                '',
                _fmt_gnf(totaux['reste']),
                _fmt_pct(totaux['pourcentage_paye']),
            ])
        else:
            data.append([P('Aucun élève dans cette classe')] + [''] * (len(ENTETES) - 1))

        table = Table(data, repeatRows=1, colWidths=col_widths)
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]
        if ligne_totaux is not None:
            style += [
                ('BACKGROUND', (0, ligne_totaux), (-1, ligne_totaux), colors.whitesmoke),
                ('FONTNAME', (1, ligne_totaux), (-1, ligne_totaux), 'Helvetica-Bold'),
            ]
        table.setStyle(TableStyle(style))
        elements.append(table)
        elements.append(Spacer(1, 0.6 * cm))

    doc.build(
        elements,
        onFirstPage=_draw_header_and_watermark,
        onLaterPages=_draw_header_and_watermark,
    )
    return response


@login_required
def export_tranches_par_classe_excel(request):
    """Export Excel (XLSX) des tranches par classe: mêmes colonnes que le PDF.

    Filtres GET facultatifs: ecole, classe/classe_id, annee_scolaire/annee.
    Respecte la séparation par école pour non-admin.
    """
    if not _peut_exporter(request.user):
        return HttpResponse(
            "Accès refusé: vous n'avez pas l'autorisation d'exporter ce rapport.",
            status=403,
        )

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        from openpyxl.utils import get_column_letter
    except Exception:
        return HttpResponse(
            "OpenPyXL n'est pas installé. Veuillez exécuter: pip install openpyxl",
            status=500,
        )

    classes, annee_scolaire = _classes_du_perimetre(request)

    wb = Workbook()
    ws_index = wb.active
    ws_index.title = 'Index'
    ws_index.append(['Tranches par classe', f"Année: {annee_scolaire}" if annee_scolaire else ''])
    ws_index.append(['École', 'Classe', 'Feuille'])

    format_gnf = '# ##0'
    format_pct = '0.##"%"'
    colonnes_montants = (2, 3, 4, 5, 6, 7, 8, 9, 11)
    col_remise_pct = 10
    col_pct_paye = 12

    def nom_feuille(classe):
        brut = classe.nom or 'Classe'
        for interdit in '[]:*?/\\':
            brut = brut.replace(interdit, '-')
        return brut[:28] or 'Classe'

    for classe in classes:
        ws = wb.create_sheet(title=nom_feuille(classe))
        ws.append([f"Classe: {classe.nom} – {getattr(classe.ecole, 'nom', '')}"])
        ws['A1'].font = Font(bold=True)
        ws.append(ENTETES)
        for col in range(1, len(ENTETES) + 1):
            ws.cell(row=2, column=col).font = Font(bold=True)

        lignes = _lignes_tranches(classe, annee_scolaire)
        for ligne in lignes:
            pourcentages = ligne['remise_pourcentages']
            # Un seul taux choisi -> valeur numérique exploitable dans Excel;
            # plusieurs remises cumulées -> libellé « 50 % + 10 % ».
            if len(pourcentages) == 1:
                cellule_pct_remise = float(pourcentages[0])
            elif pourcentages:
                cellule_pct_remise = _libelle_pourcentages(pourcentages)
            else:
                cellule_pct_remise = None
            ws.append([
                ligne['eleve'],
                int(ligne['inscription']),
                int(ligne['reinscription']),
                int(ligne['tranche_1']),
                int(ligne['tranche_2']),
                int(ligne['tranche_3']),
                int(ligne['total_du']),
                int(ligne['total_paye']),
                int(ligne['remise']),
                cellule_pct_remise,
                int(ligne['reste']),
                float(round(ligne['pourcentage_paye'], 2)),
            ])

        if lignes:
            totaux = _totaux(lignes)
            ws.append([
                'TOTAL CLASSE',
                int(totaux['inscription']),
                int(totaux['reinscription']),
                int(totaux['tranche_1']),
                int(totaux['tranche_2']),
                int(totaux['tranche_3']),
                int(totaux['total_du']),
                int(totaux['total_paye']),
                int(totaux['remise']),
                None,
                int(totaux['reste']),
                float(round(totaux['pourcentage_paye'], 2)),
            ])
            for col in range(1, len(ENTETES) + 1):
                ws.cell(row=ws.max_row, column=col).font = Font(bold=True)

        # Formats: montants en GNF, pourcentages dans leurs colonnes dédiées
        for row in range(3, ws.max_row + 1):
            for col in colonnes_montants:
                ws.cell(row=row, column=col).number_format = format_gnf
            cellule_remise_pct = ws.cell(row=row, column=col_remise_pct)
            if isinstance(cellule_remise_pct.value, (int, float)):
                cellule_remise_pct.number_format = format_pct
            ws.cell(row=row, column=col_pct_paye).number_format = format_pct

        ws.freeze_panes = 'A3'
        for col in range(1, len(ENTETES) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 26 if col == 1 else 15

        ws_index.append([getattr(classe.ecole, 'nom', ''), classe.nom, ws.title])

    if ws_index.max_row == 2:
        ws_index.append(['Aucune classe ne correspond aux filtres.'])
    for col, largeur in ((1, 30), (2, 22), (3, 22)):
        ws_index.column_dimensions[get_column_letter(col)].width = largeur

    from io import BytesIO
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    resp = HttpResponse(
        stream.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    suffix = datetime.now().strftime('%Y%m%d')
    filename = f'tranches_par_classe_{suffix}.xlsx'
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp
