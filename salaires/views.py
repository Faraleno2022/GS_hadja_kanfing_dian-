from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg, DecimalField, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import csv
import os
from xml.sax.saxutils import escape
from django.conf import settings

# ReportLab for PDF exports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from ecole_moderne.branding import get_reportlab_palette
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from .models import (
    Enseignant, AffectationClasse, PeriodeSalaire,
    EtatSalaire, DetailHeuresClasse, ModeCalculHoraire, TypeEnseignant,
    PresenceEnseignant,
    AvanceSalaire,
    ParametrePaie,
)
from .forms import (
    AffectationClasseForm,
    AvanceSalaireForm,
    EnseignantForm,
    EtatSalaireAjustementForm,
    ParametrePaieForm,
    PresenceForm,
)
from .services import (
    appliquer_primes_bareme,
    arrondir_heures,
    arrondir_montant,
    calculer_etat_salaire,
    enseignants_eligibles,
    initialiser_etats_salaire_periode,
    recalculer_salaire_ouvert_pour_date,
    reconstruire_details_heures,
    resume_pointage,
    synthese_etats_salaire,
    synchroniser_avances_enseignant,
)
from eleves.models import Ecole, Classe
from utilisateurs.utils import (
    filter_by_user_school,
    user_is_admin,
    user_is_superadmin,
    user_school,
)
from utilisateurs.permissions import can_add_teachers
from ecole_moderne.security_decorators import delete_permission_required, require_school_object

# Importer les vues de présence
from .views_presences import (
    liste_presences, pointer_presence, modifier_presence,
    supprimer_presence, rapport_presences, export_presences_csv,
    export_presences_excel
)

def _ecole_utilisateur(request):
    """Compat: utiliser l'utilitaire centralisé"""
    return user_school(request.user)


def _resume_classe_ou_fonction(enseignant):
    """Retourne l'affectation lisible sans mélanger les différents profils."""
    if enseignant.utilise_classe_principale:
        return (
            enseignant.classe_principale.nom
            if enseignant.classe_principale_id else 'Classe non renseignée'
        )
    if enseignant.type_enseignant == TypeEnseignant.ADMINISTRATEUR:
        return enseignant.fonction or 'Fonction non renseignée'

    aujourd_hui = timezone.localdate()
    affectations = [
        affectation.classe.nom
        for affectation in enseignant.affectations.all()
        if (
            affectation.actif
            and affectation.date_debut <= aujourd_hui
            and (
                affectation.date_fin is None
                or affectation.date_fin >= aujourd_hui
            )
        )
    ]
    return ', '.join(affectations) or 'Aucune affectation'


def _champs_paie(form):
    return [
        form[champ]
        for champ in (
            'matricule', 'prime_fonction', 'prime_performance',
            'prime_exceptionnelle', 'distance_km',
        )
    ]


def _clore_affectations_secondaires_si_necessaire(enseignant):
    """Ferme les anciennes affectations lorsqu'un dossier quitte le secondaire."""
    if enseignant.type_enseignant == TypeEnseignant.SECONDAIRE:
        return
    aujourd_hui = timezone.localdate()
    for affectation in enseignant.affectations.filter(actif=True):
        affectation.actif = False
        affectation.date_fin = max(affectation.date_debut, aujourd_hui)
        affectation.save(update_fields=['actif', 'date_fin', 'date_modification'])

@login_required
def tableau_bord(request):
    """Tableau de bord du module Salaires"""
    ecole_user = _ecole_utilisateur(request)
    # Seul le super-administrateur dispose d'une vue globale. Un administrateur
    # d'école reste limité à son établissement et un compte sans école ne voit
    # aucune donnée d'un autre établissement.
    restreindre = not request.user.is_superuser

    # Statistiques générales
    base_qs = Enseignant.objects.all()
    if restreindre:
        base_qs = base_qs.filter(ecole=ecole_user)
    stats = {
        'total_enseignants': base_qs.count(),
        'enseignants_actifs': base_qs.filter(statut='ACTIF').count(),
        'enseignants_taux_horaire': base_qs.filter(type_enseignant='SECONDAIRE').count(),
        'enseignants_salaire_fixe': base_qs.exclude(type_enseignant='SECONDAIRE').count(),
    }

    avances_qs = filter_by_user_school(
        AvanceSalaire.objects.all(), request.user, 'enseignant__ecole'
    )
    avances_qs = avances_qs.annotate(
        deja_rembourse=Coalesce(
            Sum(
                'remboursements__montant',
                filter=Q(remboursements__etat_salaire__valide=True),
            ),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )
    stats['avances_en_cours'] = avances_qs.filter(
        montant__gt=F('deja_rembourse')
    ).count()
    stats['solde_avances'] = sum(
        (
            max(avance.montant - avance.deja_rembourse, Decimal('0'))
            for avance in avances_qs
        ),
        Decimal('0'),
    )
    
    # Période courante
    periode_courante = None
    try:
        now = timezone.now()
        qs_periodes = PeriodeSalaire.objects.filter(mois=now.month, annee=now.year)
        if restreindre:
            qs_periodes = qs_periodes.filter(ecole=ecole_user)
        periode_courante = qs_periodes.first()
    except:
        pass
    
    # États de salaire récents
    etats_recents = EtatSalaire.objects.select_related('enseignant', 'periode')
    if restreindre:
        etats_recents = etats_recents.filter(periode__ecole=ecole_user)
    etats_recents = etats_recents.order_by('-date_calcul')[:10]
    
    # Statistiques par école
    stats_ecoles = []
    if request.user.is_superuser:
        ecoles_iter = Ecole.objects.all()
    elif ecole_user is not None:
        ecoles_iter = Ecole.objects.filter(id=ecole_user.id)
    else:
        ecoles_iter = Ecole.objects.none()
    for ecole in ecoles_iter:
        enseignants_ecole = Enseignant.objects.filter(ecole=ecole, statut='ACTIF')
        stats_ecoles.append({
            'ecole': ecole,
            'total_enseignants': enseignants_ecole.count(),
            'taux_horaire': enseignants_ecole.filter(type_enseignant='SECONDAIRE').count(),
            'salaire_fixe': enseignants_ecole.exclude(type_enseignant='SECONDAIRE').count(),
        })
    
    # Alertes
    alertes = []
    
    # Vérifier les enseignants sans affectation active (période en cours)
    aujourd_hui = timezone.now().date()
    enseignants_base = Enseignant.objects.filter(statut='ACTIF')
    if restreindre:
        enseignants_base = enseignants_base.filter(ecole=ecole_user)
    enseignants_sans_affectation = (
        enseignants_base.filter(type_enseignant=TypeEnseignant.SECONDAIRE)
        .annotate(
            nb_actives=Count(
                'affectations',
                filter=(
                    Q(affectations__actif=True,
                      affectations__date_debut__lte=aujourd_hui) &
                    (Q(affectations__date_fin__isnull=True) | Q(affectations__date_fin__gte=aujourd_hui))
                )
            )
        )
        .filter(nb_actives=0)
        .count()
    )
    
    if enseignants_sans_affectation > 0:
        alertes.append({
            'type': 'warning',
            'message': f'{enseignants_sans_affectation} enseignant(s) sans affectation de classe',
            'action': 'Gérer les affectations'
        })

    enseignants_sans_classe = enseignants_base.filter(
        type_enseignant__in=[
            TypeEnseignant.GARDERIE,
            TypeEnseignant.MATERNELLE,
            TypeEnseignant.PRIMAIRE,
        ],
        classe_principale__isnull=True,
    ).count()
    if enseignants_sans_classe > 0:
        alertes.append({
            'type': 'warning',
            'message': (
                f'{enseignants_sans_classe} enseignant(s) de garderie, '
                'maternelle ou primaire sans classe principale'
            ),
            'action': 'Compléter les dossiers',
        })
    
    # Vérifier les périodes non clôturées
    periodes_ouvertes_qs = PeriodeSalaire.objects.filter(cloturee=False)
    if restreindre:
        periodes_ouvertes_qs = periodes_ouvertes_qs.filter(ecole=ecole_user)
    periodes_ouvertes = periodes_ouvertes_qs.count()
    if periodes_ouvertes > 2:
        alertes.append({
            'type': 'info',
            'message': f'{periodes_ouvertes} périodes de salaire ouvertes',
            'action': 'Clôturer les anciennes périodes'
        })
    
    context = {
        'stats': stats,
        'periode_courante': periode_courante,
        'etats_recents': etats_recents,
        'stats_ecoles': stats_ecoles,
        'alertes': alertes,
    }
    
    return render(request, 'salaires/tableau_bord.html', context)


@login_required
def liste_enseignants(request):
    """Liste des enseignants avec filtres"""
    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_superadmin(request.user)

    # Récupération des paramètres de filtrage
    search = request.GET.get('search', '')
    ecole_id = request.GET.get('ecole', '')
    type_enseignant = request.GET.get('type_enseignant', '')
    statut = request.GET.get('statut', '')
    
    # Construction de la requête
    enseignants = Enseignant.objects.select_related(
        'ecole', 'classe_principale'
    ).prefetch_related('affectations__classe')
    if restreindre:
        enseignants = enseignants.filter(ecole=ecole_user)
    
    if search:
        enseignants = enseignants.filter(
            Q(nom__icontains=search) | 
            Q(prenoms__icontains=search) |
            Q(email__icontains=search)
        )
    
    if ecole_id:
        enseignants = enseignants.filter(ecole_id=ecole_id)
    
    if type_enseignant:
        enseignants = enseignants.filter(type_enseignant=type_enseignant)
    
    if statut:
        enseignants = enseignants.filter(statut=statut)
    
    # Pagination
    paginator = Paginator(enseignants, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    ecoles = Ecole.objects.all()
    if restreindre:
        ecoles = ecoles.filter(id=ecole_user.id)
    types_enseignant = TypeEnseignant.choices
    
    # Vérifier s'il y a des enseignants
    if not enseignants.exists() and not any([search, ecole_id, type_enseignant, statut]):
        # Aucun enseignant et aucun filtre appliqué = base de données vide
        return render(request, 'salaires/empty_teachers_help.html')
    
    # Statistiques des résultats filtrés
    stats = {
        'total_enseignants': enseignants.count(),
        'enseignants_actifs': enseignants.filter(statut='ACTIF').count(),
        'taux_horaire': enseignants.filter(type_enseignant='SECONDAIRE').count(),
        'salaire_fixe': enseignants.exclude(type_enseignant='SECONDAIRE').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'enseignants': page_obj,
        'ecoles': ecoles,
        'types_enseignant': types_enseignant,
        'stats': stats,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'salaires/liste_enseignants.html', context)


@login_required
def export_enseignants_csv(request):
    """Export CSV de la liste des enseignants en respectant les filtres"""
    search = request.GET.get('search', '')
    ecole_id = request.GET.get('ecole', '')
    type_enseignant = request.GET.get('type_enseignant', '')
    statut = request.GET.get('statut', '')

    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_superadmin(request.user)
    enseignants = Enseignant.objects.select_related(
        'ecole', 'classe_principale'
    ).prefetch_related('affectations__classe')
    if restreindre:
        enseignants = enseignants.filter(ecole=ecole_user)
    if search:
        enseignants = enseignants.filter(
            Q(nom__icontains=search) |
            Q(prenoms__icontains=search) |
            Q(email__icontains=search)
        )
    if ecole_id:
        enseignants = enseignants.filter(ecole_id=ecole_id)
    if type_enseignant:
        enseignants = enseignants.filter(type_enseignant=type_enseignant)
    if statut:
        enseignants = enseignants.filter(statut=statut)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="enseignants.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Ecole', 'Nom', 'Prénoms', 'Email', 'Téléphone', 'Type', 'Statut',
        'Classe / Fonction', 'Salaire Fixe', 'Taux Horaire', 'Heures Mensuelles'
    ])

    for ens in enseignants.order_by('ecole__nom', 'nom'):
        writer.writerow([
            getattr(ens.ecole, 'nom', ''),
            ens.nom,
            ens.prenoms,
            ens.email or '',
            getattr(ens, 'telephone', ''),
            ens.type_enseignant,
            ens.statut,
            _resume_classe_ou_fonction(ens),
            ens.salaire_fixe or '',
            ens.taux_horaire or '',
            ens.heures_mensuelles or ''
        ])

    return response


