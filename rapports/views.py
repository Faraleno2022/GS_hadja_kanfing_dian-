from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.utils import timezone as django_timezone
from decimal import Decimal
import json
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .utils import ventiler_encaissements, soldes_actuels_par_classe
from .models import Rapport, TypeRapport, ExportProgramme
from .utils import collecter_donnees_periode, generer_pdf_periode, _draw_header_and_watermark, remises_par_categorie
from eleves.models import Eleve, Ecole
from eleves.utils_annee import get_annee_active
from paiements.models import Paiement, PaiementRemise, EcheancierPaiement, TypePaiement
from paiements.allocation import registration_kind_for_type
from bus.models import AbonnementBus
from depenses.models import Depense
from salaires.models import Enseignant, EtatSalaire
from utilisateurs.utils import user_is_admin, user_is_superadmin, user_school
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side, numbers
from openpyxl.utils import get_column_letter

# Décorateur d'accès admin uniquement
admin_required = user_passes_test(user_is_admin)

def can_access_rapports(user):
    """Vérifie si l'utilisateur peut accéder aux rapports"""
    if not user.is_authenticated:
        return False
    
    # Super admin et staff ont accès
    if user.is_superuser or user.is_staff:
        return True
    
    # Vérifier le rôle via le profil
    try:
        profil = user.profil
        return profil.role in ['ADMIN', 'COMPTABLE', 'DIRECTEUR']
    except:
        return False

@login_required
@user_passes_test(can_access_rapports)
def tableau_bord(request):
    """Vue principale du module Rapports"""
    context = {
        'rapports_recents': Rapport.objects.filter(
            genere_par=request.user
        ).order_by('-date_generation')[:10],
        'types_rapports': TypeRapport.objects.filter(actif=True),
        'exports_programmes': ExportProgramme.objects.filter(
            cree_par=request.user,
            statut='ACTIF'
        )[:5],
        'today': date.today()
    }
    return render(request, 'rapports/tableau_bord.html', context)

@login_required
@user_passes_test(can_access_rapports)
def generer_rapport_journalier(request):
    """Génère un rapport journalier automatique"""
    date_rapport = date.today()
    if request.GET.get('date'):
        date_rapport = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
    
    # Collecte des données journalières
    donnees = collecter_donnees_journalieres(date_rapport, user=request.user)
    
    # Génération du PDF
    pdf_buffer = generer_pdf_journalier(donnees, date_rapport)
    
    # Sauvegarde du rapport
    rapport = Rapport.objects.create(
        type_rapport=get_or_create_type_rapport('JOURNALIER'),
        titre=f"Rapport Journalier - {date_rapport.strftime('%d/%m/%Y')}",
        periode_debut=date_rapport,
        periode_fin=date_rapport,
        format_rapport='PDF',
        statut='TERMINE',
        genere_par=request.user,
        parametres=json.dumps(donnees, default=str)
    )
    
    # Sauvegarde du fichier PDF
    rapport.fichier.save(
        f'rapport_journalier_{date_rapport.strftime("%Y%m%d")}.pdf',
        pdf_buffer
    )
    
    return HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')

@login_required
@user_passes_test(can_access_rapports)
def export_rapport_annuel_excel(request):
    """Export Excel du rapport annuel."""
    aujourd_hui = date.today()
    debut_annee = date(aujourd_hui.year, 1, 1)
    fin_annee = date(aujourd_hui.year, 12, 31)
    if request.GET.get('annee'):
        annee = int(request.GET.get('annee'))
        debut_annee = date(annee, 1, 1)
        fin_annee = date(annee, 12, 31)
    debut_dt = django_timezone.make_aware(datetime.combine(debut_annee, datetime.min.time()))
    fin_dt = django_timezone.make_aware(datetime.combine(fin_annee, datetime.max.time()))

    donnees = collecter_donnees_periode(debut_dt, fin_dt, 'ANNUEL', user=request.user)
    wb = _build_excel_from_donnees(donnees, titre=f"Rapport Annuel - {debut_annee.year}")
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="rapport_annuel_{debut_annee.year}.xlsx"'
    wb.save(response)
    return response

