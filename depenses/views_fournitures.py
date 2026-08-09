from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import (
    Count, DecimalField, ExpressionWrapper, F, IntegerField, Q, Sum, Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from eleves.models import Ecole
from utilisateurs.utils import filter_by_user_school, user_is_superadmin, user_school

from .forms_fournitures import FournitureScolaireForm, VenteFournitureForm
from .models_fournitures import FournitureScolaire, VenteFourniture


DECIMAL_ZERO = Value(
    Decimal('0'),
    output_field=DecimalField(max_digits=18, decimal_places=0),
)
INTEGER_ZERO = Value(0, output_field=IntegerField())


def _produits_visibles(user):
    return filter_by_user_school(
        FournitureScolaire.objects.select_related('ecole'),
        user,
        'ecole',
    )


def _ventes_visibles(user):
    return filter_by_user_school(
        VenteFourniture.objects.select_related('ecole', 'produit', 'cree_par'),
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


def _generer_reference(ecole):
    prefixe_brut = getattr(ecole, 'code_prefixe', None) or f'E{ecole.pk}'
    prefixe_ecole = ''.join(
        caractere for caractere in str(prefixe_brut).upper() if caractere.isalnum()
    ) or f'E{ecole.pk}'
    prefixe = f'FOUR-{prefixe_ecole}-{date.today().year}'
    derniere = (
        FournitureScolaire.objects
        .filter(ecole=ecole, reference__startswith=prefixe)
        .order_by('-reference')
        .first()
    )
    sequence = 1
    if derniere:
        try:
            sequence = int(derniere.reference.rsplit('-', 1)[-1]) + 1
        except (TypeError, ValueError):
            sequence = 1
    return f'{prefixe}-{sequence:04d}'


def _produits_avec_totaux(queryset):
    produits = queryset.annotate(
        qte_vendue=Coalesce(Sum('ventes__quantite'), INTEGER_ZERO),
        chiffre_affaires_calc=Coalesce(Sum('ventes__montant_total'), DECIMAL_ZERO),
    ).annotate(
        reste_stock=ExpressionWrapper(
            F('quantite_stock') - F('qte_vendue'),
            output_field=IntegerField(),
        ),
        cout_vendu_calc=ExpressionWrapper(
            F('qte_vendue') * F('prix_achat_unitaire'),
            output_field=DecimalField(max_digits=18, decimal_places=0),
        ),
    ).annotate(
        solde_calc=ExpressionWrapper(
            F('chiffre_affaires_calc') - F('cout_vendu_calc'),
            output_field=DecimalField(max_digits=18, decimal_places=0),
        )
    )
    return produits


def _resume(produits, ventes):
    valeur_stock_expr = ExpressionWrapper(
        F('quantite_stock') * F('prix_achat_unitaire'),
        output_field=DecimalField(max_digits=18, decimal_places=0),
    )
    cout_vendu_expr = ExpressionWrapper(
        F('quantite') * F('produit__prix_achat_unitaire'),
        output_field=DecimalField(max_digits=18, decimal_places=0),
    )
    resume_produits = produits.aggregate(
        total_produits=Count('id'),
        stock_total=Coalesce(Sum('quantite_stock'), INTEGER_ZERO),
        valeur_stock_totale=Coalesce(Sum(valeur_stock_expr), DECIMAL_ZERO),
    )
    resume_ventes = ventes.aggregate(
        quantite_vendue=Coalesce(Sum('quantite'), INTEGER_ZERO),
        chiffre_affaires=Coalesce(Sum('montant_total'), DECIMAL_ZERO),
        cout_vendu=Coalesce(Sum(cout_vendu_expr), DECIMAL_ZERO),
    )
    resume = {**resume_produits, **resume_ventes}
    resume['quantite_stock'] = resume.pop('stock_total')
    resume['valeur_stock'] = resume.pop('valeur_stock_totale')
    resume['quantite_restante'] = max(
        0,
        resume['quantite_stock'] - resume['quantite_vendue'],
    )
    resume['solde'] = resume['chiffre_affaires'] - resume['cout_vendu']
    return resume


@login_required
def dashboard_fournitures(request):
    q = (request.GET.get('q') or '').strip()
    categorie = (request.GET.get('categorie') or '').strip()
    stock_bas = request.GET.get('stock_bas') == '1'

    tous_produits = _produits_visibles(request.user).filter(actif=True)
    toutes_ventes = _ventes_visibles(request.user)
    produits = tous_produits
    if q:
        produits = produits.filter(
            Q(reference__icontains=q)
            | Q(nom__icontains=q)
            | Q(description__icontains=q)
        )
    if categorie:
        produits = produits.filter(categorie=categorie)

    produits = _produits_avec_totaux(produits)
    if stock_bas:
        produits = produits.filter(reste_stock__lte=F('stock_minimum'))

    produits = produits.order_by('nom', 'reference')
    produits_alerte = _produits_avec_totaux(tous_produits).filter(
        reste_stock__lte=F('stock_minimum')
    ).count()

    context = {
        'titre_page': 'Gestion et vente des fournitures scolaires',
        'page_obj': Paginator(produits, 25).get_page(request.GET.get('page') or 1),
        'resume': _resume(tous_produits, toutes_ventes),
        'ventes_recentes': toutes_ventes.order_by('-date_vente', '-date_creation')[:8],
        'produits_alerte': produits_alerte,
        'categories': FournitureScolaire.CATEGORIE_CHOICES,
        'q': q,
        'categorie': categorie,
        'stock_bas': stock_bas,
    }
    return render(request, 'depenses/fournitures/dashboard.html', context)


@login_required
def creer_fourniture(request):
    ecole = _ecole_creation(request)
    form = FournitureScolaireForm(request.POST or None, ecole=ecole)
    if request.method == 'POST' and form.is_valid():
        if not ecole:
            form.add_error(None, 'Sélectionnez un établissement pour ce produit.')
        else:
            produit = form.save(commit=False)
            produit.ecole = ecole
            produit.cree_par = request.user
            if not produit.reference:
                produit.reference = _generer_reference(ecole)
            produit.full_clean()
            produit.save()
            messages.success(request, f'Le produit « {produit.nom} » a été ajouté au stock.')
            return redirect('depenses:dashboard_fournitures')

    return render(request, 'depenses/fournitures/form_produit.html', {
        'titre_page': 'Ajouter une fourniture scolaire',
        'form': form,
        'ecoles': Ecole.objects.order_by('nom') if user_is_superadmin(request.user) else None,
        'ecole_selectionnee': getattr(ecole, 'pk', ''),
    })


@login_required
def modifier_fourniture(request, produit_id):
    produit = get_object_or_404(_produits_visibles(request.user), pk=produit_id)
    form = FournitureScolaireForm(
        request.POST or None,
        instance=produit,
        ecole=produit.ecole,
    )
    if request.method == 'POST' and form.is_valid():
        produit = form.save(commit=False)
        produit.full_clean()
        produit.save()
        messages.success(request, f'Le produit « {produit.nom} » a été mis à jour.')
        return redirect('depenses:dashboard_fournitures')

    return render(request, 'depenses/fournitures/form_produit.html', {
        'titre_page': f'Modifier : {produit.nom}',
        'form': form,
        'produit': produit,
    })


@login_required
def enregistrer_vente_fourniture(request):
    form = VenteFournitureForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        produit_form = form.cleaned_data['produit']
        quantite = form.cleaned_data['quantite']
        with transaction.atomic():
            produit = get_object_or_404(
                _produits_visibles(request.user).select_for_update(),
                pk=produit_form.pk,
                actif=True,
            )
            disponible = produit.quantite_restante
            if quantite > disponible:
                form.add_error(
                    'quantite',
                    f'Stock restant insuffisant : {disponible} disponible(s).',
                )
            else:
                vente = form.save(commit=False)
                vente.produit = produit
                vente.ecole = produit.ecole
                vente.cree_par = request.user
                vente.full_clean()
                vente.save()
                messages.success(
                    request,
                    f'Vente enregistrée : {quantite} × {produit.nom}.',
                )
                return redirect('depenses:dashboard_fournitures')

    produits = form.fields['produit'].queryset
    produits_infos = {
        str(produit.pk): {
            'prix': int(produit.prix_vente_unitaire),
            'stock': produit.quantite_restante,
            'unite': produit.get_unite_display(),
        }
        for produit in produits
    }
    return render(request, 'depenses/fournitures/form_vente.html', {
        'titre_page': 'Enregistrer une vente de fournitures',
        'form': form,
        'produits_infos': produits_infos,
    })


@login_required
def liste_ventes_fournitures(request):
    q = (request.GET.get('q') or '').strip()
    date_debut = (request.GET.get('date_debut') or '').strip()
    date_fin = (request.GET.get('date_fin') or '').strip()

    ventes = _ventes_visibles(request.user)
    if q:
        ventes = ventes.filter(
            Q(numero_vente__icontains=q)
            | Q(produit__reference__icontains=q)
            | Q(produit__nom__icontains=q)
            | Q(client__icontains=q)
        )
    if date_debut:
        ventes = ventes.filter(date_vente__gte=date_debut)
    if date_fin:
        ventes = ventes.filter(date_vente__lte=date_fin)

    cout_expr = ExpressionWrapper(
        F('quantite') * F('produit__prix_achat_unitaire'),
        output_field=DecimalField(max_digits=18, decimal_places=0),
    )
    resume = ventes.aggregate(
        nombre_ventes=Count('id'),
        quantite_vendue=Coalesce(Sum('quantite'), INTEGER_ZERO),
        chiffre_affaires=Coalesce(Sum('montant_total'), DECIMAL_ZERO),
        cout_vendu=Coalesce(Sum(cout_expr), DECIMAL_ZERO),
    )
    resume['solde'] = resume['chiffre_affaires'] - resume['cout_vendu']

    return render(request, 'depenses/fournitures/liste_ventes.html', {
        'titre_page': 'Historique des ventes de fournitures',
        'page_obj': Paginator(ventes, 30).get_page(request.GET.get('page') or 1),
        'resume': resume,
        'q': q,
        'date_debut': date_debut,
        'date_fin': date_fin,
    })