@login_required
def export_enseignants_pdf(request):
    """Export PDF de la liste des enseignants en respectant les mêmes filtres que la vue liste et CSV."""
    # Filtres
    search = request.GET.get('search', '')
    ecole_id = request.GET.get('ecole', '')
    type_enseignant = request.GET.get('type_enseignant', '')
    statut = request.GET.get('statut', '')

    ecole_user = _ecole_utilisateur(request)
    palette = get_reportlab_palette(ecole_user)
    restreindre = not user_is_superadmin(request.user)
    enseignants = Enseignant.objects.select_related(
        'ecole', 'classe_principale'
    ).prefetch_related('affectations__classe')
    if restreindre:
        enseignants = enseignants.filter(ecole=ecole_user)
    if search:
        enseignants = enseignants.filter(
            Q(nom__icontains=search) |
            Q(prenoms__icontains=search) |
            Q(email__icontains=search)
        )
    if ecole_id:
        enseignants = enseignants.filter(ecole_id=ecole_id)
    if type_enseignant:
        enseignants = enseignants.filter(type_enseignant=type_enseignant)
    if statut:
        enseignants = enseignants.filter(statut=statut)

    # Préparer la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="enseignants.pdf"'

    # Document (paysage pour meilleure lisibilité)
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=60, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    styles['Title'].textColor = palette['primary']
    cell_style = ParagraphStyle(
        name='Cell',
        parent=styles['Normal'],
        fontSize=7,
        leading=8,
    )

    title_text = "Liste des enseignants"
    elements.append(Paragraph(title_text, styles['Title']))
    elements.append(Spacer(1, 0.5*cm))

    # Table avec largeurs de colonnes et wrap des textes
    data = [[
        'École', 'Nom', 'Prénoms', 'Email', 'Téléphone', 'Type', 'Statut',
        'Classe / Fonction', 'Salaire Fixe', 'Taux Horaire', 'Heures Mensuelles'
    ]]

    def P(txt):
        return Paragraph(str(txt or ''), cell_style)

    # Abréviation des noms d'écoles pour économiser l'espace
    def _abbr_ecole(nom):
        n = str(nom or '')
        low = n.lower()
        campus = ''
        if 'somayah' in low:
            campus = 'Somayah'
        elif 'sonfonia' in low:
            campus = 'Sonfonia'
        base_is_hk = (
            'hadja kanfing' in low or 'h.k' in low or 'h k' in low or 'hk' in low or 'diané' in low or 'diane' in low
        )
        if base_is_hk and campus:
            return f"H. K DIANÉ – {campus}"
        return n

    for ens in enseignants.order_by('ecole__nom', 'nom'):
        data.append([
            _abbr_ecole(getattr(ens.ecole, 'nom', '') or ''),
            P(ens.nom),
            P(ens.prenoms),
            P(ens.email or ''),
            P(getattr(ens, 'telephone', '')),
            P(ens.type_enseignant),
            P(ens.statut),
            P(_resume_classe_ou_fonction(ens)),
            f"{ens.salaire_fixe:,}".replace(',', ' ') if ens.salaire_fixe is not None else '',
            f"{ens.taux_horaire:,}".replace(',', ' ') if ens.taux_horaire is not None else '',
            f"{ens.heures_mensuelles:,}".replace(',', ' ') if ens.heures_mensuelles is not None else ''
        ])

    col_widths = [
        3.0*cm,  # École
        2.2*cm,  # Nom
        2.6*cm,  # Prénoms
        3.1*cm,  # Email
        2.2*cm,  # Téléphone
        2.1*cm,  # Type
        1.7*cm,  # Statut
        3.0*cm,  # Classe / Fonction
        2.2*cm,  # Salaire Fixe
        2.2*cm,  # Taux Horaire
        1.8*cm,  # Heures Mensuelles
    ]

    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), palette['header']),
        ('TEXTCOLOR', (0,0), (-1,0), palette['header_text']),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, palette['border']),
        # Le corps utilise ParagraphStyle(Cell) à 7pt; on maintient ici pour les cellules non-Paragraph
        ('FONTSIZE', (0,1), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    elements.append(table)

    # Logo + filigrane dynamiques par école
    def _draw_header_and_watermark(canvas, doc_):
        # Déterminer l'école courante (si l'utilisateur est restreint)
        try:
            ecole_user = _ecole_utilisateur(request)
        except Exception:
            ecole_user = None
        # Chercher logo d'école prioritaire
        school_logo_path = None
        try:
            if ecole_user and getattr(ecole_user, 'logo', None) and hasattr(ecole_user.logo, 'path') and os.path.exists(ecole_user.logo.path):
                school_logo_path = ecole_user.logo.path
        except Exception:
            school_logo_path = None
        if not school_logo_path:
            school_logo_path = os.path.join(getattr(settings, 'BASE_DIR', ''), 'static', 'logos', 'logo.png')

        # En-tête avec logo
        try:
            if school_logo_path and os.path.exists(school_logo_path):
                canvas.drawImage(school_logo_path, doc_.leftMargin, doc_.pagesize[1]-40, width=30, height=30, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
        canvas.setFont('Helvetica-Bold', 8)
        # Libellé d'école
        school_label = getattr(ecole_user, 'nom', None) or title_text
        canvas.drawString(doc_.leftMargin + 40, doc_.pagesize[1]-25, school_label)
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(doc_.pagesize[0]-doc_.rightMargin, doc_.pagesize[1]-25, title_text)

        # Filigrane avec logo (comme les autres documents), dynamique par école
        canvas.saveState()
        try:
            if school_logo_path and os.path.exists(school_logo_path):
                wm_width = doc_.pagesize[0] * 1.5
                wm_height = wm_width
                wm_x = (doc_.pagesize[0] - wm_width) / 2
                wm_y = (doc_.pagesize[1] - wm_height) / 2
                try:
                    canvas.setFillAlpha(0.15)
                except Exception:
                    pass
                canvas.translate(doc_.pagesize[0] / 2.0, doc_.pagesize[1] / 2.0)
                canvas.rotate(30)
                canvas.translate(-doc_.pagesize[0] / 2.0, -doc_.pagesize[1] / 2.0)
                canvas.drawImage(school_logo_path, wm_x, wm_y, width=wm_width, height=wm_height, preserveAspectRatio=True, mask='auto')
        finally:
            canvas.restoreState()

    doc.build(elements, onFirstPage=_draw_header_and_watermark, onLaterPages=_draw_header_and_watermark)
    return response


@login_required
@require_school_object(model=Enseignant, pk_kwarg='enseignant_id', field_path='ecole')
def detail_enseignant(request, enseignant_id):
    """Détail d'un enseignant"""
    ecole_user = _ecole_utilisateur(request)
    qs = Enseignant.objects.all()
    if not user_is_superadmin(request.user):
        qs = qs.filter(ecole=ecole_user)
    
    try:
        enseignant = get_object_or_404(qs, id=enseignant_id)
    except:
        # Si l'enseignant n'existe pas, rediriger vers la liste avec un message
        messages.error(
            request, 
            f"Aucun enseignant trouvé avec l'ID {enseignant_id}. "
            f"Voici la liste des enseignants disponibles."
        )
        return redirect('salaires:liste_enseignants')
    
    # Affectations actuelles
    affectations_actuelles = enseignant.affectations.filter(
        actif=True,
        date_debut__lte=timezone.now().date()
    ).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=timezone.now().date())
    ).select_related('classe')
    
    # Historique des affectations
    historique_affectations = enseignant.affectations.exclude(
        id__in=affectations_actuelles.values_list('id', flat=True)
    ).select_related('classe').order_by('-date_debut')
    
    # États de salaire récents
    etats_salaire = enseignant.etats_salaire.select_related(
        'periode'
    ).order_by('-periode__annee', '-periode__mois')[:12]

    avances_salaire = list(
        enseignant.avances_salaire.select_related('periode_prevue')
        .prefetch_related('remboursements')
        .order_by('-date_avance', '-id')[:10]
    )
    
    # Statistiques
    stats = {
        'total_affectations': enseignant.affectations.count(),
        'affectations_actuelles': affectations_actuelles.count(),
        'etats_salaire': enseignant.etats_salaire.count(),
        'etats_valides': enseignant.etats_salaire.filter(valide=True).count(),
    }
    
    # Calcul du salaire moyen si applicable
    if enseignant.etats_salaire.exists():
        stats['salaire_moyen'] = enseignant.etats_salaire.aggregate(
            moyenne=Avg('salaire_net')
        )['moyenne'] or 0
    else:
        stats['salaire_moyen'] = 0
    
    context = {
        'enseignant': enseignant,
        'affectations_actuelles': affectations_actuelles,
        'historique_affectations': historique_affectations,
        'etats_salaire': etats_salaire,
        'avances_salaire': avances_salaire,
        'stats': stats,
    }
    
    return render(request, 'salaires/detail_enseignant.html', context)