@login_required
@user_passes_test(can_access_rapports)
def export_rapport_mensuel_excel(request):
    """Export Excel du rapport mensuel."""
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    if request.GET.get('mois') and request.GET.get('annee'):
        mois = int(request.GET.get('mois'))
        annee = int(request.GET.get('annee'))
        debut_mois = date(annee, mois, 1)
        fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    debut_dt = django_timezone.make_aware(datetime.combine(debut_mois, datetime.min.time()))
    fin_dt = django_timezone.make_aware(datetime.combine(fin_mois, datetime.max.time()))

    donnees = collecter_donnees_periode(debut_dt, fin_dt, 'MENSUEL', user=request.user)
    wb = _build_excel_from_donnees(donnees, titre=f"Rapport Mensuel - {debut_mois.strftime('%B %Y')}")
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="rapport_mensuel_{debut_mois.strftime("%Y%m")}.xlsx"'
    wb.save(response)
    return response

@login_required
@user_passes_test(can_access_rapports)
def export_rapport_hebdomadaire_excel(request):
    """Export Excel du rapport hebdomadaire (lundi-dimanche)."""
    aujourd_hui = date.today()
    debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    if request.GET.get('debut'):
        debut_semaine = datetime.strptime(request.GET.get('debut'), '%Y-%m-%d').date()
        fin_semaine = debut_semaine + timedelta(days=6)
    debut_dt = django_timezone.make_aware(datetime.combine(debut_semaine, datetime.min.time()))
    fin_dt = django_timezone.make_aware(datetime.combine(fin_semaine, datetime.max.time()))

    donnees = collecter_donnees_periode(debut_dt, fin_dt, 'HEBDOMADAIRE', user=request.user)
    wb = _build_excel_from_donnees(donnees, titre=f"Rapport Hebdomadaire - {debut_semaine.strftime('%d/%m')} au {fin_semaine.strftime('%d/%m/%Y')}")
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="rapport_hebdomadaire_{debut_semaine.strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response

@login_required
@user_passes_test(can_access_rapports)
def export_rapport_journalier_excel(request):
    """Export Excel du rapport journalier (mêmes données que le PDF)."""
    date_rapport = date.today()
    if request.GET.get('date'):
        date_rapport = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()

    donnees = collecter_donnees_journalieres(date_rapport, user=request.user)
    wb = _build_excel_from_donnees(donnees, titre=f"Rapport Journalier - {date_rapport.strftime('%d/%m/%Y')}")

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="rapport_journalier_{date_rapport.strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response

@login_required
@user_passes_test(can_access_rapports)
def generer_rapport_hebdomadaire(request):
    """Génère un rapport hebdomadaire"""
    # Calcul de la semaine (lundi à dimanche)
    aujourd_hui = date.today()
    debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    
    if request.GET.get('debut'):
        debut_semaine = datetime.strptime(request.GET.get('debut'), '%Y-%m-%d').date()
        fin_semaine = debut_semaine + timedelta(days=6)
    
    # Convertir les dates en datetime timezone-aware pour éviter les warnings
    debut_dt = django_timezone.make_aware(datetime.combine(debut_semaine, datetime.min.time()))
    fin_dt = django_timezone.make_aware(datetime.combine(fin_semaine, datetime.max.time()))
    
    donnees = collecter_donnees_periode(debut_dt, fin_dt, 'HEBDOMADAIRE', user=request.user)
    # Branding: si utilisateur restreint à une école, utiliser son logo/nom
    # IMPORTANT: Seul le superuser peut voir toutes les écoles
    ecole_ctx = user_school(request.user) if not user_is_superadmin(request.user) else None
    pdf_buffer = generer_pdf_periode(donnees, debut_semaine, fin_semaine, 'HEBDOMADAIRE', ecole=ecole_ctx)
    
    # Sauvegarde
    rapport = Rapport.objects.create(
        type_rapport=get_or_create_type_rapport('HEBDOMADAIRE'),
        titre=f"Rapport Hebdomadaire - {debut_semaine.strftime('%d/%m')} au {fin_semaine.strftime('%d/%m/%Y')}",
        periode_debut=datetime.combine(debut_semaine, datetime.min.time()),
        periode_fin=datetime.combine(fin_semaine, datetime.max.time()),
        format_rapport='PDF',
        statut='TERMINE',
        genere_par=request.user,
        parametres=json.dumps(donnees, default=str)
    )
    
    rapport.fichier.save(
        f'rapport_hebdomadaire_{debut_semaine.strftime("%Y%m%d")}.pdf',
        pdf_buffer
    )
    
    return HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')

