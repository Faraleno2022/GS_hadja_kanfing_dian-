"""Vues du module Recouvrement.

Le hub (`hub_recouvrement`) affiche un tableau de bord général puis une carte
par sous-module. Les modules Cuisine, Documents et Versements partagent la même
mécanique (saisie, tableau de bord, exports) décrite par `ModuleSimple`.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Type

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from eleves.models import Classe, Eleve
from utilisateurs.permissions import (
    can_add_expenses, can_delete_expenses, can_modify_expenses,
)
from utilisateurs.utils import filter_by_user_school, user_is_superadmin, user_school

from .exports_recouvrement import (
    carte_abonnement_pdf, export_excel, export_pdf, formater_montant,
)
from .forms_recouvrement import (
    AbonnementInformatiqueForm, DepenseCuisineForm, DepenseDocumentForm, VersementForm,
)
from .models import Depense
from .models_fournitures import VenteFourniture
from .models_recouvrement import (
    AbonnementInformatique, DepenseCuisine, DepenseDocument, Versement,
)
from .views_fournitures import _ecole_creation

ZERO = Decimal('0')


# ─────────────────────────── Recouvrement Salaires ───────────────────────────
# Suivi (lecture) des salaires enseignants effectivement payés, tels que
# calculés/validés dans l'app `salaires`. Regroupement par niveau
# (Maternelle/Primaire/Collège/Lycée) et par mois.

NIVEAUX_SALAIRE = ['Maternelle', 'Primaire', 'Collège', 'Lycée', 'Administration', 'Autre']

_NIVEAU_PAR_TYPE_ENSEIGNANT = {
    'GARDERIE': 'Maternelle',
    'MATERNELLE': 'Maternelle',
    'PRIMAIRE': 'Primaire',
    'SECONDAIRE': 'Collège',
    'ADMINISTRATEUR': 'Administration',
}


def _bucket_depuis_niveau_classe(niveau_code):
    """Convertit un niveau de `Classe` (ex: 'COLLEGE_8') en catégorie large."""
    if not niveau_code:
        return None
    if niveau_code in ('GARDERIE', 'MATERNELLE'):
        return 'Maternelle'
    if niveau_code.startswith('PRIMAIRE'):
        return 'Primaire'
    if niveau_code.startswith('COLLEGE'):
        return 'Collège'
    if niveau_code.startswith('LYCEE') or niveau_code == 'TERMINALE':
        return 'Lycée'
    return None


def _niveau_enseignant(enseignant):
    """Détermine le niveau (Maternelle/Primaire/Collège/Lycée) d'un enseignant.

    Priorité à la classe réellement affectée: `type_enseignant` regroupe
    Collège et Lycée sous « Secondaire », ce qui ne suffit pas ici.
    """
    from salaires.models import AffectationClasse

    affectation = (
        AffectationClasse.objects.filter(enseignant=enseignant, actif=True)
        .select_related('classe')
        .order_by('-date_debut')
        .first()
    )
    if affectation:
        bucket = _bucket_depuis_niveau_classe(affectation.classe.niveau)
        if bucket:
            return bucket
    return _NIVEAU_PAR_TYPE_ENSEIGNANT.get(enseignant.type_enseignant, 'Autre')


def _etats_salaire_payes_visibles(user):
    from salaires.models import EtatSalaire

    etats = EtatSalaire.objects.filter(paye=True).select_related(
        'enseignant', 'enseignant__ecole', 'periode',
    )
    return filter_by_user_school(etats, user, 'enseignant__ecole')


@login_required
def dashboard_salaires(request):
    """Suivi des salaires enseignants: tableau par mois + dashboard par niveau.

    Chaque enseignant actif (créé dans l'app `salaires`) apparaît directement
    dans le tableau, même sans paiement encore enregistré (montants à « — »).
    """
    from salaires.models import Enseignant

    niveau_filtre = (request.GET.get('niveau') or '').strip()
    q = (request.GET.get('q') or '').strip()

    # Niveau par enseignant (mis en cache pour éviter de répéter la requête)
    niveau_cache = {}

    def niveau_de(enseignant):
        if enseignant.id not in niveau_cache:
            niveau_cache[enseignant.id] = _niveau_enseignant(enseignant)
        return niveau_cache[enseignant.id]

    # Base du tableau: tous les enseignants actifs visibles par l'utilisateur,
    # qu'ils aient déjà été payés ou non.
    enseignants = filter_by_user_school(
        Enseignant.objects.filter(statut='ACTIF'), request.user, 'ecole'
    )
    if q:
        enseignants = enseignants.filter(
            Q(nom__icontains=q) | Q(prenoms__icontains=q)
        )
    enseignants = list(enseignants)
    if niveau_filtre:
        enseignants = [e for e in enseignants if niveau_de(e) == niveau_filtre]

    etats = _etats_salaire_payes_visibles(request.user)
    if q:
        etats = etats.filter(
            Q(enseignant__nom__icontains=q) | Q(enseignant__prenoms__icontains=q)
        )
    etats = list(etats.order_by('-periode__annee', '-periode__mois', 'enseignant__nom'))
    if niveau_filtre:
        etats = [e for e in etats if niveau_de(e.enseignant) == niveau_filtre]

    # Colonnes: les 12 derniers mois pour lesquels un paiement existe
    mois_labels = {}
    for e in etats:
        cle = (e.periode.annee, e.periode.mois)
        mois_labels.setdefault(cle, e.periode.nom_periode)
    mois_ordonnes = sorted(mois_labels.keys(), reverse=True)[:12]
    mois_ordonnes.reverse()

    totaux_par_mois = {cle: ZERO for cle in mois_ordonnes}
    for e in etats:
        cle = (e.periode.annee, e.periode.mois)
        if cle in totaux_par_mois:
            totaux_par_mois[cle] += (e.salaire_net or ZERO)
    max_mois = max(totaux_par_mois.values()) if totaux_par_mois else ZERO
    colonnes_mois = [
        {
            'cle': cle,
            'libelle': mois_labels[cle],
            'total': totaux_par_mois[cle],
            'part': int(totaux_par_mois[cle] * 100 / max_mois) if max_mois else 0,
        }
        for cle in mois_ordonnes
    ]

    # Pivot enseignant -> montant par mois. On part de tous les enseignants
    # actifs filtrés (une ligne existe dès l'ajout de l'enseignant), puis on
    # y ajoute les montants réellement payés.
    pivot = {
        ens.id: {'enseignant': ens, 'niveau': niveau_de(ens), 'montants': {}, 'total': ZERO}
        for ens in enseignants
    }
    for e in etats:
        cle_mois = (e.periode.annee, e.periode.mois)
        if cle_mois not in mois_labels or cle_mois not in mois_ordonnes:
            continue
        ens = e.enseignant
        # Un enseignant payé mais devenu inactif/hors filtre entre-temps
        # reste visible dans l'historique des paiements.
        ligne = pivot.setdefault(ens.id, {
            'enseignant': ens,
            'niveau': niveau_de(ens),
            'montants': {},
            'total': ZERO,
        })
        ligne['montants'][cle_mois] = ligne['montants'].get(cle_mois, ZERO) + (e.salaire_net or ZERO)
        ligne['total'] += (e.salaire_net or ZERO)

    lignes = []
    for ligne in sorted(pivot.values(), key=lambda r: (r['enseignant'].nom, r['enseignant'].prenoms)):
        ligne['paires'] = [(col, ligne['montants'].get(col['cle'], ZERO)) for col in colonnes_mois]
        lignes.append(ligne)

    nb_avec_paiement = sum(1 for l in lignes if l['total'])
    total_general = sum((l['total'] for l in lignes), ZERO)
    par_niveau = {}
    for l in lignes:
        par_niveau[l['niveau']] = par_niveau.get(l['niveau'], ZERO) + l['total']

    aujourdhui = timezone.localdate()
    mois_courant = (aujourdhui.year, aujourdhui.month)
    total_mois_courant = sum((l['montants'].get(mois_courant, ZERO) for l in lignes), ZERO)
    nb_payes_mois_courant = sum(1 for l in lignes if l['montants'].get(mois_courant))

    nb_enseignants_total = filter_by_user_school(
        Enseignant.objects.filter(statut='ACTIF'), request.user, 'ecole'
    ).count()

    contexte = {
        'titre_page': 'Recouvrement salaires',
        'colonnes_mois': colonnes_mois,
        'lignes': lignes,
        'niveaux': NIVEAUX_SALAIRE,
        'niveau_filtre': niveau_filtre,
        'q': q,
        'total_general': total_general,
        'par_niveau': sorted(par_niveau.items(), key=lambda item: -item[1]),
        'total_mois_courant': total_mois_courant,
        'nb_payes_mois_courant': nb_payes_mois_courant,
        'nb_enseignants_total': nb_enseignants_total,
        'nb_lignes': len(lignes),
        'nb_avec_paiement': nb_avec_paiement,
    }
    return render(request, 'depenses/recouvrement/salaires_dashboard.html', contexte)


@login_required
def export_salaires_excel(request):
    niveau_filtre = (request.GET.get('niveau') or '').strip()
    q = (request.GET.get('q') or '').strip()

    etats = _etats_salaire_payes_visibles(request.user)
    if q:
        etats = etats.filter(
            Q(enseignant__nom__icontains=q) | Q(enseignant__prenoms__icontains=q)
        )
    etats = etats.order_by('-periode__annee', '-periode__mois', 'enseignant__nom')

    colonnes = ['Mois', 'Prénom', 'Nom', 'Niveau', 'Montant (GNF)']
    donnees = []
    total = ZERO
    for e in etats:
        niveau = _niveau_enseignant(e.enseignant)
        if niveau_filtre and niveau != niveau_filtre:
            continue
        montant = e.salaire_net or ZERO
        total += montant
        donnees.append([
            e.periode.nom_periode,
            e.enseignant.prenoms,
            e.enseignant.nom,
            niveau,
            formater_montant(montant),
        ])

    ligne_total = ['', '', '', 'TOTAL', formater_montant(total)]
    horodatage = timezone.now().strftime('%Y%m%d')
    return export_excel(
        f'salaires_{horodatage}.xlsx', 'Recouvrement salaires', colonnes, donnees, ligne_total,
    )


# ─────────────────────────── Modules simples ────────────────────────────────

@dataclass(frozen=True)
class ModuleSimple:
    """Description d'un module de saisie « date / libellé / montant / observation »."""

    slug: str
    model: Type
    form_class: Type
    titre: str
    intro: str
    icone: str
    couleur: str
    champ_libelle: str
    label_libelle: str
    label_operation: str


MODULES_SIMPLES = {
    'cuisine': ModuleSimple(
        slug='cuisine',
        model=DepenseCuisine,
        form_class=DepenseCuisineForm,
        titre='Dépenses de la cuisine',
        intro="Suivi des achats et frais engagés pour la cuisine de l'établissement.",
        icone='fa-utensils',
        couleur='warning',
        champ_libelle='designation',
        label_libelle='Désignation',
        label_operation='dépense',
    ),
    'documents': ModuleSimple(
        slug='documents',
        model=DepenseDocument,
        form_class=DepenseDocumentForm,
        titre='Dépenses de documents',
        intro='Impressions, actes administratifs et fournitures de bureau.',
        icone='fa-file-lines',
        couleur='info',
        champ_libelle='designation',
        label_libelle='Désignation',
        label_operation='dépense',
    ),
    'versements': ModuleSimple(
        slug='versements',
        model=Versement,
        form_class=VersementForm,
        titre='Versements',
        intro='Fonds versés en banque, à la direction ou dans une autre caisse.',
        icone='fa-money-bill-transfer',
        couleur='success',
        champ_libelle='lieu_versement',
        label_libelle='Lieu de versement',
        label_operation='versement',
    ),
}


def _module(slug):
    module = MODULES_SIMPLES.get(slug)
    if module is None:
        raise Http404('Module de recouvrement inconnu.')
    return module


def _lignes_visibles(module, user):
    return filter_by_user_school(
        module.model.objects.select_related('ecole', 'cree_par'), user, 'ecole'
    )


def _appliquer_filtres(queryset, module, request):
    """Filtres communs: période (du/au) et recherche plein texte."""
    du = (request.GET.get('du') or '').strip()
    au = (request.GET.get('au') or '').strip()
    recherche = (request.GET.get('q') or '').strip()

    if du:
        queryset = queryset.filter(date__gte=du)
    if au:
        queryset = queryset.filter(date__lte=au)
    if recherche:
        queryset = queryset.filter(
            Q(**{f'{module.champ_libelle}__icontains': recherche})
            | Q(observation__icontains=recherche)
        )
    return queryset, {'du': du, 'au': au, 'q': recherche}


def _evolution_mensuelle(queryset, nb_mois=12):
    """Total par mois sur les `nb_mois` derniers mois, du plus ancien au plus récent."""
    aujourdhui = timezone.localdate()
    premier_mois = date(aujourdhui.year, aujourdhui.month, 1)
    for _ in range(nb_mois - 1):
        premier_mois = (premier_mois - timedelta(days=1)).replace(day=1)

    totaux = {}
    agregats = (
        queryset.filter(date__gte=premier_mois)
        .values('date__year', 'date__month')
        .annotate(total=Sum('montant'))
    )
    for ligne in agregats:
        totaux[(ligne['date__year'], ligne['date__month'])] = ligne['total'] or ZERO

    libelles_mois = [
        'janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin',
        'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.',
    ]
    mois = []
    curseur = premier_mois
    while curseur <= aujourdhui:
        total = totaux.get((curseur.year, curseur.month), ZERO)
        mois.append({
            'libelle': f'{libelles_mois[curseur.month - 1]} {curseur.year}',
            'total': total,
        })
        curseur = (curseur.replace(day=28) + timedelta(days=4)).replace(day=1)

    maximum = max([m['total'] for m in mois] or [ZERO]) or Decimal('1')
    for m in mois:
        m['part'] = int(m['total'] * 100 / maximum)
    return mois


@login_required
def dashboard_module(request, module):
    """Tableau de bord et liste filtrable d'un module simple."""
    spec = _module(module)
    base = _lignes_visibles(spec, request.user)
    lignes, filtres = _appliquer_filtres(base, spec, request)

    aujourdhui = timezone.localdate()
    debut_mois = aujourdhui.replace(day=1)
    debut_annee = aujourdhui.replace(month=1, day=1)

    resume = lignes.aggregate(
        nombre=Count('id'), total=Sum('montant'), moyenne=Avg('montant'),
    )
    total_mois = base.filter(date__gte=debut_mois).aggregate(t=Sum('montant'))['t'] or ZERO
    total_annee = base.filter(date__gte=debut_annee).aggregate(t=Sum('montant'))['t'] or ZERO

    top_libelles = (
        lignes.values(spec.champ_libelle)
        .annotate(total=Sum('montant'), nombre=Count('id'))
        .order_by('-total')[:5]
    )

    paginator = Paginator(lignes, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    contexte = {
        'spec': spec,
        'module': spec.slug,
        'titre_page': spec.titre,
        'page_obj': page_obj,
        'filtres': filtres,
        'nombre': resume['nombre'] or 0,
        'total_filtre': resume['total'] or ZERO,
        'moyenne': resume['moyenne'] or ZERO,
        'total_mois': total_mois,
        'total_annee': total_annee,
        'top_libelles': [
            {'libelle': item[spec.champ_libelle], 'total': item['total'], 'nombre': item['nombre']}
            for item in top_libelles
        ],
        'evolution': _evolution_mensuelle(base),
    }
    return render(request, 'depenses/recouvrement/module_dashboard.html', contexte)


@login_required
@can_add_expenses
def creer_ligne_module(request, module):
    spec = _module(module)
    ecole = _ecole_creation(request)
    if ecole is None:
        messages.error(
            request,
            "Aucun établissement n'est associé à votre compte : impossible d'enregistrer.",
        )
        return redirect('depenses:module_recouvrement', module=spec.slug)

    if request.method == 'POST':
        form = spec.form_class(request.POST)
        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.ecole = ecole
            ligne.cree_par = request.user
            ligne.save()
            messages.success(request, f"{spec.label_operation.capitalize()} enregistrée.")
            return redirect('depenses:module_recouvrement', module=spec.slug)
    else:
        form = spec.form_class()

    return render(request, 'depenses/recouvrement/module_form.html', {
        'spec': spec,
        'module': spec.slug,
        'form': form,
        'titre_page': f'Nouvelle {spec.label_operation}',
    })


@login_required
@can_modify_expenses
def modifier_ligne_module(request, module, pk):
    spec = _module(module)
    ligne = get_object_or_404(_lignes_visibles(spec, request.user), pk=pk)

    if request.method == 'POST':
        form = spec.form_class(request.POST, instance=ligne)
        if form.is_valid():
            form.save()
            messages.success(request, f"{spec.label_operation.capitalize()} modifiée.")
            return redirect('depenses:module_recouvrement', module=spec.slug)
    else:
        form = spec.form_class(instance=ligne)

    return render(request, 'depenses/recouvrement/module_form.html', {
        'spec': spec,
        'module': spec.slug,
        'form': form,
        'ligne': ligne,
        'titre_page': f'Modifier la {spec.label_operation}',
    })


@login_required
@can_delete_expenses
def supprimer_ligne_module(request, module, pk):
    spec = _module(module)
    ligne = get_object_or_404(_lignes_visibles(spec, request.user), pk=pk)

    if request.method == 'POST':
        ligne.delete()
        messages.success(request, f"{spec.label_operation.capitalize()} supprimée.")
        return redirect('depenses:module_recouvrement', module=spec.slug)

    return render(request, 'depenses/recouvrement/module_confirm_delete.html', {
        'spec': spec,
        'module': spec.slug,
        'ligne': ligne,
        'titre_page': f'Supprimer la {spec.label_operation}',
    })


def _lignes_export(spec, request):
    """Lignes filtrées + total, prêtes pour Excel ou PDF."""
    lignes, filtres = _appliquer_filtres(_lignes_visibles(spec, request.user), spec, request)
    colonnes = ['Date', spec.label_libelle, 'Montant (GNF)', 'Observation', 'Enregistré par']
    donnees = [
        [
            ligne.date.strftime('%d/%m/%Y'),
            ligne.libelle or '',
            formater_montant(ligne.montant),
            ligne.observation or '',
            ligne.cree_par.get_full_name() or ligne.cree_par.username if ligne.cree_par else '',
        ]
        for ligne in lignes
    ]
    total = lignes.aggregate(t=Sum('montant'))['t'] or ZERO
    ligne_total = ['', 'TOTAL', formater_montant(total), '', '']

    periode = 'Toutes périodes'
    if filtres['du'] or filtres['au']:
        periode = f"Du {filtres['du'] or '…'} au {filtres['au'] or '…'}"
    return colonnes, donnees, ligne_total, periode


@login_required
def export_module_excel(request, module):
    spec = _module(module)
    colonnes, donnees, ligne_total, _ = _lignes_export(spec, request)
    horodatage = timezone.now().strftime('%Y%m%d')
    return export_excel(
        f'{spec.slug}_{horodatage}.xlsx', spec.titre, colonnes, donnees, ligne_total
    )


@login_required
def export_module_pdf(request, module):
    spec = _module(module)
    colonnes, donnees, ligne_total, periode = _lignes_export(spec, request)
    horodatage = timezone.now().strftime('%Y%m%d')
    return export_pdf(
        f'{spec.slug}_{horodatage}.pdf',
        spec.titre,
        f'{periode} — {len(donnees)} opération(s)',
        colonnes,
        donnees,
        ligne_total,
        ecole=user_school(request.user),
    )


# ───────────────────────── Module informatique ──────────────────────────────

def _abonnements_visibles(user):
    return filter_by_user_school(
        AbonnementInformatique.objects.select_related(
            'eleve', 'eleve__classe', 'eleve__classe__ecole', 'cree_par'
        ),
        user,
        'eleve__classe__ecole',
    )


def _eleves_visibles(user):
    return filter_by_user_school(
        Eleve.objects.select_related('classe').filter(statut='ACTIF'),
        user,
        'classe__ecole',
    ).order_by('classe__nom', 'nom', 'prenom')


def _filtrer_abonnements(queryset, request):
    """Recherche par matricule/nom et filtres de statut."""
    recherche = (request.GET.get('q') or '').strip()
    filtre = (request.GET.get('filtre') or '').strip().lower()
    classe_id = (request.GET.get('classe') or '').strip()
    aujourdhui = timezone.localdate()

    if recherche:
        queryset = queryset.filter(
            Q(eleve__matricule__icontains=recherche)
            | Q(eleve__nom__icontains=recherche)
            | Q(eleve__prenom__icontains=recherche)
        )
    if classe_id:
        queryset = queryset.filter(eleve__classe_id=classe_id)

    if filtre == 'actif':
        queryset = queryset.filter(statut='ACTIF', date_fin__gte=aujourdhui)
    elif filtre == 'expire':
        queryset = queryset.filter(statut='ACTIF', date_fin__lt=aujourdhui)
    elif filtre == 'bientot':
        queryset = queryset.filter(
            statut='ACTIF', date_fin__gte=aujourdhui, date_fin__lte=aujourdhui + timedelta(days=7)
        )
    elif filtre == 'suspendu':
        queryset = queryset.filter(statut='SUSPENDU')
    elif filtre == 'resilie':
        queryset = queryset.filter(statut='RESILIE')

    return queryset, {'q': recherche, 'filtre': filtre, 'classe': classe_id}


@login_required
def dashboard_informatique(request):
    """Tableau de bord des abonnements informatiques, avec alertes d'expiration."""
    base = _abonnements_visibles(request.user)
    abonnements, filtres = _filtrer_abonnements(base, request)

    aujourdhui = timezone.localdate()
    debut_mois = aujourdhui.replace(day=1)

    expires = base.filter(statut='ACTIF', date_fin__lt=aujourdhui)
    bientot = base.filter(
        statut='ACTIF', date_fin__gte=aujourdhui, date_fin__lte=aujourdhui + timedelta(days=7)
    )
    critiques = base.filter(
        statut='ACTIF', date_fin__gte=aujourdhui, date_fin__lte=aujourdhui + timedelta(days=3)
    )

    paginator = Paginator(abonnements.order_by('date_fin', 'eleve__nom'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    contexte = {
        'titre_page': 'Abonnements informatique',
        'page_obj': page_obj,
        'filtres': filtres,
        'total': base.count(),
        'actifs': base.filter(statut='ACTIF', date_fin__gte=aujourdhui).count(),
        'nb_expires': expires.count(),
        'nb_bientot': bientot.count(),
        'nb_critiques': critiques.count(),
        'recettes_total': base.aggregate(t=Sum('montant'))['t'] or ZERO,
        'recettes_mois': base.filter(date__gte=debut_mois).aggregate(t=Sum('montant'))['t'] or ZERO,
        'alertes_expires': expires.order_by('date_fin')[:10],
        'alertes_bientot': bientot.order_by('date_fin')[:10],
        'classes': filter_by_user_school(Classe.objects.all(), request.user, 'ecole').order_by('nom'),
    }
    return render(request, 'depenses/recouvrement/informatique_dashboard.html', contexte)


@login_required
@can_add_expenses
def creer_abonnement_informatique(request):
    eleves = _eleves_visibles(request.user)

    if request.method == 'POST':
        form = AbonnementInformatiqueForm(request.POST, eleves=eleves)
        if form.is_valid():
            abonnement = form.save(commit=False)
            abonnement.cree_par = request.user
            abonnement.save()
            messages.success(request, f"Abonnement enregistré pour {abonnement.eleve}.")
            return redirect('depenses:dashboard_informatique')
    else:
        initial = {}
        eleve_id = request.GET.get('eleve')
        if eleve_id:
            initial['eleve'] = eleve_id
        form = AbonnementInformatiqueForm(eleves=eleves, initial=initial)

    return render(request, 'depenses/recouvrement/informatique_form.html', {
        'form': form,
        'eleves': eleves,
        'titre_page': 'Nouvel abonnement informatique',
    })


@login_required
@can_modify_expenses
def modifier_abonnement_informatique(request, pk):
    abonnement = get_object_or_404(_abonnements_visibles(request.user), pk=pk)
    eleves = _eleves_visibles(request.user)

    if request.method == 'POST':
        form = AbonnementInformatiqueForm(request.POST, instance=abonnement, eleves=eleves)
        if form.is_valid():
            form.save()
            messages.success(request, 'Abonnement modifié.')
            return redirect('depenses:dashboard_informatique')
    else:
        form = AbonnementInformatiqueForm(instance=abonnement, eleves=eleves)

    return render(request, 'depenses/recouvrement/informatique_form.html', {
        'form': form,
        'eleves': eleves,
        'abonnement': abonnement,
        'titre_page': 'Modifier l’abonnement informatique',
    })


@login_required
@can_delete_expenses
def supprimer_abonnement_informatique(request, pk):
    abonnement = get_object_or_404(_abonnements_visibles(request.user), pk=pk)

    if request.method == 'POST':
        eleve = str(abonnement.eleve)
        abonnement.delete()
        messages.success(request, f'Abonnement supprimé pour {eleve}.')
        return redirect('depenses:dashboard_informatique')

    return render(request, 'depenses/recouvrement/informatique_confirm_delete.html', {
        'abonnement': abonnement,
        'titre_page': 'Supprimer l’abonnement',
    })


@login_required
def carte_abonnement_informatique(request, pk):
    """Carte d'abonnement au format carte bancaire, à imprimer."""
    abonnement = get_object_or_404(_abonnements_visibles(request.user), pk=pk)
    return carte_abonnement_pdf(abonnement)


@login_required
def api_eleve_informatique(request, eleve_id):
    """Fiche élève minimale pour la saisie assistée (recherche par matricule)."""
    eleve = get_object_or_404(_eleves_visibles(request.user), pk=eleve_id)
    dernier = (
        _abonnements_visibles(request.user)
        .filter(eleve=eleve).order_by('-date_fin').first()
    )
    return JsonResponse({
        'matricule': eleve.matricule or '',
        'nom_complet': f'{eleve.prenom} {eleve.nom}',
        'classe': eleve.classe.nom if eleve.classe_id else '',
        'dernier_abonnement': (
            {
                'fin': dernier.date_fin.strftime('%d/%m/%Y'),
                'statut': dernier.libelle_statut,
            }
            if dernier else None
        ),
    })


def _abonnements_export(request):
    abonnements, filtres = _filtrer_abonnements(_abonnements_visibles(request.user), request)
    abonnements = abonnements.order_by('date_fin', 'eleve__nom')
    colonnes = [
        'Matricule', 'Élève', 'Classe', 'Montant (GNF)', 'Début', 'Fin',
        'Jours restants', 'Statut', 'Observation',
    ]
    donnees = [
        [
            abo.eleve.matricule or '',
            f'{abo.eleve.prenom} {abo.eleve.nom}',
            abo.eleve.classe.nom if abo.eleve.classe_id else '',
            formater_montant(abo.montant),
            abo.date_debut.strftime('%d/%m/%Y'),
            abo.date_fin.strftime('%d/%m/%Y'),
            abo.jours_restants,
            abo.libelle_statut,
            abo.observation or '',
        ]
        for abo in abonnements
    ]
    total = abonnements.aggregate(t=Sum('montant'))['t'] or ZERO
    ligne_total = ['', 'TOTAL', '', formater_montant(total), '', '', '', '', '']
    return colonnes, donnees, ligne_total, filtres


@login_required
def export_informatique_excel(request):
    colonnes, donnees, ligne_total, _ = _abonnements_export(request)
    horodatage = timezone.now().strftime('%Y%m%d')
    return export_excel(
        f'abonnements_informatique_{horodatage}.xlsx',
        'Abonnements informatique', colonnes, donnees, ligne_total,
    )


@login_required
def export_informatique_pdf(request):
    colonnes, donnees, ligne_total, filtres = _abonnements_export(request)
    horodatage = timezone.now().strftime('%Y%m%d')
    libelles_filtre = {
        'actif': 'Abonnements actifs',
        'expire': 'Abonnements expirés',
        'bientot': 'Expiration sous 7 jours',
        'suspendu': 'Abonnements suspendus',
        'resilie': 'Abonnements résiliés',
    }
    sous_titre = libelles_filtre.get(filtres['filtre'], 'Tous les abonnements')
    return export_pdf(
        f'abonnements_informatique_{horodatage}.pdf',
        'Abonnements informatique',
        f'{sous_titre} — {len(donnees)} abonnement(s)',
        colonnes,
        donnees,
        ligne_total,
        ecole=user_school(request.user),
        paysage=True,
    )


# ─────────────────────────────── Hub ────────────────────────────────────────

@login_required
def hub_recouvrement(request):
    """Tableau de bord général du recouvrement + accès aux sous-modules."""
    aujourdhui = timezone.localdate()
    debut_mois = aujourdhui.replace(day=1)
    debut_annee = aujourdhui.replace(month=1, day=1)

    def totaux(queryset, champ='montant'):
        return {
            'mois': queryset.filter(date__gte=debut_mois).aggregate(t=Sum(champ))['t'] or ZERO,
            'annee': queryset.filter(date__gte=debut_annee).aggregate(t=Sum(champ))['t'] or ZERO,
            'nombre': queryset.count(),
        }

    depenses = Depense.objects.all()
    if not user_is_superadmin(request.user):
        ecole = user_school(request.user)
        depenses = (
            depenses.filter(cree_par__profil__ecole=ecole) if ecole else Depense.objects.none()
        )
    depenses_mois = depenses.filter(
        date_creation__date__gte=debut_mois
    ).aggregate(t=Sum('montant_ttc'))['t'] or ZERO
    depenses_annee = depenses.filter(
        date_creation__date__gte=debut_annee
    ).aggregate(t=Sum('montant_ttc'))['t'] or ZERO

    cuisine = totaux(_lignes_visibles(MODULES_SIMPLES['cuisine'], request.user))
    documents = totaux(_lignes_visibles(MODULES_SIMPLES['documents'], request.user))
    versements = totaux(_lignes_visibles(MODULES_SIMPLES['versements'], request.user))
    informatique = totaux(_abonnements_visibles(request.user))

    ventes = filter_by_user_school(VenteFourniture.objects.all(), request.user, 'ecole')
    ventes_mois = ventes.filter(
        date_vente__gte=debut_mois
    ).aggregate(t=Sum('montant_total'))['t'] or ZERO

    abonnements = _abonnements_visibles(request.user)
    nb_expires = abonnements.filter(statut='ACTIF', date_fin__lt=aujourdhui).count()
    nb_bientot = abonnements.filter(
        statut='ACTIF', date_fin__gte=aujourdhui, date_fin__lte=aujourdhui + timedelta(days=7)
    ).count()

    salaires_payes = _etats_salaire_payes_visibles(request.user)
    salaires_mois = salaires_payes.filter(
        periode__annee=aujourdhui.year, periode__mois=aujourdhui.month
    ).aggregate(t=Sum('salaire_net'))['t'] or ZERO

    sorties_mois = depenses_mois + cuisine['mois'] + documents['mois']
    sorties_annee = depenses_annee + cuisine['annee'] + documents['annee']

    cartes = [
        {
            'titre': 'Dépenses générales',
            'description': 'Factures, fournisseurs, validation et suivi des paiements.',
            'icone': 'fa-receipt',
            'couleur': 'primary',
            'url': reverse('depenses:dashboard_depenses'),
            'valeur': depenses_mois,
            'libelle_valeur': 'ce mois-ci (GNF)',
        },
        {
            'titre': 'Dépenses de la cuisine',
            'description': 'Achats et frais de la cuisine, avec exports PDF et Excel.',
            'icone': 'fa-utensils',
            'couleur': 'warning',
            'url': reverse('depenses:module_recouvrement', kwargs={'module': 'cuisine'}),
            'valeur': cuisine['mois'],
            'libelle_valeur': 'ce mois-ci (GNF)',
        },
        {
            'titre': 'Documents',
            'description': 'Impressions, actes et fournitures administratives.',
            'icone': 'fa-file-lines',
            'couleur': 'info',
            'url': reverse('depenses:module_recouvrement', kwargs={'module': 'documents'}),
            'valeur': documents['mois'],
            'libelle_valeur': 'ce mois-ci (GNF)',
        },
        {
            'titre': 'Versements',
            'description': 'Fonds versés en banque, à la direction ou en caisse.',
            'icone': 'fa-money-bill-transfer',
            'couleur': 'success',
            'url': reverse('depenses:module_recouvrement', kwargs={'module': 'versements'}),
            'valeur': versements['mois'],
            'libelle_valeur': 'ce mois-ci (GNF)',
        },
        {
            'titre': 'Informatique',
            'description': "Abonnements des élèves à la salle informatique, alertes et cartes.",
            'icone': 'fa-desktop',
            'couleur': 'purple',
            'url': reverse('depenses:dashboard_informatique'),
            'valeur': informatique['mois'],
            'libelle_valeur': 'encaissé ce mois-ci (GNF)',
            'alerte': (
                f"{nb_expires} expiré(s), {nb_bientot} à renouveler"
                if (nb_expires or nb_bientot) else ''
            ),
        },
        {
            'titre': 'Salaires enseignants',
            'description': 'Suivi des salaires payés par mois et par niveau (Maternelle à Lycée).',
            'icone': 'fa-chalkboard-teacher',
            'couleur': 'teal',
            'url': reverse('depenses:dashboard_salaires'),
            'valeur': salaires_mois,
            'libelle_valeur': 'payé ce mois-ci (GNF)',
        },
        {
            'titre': 'Fournitures scolaires',
            'description': 'Stock, ventes, chiffre d’affaires et marge.',
            'icone': 'fa-store',
            'couleur': 'orange',
            'url': reverse('depenses:dashboard_fournitures'),
            'valeur': ventes_mois,
            'libelle_valeur': 'vendu ce mois-ci (GNF)',
        },
        {
            'titre': 'Logistique',
            'description': "Biens de l'établissement et contributions en rames de papier.",
            'icone': 'fa-boxes-stacked',
            'couleur': 'danger',
            'url': reverse('depenses:dashboard_logistique'),
        },
        {
            'titre': 'Bibliothèque',
            'description': 'Catalogue, emprunts, réservations et statistiques.',
            'icone': 'fa-book-reader',
            'couleur': 'magic',
            'url': reverse('depenses:dashboard_bibliotheque'),
        },
        {
            'titre': 'Catégories de dépenses',
            'description': 'Paramétrer les catégories utilisées par les dépenses générales.',
            'icone': 'fa-tags',
            'couleur': 'rose',
            'url': reverse('depenses:gestion_categories'),
        },
    ]

    contexte = {
        'titre_page': 'Recouvrement',
        'cartes': cartes,
        'sorties_mois': sorties_mois,
        'sorties_annee': sorties_annee,
        'versements_mois': versements['mois'],
        'versements_annee': versements['annee'],
        'recettes_mois': informatique['mois'] + ventes_mois,
        'nb_operations_mois': (
            depenses.filter(date_creation__date__gte=debut_mois).count()
            + cuisine['nombre'] + documents['nombre'] + versements['nombre']
        ),
        'nb_expires': nb_expires,
        'nb_bientot': nb_bientot,
        'detail_modules': [
            {'titre': 'Dépenses générales', 'mois': depenses_mois, 'annee': depenses_annee},
            {'titre': 'Cuisine', 'mois': cuisine['mois'], 'annee': cuisine['annee']},
            {'titre': 'Documents', 'mois': documents['mois'], 'annee': documents['annee']},
            {'titre': 'Versements', 'mois': versements['mois'], 'annee': versements['annee']},
            {'titre': 'Informatique', 'mois': informatique['mois'], 'annee': informatique['annee']},
        ],
    }
    return render(request, 'depenses/recouvrement/hub.html', contexte)
