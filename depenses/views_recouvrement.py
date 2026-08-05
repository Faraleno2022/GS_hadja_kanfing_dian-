"""Vues des nouveaux modules du menu Recouvrement (ex-Dépenses) :
Cuisine, Document, Versement et Informatique (abonnements élèves).

Les modules Cuisine / Document / Versement partagent la même forme
(date automatique, un champ principal, montant, observation) : ils sont
donc pilotés par un petit tableau de configuration (MODULES_SIMPLES) au
lieu de dupliquer 3 fois les mêmes vues CRUD/dashboard/export.
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from eleves.models import Eleve
from ecole_moderne.security_decorators import require_school_object
from utilisateurs.permissions import can_add_expenses, can_modify_expenses, can_delete_expenses, can_delete_subscriptions
from utilisateurs.utils import user_is_superadmin, user_school, filter_by_user_school

from .models_recouvrement import (
    DepenseCuisine, DepenseDocument, Versement, AbonnementInformatique
)
from .forms import (
    DepenseCuisineForm, DepenseDocumentForm, VersementForm, AbonnementInformatiqueForm
)


# =====================================================================
# Tableau de bord général du menu Recouvrement (vue d'ensemble en cartes)
# =====================================================================

@login_required
def tableau_bord_general(request):
    """Vue d'ensemble générale du menu Recouvrement : une carte par sous-module,
    plus des totaux agrégés en haut de page."""
    from .models import Depense
    from .models_logistique import Article, BienEtablissement
    from .models_bibliotheque import Livre, Emprunt

    user = request.user
    ecole = None if user_is_superadmin(user) else user_school(user)

    def _depenses_qs():
        qs = Depense.objects.all()
        if not user_is_superadmin(user):
            qs = qs.none() if ecole is None else qs.filter(cree_par__profil__ecole=ecole)
        return qs

    depenses_qs = _depenses_qs()
    cuisine_qs = _base_qs_module('cuisine', user)
    document_qs = _base_qs_module('document', user)
    versement_qs = _base_qs_module('versement', user)

    informatique_qs = AbonnementInformatique.objects.all()
    if not user_is_superadmin(user):
        informatique_qs = filter_by_user_school(informatique_qs, user, 'eleve__classe__ecole')

    logistique_qs = BienEtablissement.objects.filter(actif=True)
    if not user_is_superadmin(user):
        logistique_qs = logistique_qs.none() if ecole is None else logistique_qs.filter(cree_par__profil__ecole=ecole)

    bibliotheque_qs = Livre.objects.all()
    if not user_is_superadmin(user):
        bibliotheque_qs = bibliotheque_qs.none() if ecole is None else bibliotheque_qs.filter(cree_par__profil__ecole=ecole)

    montant_total_general = (
        (depenses_qs.aggregate(t=Sum('montant_ttc'))['t'] or Decimal('0')) +
        (cuisine_qs.aggregate(t=Sum('montant'))['t'] or Decimal('0')) +
        (document_qs.aggregate(t=Sum('montant'))['t'] or Decimal('0')) +
        (versement_qs.aggregate(t=Sum('montant'))['t'] or Decimal('0'))
    )

    cartes = [
        {
            'titre': 'Dépenses courantes', 'icone': 'fa-receipt', 'couleur': 'primary',
            'description': 'Factures, fournisseurs, catégories et budgets.',
            'href': reverse('depenses:dashboard_courantes'),
            'total': depenses_qs.count(),
            'montant': depenses_qs.aggregate(t=Sum('montant_ttc'))['t'] or Decimal('0'),
        },
        {
            'titre': 'Logistique & Fournitures', 'icone': 'fa-boxes', 'couleur': 'info',
            'description': 'Biens, stock et vente de fournitures scolaires.',
            'href': reverse('depenses:dashboard_logistique'),
            'total': logistique_qs.count(),
            'montant': None,
        },
        {
            'titre': 'Bibliothèque', 'icone': 'fa-book-reader', 'couleur': 'success',
            'description': 'Catalogue, emprunts et réservations de livres.',
            'href': reverse('depenses:dashboard_bibliotheque'),
            'total': bibliotheque_qs.count(),
            'montant': None,
        },
        {
            'titre': 'Cuisine', 'icone': 'fa-utensils', 'couleur': 'orange',
            'description': 'Dépenses de la cuisine (denrées, matériel...).',
            'href': reverse('depenses:dashboard_module_simple', args=['cuisine']),
            'total': cuisine_qs.count(),
            'montant': cuisine_qs.aggregate(t=Sum('montant'))['t'] or Decimal('0'),
        },
        {
            'titre': 'Document', 'icone': 'fa-file-alt', 'couleur': 'purple',
            'description': 'Dépenses liées aux documents administratifs.',
            'href': reverse('depenses:dashboard_module_simple', args=['document']),
            'total': document_qs.count(),
            'montant': document_qs.aggregate(t=Sum('montant'))['t'] or Decimal('0'),
        },
        {
            'titre': 'Versement', 'icone': 'fa-hand-holding-usd', 'couleur': 'rose',
            'description': 'Versements effectués par l\'établissement.',
            'href': reverse('depenses:dashboard_module_simple', args=['versement']),
            'total': versement_qs.count(),
            'montant': versement_qs.aggregate(t=Sum('montant'))['t'] or Decimal('0'),
        },
        {
            'titre': 'Informatique', 'icone': 'fa-laptop-code', 'couleur': 'magic',
            'description': 'Abonnements informatique des élèves et alertes.',
            'href': reverse('depenses:dashboard_informatique'),
            'total': informatique_qs.count(),
            'montant': informatique_qs.filter(statut='ACTIF').aggregate(t=Sum('montant'))['t'] or Decimal('0'),
        },
    ]

    context = {
        'cartes': cartes,
        'montant_total_general': montant_total_general,
    }
    return render(request, 'depenses/tableau_bord.html', context)


# =====================================================================
# Modules simples : Cuisine / Document / Versement
# =====================================================================

MODULES_SIMPLES = {
    'cuisine': {
        'model': DepenseCuisine,
        'form': DepenseCuisineForm,
        'titre': 'Dépenses Cuisine',
        'champ_principal': 'designation',
        'champ_principal_label': 'Désignation',
        'icone': 'fa-utensils',
    },
    'document': {
        'model': DepenseDocument,
        'form': DepenseDocumentForm,
        'titre': 'Dépenses Document',
        'champ_principal': 'designation',
        'champ_principal_label': 'Désignation',
        'icone': 'fa-file-alt',
    },
    'versement': {
        'model': Versement,
        'form': VersementForm,
        'titre': 'Versements',
        'champ_principal': 'lieu_versement',
        'champ_principal_label': 'Lieu de versement',
        'icone': 'fa-hand-holding-usd',
    },
}


def _base_qs_module(cle, user):
    cfg = MODULES_SIMPLES[cle]
    qs = cfg['model'].objects.all()
    if not user_is_superadmin(user):
        ecole = user_school(user)
        if ecole is None:
            return qs.none()
        qs = qs.filter(cree_par__profil__ecole=ecole)
    return qs


@login_required
def liste_module_simple(request, cle):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    qs = _base_qs_module(cle, request.user).order_by('-date', '-date_creation')

    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(**{f"{cfg['champ_principal']}__icontains": q}) | Q(observation__icontains=q)
        )

    date_debut = request.GET.get('date_debut') or ''
    date_fin = request.GET.get('date_fin') or ''
    if date_debut:
        qs = qs.filter(date__gte=date_debut)
    if date_fin:
        qs = qs.filter(date__lte=date_fin)

    total_montant = qs.aggregate(total=Sum('montant'))['total'] or Decimal('0')

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'cle': cle,
        'cfg': cfg,
        'page_obj': page_obj,
        'total_montant': total_montant,
        'q': q,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    return render(request, 'depenses/recouvrement/liste.html', context)


@login_required
@can_add_expenses
def ajouter_module_simple(request, cle):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    if request.method == 'POST':
        form = cfg['form'](request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.cree_par = request.user
            instance.save()
            messages.success(request, f"{cfg['titre']} : enregistrement ajouté avec succès.")
            return redirect('depenses:liste_module_simple', cle=cle)
    else:
        form = cfg['form']()
    return render(request, 'depenses/recouvrement/form.html', {'cle': cle, 'cfg': cfg, 'form': form})


@login_required
@can_modify_expenses
def modifier_module_simple(request, cle, pk):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    instance = get_object_or_404(_base_qs_module(cle, request.user), pk=pk)
    if request.method == 'POST':
        form = cfg['form'](request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{cfg['titre']} : enregistrement modifié avec succès.")
            return redirect('depenses:liste_module_simple', cle=cle)
    else:
        form = cfg['form'](instance=instance)
    return render(request, 'depenses/recouvrement/form.html', {
        'cle': cle, 'cfg': cfg, 'form': form, 'instance': instance,
    })


@login_required
@can_delete_expenses
def supprimer_module_simple(request, cle, pk):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    instance = get_object_or_404(_base_qs_module(cle, request.user), pk=pk)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, f"{cfg['titre']} : enregistrement supprimé.")
        return redirect('depenses:liste_module_simple', cle=cle)
    return render(request, 'depenses/recouvrement/confirmer_suppression.html', {
        'cle': cle, 'cfg': cfg, 'instance': instance,
    })


@login_required
def dashboard_module_simple(request, cle):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    qs = _base_qs_module(cle, request.user)

    total_count = qs.count()
    total_montant = qs.aggregate(total=Sum('montant'))['total'] or Decimal('0')

    today = timezone.localdate()
    debut_mois = today.replace(day=1)
    montant_mois = qs.filter(date__gte=debut_mois).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    count_mois = qs.filter(date__gte=debut_mois).count()

    recents = qs.order_by('-date', '-date_creation')[:10]

    context = {
        'cle': cle,
        'cfg': cfg,
        'total_count': total_count,
        'total_montant': total_montant,
        'montant_mois': montant_mois,
        'count_mois': count_mois,
        'recents': recents,
    }
    return render(request, 'depenses/recouvrement/dashboard.html', context)


@login_required
def export_module_simple_excel(request, cle):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    qs = _base_qs_module(cle, request.user).order_by('-date')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = cfg['titre'][:31]

    headers = ['Date', cfg['champ_principal_label'], 'Montant (GNF)', 'Observation']
    header_fill = PatternFill(start_color='0D6EFD', end_color='0D6EFD', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    for row, item in enumerate(qs, 2):
        ws.cell(row=row, column=1, value=item.date.strftime('%d/%m/%Y') if item.date else '')
        ws.cell(row=row, column=2, value=getattr(item, cfg['champ_principal']))
        ws.cell(row=row, column=3, value=float(item.montant))
        ws.cell(row=row, column=4, value=item.observation)

    for col in ws.columns:
        largeur = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(largeur + 2, 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f"attachment; filename={cle}_{timezone.localdate()}.xlsx"
    wb.save(response)
    return response


@login_required
def export_module_simple_pdf(request, cle):
    if cle not in MODULES_SIMPLES:
        raise Http404()
    cfg = MODULES_SIMPLES[cle]
    qs = _base_qs_module(cle, request.user).order_by('-date')

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph(cfg['titre'], titre_style))
    story.append(Paragraph(f"Édité le {timezone.localdate().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 16))

    data = [['Date', cfg['champ_principal_label'], 'Montant (GNF)', 'Observation']]
    total = Decimal('0')
    for item in qs:
        total += item.montant or Decimal('0')
        data.append([
            item.date.strftime('%d/%m/%Y') if item.date else '',
            getattr(item, cfg['champ_principal']),
            f"{item.montant:,.0f}".replace(',', ' '),
            (item.observation or '')[:60],
        ])
    data.append(['', 'TOTAL', f"{total:,.0f}".replace(',', ' '), ''])

    table = Table(data, colWidths=[70, 190, 90, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D6EFD')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f1f1')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f"attachment; filename={cle}_{timezone.localdate()}.pdf"
    return response


# =====================================================================
# Module Informatique (abonnements élèves)
# =====================================================================

@login_required
def liste_abonnements_informatique(request):
    qs = AbonnementInformatique.objects.select_related('eleve', 'eleve__classe', 'eleve__classe__ecole')
    if not user_is_superadmin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')

    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__matricule__icontains=q)
        )

    filtre = (request.GET.get('filtre') or '').strip().lower()
    today = timezone.localdate()
    if filtre == 'actif':
        qs = qs.filter(statut='ACTIF')
    elif filtre == 'expire':
        qs = qs.filter(statut='EXPIRE')
    elif filtre == 'proche_expiration':
        qs = qs.filter(statut='ACTIF', date_fin__gte=today, date_fin__lte=today + timedelta(days=7))

    qs = qs.order_by('-updated_at')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'q': q,
        'filtre': filtre,
    }
    return render(request, 'depenses/recouvrement/informatique_liste.html', context)


@login_required
def recherche_eleve_informatique(request):
    """Recherche d'élèves par matricule/nom pour créer un abonnement (API JSON)."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return HttpResponse('[]', content_type='application/json')

    qs = Eleve.objects.select_related('classe')
    if not user_is_superadmin(request.user):
        qs = filter_by_user_school(qs, request.user, 'classe__ecole')

    qs = qs.filter(
        Q(matricule__icontains=q) | Q(nom__icontains=q) | Q(prenom__icontains=q)
    )[:15]

    import json
    resultats = [
        {
            'id': e.id,
            'matricule': e.matricule or '',
            'nom_complet': f"{e.prenom} {e.nom}",
            'classe': e.classe.nom if e.classe else '',
        }
        for e in qs
    ]
    return HttpResponse(json.dumps(resultats), content_type='application/json')


