from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from eleves.models import Classe, Ecole
from utilisateurs.utils import (
    filter_by_user_school,
    user_is_superadmin,
    user_school,
)

from .forms import BienEtablissementForm, ContributionRamePapierForm
from .models_logistique import BienEtablissement, ContributionRamePapier


DECIMAL_ZERO = Value(
    Decimal('0'),
    output_field=DecimalField(max_digits=18, decimal_places=0),
)


def _biens_visibles(user):
    biens = BienEtablissement.objects.select_related('ecole').filter(actif=True)
    if user_is_superadmin(user):
        return biens
    ecole = user_school(user)
    if not ecole:
        return biens.none()
    # Les anciens biens n'avaient pas encore de champ ecole. Ce repli les rend
    # visibles à leur établissement jusqu'à leur rattachement par la migration.
    return biens.filter(
        Q(ecole=ecole)
        | Q(ecole__isnull=True, cree_par__profil__ecole=ecole)
    ).distinct()


def _contributions_visibles(user):
    return filter_by_user_school(
        ContributionRamePapier.objects.select_related(
            'ecole', 'eleve', 'eleve__classe', 'cree_par'
        ),
        user,
        'ecole',
    )


def _ecole_creation(request):
    ecole = user_school(request.user)
    if ecole or not user_is_superadmin(request.user):
        return ecole
    ecole_id = request.POST.get('ecole') or request.GET.get('ecole')
    if ecole_id:
        try:
            return Ecole.objects.get(pk=int(ecole_id))
        except (Ecole.DoesNotExist, TypeError, ValueError):
            return None
    if Ecole.objects.count() == 1:
        return Ecole.objects.first()
    return None


def _generer_code_bien(ecole):
    prefixe_ecole = getattr(ecole, 'code_prefixe', None) or f'E{ecole.pk}'
    prefixe = f"BIEN-{prefixe_ecole}-{date.today().year}"
    dernier = (
        BienEtablissement.objects
        .filter(code_bien__startswith=prefixe)
        .order_by('-code_bien')
        .first()
    )
    sequence = 1
    if dernier:
        try:
            sequence = int(dernier.code_bien.rsplit('-', 1)[-1]) + 1
        except (TypeError, ValueError):
            sequence = 1
    return f"{prefixe}-{sequence:04d}"


def _resume_biens(queryset):
    valeur_expr = ExpressionWrapper(
        F('quantite_achetee') * F('prix_achat_unitaire'),
        output_field=DecimalField(max_digits=18, decimal_places=0),
    )
    resume = queryset.aggregate(
        total_biens=Count('id'),
        total_quantite_achetee=Coalesce(Sum('quantite_achetee'), Value(0)),
        total_quantite_utilisee=Coalesce(Sum('quantite_utilisee'), Value(0)),
        total_quantite_endommagee=Coalesce(Sum('quantite_endommagee'), Value(0)),
        valeur_achat=Coalesce(Sum(valeur_expr), DECIMAL_ZERO),
    )
    resume['quantite_achetee'] = resume.pop('total_quantite_achetee')
    resume['quantite_utilisee'] = resume.pop('total_quantite_utilisee')
    resume['quantite_endommagee'] = resume.pop('total_quantite_endommagee')
    return resume


def _resume_contributions(queryset):
    return queryset.aggregate(
        total_contributions=Count('id'),
        eleves_contributeurs=Count('eleve_id', distinct=True),
        total_paquets=Coalesce(Sum('nombre_paquets'), Value(0)),
        total_argent=Coalesce(Sum('montant_paye'), DECIMAL_ZERO),
    )


@login_required
def dashboard_logistique(request):
    biens = _biens_visibles(request.user)
    contributions = _contributions_visibles(request.user)
    annee = (request.GET.get('annee') or '').strip()
    if annee:
        contributions = contributions.filter(annee_scolaire=annee)

    resume_biens = _resume_biens(biens)
    resume_biens['quantite_disponible'] = max(
        0,
        (resume_biens['quantite_achetee'] or 0)
        - (resume_biens['quantite_utilisee'] or 0)
        - (resume_biens['quantite_endommagee'] or 0),
    )
    resume_rames = _resume_contributions(contributions)

    annees = list(
        _contributions_visibles(request.user)
        .values_list('annee_scolaire', flat=True)
        .distinct()
        .order_by('-annee_scolaire')
    )
    context = {
        'titre_page': 'Logistique simplifiée',
        'resume_biens': resume_biens,
        'resume_rames': resume_rames,
        'biens_recents': biens.order_by('-date_creation')[:6],
        'contributions_recentes': contributions.order_by(
            '-date_contribution', '-date_creation'
        )[:8],
        'biens_endommages': biens.filter(quantite_endommagee__gt=0).count(),
        'annees': annees,
        'annee': annee,
    }
    return render(request, 'depenses/logistique/dashboard.html', context)