@login_required
@require_school_object(model=Enseignant, pk_kwarg='enseignant_id', field_path='ecole')
def ajouter_affectation(request, enseignant_id):
    """Créer une affectation de classe pour un enseignant"""
    ecole_user = _ecole_utilisateur(request)
    qs = Enseignant.objects.all()
    if not user_is_superadmin(request.user):
        qs = qs.filter(ecole=ecole_user)
    enseignant = get_object_or_404(qs, id=enseignant_id)

    if enseignant.type_enseignant != TypeEnseignant.SECONDAIRE:
        messages.info(
            request,
            "Utilisez le champ « Classe principale » pour la garderie, "
            "la maternelle et le primaire."
        )
        return redirect('salaires:modifier_enseignant', enseignant_id=enseignant.id)

    if request.method == 'POST':
        form = AffectationClasseForm(request.POST, enseignant=enseignant)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                _, salaire_recalcule = recalculer_salaire_ouvert_pour_date(
                    enseignant, timezone.localdate(), request.user
                )
            messages.success(
                request,
                'Affectation créée avec succès.'
                + (
                    ' Le salaire du mois ouvert a été recalculé.'
                    if salaire_recalcule else ''
                )
            )
            return redirect('salaires:detail_enseignant', enseignant_id=enseignant.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = AffectationClasseForm(enseignant=enseignant)

    context = {
        'enseignant': enseignant,
        'form': form,
    }
    return render(request, 'salaires/affectation_form.html', context)


@login_required
@require_school_object(model=AffectationClasse, pk_kwarg='affectation_id', field_path='enseignant__ecole')
def clore_affectation(request, affectation_id):
    """Clore (désactiver) une affectation en mettant une date de fin à aujourd'hui"""
    affectation = get_object_or_404(
        AffectationClasse.objects.select_related('enseignant__ecole'),
        id=affectation_id
    )
    ecole_user = _ecole_utilisateur(request)
    if not user_is_admin(request.user) and ecole_user is not None and affectation.enseignant.ecole_id != ecole_user.id:
        messages.error(request, "Accès refusé.")
        return redirect('salaires:detail_enseignant', enseignant_id=affectation.enseignant_id)

    if request.method == 'POST':
        affectation.actif = False
        affectation.date_fin = timezone.now().date()
        affectation.save()
        messages.success(request, 'Affectation clôturée avec succès.')
    else:
        messages.error(request, "Méthode non autorisée.")
    return redirect('salaires:detail_enseignant', enseignant_id=affectation.enseignant_id)


@login_required
@delete_permission_required()
@require_school_object(model=AffectationClasse, pk_kwarg='affectation_id', field_path='enseignant__ecole')
def supprimer_affectation(request, affectation_id):
    """Supprimer une affectation (si besoin)"""
    affectation = get_object_or_404(
        AffectationClasse.objects.select_related('enseignant__ecole'),
        id=affectation_id
    )
    ecole_user = _ecole_utilisateur(request)
    if not user_is_admin(request.user) and ecole_user is not None and affectation.enseignant.ecole_id != ecole_user.id:
        messages.error(request, "Accès refusé.")
        return redirect('salaires:detail_enseignant', enseignant_id=affectation.enseignant_id)

    if request.method == 'POST':
        enseignant_id = affectation.enseignant_id
        affectation.delete()
        messages.success(request, 'Affectation supprimée.')
        return redirect('salaires:detail_enseignant', enseignant_id=enseignant_id)
    else:
        messages.error(request, "Méthode non autorisée.")
        return redirect('salaires:detail_enseignant', enseignant_id=affectation.enseignant_id)


@login_required
def etats_salaire(request):
    """Liste des états de salaire avec filtres"""
    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_admin(request.user) and ecole_user is not None

    # Récupération des paramètres de filtrage
    periode_id = request.GET.get('periode', '')
    ecole_id = request.GET.get('ecole', '')
    enseignant_id = request.GET.get('enseignant', '')
    statut = request.GET.get('statut', '')
    search = request.GET.get('search', '')
    
    # Construction de la requête
    etats = EtatSalaire.objects.select_related('enseignant', 'periode', 'periode__ecole')
    if restreindre:
        etats = etats.filter(periode__ecole=ecole_user)
    
    if periode_id:
        etats = etats.filter(periode_id=periode_id)
    
    if ecole_id:
        etats = etats.filter(periode__ecole_id=ecole_id)
    
    if enseignant_id:
        etats = etats.filter(enseignant_id=enseignant_id)
    
    if statut == 'valide':
        etats = etats.filter(valide=True)
    elif statut == 'en_attente':
        etats = etats.filter(valide=False)
    elif statut == 'paye':
        etats = etats.filter(paye=True)
    elif statut == 'non_paye':
        etats = etats.filter(paye=False)
    
    if search:
        etats = etats.filter(
            Q(enseignant__nom__icontains=search) |
            Q(enseignant__prenoms__icontains=search)
        )
    
    # Tri par défaut
    etats = etats.order_by('-periode__annee', '-periode__mois', 'enseignant__nom')

    # Fallback intelligent: si aucun filtre n'est appliqué et que la requête est vide,
    # afficher les états des 3 dernières périodes disponibles (par école si restreint)
    filters_applied = any([periode_id, ecole_id, enseignant_id, statut, search])
    if not filters_applied and not etats.exists():
        periodes_recent = PeriodeSalaire.objects.order_by('-annee', '-mois')
        if restreindre:
            periodes_recent = periodes_recent.filter(ecole=ecole_user)
        recent_ids = list(periodes_recent.values_list('id', flat=True)[:3])
        if recent_ids:
            etats = (
                EtatSalaire.objects.select_related('enseignant', 'periode', 'periode__ecole')
                .filter(periode_id__in=recent_ids)
                .order_by('-periode__annee', '-periode__mois', 'enseignant__nom')
            )
    
    # Si toujours aucun résultat, vérifier s'il y a des périodes créées
    no_periods_exist = False
    periode_selected_exists = False
    if not etats.exists():
        periodes_count = PeriodeSalaire.objects.all()
        if restreindre:
            periodes_count = periodes_count.filter(ecole=ecole_user)
        no_periods_exist = periodes_count.count() == 0
        
        # Vérifier si une période spécifique est sélectionnée et existe
        if periode_id:
            try:
                periode_selected = PeriodeSalaire.objects.get(id=periode_id)
                if not restreindre or periode_selected.ecole == ecole_user:
                    periode_selected_exists = True
            except PeriodeSalaire.DoesNotExist:
                pass
    
    # Pagination
    paginator = Paginator(etats, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    periodes = PeriodeSalaire.objects.order_by('-annee', '-mois')
    if restreindre:
        periodes = periodes.filter(ecole=ecole_user)
    ecoles = Ecole.objects.all()
    if restreindre:
        ecoles = ecoles.filter(id=ecole_user.id)
    
    # Statistiques des résultats filtrés
    totaux = synthese_etats_salaire(etats)
    # Clés historiques conservées pour les cartes déjà présentes.
    totaux.update({
        'montant_total': totaux['total_net'],
        'en_attente': etats.filter(valide=False).count(),
        'payes': etats.filter(paye=True).count(),
    })
    
    context = {
        'page_obj': page_obj,
        'etats': page_obj,
        'periodes': periodes,
        'ecoles': ecoles,
        'totaux': totaux,
        'is_paginated': page_obj.has_other_pages(),
        'no_periods_exist': no_periods_exist,
        'periode_selected_exists': periode_selected_exists,
        # Conserver les filtres sélectionnés
        'periode_selectionnee': periode_id,
        'ecole_selectionnee': ecole_id,
        'statut_selectionne': statut,
    }
    return render(request, 'salaires/etats_salaire.html', context)

@login_required
def export_etats_salaire_csv(request):
    """Export CSV des états de salaire en respectant exactement les filtres de la vue liste."""
    # Filtres identiques à etats_salaire()
    periode_id = request.GET.get('periode', '')
    ecole_id = request.GET.get('ecole', '')
    statut = request.GET.get('statut', '')
    search = request.GET.get('search', '')

    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_admin(request.user) and ecole_user is not None
    etats = EtatSalaire.objects.select_related('enseignant', 'periode', 'periode__ecole')
    if restreindre:
        etats = etats.filter(periode__ecole=ecole_user)

    if periode_id:
        etats = etats.filter(periode_id=periode_id)
    if ecole_id:
        etats = etats.filter(periode__ecole_id=ecole_id)
    if statut == 'valide':
        etats = etats.filter(valide=True)
    elif statut == 'en_attente':
        etats = etats.filter(valide=False)
    elif statut == 'paye':
        etats = etats.filter(paye=True)
    elif statut == 'non_paye':
        etats = etats.filter(paye=False)
    if search:
        etats = etats.filter(
            Q(enseignant__nom__icontains=search) |
            Q(enseignant__prenoms__icontains=search)
        )

    etats = etats.order_by('-periode__annee', '-periode__mois', 'enseignant__nom')

    synthese = synthese_etats_salaire(etats)

    # Générer le CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="etats_salaire.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Ecole', 'Periode', 'Enseignant', 'Type', 'Valide', 'Payé',
        'Matricule', 'Salaire Base',
        *[libelle for _, libelle in EtatSalaire.RUBRIQUES_PRIMES],
        'Primes', 'Retenues', 'Avances déduites',
        'Salaire Net', 'Total Heures', 'Date Calcul'
    ])

    for e in etats:
        writer.writerow([
            getattr(e.periode.ecole, 'nom', ''),
            f"{e.periode.mois:02d}/{e.periode.annee}",
            getattr(e.enseignant, 'nom_complet', str(e.enseignant)),
            getattr(e.enseignant, 'type_enseignant', ''),
            'Oui' if e.valide else 'Non',
            'Oui' if e.paye else 'Non',
            e.enseignant.matricule,
            e.salaire_base,
            *[getattr(e, champ) for champ, _ in EtatSalaire.RUBRIQUES_PRIMES],
            e.primes,
            e.deductions,
            e.avances_deduites,
            e.salaire_net,
            e.total_heures if e.total_heures is not None else '',
            e.date_calcul.strftime('%Y-%m-%d %H:%M') if e.date_calcul else ''
        ])

    writer.writerow([
        'TOTAL CUMULÉ', '', f"{synthese['total_etats']} salaire(s)", '', '', '',
        '',
        synthese['total_salaire_base'],
        *[''] * len(EtatSalaire.RUBRIQUES_PRIMES),
        synthese['total_primes'],
        synthese['total_deductions'],
        synthese['total_avances'],
        synthese['total_net'],
        synthese['total_heures'],
        '',
    ])

    return response