@login_required
def ajouter_abonnement_informatique(request):
    if request.method == 'POST':
        form = AbonnementInformatiqueForm(request.POST)
        if form.is_valid():
            abonnement = form.save(commit=False)
            abonnement.cree_par = request.user
            abonnement.save()
            messages.success(request, f"Abonnement informatique créé pour {abonnement.eleve}")
            return redirect('depenses:liste_abonnements_informatique')
    else:
        form = AbonnementInformatiqueForm()
        eleve_id = request.GET.get('eleve')
        if eleve_id:
            try:
                form.initial['eleve'] = Eleve.objects.get(pk=eleve_id)
            except Eleve.DoesNotExist:
                pass

    if not user_is_superadmin(request.user):
        form.fields['eleve'].queryset = filter_by_user_school(Eleve.objects.all(), request.user, 'classe__ecole')

    return render(request, 'depenses/recouvrement/informatique_form.html', {'form': form})


@login_required
@require_school_object(model=AbonnementInformatique, pk_kwarg='pk', field_path='eleve__classe__ecole')
def modifier_abonnement_informatique(request, pk):
    abonnement = get_object_or_404(AbonnementInformatique, pk=pk)
    if request.method == 'POST':
        form = AbonnementInformatiqueForm(request.POST, instance=abonnement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Abonnement informatique modifié pour {abonnement.eleve}")
            return redirect('depenses:liste_abonnements_informatique')
    else:
        form = AbonnementInformatiqueForm(instance=abonnement)

    if not user_is_superadmin(request.user):
        form.fields['eleve'].queryset = filter_by_user_school(Eleve.objects.all(), request.user, 'classe__ecole')

    return render(request, 'depenses/recouvrement/informatique_form.html', {'form': form, 'abonnement': abonnement})


@login_required
@can_delete_subscriptions
@require_school_object(model=AbonnementInformatique, pk_kwarg='pk', field_path='eleve__classe__ecole')
def supprimer_abonnement_informatique(request, pk):
    abonnement = get_object_or_404(AbonnementInformatique, pk=pk)
    if request.method == 'POST':
        eleve_nom = str(abonnement.eleve)
        abonnement.delete()
        messages.success(request, f"Abonnement informatique supprimé pour {eleve_nom}")
        return redirect('depenses:liste_abonnements_informatique')
    return render(request, 'depenses/recouvrement/informatique_confirmer_suppression.html', {'abonnement': abonnement})


@login_required
def dashboard_informatique(request):
    qs = AbonnementInformatique.objects.select_related('eleve', 'eleve__classe')
    if not user_is_superadmin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')

    today = timezone.localdate()
    total = qs.count()
    actifs = qs.filter(statut='ACTIF').count()
    expires = qs.filter(statut='EXPIRE').count()
    suspendus = qs.filter(statut='SUSPENDU').count()

    abonnements_expires = qs.filter(statut='ACTIF', date_fin__lt=today)
    abonnements_proche_expiration = qs.filter(
        statut='ACTIF', date_fin__gte=today, date_fin__lte=today + timedelta(days=7)
    )

    montant_total = qs.filter(statut='ACTIF').aggregate(total=Sum('montant'))['total'] or Decimal('0')

    context = {
        'total': total,
        'actifs': actifs,
        'expires': expires,
        'suspendus': suspendus,
        'abonnements_expires': abonnements_expires,
        'abonnements_proche_expiration': abonnements_proche_expiration,
        'nb_expires': abonnements_expires.count(),
        'nb_proche_expiration': abonnements_proche_expiration.count(),
        'montant_total': montant_total,
    }
    return render(request, 'depenses/recouvrement/informatique_dashboard.html', context)


@login_required
@require_school_object(model=AbonnementInformatique, pk_kwarg='pk', field_path='eleve__classe__ecole')
def carte_abonnement_informatique_pdf(request, pk):
    """Génère la carte d'abonnement informatique PDF d'un élève."""
    abonnement = get_object_or_404(
        AbonnementInformatique.objects.select_related('eleve', 'eleve__classe', 'eleve__classe__ecole'),
        pk=pk
    )

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from django.contrib.staticfiles import finders
    import os

    buffer = io.BytesIO()
    # Format carte (85.6mm x 54mm, format carte bancaire standard) sur fond A4 centré
    carte_w, carte_h = 85.6 * mm, 54 * mm
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x0 = (width - carte_w) / 2
    y0 = (height - carte_h) / 2

    c.setFillColorRGB(0.05, 0.15, 0.35)
    c.roundRect(x0, y0, carte_w, carte_h, 8, fill=1, stroke=0)

    ecole_obj = getattr(getattr(abonnement.eleve, 'classe', None), 'ecole', None)
    logo_path = None
    try:
        if ecole_obj and getattr(ecole_obj, 'logo', None) and hasattr(ecole_obj.logo, 'path'):
            if os.path.exists(ecole_obj.logo.path):
                logo_path = ecole_obj.logo.path
    except Exception:
        logo_path = None
    if not logo_path:
        logo_path = finders.find('logos/logo.png')
    if logo_path:
        try:
            c.drawImage(ImageReader(logo_path), x0 + 6, y0 + carte_h - 22, width=16, height=16,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 9)
    nom_ecole = ecole_obj.nom if ecole_obj and getattr(ecole_obj, 'nom', None) else 'MySchoolGN'
    c.drawString(x0 + 26, y0 + carte_h - 16, nom_ecole[:32])

    c.setFont('Helvetica-Bold', 8)
    c.drawString(x0 + 6, y0 + carte_h - 30, "CARTE D'ABONNEMENT INFORMATIQUE")

    c.setFont('Helvetica', 8)
    c.drawString(x0 + 6, y0 + carte_h - 42, f"Élève : {abonnement.eleve.prenom} {abonnement.eleve.nom}")
    c.drawString(x0 + 6, y0 + carte_h - 52, f"Matricule : {abonnement.eleve.matricule or '-'}")
    classe_nom = abonnement.eleve.classe.nom if abonnement.eleve.classe else '-'
    c.drawString(x0 + 6, y0 + carte_h - 62, f"Classe : {classe_nom}")
    c.drawString(x0 + 6, y0 + carte_h - 74, f"Validité : {abonnement.date_debut.strftime('%d/%m/%Y')} au {abonnement.date_fin.strftime('%d/%m/%Y')}")
    c.drawString(x0 + 6, y0 + carte_h - 84, f"Statut : {abonnement.get_statut_display()}")

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f"attachment; filename=carte_informatique_{abonnement.eleve.matricule or abonnement.pk}.pdf"
    return response


@login_required
def export_informatique_excel(request):
    qs = AbonnementInformatique.objects.select_related('eleve', 'eleve__classe').order_by('-updated_at')
    if not user_is_superadmin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Abonnements Informatique'
    headers = ['Matricule', 'Élève', 'Classe', 'Montant (GNF)', 'Début', 'Fin', 'Statut']
    header_fill = PatternFill(start_color='0D6EFD', end_color='0D6EFD', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    for row, abo in enumerate(qs, 2):
        ws.cell(row=row, column=1, value=abo.eleve.matricule or '')
        ws.cell(row=row, column=2, value=f"{abo.eleve.prenom} {abo.eleve.nom}")
        ws.cell(row=row, column=3, value=abo.eleve.classe.nom if abo.eleve.classe else '')
        ws.cell(row=row, column=4, value=float(abo.montant))
        ws.cell(row=row, column=5, value=abo.date_debut.strftime('%d/%m/%Y'))
        ws.cell(row=row, column=6, value=abo.date_fin.strftime('%d/%m/%Y'))
        ws.cell(row=row, column=7, value=abo.get_statut_display())

    for col in ws.columns:
        largeur = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(largeur + 2, 40)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f"attachment; filename=abonnements_informatique_{timezone.localdate()}.xlsx"
    wb.save(response)
    return response


@login_required
def export_informatique_pdf(request):
    qs = AbonnementInformatique.objects.select_related('eleve', 'eleve__classe').order_by('-updated_at')
    if not user_is_superadmin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph('Abonnements Informatique', titre_style))
    story.append(Paragraph(f"Édité le {timezone.localdate().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 16))

    data = [['Matricule', 'Élève', 'Classe', 'Montant', 'Début', 'Fin', 'Statut']]
    for abo in qs:
        data.append([
            abo.eleve.matricule or '',
            f"{abo.eleve.prenom} {abo.eleve.nom}"[:22],
            abo.eleve.classe.nom if abo.eleve.classe else '',
            f"{abo.montant:,.0f}".replace(',', ' '),
            abo.date_debut.strftime('%d/%m/%Y'),
            abo.date_fin.strftime('%d/%m/%Y'),
            abo.get_statut_display(),
        ])

    table = Table(data, colWidths=[55, 110, 60, 60, 55, 55, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D6EFD')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f"attachment; filename=abonnements_informatique_{timezone.localdate()}.pdf"
    return response