@login_required
@user_passes_test(can_access_rapports)
def generer_rapport_mensuel(request):
    """Génère un rapport mensuel"""
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    if request.GET.get('mois') and request.GET.get('annee'):
        mois = int(request.GET.get('mois'))
        annee = int(request.GET.get('annee'))
        debut_mois = date(annee, mois, 1)
        fin_mois = (debut_mois + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # Convertir les dates en datetime timezone-aware pour éviter les warnings
    debut_dt = django_timezone.make_aware(datetime.combine(debut_mois, datetime.min.time()))
    fin_dt = django_timezone.make_aware(datetime.combine(fin_mois, datetime.max.time()))
    
    donnees = collecter_donnees_periode(debut_dt, fin_dt, 'MENSUEL', user=request.user)
    # IMPORTANT: Seul le superuser peut voir toutes les écoles
    ecole_ctx = user_school(request.user) if not user_is_superadmin(request.user) else None
    pdf_buffer = generer_pdf_periode(donnees, debut_mois, fin_mois, 'MENSUEL', ecole=ecole_ctx)
    
    # Sauvegarde
    rapport = Rapport.objects.create(
        type_rapport=get_or_create_type_rapport('MENSUEL'),
        titre=f"Rapport Mensuel - {debut_mois.strftime('%B %Y')}",
        periode_debut=datetime.combine(debut_mois, datetime.min.time()),
        periode_fin=datetime.combine(fin_mois, datetime.max.time()),
        format_rapport='PDF',
        statut='TERMINE',
        genere_par=request.user,
        parametres=json.dumps(donnees, default=str)
    )
    
    rapport.fichier.save(
        f'rapport_mensuel_{debut_mois.strftime("%Y%m")}.pdf',
        pdf_buffer
    )
    
    return HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')

@login_required
@user_passes_test(can_access_rapports)
def generer_rapport_annuel(request):
    """Génère un rapport annuel"""
    aujourd_hui = date.today()
    debut_annee = date(aujourd_hui.year, 1, 1)
    fin_annee = date(aujourd_hui.year, 12, 31)
    
    if request.GET.get('annee'):
        annee = int(request.GET.get('annee'))
        debut_annee = date(annee, 1, 1)
        fin_annee = date(annee, 12, 31)
    
    # Convertir les dates en datetime timezone-aware pour éviter les warnings
    debut_dt = django_timezone.make_aware(datetime.combine(debut_annee, datetime.min.time()))
    fin_dt = django_timezone.make_aware(datetime.combine(fin_annee, datetime.max.time()))
    
    donnees = collecter_donnees_periode(debut_dt, fin_dt, 'ANNUEL', user=request.user)
    # IMPORTANT: Seul le superuser peut voir toutes les écoles
    ecole_ctx = user_school(request.user) if not user_is_superadmin(request.user) else None
    pdf_buffer = generer_pdf_periode(donnees, debut_annee, fin_annee, 'ANNUEL', ecole=ecole_ctx)
    
    # Sauvegarde
    rapport = Rapport.objects.create(
        type_rapport=get_or_create_type_rapport('ANNUEL'),
        titre=f"Rapport Annuel - {debut_annee.year}",
        periode_debut=datetime.combine(debut_annee, datetime.min.time()),
        periode_fin=datetime.combine(fin_annee, datetime.max.time()),
        format_rapport='PDF',
        statut='TERMINE',
        genere_par=request.user,
        parametres=json.dumps(donnees, default=str)
    )
    
    rapport.fichier.save(
        f'rapport_annuel_{debut_annee.year}.pdf',
        pdf_buffer
    )
    
    return HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')

@login_required
@user_passes_test(can_access_rapports)
def liste_rapports(request):
    """Liste tous les rapports générés"""
    rapports = Rapport.objects.filter(
        genere_par=request.user
    ).order_by('-date_generation')
    
    context = {
        'rapports': rapports
    }
    return render(request, 'rapports/liste_rapports.html', context)


@login_required
@user_passes_test(can_access_rapports)
def rapport_transport_scolaire(request):
    """Rapport des versements bus de l'année active et de leurs tarifs."""
    from django.db.models import F
    from bus.suivi_classes import resume_transport_par_classe
    from utilisateurs.utils import filter_by_user_school

    ecole_user = user_school(request.user)
    annee = get_annee_active(request, ecole_user)
    versements = filter_by_user_school(
        AbonnementBus.objects.all(), request.user, 'eleve__classe__ecole',
    )
    if annee:
        versements = versements.filter(annee_scolaire=annee)
    else:
        versements = versements.filter(annee_scolaire=F('eleve__classe__annee_scolaire'))
    versements = versements.filter(
        Q(grille__isnull=True)
        | Q(grille__ecole_id=F('eleve__classe__ecole_id'),
            grille__annee_scolaire=F('annee_scolaire'))
    )
    # Une suspension ou une expiration n'annule pas les sommes encaissées.
    lignes, totals = resume_transport_par_classe(versements)
    return render(request, 'rapports/transport_scolaire.html', {
        'lignes': lignes, 'totals': totals, 'annee_scolaire': annee,
        'ecole': getattr(ecole_user, 'nom', None),
        'soldes_inconnus': totals['reste'] is None,
    })


def get_or_create_type_rapport(nom):
    """Récupère ou crée un type de rapport"""
    type_rapport, created = TypeRapport.objects.get_or_create(
        nom=nom,
        defaults={
            'description': f'Rapport {nom.lower()}',
            'categorie': 'FINANCIER',
            'template_path': f'rapports/{nom.lower()}.html',
            'actif': True
        }
    )
    return type_rapport

def _build_excel_from_donnees(donnees, titre):
    """Construit un classeur Excel à partir de la structure de données des rapports.
    Feuille 1: Synthèse par école.
    Feuille 2: Répartition par classe (toutes écoles).
    """
    wb = Workbook()
    ws1 = wb.active
    ws1.title = 'Synthèse'

    header_fill = PatternFill(start_color='0D47A1', end_color='0D47A1', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    thin = Side(style='thin', color='DDDDDD')
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Titre
    ws1.append([titre])
    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    ws1['A1'].font = Font(bold=True, size=14)
    ws1['A1'].alignment = Alignment(horizontal='center')

    headers1 = [
        'École', 'Nouveaux élèves', 'Nb paiements', 'Scolarité normale', "Scolarité payée",
        "Frais d'inscription", "Frais de réinscription", 'Reste à payer', 'Montant original', 'Remises', 'Net encaissé',
        'Nb dépenses', 'Total dépenses', 'États salaires', 'Total salaires'
    ]
    ws1.append(headers1)
    for col in range(1, len(headers1) + 1):
        c = ws1.cell(row=2, column=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center')
        c.border = border_all

    row = 3
    for _, e in donnees.get('ecoles', {}).items():
        vals = [
            e.get('nom', ''),
            e.get('nouveaux_eleves', 0),
            e['paiements'].get('nombre', 0),
            float(e['paiements'].get('total_du_concernes', 0) or 0),
            float(e['paiements'].get('scolarite', 0) or 0),
            float(e['paiements'].get('frais_inscription', 0) or 0),
            float(e['paiements'].get('reinscription', 0) or 0),
            float(e['paiements'].get('reste_a_payer', 0) or 0),
            float(e['paiements'].get('montant_original', 0) or 0),
            float(e['paiements'].get('total_remises', 0) or 0),
            float(e['paiements'].get('montant_total', 0) or 0),
            e['depenses'].get('nombre', 0),
            float(donnees.get('depenses_globales', {}).get('montant_total', 0) or 0) if False else float(e['depenses'].get('montant_total', 0) or 0),
            e['salaires'].get('etats_valides', 0),
            float(e['salaires'].get('montant_total', 0) or 0),
        ]
        ws1.append(vals)
        for col in range(1, len(headers1) + 1):
            cell = ws1.cell(row=row, column=col)
            cell.border = border_all
            if col >= 4 and col != 12 and col != 14:  # colonnes montants
                cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
        row += 1

    # Largeurs
    widths = [26, 16, 14, 18, 18, 18, 18, 16, 18, 16, 16, 14, 16, 14, 16]
    for i, w in enumerate(widths, start=1):
        ws1.column_dimensions[get_column_letter(i)].width = w

    # Feuille 2: par classe
    ws2 = wb.create_sheet('Par classe')
    headers2 = ['École', 'Classe', 'Effectif', 'Total dû', 'Total payé', 'Remises', 'Solde actuel']
    ws2.append(headers2)
    for col in range(1, len(headers2) + 1):
        c = ws2.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center')
        c.border = border_all

    r = 2
    for _, e in donnees.get('ecoles', {}).items():
        ecole_nom = e.get('nom', '')
        for c in e.get('classes', []) or []:
            ws2.append([
                ecole_nom,
                c.get('classe', ''),
                c.get('effectif', 0),
                float(c.get('total_du', 0) or 0),
                float(c.get('total_paye', 0) or 0),
                float(c.get('remises', 0) or 0),
                float(c.get('reste', 0) or 0),
            ])
            for col in range(1, len(headers2) + 1):
                cell = ws2.cell(row=r, column=col)
                cell.border = border_all
                if col >= 4:
                    cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
            r += 1

    for i, w in enumerate([22, 18, 12, 16, 16, 16, 16], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    # Feuille 3: remises par catégorie (motif), toutes écoles
    ws3 = wb.create_sheet('Remises par catégorie')
    headers3 = ['École', 'Catégorie (motif)', 'Montant (GNF)']
    ws3.append(headers3)
    for col in range(1, len(headers3) + 1):
        c = ws3.cell(row=1, column=col)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center')
        c.border = border_all

    r = 2
    for _, e in donnees.get('ecoles', {}).items():
        ecole_nom = e.get('nom', '')
        for categorie, montant in (e['paiements'].get('remises_par_categorie') or {}).items():
            ws3.append([ecole_nom, categorie, float(montant or 0)])
            for col in range(1, len(headers3) + 1):
                cell = ws3.cell(row=r, column=col)
                cell.border = border_all
                if col == 3:
                    cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
            r += 1

    for i, w in enumerate([26, 26, 18], start=1):
        ws3.column_dimensions[get_column_letter(i)].width = w

    return wb

def collecter_donnees_journalieres(date_rapport, user=None):
    """Collecte toutes les données importantes pour le rapport journalier"""
    donnees = {
        'date': date_rapport,
        'ecoles': {},
        # Dépenses non reliées à l'école: globales pour la journée
        'depenses_globales': {
            'nombre': 0,  # initialisé, sera remplacé par des entiers
            'montant_total': Decimal('0')
        }
    }

    # Restreindre le périmètre des écoles selon l'utilisateur
    # IMPORTANT: Seul le superuser peut voir toutes les écoles
    ecoles_qs = Ecole.objects.all()
    if user is not None and not user_is_superadmin(user):
        ecole_user = user_school(user)
        ecoles_qs = ecoles_qs.filter(id=getattr(ecole_user, 'id', None)) if ecole_user else Ecole.objects.none()

    # Dépenses du jour (GLOBAL - pas de relation à Ecole)
    depenses_jour_global = Depense.objects.filter(
        date_facture=date_rapport,
        statut__in=['VALIDEE', 'PAYEE']
    )
    if user is not None:
        from utilisateurs.utils import filter_by_user_school
        depenses_jour_global = filter_by_user_school(
            depenses_jour_global, user, 'cree_par__profil__ecole',
        )
    donnees['depenses_globales']['nombre'] = depenses_jour_global.count()
    donnees['depenses_globales']['montant_total'] = depenses_jour_global.aggregate(
        total=Sum('montant_ttc')
    )['total'] or Decimal('0')

    # Pour chaque école
    for ecole in ecoles_qs:
        # Nom d'école affiché (normalisation pour SONFONIA)
        _nom_affiche = ecole.nom
        _nom_upper = (ecole.nom or '').upper()
        if any(key in _nom_upper for key in ['SONFONIA', 'SONFONIE']):
            _nom_affiche = "GROUPE SCOLAIRE myschool-SONFONIA"

        donnees_ecole = {
            'nom': _nom_affiche,
            'nouveaux_eleves': Eleve.objects.filter(
                classe__ecole=ecole,
                date_inscription=date_rapport
            ).count(),
            'paiements': {
                'nombre': 0,
                'montant_total': Decimal('0'),
                'frais_inscription': Decimal('0'),
                'reinscription': Decimal('0'),
                'scolarite': Decimal('0'),
                'remises_par_categorie': {},
                # Total dû (GNF) pour les élèves concernés ce jour (paiement/inscription)
                'total_du_concernes': Decimal('0')
            },
            # Répartition par classe (remplie plus bas)
            'classes': [],
            # Dépenses affichées par école mises à 0 pour éviter toute confusion,
            # car le modèle Depense n'est pas lié à Ecole. Un total global sera affiché.
            'depenses': {
                'nombre': 0,
                'montant_total': Decimal('0')
            },
            'salaires': {
                'etats_valides': 0,
                'montant_total': Decimal('0')
            }
        }
        
        paiements_jour = Paiement.objects.filter(
            eleve__classe__ecole=ecole, date_paiement=date_rapport, statut='VALIDE',
        )

        donnees_ecole['paiements']['nombre'] = paiements_jour.count()
        donnees_ecole['paiements']['montant_total'] = paiements_jour.aggregate(
            total=Sum('montant')
        )['total'] or Decimal('0')
        
        # Calculer les remises appliquées
        remises_appliquees = PaiementRemise.objects.filter(
            paiement__in=paiements_jour
        ).aggregate(
            total_remises=Sum('montant_remise')
        )['total_remises'] or Decimal('0')
        
        # Calculer le montant original (avant remises)
        montant_original = donnees_ecole['paiements']['montant_total'] + remises_appliquees
        
        # Ajouter les données des remises
        donnees_ecole['paiements']['montant_original'] = montant_original
        donnees_ecole['paiements']['total_remises'] = remises_appliquees
        donnees_ecole['paiements']['montant_net'] = donnees_ecole['paiements']['montant_total']
        donnees_ecole['paiements']['remises_par_categorie'] = remises_par_categorie(paiements_jour)

        donnees_ecole['paiements'].update(ventiler_encaissements(paiements_jour))
        
        soldes = soldes_actuels_par_classe(
            ecole, paiements_jour, date_rapport, date_rapport,
        )
        donnees_ecole['classes'] = soldes.pop('classes')
        donnees_ecole['paiements'].update(soldes)

        # Dépenses: pas de répartition par école (le modèle n'est pas rattaché à Ecole)
        # On laisse 0 au niveau de l'école et on affiche un total global dans le résumé

        # États de salaire validés
        # Convertir la date en timezone aware pour éviter les warnings
        debut_jour = django_timezone.make_aware(datetime.combine(date_rapport, datetime.min.time()))
        fin_jour = django_timezone.make_aware(datetime.combine(date_rapport, datetime.max.time()))
        
        etats_jour = EtatSalaire.objects.filter(
            enseignant__ecole=ecole,
            date_validation__range=[debut_jour, fin_jour],
            valide=True
        )
        
        donnees_ecole['salaires']['etats_valides'] = etats_jour.count()
        donnees_ecole['salaires']['montant_total'] = etats_jour.aggregate(
            total=Sum('salaire_net')
        )['total'] or Decimal('0')
        
        donnees['ecoles'][ecole.id] = donnees_ecole
    
    return donnees

def generer_pdf_journalier(donnees, date_rapport):
    """Génère le PDF du rapport journalier"""
    buffer = BytesIO()
    
    # Créer le canvas pour ajouter le filigrane
    from reportlab.pdfgen import canvas as pdf_canvas
    
    # Déterminer l'école de l'utilisateur (branding dynamique si restreint)
    from utilisateurs.utils import user_school
    ecole_user = None
    try:
        # Note: on n'a pas directement request ici, mais ce générateur est appelé depuis des vues
        # qui passent les données selon l'utilisateur. On tente de récupérer via contexte si disponible.
        # Si indisponible, on laisse à None pour fallback générique.
        import threading
        ecole_user = None
    except Exception:
        ecole_user = None

    class WatermarkDocTemplate(SimpleDocTemplate):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        def afterPage(self):
            c = self.canv
            try:
                from ecole_moderne.pdf_utils import draw_logo_watermark
                # Si l'utilisateur est restreint à une école, utiliser son logo
                draw_logo_watermark(c, self.pagesize[0], self.pagesize[1], ecole=ecole_user)
            except Exception:
                pass
    
    doc = WatermarkDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Ajouter le logo en en-tête (dynamique par école si possible)
    try:
        from django.contrib.staticfiles import finders
        logo_path = None
        try:
            if ecole_user and getattr(ecole_user, 'logo', None) and hasattr(ecole_user.logo, 'path'):
                import os
                if os.path.exists(ecole_user.logo.path):
                    logo_path = ecole_user.logo.path
        except Exception:
            logo_path = None
        if not logo_path:
            logo_path = finders.find('logos/logo.png')
        if logo_path:
            from reportlab.platypus import Image
            logo = Image(logo_path, width=60, height=60)
            story.append(logo)
            story.append(Spacer(1, 10))
    except Exception:
        pass
    
    # Titre
    titre_style = ParagraphStyle(
        'TitreRapport',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        alignment=1  # Centré
    )
    
    story.append(Paragraph(f"RAPPORT JOURNALIER - {date_rapport.strftime('%d/%m/%Y')}", titre_style))
    story.append(Spacer(1, 20))
    
    # Pour chaque école
    for ecole_id, donnees_ecole in donnees['ecoles'].items():
        # Titre de l'école
        story.append(Paragraph(f"École: {donnees_ecole['nom']}", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Tableau des données
        data = [
            ['Indicateur', 'Valeur'],
            ['Nouveaux élèves inscrits', str(donnees_ecole['nouveaux_eleves'])],
            ['Nombre de paiements', str(donnees_ecole['paiements']['nombre'])],
            ["Scolarité normale", f"{donnees_ecole['paiements'].get('total_du_concernes', Decimal('0')):,} GNF".replace(',', ' ')],
            ['Scolarité payé', f"{donnees_ecole['paiements']['scolarite']:,} GNF".replace(',', ' ')],
            ["Frais d'inscription", f"{donnees_ecole['paiements']['frais_inscription']:,} GNF".replace(',', ' ')],
            ["Frais de réinscription", f"{donnees_ecole['paiements'].get('reinscription', Decimal('0')):,} GNF".replace(',', ' ')],
            ["Solde actuel restant", f"{donnees_ecole['paiements'].get('reste_a_payer', Decimal('0')):,} GNF".replace(',', ' ')],
            ['Montant original (avant remises)', f"{donnees_ecole['paiements']['montant_original']:,} GNF".replace(',', ' ')],
            ['Total des remises accordées', f"{donnees_ecole['paiements']['total_remises']:,} GNF".replace(',', ' ')],
            ['Montant net encaissé', f"{donnees_ecole['paiements']['montant_total']:,} GNF".replace(',', ' ')],
            ['Nombre de dépenses', str(donnees_ecole['depenses']['nombre'])],
            ['Montant total des dépenses', f"{donnees_ecole['depenses']['montant_total']:,} GNF".replace(',', ' ')],
            ['États de salaire validés', str(donnees_ecole['salaires']['etats_valides'])],
            ['Montant total des salaires', f"{donnees_ecole['salaires']['montant_total']:,} GNF".replace(',', ' ')],
        ]
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 16))

        # Répartition par classe
        if donnees_ecole.get('classes'):
            story.append(Paragraph("Situation actuelle des échéanciers par classe", styles['Heading3']))
            story.append(Spacer(1, 6))
            class_data = [[
                'Classe', 'Effectif', 'Total dû', 'Total payé', 'Remises', 'Solde actuel'
            ]]
            for c in donnees_ecole['classes']:
                class_data.append([
                    c['classe'],
                    str(c['effectif']),
                    f"{c['total_du']:,} GNF".replace(',', ' '),
                    f"{c['total_paye']:,} GNF".replace(',', ' '),
                    f"{c.get('remises', 0):,} GNF".replace(',', ' '),
                    f"{c['reste']:,} GNF".replace(',', ' '),
                ])

            class_table = Table(class_data, colWidths=[120, 60, 90, 90, 90, 90])
            class_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                ('ALIGN', (0,0), (0,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ]))
            story.append(class_table)
            story.append(Spacer(1, 16))

        # Remises par catégorie (motif)
        remises_categorie = donnees_ecole['paiements'].get('remises_par_categorie') or {}
        if remises_categorie:
            story.append(Paragraph("Remises par catégorie", styles['Heading3']))
            story.append(Spacer(1, 6))
            remises_data = [['Catégorie (motif)', 'Montant']]
            for categorie, montant in remises_categorie.items():
                remises_data.append([categorie, f"{montant:,} GNF".replace(',', ' ')])

            remises_table = Table(remises_data, colWidths=[220, 120])
            remises_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            story.append(remises_table)
            story.append(Spacer(1, 16))

    # Section Dépenses globales (non rattachées à une école)
    story.append(Paragraph("DÉPENSES GLOBALES (journée)", styles['Heading2']))
    story.append(Spacer(1, 8))
    dep_global = donnees.get('depenses_globales', {'nombre': 0, 'montant_total': Decimal('0')})
    depenses_data = [
        ['Nombre de dépenses', str(dep_global.get('nombre', 0))],
        ['Montant total des dépenses', f"{dep_global.get('montant_total', Decimal('0')):,} GNF".replace(',', ' ')]
    ]
    dep_table = Table(depenses_data, colWidths=[3*inch, 2*inch])
    dep_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(dep_table)
    story.append(Spacer(1, 16))

    # Résumé global
    total_paiements = sum(d['paiements']['montant_total'] for d in donnees['ecoles'].values())
    total_depenses = donnees['depenses_globales']['montant_total']
    total_paiements_original = sum(d['paiements']['montant_original'] for d in donnees['ecoles'].values())
    total_remises = sum(d['paiements']['total_remises'] for d in donnees['ecoles'].values())
    total_salaires = sum(d['salaires']['montant_total'] for d in donnees['ecoles'].values())
    
    # Résumé global
    resume_data = [
        ['Indicateur', 'Montant'],
        ['Montant original des paiements', f"{total_paiements_original:,} GNF".replace(',', ' ')],
        ['Total des remises accordées', f"{total_remises:,} GNF".replace(',', ' ')],
        ['Montant net des paiements', f"{total_paiements:,} GNF".replace(',', ' ')],
        ['Total des dépenses', f"{total_depenses:,} GNF".replace(',', ' ')],
        ['Total des salaires', f"{total_salaires:,} GNF".replace(',', ' ')],
        ['Solde net', f"{total_paiements - total_depenses - total_salaires:,} GNF".replace(',', ' ')],
    ]
    
    resume_table = Table(resume_data, colWidths=[3*inch, 2*inch])
    resume_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(resume_table)
    
    # Ajout entête + filigrane sur toutes les pages
    doc.build(story, onFirstPage=_draw_header_and_watermark, onLaterPages=_draw_header_and_watermark)
    buffer.seek(0)
    return buffer


@login_required
@user_passes_test(can_access_rapports)
def rapport_remises_detaille(request):
    """Rapport détaillé des remises appliquées"""
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Par défaut, couvrir l'année scolaire active. Une fenêtre limitée au mois
    # courant rendait le rapport vide les premiers jours d'un nouveau mois.
    ecole_user = user_school(request.user)
    annee_active = get_annee_active(request, ecole_user) if ecole_user else None
    try:
        annee_debut = int(str(annee_active).split('-')[0])
    except (ValueError, TypeError, IndexError):
        aujourd_hui = date.today()
        annee_debut = aujourd_hui.year if aujourd_hui.month >= 9 else aujourd_hui.year - 1

    try:
        date_debut = (
            datetime.strptime(date_debut, '%Y-%m-%d').date()
            if date_debut else date(annee_debut, 9, 1)
        )
        date_fin = (
            datetime.strptime(date_fin, '%Y-%m-%d').date()
            if date_fin else date.today()
        )
    except (ValueError, TypeError):
        return HttpResponse("Dates invalides : utilisez le format AAAA-MM-JJ.", status=400)
    if date_debut > date_fin:
        return HttpResponse("La date de début doit précéder la date de fin.", status=400)

    # Récupérer toutes les remises appliquées dans la période
    remises_appliquees = PaiementRemise.objects.filter(
        paiement__date_paiement__range=[date_debut, date_fin],
        paiement__statut='VALIDE'
    ).select_related(
        'paiement', 'paiement__eleve', 'paiement__eleve__classe',
        'paiement__eleve__classe__ecole', 'remise'
    ).order_by('-paiement__date_paiement')

    # Filtrer par école de l'utilisateur (sauf superadmin)
    if not user_is_superadmin(request.user):
        ecole_user = user_school(request.user)
        if ecole_user:
            remises_appliquees = remises_appliquees.filter(
                paiement__eleve__classe__ecole=ecole_user
            )
        else:
            remises_appliquees = remises_appliquees.none()
    
    # Calcul des totaux
    total_remises = remises_appliquees.aggregate(
        total=Sum('montant_remise')
    )['total'] or Decimal('0')
    
    # Compter chaque reçu une fois, même s'il porte plusieurs remises.
    # Deux reçus de même montant doivent toutefois tous les deux être comptés.
    total_montants_finals = Paiement.objects.filter(
        pk__in=remises_appliquees.values('paiement_id'),
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    montant_avant_remises = total_montants_finals + total_remises
    
    # Statistiques des remises
    stats_remises = {
        'total_remises': total_remises,
        'total_montants_finals': total_montants_finals,
        'montant_avant_remises': montant_avant_remises,
        'nombre_paiements_avec_remise': remises_appliquees.values('paiement').distinct().count(),
        'nombre_eleves_beneficiaires': remises_appliquees.values('paiement__eleve').distinct().count(),
    }
    
    # Répartition par type de remise
    repartition_types = remises_appliquees.values(
        'remise__nom', 'remise__motif'
    ).annotate(
        total_montant=Sum('montant_remise'),
        nombre_applications=Count('id')
    ).order_by('-total_montant')
    
    # Répartition par école
    repartition_ecoles = remises_appliquees.values(
        'paiement__eleve__classe__ecole__nom'
    ).annotate(
        total_montant=Sum('montant_remise'),
        nombre_applications=Count('id')
    ).order_by('-total_montant')
    
    recus_affiches = set()
    for remise in remises_appliquees:
        remise.afficher_montant_recu = remise.paiement_id not in recus_affiches
        recus_affiches.add(remise.paiement_id)

    context = {
        'remises_appliquees': remises_appliquees,
        'stats_remises': stats_remises,
        'repartition_types': repartition_types,
        'repartition_ecoles': repartition_ecoles,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'periode_str': f"du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
    }
    
    return render(request, 'rapports/rapport_remises.html', context)