@login_required
def export_etats_salaire_pdf(request):
    """Export PDF des états de salaire avec les mêmes filtres, en-tête logo et filigrane."""
    # Filtres
    periode_id = request.GET.get('periode', '')
    ecole_id = request.GET.get('ecole', '')
    statut = request.GET.get('statut', '')
    search = request.GET.get('search', '')

    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_admin(request.user) and ecole_user is not None
    etats = EtatSalaire.objects.select_related('enseignant', 'periode', 'periode__ecole')
    if restreindre:
        etats = etats.filter(periode__ecole=ecole_user)
    if periode_id:
        etats = etats.filter(periode_id=periode_id)
    if ecole_id:
        etats = etats.filter(periode__ecole_id=ecole_id)
    if statut == 'valide':
        etats = etats.filter(valide=True)
    elif statut == 'en_attente':
        etats = etats.filter(valide=False)
    elif statut == 'paye':
        etats = etats.filter(paye=True)
    elif statut == 'non_paye':
        etats = etats.filter(paye=False)
    if search:
        etats = etats.filter(
            Q(enseignant__nom__icontains=search) |
            Q(enseignant__prenoms__icontains=search)
        )

    etats = etats.order_by('-periode__annee', '-periode__mois', 'enseignant__nom')
    synthese = synthese_etats_salaire(etats)

    # Préparer la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="etats_salaire.pdf"'

    # Document (paysage pour meilleure lisibilité)
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=60, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    periode_label = ''
    periode_obj = None
    if periode_id:
        periode_obj = (
            PeriodeSalaire.objects.select_related('ecole')
            .filter(pk=periode_id)
            .first()
        )
        if periode_obj:
            periode_label = periode_obj.nom_periode
    ecole_document = periode_obj.ecole if periode_obj else ecole_user
    palette = get_reportlab_palette(ecole_document)
    styles['Title'].textColor = palette['primary']
    title_text = (
        f"État de salaire mensuel - {periode_label}"
        if periode_label else "États de salaire cumulés"
    )
    elements.append(Paragraph(title_text, styles['Title']))
    elements.append(Spacer(1, 0.5*cm))

    resume = Table(
        [[
            f"Salaires disponibles : {synthese['total_etats']}",
            f"Base : {synthese['total_salaire_base']:,.0f} GNF".replace(',', ' '),
            f"Primes : {synthese['total_primes']:,.0f} GNF".replace(',', ' '),
            f"Retenues + avances : {(synthese['total_deductions'] + synthese['total_avances']):,.0f} GNF".replace(',', ' '),
            f"TOTAL NET : {synthese['total_net']:,.0f} GNF".replace(',', ' '),
        ]],
        colWidths=[4.1*cm, 4.2*cm, 3.8*cm, 5.2*cm, 4.8*cm],
    )
    resume.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-2, 0), palette['primary_soft']),
        ('BACKGROUND', (-1, 0), (-1, 0), palette['card_success_soft']),
        ('TEXTCOLOR', (0, 0), (-1, 0), palette['text']),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOX', (0, 0), (-1, 0), 0.5, palette['border']),
        ('INNERGRID', (0, 0), (-1, 0), 0.25, palette['table']),
        ('TOPPADDING', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
    ]))
    elements.append(resume)
    elements.append(Spacer(1, 0.4*cm))

    # Table
    cellule_style = ParagraphStyle(
        'EtatSalaireCellule',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=6.4,
        leading=7.4,
        alignment=1,
        spaceAfter=0,
        spaceBefore=0,
    )
    entete_style = ParagraphStyle(
        'EtatSalaireEntete',
        parent=cellule_style,
        fontName='Helvetica-Bold',
        fontSize=6.3,
        leading=7.2,
        textColor=palette['header_text'],
    )

    def cellule(texte, style=cellule_style):
        return Paragraph(escape(str(texte)), style)

    def montant_pdf(montant):
        return f"{Decimal(montant or 0):,.0f}".replace(',', ' ')

    entetes = [
        'École', 'Période', 'Enseignant', 'Type', 'Validé', 'Payé',
        'Salaire base', 'Primes', 'Retenues', 'Avances',
        'Salaire net', 'Heures', 'Date calcul'
    ]
    data = [[cellule(texte, entete_style) for texte in entetes]]
    for e in etats:
        data.append([
            cellule(getattr(e.periode.ecole, 'nom', '')),
            cellule(f"{e.periode.mois:02d}/{e.periode.annee}"),
            cellule(getattr(e.enseignant, 'nom_complet', str(e.enseignant))),
            cellule(e.enseignant.get_type_enseignant_display()),
            cellule('Oui' if e.valide else 'Non'),
            cellule('Oui' if e.paye else 'Non'),
            cellule(montant_pdf(e.salaire_base)),
            cellule(montant_pdf(e.primes)),
            cellule(montant_pdf(e.deductions)),
            cellule(montant_pdf(e.avances_deduites)),
            cellule(montant_pdf(e.salaire_net)),
            cellule(e.total_heures if e.total_heures is not None else '-'),
            cellule(e.date_calcul.strftime('%d/%m/%Y') if e.date_calcul else '-'),
        ])

    data.append([
        cellule('TOTAL', entete_style), '',
        cellule(f"{synthese['total_etats']} salaire(s)", entete_style),
        '', '', '',
        cellule(montant_pdf(synthese['total_salaire_base']), entete_style),
        cellule(montant_pdf(synthese['total_primes']), entete_style),
        cellule(montant_pdf(synthese['total_deductions']), entete_style),
        cellule(montant_pdf(synthese['total_avances']), entete_style),
        cellule(montant_pdf(synthese['total_net']), entete_style),
        cellule(f"{synthese['total_heures']:.2f}", entete_style),
        '',
    ])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            3.4*cm, 1.35*cm, 2.7*cm, 1.9*cm, 1.05*cm, 0.95*cm,
            2.05*cm, 1.45*cm, 1.55*cm, 1.45*cm, 2.05*cm, 1.15*cm,
            1.7*cm,
        ],
        hAlign='CENTER',
    )
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), palette['header']),
        ('TEXTCOLOR', (0,0), (-1,0), palette['header_text']),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 6.3),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, palette['border']),
        ('FONTSIZE', (0,1), (-1,-1), 6.4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,-1), (-1,-1), palette['card_success_soft']),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('LINEABOVE', (0,-1), (-1,-1), 1, palette['card_success']),
    ]))
    elements.append(table)

    # Logo + filigrane dynamiques par école
    def _draw_header_and_watermark(canvas, doc_):
        # Déterminer l'école courante (si l'utilisateur est restreint)
        try:
            ecole_user = _ecole_utilisateur(request)
        except Exception:
            ecole_user = None
        # Chercher logo d'école prioritaire
        school_logo_path = None
        try:
            if ecole_document and getattr(ecole_document, 'logo', None) and hasattr(ecole_document.logo, 'path') and os.path.exists(ecole_document.logo.path):
                school_logo_path = ecole_document.logo.path
        except Exception:
            school_logo_path = None
        if not school_logo_path:
            for nom_logo in ('le-jourdain.jpg', 'logo.jpeg', 'logo.png'):
                candidat = os.path.join(
                    getattr(settings, 'BASE_DIR', ''), 'static', 'logos', nom_logo
                )
                if os.path.exists(candidat):
                    school_logo_path = candidat
                    break

        # En-tête avec logo
        try:
            if school_logo_path and os.path.exists(school_logo_path):
                canvas.drawImage(school_logo_path, doc_.leftMargin, doc_.pagesize[1]-40, width=30, height=30, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
        canvas.setFont('Helvetica-Bold', 8)
        school_label = getattr(ecole_document, 'nom', None) or title_text
        canvas.drawString(doc_.leftMargin + 40, doc_.pagesize[1]-25, school_label)
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(doc_.pagesize[0]-doc_.rightMargin, doc_.pagesize[1]-25, title_text)

        # Filigrane avec logo (comme les autres documents), dynamique par école
        canvas.saveState()
        try:
            if school_logo_path and os.path.exists(school_logo_path):
                wm_width = doc_.pagesize[0] * 1.5
                wm_height = wm_width
                wm_x = (doc_.pagesize[0] - wm_width) / 2
                wm_y = (doc_.pagesize[1] - wm_height) / 2
                try:
                    canvas.setFillAlpha(0.15)
                except Exception:
                    pass
                canvas.translate(doc_.pagesize[0] / 2.0, doc_.pagesize[1] / 2.0)
                canvas.rotate(30)
                canvas.translate(-doc_.pagesize[0] / 2.0, -doc_.pagesize[1] / 2.0)
                canvas.drawImage(school_logo_path, wm_x, wm_y, width=wm_width, height=wm_height, preserveAspectRatio=True, mask='auto')
        finally:
            canvas.restoreState()

    doc.build(elements, onFirstPage=_draw_header_and_watermark, onLaterPages=_draw_header_and_watermark)
    return response


@login_required
@require_POST
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def calculer_salaires(request, periode_id):
    """Calculer tous les salaires d'une période en une transaction atomique."""
    try:
        with transaction.atomic():
            periode = get_object_or_404(
                PeriodeSalaire.objects.select_for_update(), id=periode_id
            )
            if periode.cloturee:
                messages.error(
                    request,
                    "Impossible de calculer les salaires d'une période clôturée.",
                )
                return redirect('salaires:etats_salaire')

            calculs_effectues = 0
            enseignants = list(
                enseignants_eligibles(periode).select_for_update()
            )
            ids_eligibles = [enseignant.id for enseignant in enseignants]
            # Retirer les brouillons devenus inéligibles afin qu'un ancien état
            # ne puisse pas être validé après une démission ou une correction
            # de date d'embauche. Les états déjà validés/payés restent archivés.
            periode.etats_salaire.filter(
                valide=False,
                paye=False,
            ).exclude(enseignant_id__in=ids_eligibles).delete()

            for enseignant in enseignants:
                _, modifie = calculer_etat_salaire(
                    enseignant, periode, request.user
                )
                calculs_effectues += int(modifie)

        messages.success(
            request,
            f"Calcul des salaires terminé. {calculs_effectues} état(s) calculé(s).",
        )
    except Exception as exc:
        messages.error(
            request,
            "Aucun salaire n'a été enregistré car le calcul a échoué : "
            f"{exc}",
        )
    
    return redirect(
        f"{reverse('salaires:etats_salaire')}?periode={periode_id}"
    )


@login_required
@require_school_object(model=EtatSalaire, pk_kwarg='etat_id', field_path='periode__ecole')
def ajuster_etat_salaire(request, etat_id):
    """Modifier les éléments d'un salaire avant sa validation finale."""
    etat = get_object_or_404(
        EtatSalaire.objects.select_related('enseignant', 'periode'), id=etat_id
    )

    if etat.valide or etat.periode.cloturee:
        messages.error(
            request,
            "Un état validé ou appartenant à une période clôturée ne peut plus être ajusté.",
        )
        return redirect('salaires:etats_salaire')

    if request.method == 'POST':
        form = EtatSalaireAjustementForm(request.POST, instance=etat)
        if form.is_valid():
            with transaction.atomic():
                etat_verrouille = EtatSalaire.objects.select_for_update().get(pk=etat.pk)
                if etat_verrouille.valide or etat_verrouille.periode.cloturee:
                    messages.error(request, "Cet état ne peut plus être ajusté.")
                    return redirect('salaires:etats_salaire')

                ancien_total = arrondir_heures(etat_verrouille.total_heures)
                ancien_taux = arrondir_montant(
                    etat_verrouille.taux_horaire_applique
                )

                # Libérer d'abord les avances provisoirement imputées. Elles
                # seront rejouées après le nouveau calcul, ce qui permet aussi
                # de diminuer un salaire sans conserver une retenue devenue
                # supérieure au brut.
                etat_verrouille.remboursements_avances.all().delete()
                etat_verrouille.avances_deduites = Decimal('0')

                etat_verrouille.salaire_base = form.cleaned_data['salaire_base']
                if etat_verrouille.enseignant.est_taux_horaire:
                    nouveau_total = arrondir_heures(
                        form.cleaned_data['total_heures']
                    )
                    nouveau_taux = arrondir_montant(
                        form.cleaned_data['taux_horaire_applique']
                    )
                    etat_verrouille.total_heures = nouveau_total
                    etat_verrouille.taux_horaire_applique = nouveau_taux
                    etat_verrouille.salaire_base = arrondir_montant(
                        nouveau_total * nouveau_taux
                    )
                    if (
                        nouveau_total != ancien_total
                        or nouveau_taux != ancien_taux
                    ):
                        etat_verrouille.mode_calcul_heures = (
                            ModeCalculHoraire.MANUEL
                        )
                else:
                    etat_verrouille.total_heures = None
                    etat_verrouille.taux_horaire_applique = None
                    etat_verrouille.mode_calcul_heures = ''

                etat_verrouille.jours_presence = resume_pointage(
                    etat_verrouille.enseignant,
                    etat_verrouille.periode,
                )['jours_presence']
                etat_verrouille.heures_revision = form.cleaned_data['heures_revision']
                if request.POST.get('reappliquer_bareme'):
                    etat_verrouille.primes_ajustees = False
                    appliquer_primes_bareme(etat_verrouille)
                else:
                    for champ, _ in EtatSalaire.RUBRIQUES_PRIMES:
                        setattr(etat_verrouille, champ, form.cleaned_data[champ])
                    etat_verrouille.primes = Decimal('0')
                    etat_verrouille.primes_ajustees = True
                etat_verrouille.deductions = form.cleaned_data['deductions']
                etat_verrouille.observations = form.cleaned_data['observations']
                etat_verrouille.save()
                reconstruire_details_heures(etat_verrouille)
                synchroniser_avances_enseignant(etat_verrouille.enseignant)

            messages.success(
                request,
                f"Salaire de {etat.enseignant.nom_complet} recalculé et mis à jour.",
            )
            return redirect(
                f"{reverse('salaires:etats_salaire')}?periode={etat.periode_id}"
            )
    else:
        form = EtatSalaireAjustementForm(instance=etat)

    parametre = ParametrePaie.pour_ecole(etat.periode.ecole)
    return render(
        request,
        'salaires/ajuster_etat_salaire.html',
        {
            'form': form,
            'etat': etat,
            'parametre': parametre,
            'champs_primes': [
                form[champ] for champ, _ in EtatSalaire.RUBRIQUES_PRIMES
            ],
        },
    )


@login_required
@require_POST
@require_school_object(model=EtatSalaire, pk_kwarg='etat_id', field_path='periode__ecole')
def valider_etat_salaire(request, etat_id):
    """Valider un état de salaire"""
    with transaction.atomic():
        etat = get_object_or_404(
            EtatSalaire.objects.select_for_update().select_related(
                'enseignant', 'periode'
            ),
            id=etat_id,
        )

        if not etat.peut_etre_valide:
            messages.error(request, "Cet état de salaire ne peut pas être validé.")
            return redirect('salaires:etats_salaire')

        # Figer l'imputation exacte des avances au moment de la validation.
        synchroniser_avances_enseignant(etat.enseignant)
        etat.refresh_from_db()

        etat.valide = True
        etat.valide_par = request.user
        etat.date_validation = timezone.now()
        etat.save()

    messages.success(
        request,
        f"État de salaire de {etat.enseignant.nom_complet} validé avec succès.",
    )

    return redirect('salaires:etats_salaire')


def _avances_annotees(request):
    avances = AvanceSalaire.objects.select_related(
        'enseignant', 'enseignant__ecole', 'periode_prevue', 'cree_par'
    )
    avances = filter_by_user_school(
        avances, request.user, 'enseignant__ecole'
    )
    return avances.annotate(
        montant_rembourse_calc=Coalesce(
            Sum(
                'remboursements__montant',
                filter=Q(remboursements__etat_salaire__valide=True),
            ),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )


@login_required
def liste_avances(request):
    """Journal filtrable des avances et de leur récupération."""
    avances = _avances_annotees(request)
    search = (request.GET.get('search') or '').strip()
    enseignant_id = request.GET.get('enseignant', '')
    statut = request.GET.get('statut', '')

    if search:
        avances = avances.filter(
            Q(enseignant__nom__icontains=search)
            | Q(enseignant__prenoms__icontains=search)
            | Q(reference_externe__icontains=search)
            | Q(motif__icontains=search)
        )
    if enseignant_id:
        avances = avances.filter(enseignant_id=enseignant_id)
    if statut == 'soldee':
        avances = avances.filter(montant__lte=F('montant_rembourse_calc'))
    elif statut == 'en_cours':
        avances = avances.filter(montant__gt=F('montant_rembourse_calc'))

    avances = list(avances.order_by('-date_avance', '-id'))
    synthese = {
        'total': sum((avance.montant for avance in avances), Decimal('0')),
        'rembourse': sum(
            (avance.montant_rembourse_calc for avance in avances), Decimal('0')
        ),
    }
    synthese['reste'] = max(
        synthese['total'] - synthese['rembourse'], Decimal('0')
    )
    synthese['nombre'] = len(avances)

    paginator = Paginator(avances, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    for avance in page_obj:
        avance.solde_calcule = max(
            avance.montant - avance.montant_rembourse_calc, Decimal('0')
        )

    enseignants = filter_by_user_school(
        Enseignant.objects.filter(statut='ACTIF'), request.user
    )

    return render(request, 'salaires/avances_liste.html', {
        'page_obj': page_obj,
        'synthese': synthese,
        'enseignants': enseignants.order_by('nom', 'prenoms'),
        'statut_selectionne': statut,
        'enseignant_selectionne': enseignant_id,
        'search': search,
    })


@login_required
def ajouter_avance(request):
    ecole_user = _ecole_utilisateur(request)
    enseignant = None
    enseignant_id = request.GET.get('enseignant') or request.POST.get('enseignant_cible')
    if enseignant_id:
        qs = Enseignant.objects.all()
        if not user_is_admin(request.user) and ecole_user is not None:
            qs = qs.filter(ecole=ecole_user)
        enseignant = get_object_or_404(qs, pk=enseignant_id)

    if request.method == 'POST':
        form = AvanceSalaireForm(
            request.POST, ecole=ecole_user, enseignant=enseignant
        )
        if form.is_valid():
            with transaction.atomic():
                avance = form.save(commit=False)
                avance.cree_par = request.user
                avance.save()
                synchroniser_avances_enseignant(avance.enseignant)
            messages.success(
                request,
                (
                    f"Avance de {avance.montant:,.0f} GNF enregistrée pour "
                    f"{avance.enseignant.nom_complet}."
                ).replace(',', ' '),
            )
            return redirect('salaires:liste_avances')
    else:
        form = AvanceSalaireForm(ecole=ecole_user, enseignant=enseignant)
        form.fields['date_avance'].initial = timezone.localdate()

    return render(request, 'salaires/avance_form.html', {
        'form': form,
        'titre': 'Enregistrer une avance sur salaire',
        'enseignant_cible': enseignant,
    })


@login_required
@require_school_object(model=AvanceSalaire, pk_kwarg='avance_id', field_path='enseignant__ecole')
def modifier_avance(request, avance_id):
    avance = get_object_or_404(
        AvanceSalaire.objects.select_related('enseignant', 'periode_prevue'),
        pk=avance_id,
    )
    if not avance.est_modifiable:
        messages.error(
            request,
            "Cette avance a déjà été retenue sur un salaire validé et ne peut plus être modifiée.",
        )
        return redirect('salaires:liste_avances')

    if request.method == 'POST':
        form = AvanceSalaireForm(
            request.POST, instance=avance, enseignant=avance.enseignant
        )
        if form.is_valid():
            with transaction.atomic():
                avance_verrouille = AvanceSalaire.objects.select_for_update().get(pk=avance.pk)
                if not avance_verrouille.est_modifiable:
                    messages.error(request, "Cette avance vient d'être figée par une paie validée.")
                    return redirect('salaires:liste_avances')
                avance = form.save()
                synchroniser_avances_enseignant(avance.enseignant)
            messages.success(request, "Avance mise à jour et salaires recalculés.")
            return redirect('salaires:liste_avances')
    else:
        form = AvanceSalaireForm(instance=avance, enseignant=avance.enseignant)

    return render(request, 'salaires/avance_form.html', {
        'form': form,
        'titre': "Modifier l'avance sur salaire",
        'avance': avance,
        'enseignant_cible': avance.enseignant,
    })


@login_required
@require_POST
@require_school_object(model=AvanceSalaire, pk_kwarg='avance_id', field_path='enseignant__ecole')
def supprimer_avance(request, avance_id):
    with transaction.atomic():
        avance = get_object_or_404(
            AvanceSalaire.objects.select_for_update().select_related('enseignant'),
            pk=avance_id,
        )
        if not avance.est_modifiable:
            messages.error(
                request,
                "Suppression impossible : cette avance figure déjà sur un salaire validé.",
            )
            return redirect('salaires:liste_avances')
        enseignant = avance.enseignant
        avance.delete()
        synchroniser_avances_enseignant(enseignant)

    messages.success(request, "Avance supprimée et salaires recalculés.")
    return redirect('salaires:liste_avances')


@login_required
@require_POST
@require_school_object(model=EtatSalaire, pk_kwarg='etat_id', field_path='periode__ecole')
def marquer_paye(request, etat_id):
    """Marquer un état de salaire comme payé"""

    with transaction.atomic():
        etat = get_object_or_404(
            EtatSalaire.objects.select_for_update().select_related(
                'enseignant', 'periode'
            ),
            id=etat_id,
        )

        if not etat.peut_etre_paye:
            messages.error(request, "Cet état de salaire ne peut pas être marqué comme payé.")
            return redirect('salaires:etats_salaire')

        etat.paye = True
        etat.date_paiement = timezone.now()
        etat.save()

    messages.success(
        request,
        f"État de salaire de {etat.enseignant.nom_complet} marqué comme payé.",
    )

    return redirect('salaires:etats_salaire')


@login_required
def gestion_periodes(request):
    """Gestion des périodes de salaire"""
    
    # Récupération des paramètres de filtrage
    ecole_id = request.GET.get('ecole', '')
    annee = request.GET.get('annee', '')
    statut = request.GET.get('statut', '')  # 'cloture' | 'ouvert' | ''
    
    # Construction de la requête
    periodes = (
        PeriodeSalaire.objects.select_related('ecole')
        .annotate(
            nombre_etats=Count('etats_salaire', distinct=True),
            etats_valides=Count(
                'etats_salaire',
                filter=Q(etats_salaire__valide=True),
                distinct=True,
            ),
            etats_payes=Count(
                'etats_salaire',
                filter=Q(etats_salaire__paye=True),
                distinct=True,
            ),
            total_salaire_base=Coalesce(
                Sum('etats_salaire__salaire_base'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_primes=Coalesce(
                Sum('etats_salaire__primes'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_retenues=Coalesce(
                Sum('etats_salaire__deductions'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_avances=Coalesce(
                Sum('etats_salaire__avances_deduites'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            total_net=Coalesce(
                Sum('etats_salaire__salaire_net'),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
    )

    # Restriction par école pour les non-admins
    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_admin(request.user) and ecole_user is not None
    if restreindre:
        periodes = periodes.filter(ecole=ecole_user)
    
    if ecole_id:
        periodes = periodes.filter(ecole_id=ecole_id)
    
    if annee:
        periodes = periodes.filter(annee=annee)
    
    # Filtre statut ouvert/clôturé
    if statut == 'cloture':
        periodes = periodes.filter(cloturee=True)
    elif statut == 'ouvert':
        periodes = periodes.filter(cloturee=False)
    
    periodes = periodes.order_by('-annee', '-mois')

    # Fallback: si aucun filtre n'est appliqué et aucune période trouvée,
    # charger les 6 dernières périodes disponibles (restreintes à l'école de l'utilisateur si nécessaire)
    filtres_appliques = any([ecole_id, annee, statut])
    if not filtres_appliques and not periodes.exists():
        fallback_base = PeriodeSalaire.objects.select_related('ecole')
        if restreindre:
            fallback_base = fallback_base.filter(ecole=ecole_user)
        fallback_ids = list(
            fallback_base.order_by('-annee', '-mois').values_list('id', flat=True)[:6]
        )
        periodes = periodes.filter(id__in=fallback_ids).order_by('-annee', '-mois')
    
    # Pagination
    paginator = Paginator(periodes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    ecoles = Ecole.objects.all()
    if restreindre and ecole_user:
        ecoles = ecoles.filter(id=ecole_user.id)
    annees_disponibles = PeriodeSalaire.objects.values_list('annee', flat=True).distinct().order_by('-annee')
    
    # Statistiques
    # Utiliser une requête de base non-slicée pour les stats globales si besoin
    base_stats_qs = PeriodeSalaire.objects.all()
    if restreindre and ecole_user:
        base_stats_qs = base_stats_qs.filter(ecole=ecole_user)
    if ecole_id:
        base_stats_qs = base_stats_qs.filter(ecole_id=ecole_id)
    if annee:
        base_stats_qs = base_stats_qs.filter(annee=annee)
    if statut == 'cloture':
        base_stats_qs = base_stats_qs.filter(cloturee=True)
    elif statut == 'ouvert':
        base_stats_qs = base_stats_qs.filter(cloturee=False)

    total_etats = EtatSalaire.objects.filter(periode__in=base_stats_qs).count()
    
    stats = {
        'total_periodes': base_stats_qs.count(),
        'periodes_ouvertes': base_stats_qs.filter(cloturee=False).count(),
        'periodes_cloturees': base_stats_qs.filter(cloturee=True).count(),
        'etats_calcules': total_etats,
    }
    
    # Période courante (première ouverte la plus récente) pour styling
    try:
        periode_courante = (
            PeriodeSalaire.objects.filter(cloturee=False, **({'ecole': ecole_user} if restreindre else {}))
            .order_by('-annee', '-mois')
            .first()
        )
    except Exception:
        periode_courante = None

    context = {
        'page_obj': page_obj,
        'periodes': page_obj,
        'ecoles': ecoles,
        'annees_disponibles': annees_disponibles,
        'stats': stats,
        'periode_courante': periode_courante,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'salaires/gestion_periodes.html', context)


@login_required
def rapport_paiements(request):
    """Rapport des salaires payés: totaux par mois et par année, avec filtres."""
    ecole_user = _ecole_utilisateur(request)
    restreindre = not user_is_admin(request.user) and ecole_user is not None

    annee = request.GET.get('annee', '')
    ecole_id = request.GET.get('ecole', '')

    qs = EtatSalaire.objects.filter(paye=True).select_related('periode', 'periode__ecole')
    if restreindre:
        qs = qs.filter(periode__ecole=ecole_user)
    if annee:
        qs = qs.filter(periode__annee=annee)
    if ecole_id:
        qs = qs.filter(periode__ecole_id=ecole_id)

    # Agrégation par année/mois de la période de salaire
    aggs = (
        qs.values('periode__annee', 'periode__mois')
          .annotate(total_paye=Sum('salaire_net'), nombre=Count('id'))
          .order_by('-periode__annee', '-periode__mois')
    )

    # Totaux globaux
    total_annuel = qs.aggregate(total=Sum('salaire_net'))['total'] or 0

    # Filtres disponibles
    annees_dispo_qs = PeriodeSalaire.objects.all()
    if restreindre:
        annees_dispo_qs = annees_dispo_qs.filter(ecole=ecole_user)
    annees_dispo = (annees_dispo_qs
                    .order_by('-annee')
                    .values_list('annee', flat=True)
                    .distinct())
    ecoles = Ecole.objects.all()
    if restreindre and ecole_user:
        ecoles = ecoles.filter(id=ecole_user.id)

    context = {
        'aggs': aggs,
        'total_annuel': total_annuel,
        'annees_dispo': annees_dispo,
        'ecoles': ecoles,
        'annee_selectionnee': annee,
        'ecole_selectionnee': ecole_id,
    }
    return render(request, 'salaires/rapport_paiements.html', context)


@login_required
def export_rapport_paiements_pdf(request):
    """Export PDF du rapport des salaires payés (paysage)."""
    ecole_user = _ecole_utilisateur(request)
    palette = get_reportlab_palette(ecole_user)
    restreindre = not user_is_admin(request.user) and ecole_user is not None

    annee = request.GET.get('annee', '')
    ecole_id = request.GET.get('ecole', '')

    qs = EtatSalaire.objects.filter(paye=True).select_related('periode', 'periode__ecole')
    if restreindre:
        qs = qs.filter(periode__ecole=ecole_user)
    if annee:
        qs = qs.filter(periode__annee=annee)
    if ecole_id:
        qs = qs.filter(periode__ecole_id=ecole_id)

    aggs = (
        qs.values('periode__annee', 'periode__mois')
          .annotate(total_paye=Sum('salaire_net'), nombre=Count('id'))
          .order_by('periode__annee', 'periode__mois')
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_paiements.pdf"'

    # Créer un template avec filigrane
    class WatermarkDocTemplate(SimpleDocTemplate):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        def afterPage(self):
            c = self.canv
            try:
                from ecole_moderne.pdf_utils import draw_logo_watermark
                from utilisateurs.utils import user_school
                draw_logo_watermark(c, self.pagesize[0], self.pagesize[1], ecole=user_school(getattr(self, 'request_user', None) or getattr(doc, 'request_user', None) or None))
            except Exception:
                pass
    
    doc = WatermarkDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=60, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    styles['Title'].textColor = palette['primary']
    
    # Ajouter le logo en en-tête
    try:
        from django.contrib.staticfiles import finders
        logo_path = finders.find('logos/logo.png')
        if logo_path:
            from reportlab.platypus import Image
            logo = Image(logo_path, width=60, height=60)
            elements.append(logo)
            elements.append(Spacer(1, 10))
    except Exception:
        pass

    titre = "Rapport des salaires payés"
    if annee:
        titre += f" - {annee}"
    elements.append(Paragraph(titre, styles['Title']))
    elements.append(Spacer(1, 0.5*cm))

    data = [['Année', 'Mois', 'Total payé (GNF)', 'Nombre d\'états payés']]
    for row in aggs:
        data.append([
            row['periode__annee'],
            f"{row['periode__mois']:02d}",
            f"{row['total_paye']:,}".replace(',', ' '),
            row['nombre'],
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), palette['header']),
        ('TEXTCOLOR', (0,0), (-1,0), palette['header_text']),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.25, palette['border']),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(table)

    logo_path = os.path.join(getattr(settings, 'BASE_DIR', ''), 'static', 'logos', 'logo.png')

    def _draw_header_and_watermark(canvas, doc_):
        try:
            if os.path.exists(logo_path):
                canvas.drawImage(logo_path, doc_.leftMargin, doc_.pagesize[1]-40, width=30, height=30, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
        canvas.setFont('Helvetica-Bold', 8)
        canvas.drawString(doc_.leftMargin + 40, doc_.pagesize[1]-25, 'myschool')
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(doc_.pagesize[0]-doc_.rightMargin, doc_.pagesize[1]-25, titre)

        # Filigrane avec logo (comme les autres documents)
        canvas.saveState()
        try:
            if os.path.exists(logo_path):
                # Taille ~150% de la largeur de page
                wm_width = doc_.pagesize[0] * 1.5
                wm_height = wm_width
                wm_x = (doc_.pagesize[0] - wm_width) / 2
                wm_y = (doc_.pagesize[1] - wm_height) / 2
                
                # Opacité visible mais discrète
                try:
                    canvas.setFillAlpha(0.15)
                except Exception:
                    pass
                
                # Rotation pour l'effet filigrane
                canvas.translate(doc_.pagesize[0] / 2.0, doc_.pagesize[1] / 2.0)
                canvas.rotate(30)
                canvas.translate(-doc_.pagesize[0] / 2.0, -doc_.pagesize[1] / 2.0)
                
                canvas.drawImage(logo_path, wm_x, wm_y, width=wm_width, height=wm_height, preserveAspectRatio=True, mask='auto')
            else:
                # Fallback vers texte si logo non trouvé
                canvas.setFont('Helvetica-Bold', 42)
                canvas.setFillGray(0.85)
                canvas.translate(doc_.pagesize[0]/2, doc_.pagesize[1]/2)
                canvas.rotate(30)
                canvas.drawCentredString(0, 0, 'H.K. DIANÉ')
        finally:
            canvas.restoreState()

    doc.build(elements, onFirstPage=_draw_header_and_watermark, onLaterPages=_draw_header_and_watermark)
    return response


@login_required
def creer_periode(request):
    """Création d'une nouvelle période de salaire"""
    if request.method == 'POST':
        try:
            mois = int(request.POST.get('mois'))
            annee = int(request.POST.get('annee'))
            ecole_id = int(request.POST.get('ecole'))
            nombre_semaines = Decimal(request.POST.get('nombre_semaines', '4.33'))
            
            # Validation des données
            if not (1 <= mois <= 12):
                messages.error(request, "Le mois doit être entre 1 et 12.")
                return redirect('salaires:gestion_periodes')
            
            if annee < 2020 or annee > 2030:
                messages.error(request, "L'année doit être entre 2020 et 2030.")
                return redirect('salaires:gestion_periodes')

            if not nombre_semaines.is_finite() or not (
                Decimal('0') < nombre_semaines <= Decimal('6')
            ):
                messages.error(
                    request,
                    "Le nombre de semaines doit être supérieur à 0 et inférieur ou égal à 6.",
                )
                return redirect('salaires:gestion_periodes')
            
            # Récupérer l'école
            from eleves.models import Ecole
            ecole = get_object_or_404(Ecole, id=ecole_id)
            
            # Vérifier que l'utilisateur a le droit de créer une période pour cette école
            ecole_user = _ecole_utilisateur(request)
            if not user_is_admin(request.user) and ecole_user is not None and ecole.id != ecole_user.id:
                messages.error(request, "Vous n'avez pas le droit de créer une période pour cette école.")
                return redirect('salaires:gestion_periodes')
            
            # Vérifier si la période existe déjà
            periode_existante = PeriodeSalaire.objects.filter(
                mois=mois,
                annee=annee,
                ecole=ecole
            ).exists()
            
            if periode_existante:
                messages.error(
                    request, 
                    f"Une période pour {mois}/{annee} existe déjà pour {ecole.nom}."
                )
                return redirect('salaires:gestion_periodes')
            
            # La période et les états groupés sont créés ensemble : en cas
            # d'erreur de calcul, aucune période partielle n'est conservée.
            with transaction.atomic():
                nouvelle_periode = PeriodeSalaire.objects.create(
                    mois=mois,
                    annee=annee,
                    ecole=ecole,
                    nombre_semaines=nombre_semaines,
                    cree_par=request.user
                )
                etats_initialises = initialiser_etats_salaire_periode(
                    nouvelle_periode, request.user
                )
            
            messages.success(
                request,
                f"Période {nouvelle_periode} créée avec succès : "
                f"{len(etats_initialises)} salaire(s) récupéré(s), pour un total de "
                f"{sum((etat.salaire_net for etat in etats_initialises), Decimal('0')):,.0f} GNF."
            )
            return redirect(
                f"{reverse('salaires:etats_salaire')}?periode={nouvelle_periode.id}"
            )
            
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Données invalides. Veuillez vérifier les champs.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la création : {str(e)}")
    
    return redirect('salaires:gestion_periodes')


@login_required
def cloturer_periode(request, periode_id):
    """Clôture d'une période de salaire et crée automatiquement la période suivante"""
    if request.method == 'POST':
        try:
            periode = get_object_or_404(PeriodeSalaire, id=periode_id)
            
            # Vérifier que l'utilisateur a le droit de clôturer cette période
            ecole_user = _ecole_utilisateur(request)
            if not user_is_admin(request.user) and ecole_user is not None and periode.ecole_id != ecole_user.id:
                messages.error(request, "Vous n'avez pas le droit de clôturer cette période.")
                return redirect('salaires:gestion_periodes')
            
            # Vérifier que la période n'est pas déjà clôturée
            if periode.cloturee:
                messages.warning(request, f"La période {periode} est déjà clôturée.")
                return redirect('salaires:gestion_periodes')
            
            # Clôturer la période actuelle
            periode.cloturee = True
            periode.date_cloture = timezone.now()
            periode.cloturee_par = request.user
            periode.save()
            
            # Calculer le mois et l'année suivants
            mois_suivant = periode.mois + 1
            annee_suivante = periode.annee
            
            if mois_suivant > 12:
                mois_suivant = 1
                annee_suivante += 1
            
            # Vérifier si la période suivante existe déjà
            periode_suivante_existe = PeriodeSalaire.objects.filter(
                mois=mois_suivant,
                annee=annee_suivante,
                ecole=periode.ecole
            ).exists()
            
            if not periode_suivante_existe:
                # Créer automatiquement la période suivante et son état
                # mensuel complet pour tous les enseignants actifs.
                with transaction.atomic():
                    nouvelle_periode = PeriodeSalaire.objects.create(
                        mois=mois_suivant,
                        annee=annee_suivante,
                        ecole=periode.ecole,
                        nombre_semaines=periode.nombre_semaines,
                        cree_par=request.user
                    )
                    etats_initialises = initialiser_etats_salaire_periode(
                        nouvelle_periode, request.user
                    )
                
                messages.success(
                    request, 
                    f"Période {periode} clôturée avec succès ! "
                    f"Nouvelle période créée automatiquement : {nouvelle_periode} "
                    f"avec {len(etats_initialises)} état(s) regroupé(s)."
                )
            else:
                messages.success(
                    request, 
                    f"Période {periode} clôturée avec succès ! "
                    f"La période suivante existe déjà."
                )
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la clôture : {str(e)}")
    
    return redirect('salaires:gestion_periodes')


@login_required
@require_school_object(model=Enseignant, pk_kwarg='enseignant_id', field_path='ecole')
def changer_statut_enseignant(request, enseignant_id):
    """Changement de statut d'un enseignant"""
    ecole_user = _ecole_utilisateur(request)
    qs = Enseignant.objects.all()
    if not user_is_superadmin(request.user):
        qs = qs.filter(ecole=ecole_user)
    enseignant = get_object_or_404(qs, id=enseignant_id)
    
    if request.method == 'POST':
        nouveau_statut = request.POST.get('nouveau_statut')
        
        if nouveau_statut in ['ACTIF', 'CONGE', 'SUSPENDU', 'DEMISSIONNAIRE']:
            ancien_statut = enseignant.get_statut_display()
            enseignant.statut = nouveau_statut
            enseignant.save()
            
            nouveau_statut_display = enseignant.get_statut_display()
            messages.success(
                request, 
                f"Le statut de {enseignant.nom_complet} a été changé de '{ancien_statut}' à '{nouveau_statut_display}' avec succès !"
            )
        else:
            messages.error(request, "Statut invalide.")
    else:
        messages.info(request, "Méthode non autorisée pour cette action.")
    
    return redirect('salaires:liste_enseignants')


@login_required
@can_add_teachers
def ajouter_enseignant(request):
    """Ajouter un nouvel enseignant"""
    if request.method == 'POST':
        form = EnseignantForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                enseignant = form.save(commit=False)
                enseignant.cree_par = request.user
                enseignant.save()
                _clore_affectations_secondaires_si_necessaire(enseignant)
                _, salaire_recalcule = recalculer_salaire_ouvert_pour_date(
                    enseignant, timezone.localdate(), request.user
                )
            
            messages.success(
                request, 
                f"L'enseignant {enseignant.nom_complet} a été ajouté avec succès !"
                + (
                    " Son salaire du mois ouvert a été calculé."
                    if salaire_recalcule
                    else ""
                )
            )
            if enseignant.type_enseignant == TypeEnseignant.SECONDAIRE:
                messages.info(
                    request,
                    "Ajoutez maintenant sa première affectation de classe, "
                    "la matière et les heures hebdomadaires."
                )
                return redirect(
                    'salaires:ajouter_affectation', enseignant_id=enseignant.id
                )
            return redirect('salaires:detail_enseignant', enseignant_id=enseignant.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = EnseignantForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Ajouter un Enseignant',
        'submit_text': 'Créer l\'Enseignant',
        'champs_paie': _champs_paie(form),
    }

    return render(request, 'salaires/ajouter_enseignant.html', context)


@login_required
def modifier_enseignant(request, enseignant_id):
    """Modifier un enseignant existant"""
    ecole_user = _ecole_utilisateur(request)
    qs = Enseignant.objects.all()
    if not user_is_superadmin(request.user):
        qs = qs.filter(ecole=ecole_user)
    enseignant = get_object_or_404(qs, id=enseignant_id)
    
    if request.method == 'POST':
        form = EnseignantForm(request.POST, request.FILES, instance=enseignant, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                enseignant = form.save()
                _clore_affectations_secondaires_si_necessaire(enseignant)
                _, salaire_recalcule = recalculer_salaire_ouvert_pour_date(
                    enseignant, timezone.localdate(), request.user
                )
            messages.success(
                request, 
                f"L'enseignant {enseignant.nom_complet} a été modifié avec succès !"
                + (
                    " Son salaire du mois ouvert a été recalculé."
                    if salaire_recalcule
                    else ""
                )
            )
            return redirect('salaires:detail_enseignant', enseignant_id=enseignant.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = EnseignantForm(instance=enseignant, user=request.user)
    
    context = {
        'form': form,
        'enseignant': enseignant,
        'title': f'Modifier {enseignant.nom_complet}',
        'submit_text': 'Enregistrer les Modifications',
        'champs_paie': _champs_paie(form),
    }
    
    return render(request, 'salaires/ajouter_enseignant.html', context)


@login_required
def supprimer_enseignant(request, enseignant_id):
    """Vue pour supprimer un enseignant avec ses états de salaire (avec code de vérification)"""
    # Filtrer selon les permissions
    qs = Enseignant.objects.all()
    if not user_is_admin(request.user):
        qs = qs.filter(ecole=user_school(request.user))
    
    try:
        enseignant = qs.get(id=enseignant_id)
    except Enseignant.DoesNotExist:
        messages.error(request, f"L'enseignant avec l'ID {enseignant_id} n'existe pas ou a déjà été supprimé.")
        return redirect('salaires:liste_enseignants')
    
    nom_complet = enseignant.nom_complet
    
    # Vérifier la permission de suppression définitive
    peut_supprimer_definitivement = user_is_admin(request.user) or (
        hasattr(request.user, 'profil') and 
        request.user.profil.peut_supprimer_enseignants_definitivement
    )
    
    # Compter les éléments associés
    etats_salaire_count = enseignant.etats_salaire.count()
    affectations_count = enseignant.affectations.count()
    presences_count = enseignant.presences.count()
    
    if request.method == 'POST':
        # Vérifier le code de sécurité
        code_verification = request.POST.get('code_verification', '').strip()
        suppression_definitive = request.POST.get('suppression_definitive') == 'on'
        
        # Pour les admins, toujours activer la suppression définitive par défaut
        if user_is_admin(request.user):
            suppression_definitive = request.POST.get('suppression_definitive') != 'off'
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Admin {request.user.username} - Suppression définitive enseignant: {suppression_definitive}")
        
        from django.conf import settings as django_settings
        expected_code = django_settings.SECURITY_VERIFICATION_CODE
        if not expected_code or code_verification != expected_code:
            messages.error(request, "Code de vérification incorrect. Suppression annulée.")
            return render(request, 'salaires/confirmer_suppression_enseignant.html', {
                'enseignant': enseignant,
                'etats_salaire_count': etats_salaire_count,
                'affectations_count': affectations_count,
                'presences_count': presences_count,
                'peut_supprimer_definitivement': peut_supprimer_definitivement,
                'titre_page': f'Supprimer {nom_complet}'
            })
        
        # Vérifier la permission pour suppression définitive
        if suppression_definitive and not peut_supprimer_definitivement:
            messages.error(request, "Vous n'avez pas la permission de supprimer définitivement un enseignant.")
            return redirect('salaires:detail_enseignant', enseignant_id=enseignant.id)
        
        # Procéder à la suppression avec le code correct
        from django.db import transaction
        try:
            with transaction.atomic():
                if suppression_definitive and peut_supprimer_definitivement:
                    # Suppression définitive pour les utilisateurs autorisés
                    # Collecter les informations avant suppression
                    etats_supprimes = []
                    for etat in enseignant.etats_salaire.all():
                        etats_supprimes.append(f"{etat.periode.nom_periode} - {etat.salaire_net} GNF")
                    
                    affectations_supprimees = []
                    for affectation in enseignant.affectations.all():
                        affectations_supprimees.append(f"{affectation.classe.nom} - {affectation.matiere or 'Toutes matières'}")
                    
                    # Créer l'entrée dans la corbeille avant suppression
                    from administration.models import SystemLog
                    SystemLog.objects.create(
                        action='SUPPRESSION_DEFINITIVE_ENSEIGNANT',
                        description=f"Suppression définitive de l'enseignant {nom_complet} avec {etats_salaire_count} état(s) de salaire, {affectations_count} affectation(s) et {presences_count} présence(s)",
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                        details={
                            'enseignant_id': enseignant.id,
                            'nom_complet': nom_complet,
                            'ecole': enseignant.ecole.nom,
                            'type_enseignant': enseignant.type_enseignant,
                            'salaire_fixe': str(enseignant.salaire_fixe) if enseignant.salaire_fixe else None,
                            'taux_horaire': str(enseignant.taux_horaire) if enseignant.taux_horaire else None,
                            'etats_supprimes': etats_supprimes,
                            'affectations_supprimees': affectations_supprimees,
                            'verification_code_used': True,
                            'user_agent': request.META.get('HTTP_USER_AGENT', '')
                        }
                    )
                    
                    # Supprimer les états de salaire
                    enseignant.etats_salaire.all().delete()
                    
                    # Supprimer les affectations
                    enseignant.affectations.all().delete()
                    
                    # Supprimer les présences
                    enseignant.presences.all().delete()
                    
                    # Supprimer l'enseignant définitivement
                    enseignant.delete()
                    
                    total_elements = etats_salaire_count + affectations_count + presences_count
                    messages.success(request, f"L'enseignant {nom_complet} et tous ses éléments associés ({total_elements} au total) ont été supprimés définitivement et sauvegardés dans la corbeille.")
                else:
                    # Soft delete - changer le statut au lieu de supprimer
                    enseignant.statut = 'DEMISSIONNAIRE'
                    enseignant.save()
                    
                    # Log de l'activité
                    from utilisateurs.models import JournalActivite
                    JournalActivite.objects.create(
                        user=request.user,
                        action='DESACTIVATION',
                        type_objet='ENSEIGNANT',
                        objet_id=enseignant.id,
                        description=f"Désactivation de l'enseignant {nom_complet} (statut → Démissionnaire)",
                        adresse_ip=request.META.get('REMOTE_ADDR', ''),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
                    messages.success(request, f"L'enseignant {nom_complet} a été marqué comme démissionnaire (soft delete).")
                    
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {e}")
            return redirect('salaires:detail_enseignant', enseignant_id=enseignant.id)
        
        return redirect('salaires:liste_enseignants')
    
    # Afficher le formulaire de confirmation
    return render(request, 'salaires/confirmer_suppression_enseignant.html', {
        'enseignant': enseignant,
        'etats_salaire_count': etats_salaire_count,
        'affectations_count': affectations_count,
        'presences_count': presences_count,
        'peut_supprimer_definitivement': peut_supprimer_definitivement,
        'titre_page': f'Supprimer {nom_complet}'
    })