@login_required
def liste_biens(request):
    q = (request.GET.get('q') or '').strip()
    type_bien = (request.GET.get('type_bien') or '').strip()
    etat = (request.GET.get('etat') or '').strip()

    biens = _biens_visibles(request.user)
    if q:
        biens = biens.filter(
            Q(code_bien__icontains=q)
            | Q(nom__icontains=q)
            | Q(marque__icontains=q)
            | Q(localisation__icontains=q)
        )
    if type_bien:
        biens = biens.filter(type_bien=type_bien)
    if etat:
        biens = biens.filter(etat=etat)

    biens = biens.order_by('type_bien', 'nom')
    context = {
        'titre_page': "Biens de l'établissement",
        'page_obj': Paginator(biens, 24).get_page(request.GET.get('page') or 1),
        'resume': _resume_biens(biens),
        'q': q,
        'type_bien': type_bien,
        'etat': etat,
        'types_biens': BienEtablissement.TYPE_CHOICES,
        'etats_biens': BienEtablissement.ETAT_CHOICES,
    }
    return render(request, 'depenses/logistique/liste_biens.html', context)


@login_required
def creer_bien(request):
    ecole = _ecole_creation(request)
    form = BienEtablissementForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        if not ecole:
            form.add_error(None, "Sélectionnez l'établissement auquel appartient ce bien.")
        else:
            bien = form.save(commit=False)
            bien.ecole = ecole
            bien.cree_par = request.user
            bien.localisation = bien.localisation or 'Non précisée'
            if not bien.code_bien:
                bien.code_bien = _generer_code_bien(ecole)
            bien.save()
            messages.success(request, f'Le bien « {bien.nom} » a été enregistré.')
            return redirect('depenses:liste_biens')

    context = {
        'titre_page': 'Ajouter un bien',
        'form': form,
        'ecoles': Ecole.objects.order_by('nom') if user_is_superadmin(request.user) else None,
        'ecole_selectionnee': getattr(ecole, 'pk', ''),
    }
    return render(request, 'depenses/logistique/form_bien.html', context)


@login_required
def modifier_bien(request, bien_id):
    bien = get_object_or_404(_biens_visibles(request.user), pk=bien_id)
    form = BienEtablissementForm(
        request.POST or None,
        request.FILES or None,
        instance=bien,
    )
    if request.method == 'POST' and form.is_valid():
        bien = form.save(commit=False)
        if not bien.ecole_id:
            bien.ecole = user_school(request.user)
        bien.save()
        messages.success(request, f'Le bien « {bien.nom} » a été mis à jour.')
        return redirect('depenses:liste_biens')

    return render(request, 'depenses/logistique/form_bien.html', {
        'titre_page': f'Modifier : {bien.nom}',
        'form': form,
        'bien': bien,
    })


@login_required
def liste_contributions_rames(request):
    q = (request.GET.get('q') or '').strip()
    classe_id = (request.GET.get('classe') or '').strip()
    mode = (request.GET.get('mode') or '').strip()
    annee = (request.GET.get('annee') or '').strip()

    contributions = _contributions_visibles(request.user)
    if q:
        contributions = contributions.filter(
            Q(eleve__matricule__icontains=q)
            | Q(eleve__nom__icontains=q)
            | Q(eleve__prenom__icontains=q)
        )
    if classe_id:
        contributions = contributions.filter(eleve__classe_id=classe_id)
    if mode:
        contributions = contributions.filter(mode_contribution=mode)
    if annee:
        contributions = contributions.filter(annee_scolaire=annee)

    classes = filter_by_user_school(
        Classe.objects.select_related('ecole').order_by('-annee_scolaire', 'nom'),
        request.user,
        'ecole',
    )
    annees = list(
        _contributions_visibles(request.user)
        .values_list('annee_scolaire', flat=True)
        .distinct()
        .order_by('-annee_scolaire')
    )
    context = {
        'titre_page': 'Rames de papier',
        'page_obj': Paginator(contributions, 30).get_page(request.GET.get('page') or 1),
        'resume': _resume_contributions(contributions),
        'classes': classes,
        'annees': annees,
        'modes': ContributionRamePapier.MODE_CHOICES,
        'q': q,
        'classe_id': classe_id,
        'mode': mode,
        'annee': annee,
    }
    return render(request, 'depenses/logistique/liste_contributions_rames.html', context)


@login_required
def ajouter_contribution_rame(request):
    form = ContributionRamePapierForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        contribution = form.save(commit=False)
        contribution.ecole = contribution.eleve.classe.ecole
        contribution.annee_scolaire = contribution.eleve.classe.annee_scolaire
        contribution.cree_par = request.user
        contribution.save()
        messages.success(
            request,
            f'Contribution enregistrée pour {contribution.eleve.nom_complet}.',
        )
        return redirect('depenses:liste_contributions_rames')

    return render(request, 'depenses/logistique/form_contribution_rame.html', {
        'titre_page': 'Enregistrer une contribution en papier',
        'form': form,
    })


@login_required
def modifier_contribution_rame(request, contribution_id):
    contribution = get_object_or_404(
        _contributions_visibles(request.user),
        pk=contribution_id,
    )
    form = ContributionRamePapierForm(
        request.POST or None,
        instance=contribution,
        user=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        contribution = form.save(commit=False)
        contribution.ecole = contribution.eleve.classe.ecole
        contribution.annee_scolaire = contribution.eleve.classe.annee_scolaire
        contribution.save()
        messages.success(request, 'La contribution a été mise à jour.')
        return redirect('depenses:liste_contributions_rames')

    return render(request, 'depenses/logistique/form_contribution_rame.html', {
        'titre_page': 'Modifier la contribution',
        'form': form,
        'contribution': contribution,
    })
