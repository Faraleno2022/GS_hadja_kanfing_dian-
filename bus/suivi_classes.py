"""Synthèse bus par élève, sans recompter une grille à chaque versement."""
from collections import defaultdict
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from eleves.models import Eleve
from eleves.suivi_listes import classes_visibles
from .models import AbonnementBus, GrilleTarifaireBus


def contexte_suivi_classe(request):
    classes = classes_visibles(request)
    classe = None
    eleve = None
    choix_eleves = Eleve.objects.none()
    lignes = []
    page = None
    classe_id = request.GET.get('classe_id')
    if classe_id:
        try:
            classe_id = int(classe_id)
        except (TypeError, ValueError):
            raise Http404("Classe invalide.")
        classe = get_object_or_404(classes, pk=classe_id)
        choix_eleves = Eleve.objects.filter(classe=classe).order_by('nom', 'prenom', 'pk')
        eleve_id = request.GET.get('eleve_id')
        if eleve_id:
            try:
                eleve_id = int(eleve_id)
            except (TypeError, ValueError):
                raise Http404("Élève invalide.")
            eleve = get_object_or_404(choix_eleves, pk=eleve_id)
        selection = choix_eleves.filter(pk=eleve.pk) if eleve else choix_eleves
        versements = AbonnementBus.objects.select_related('grille').filter(
            annee_scolaire=classe.annee_scolaire,
        ).filter(
            Q(grille__isnull=True) |
            Q(grille__ecole_id=classe.ecole_id, grille__annee_scolaire=classe.annee_scolaire)
        )
        selection = selection.select_related('classe', 'classe__ecole').prefetch_related(
            Prefetch('abonnements_bus', queryset=versements.order_by('-date_debut', '-pk'),
                     to_attr='versements_suivi')
        )
        page = Paginator(selection, 25).get_page(request.GET.get('page_bus'))
        today = timezone.localdate()
        for inscrit in page:
            paiements = inscrit.versements_suivi
            dernier = paiements[0] if paiements else None
            grilles = {}
            totaux = defaultdict(lambda: defaultdict(lambda: Decimal('0')))
            for paiement in paiements:
                if paiement.grille_id:
                    grilles[paiement.grille_id] = paiement.grille
                    totaux[paiement.grille_id][paiement.periodicite] += paiement.montant
            situations = [
                {'grille': grille, **grille.situation_depuis_totaux(totaux[pk])['ANNUEL']}
                for pk, grille in grilles.items()
            ]
            # Les anciens versements sans grille n'indiquent pas le tarif dû.
            inconnu = not paiements or any(not paiement.grille_id for paiement in paiements)
            reste = None if inconnu else sum((item['reste'] for item in situations), Decimal('0'))
            statut, couleur = 'Sans abonnement', 'secondary'
            if dernier:
                if dernier.statut == 'SUSPENDU':
                    statut, couleur = 'Suspendu', 'warning'
                elif dernier.statut == 'EXPIRE' or dernier.date_expiration < today:
                    statut, couleur = 'Expiré', 'danger'
                elif dernier.date_debut > today:
                    statut, couleur = 'À venir', 'info'
                else:
                    statut, couleur = 'Actif', 'success'
            lignes.append({
                'eleve': inscrit, 'paiements': paiements, 'nombre_paiements': len(paiements),
                'montant_paye': sum((p.montant for p in paiements), Decimal('0')),
                'reste': reste, 'situations': situations, 'statut': statut, 'couleur': couleur,
                'carte_abonnement': dernier if statut == 'Actif' else None,
            })
    elif request.GET.get('eleve_id'):
        raise Http404("Sélectionnez une classe.")
    filtres = request.GET.copy()
    filtres.pop('page_bus', None)
    return {
        'classes_bus': classes, 'classe_bus': classe, 'eleves_bus': choix_eleves,
        'eleve_bus': eleve, 'lignes_bus': lignes, 'page_bus': page,
        'filtres_bus_url': filtres.urlencode(),
    }



def resume_transport_par_classe(versements):
    """Cumule les reçus bus et compte chaque tarif une fois par élève/grille."""
    groupes = list(versements.order_by().values(
        'eleve_id', 'eleve__classe_id', 'eleve__classe__nom',
        'grille_id', 'periodicite',
    ).annotate(montant=Sum('montant')))
    grilles = GrilleTarifaireBus.objects.in_bulk(
        {g['grille_id'] for g in groupes if g['grille_id']},
    )
    classes, eleves, grilles_eleves = {}, defaultdict(set), {}
    for groupe in groupes:
        classe_id = groupe['eleve__classe_id']
        row = classes.setdefault(classe_id, {
            'classe': groupe['eleve__classe__nom'] or 'Classe',
            'nb_abonnes': 0, 'total_du': Decimal('0'),
            'total_paye': Decimal('0'), 'reste': Decimal('0'),
        })
        eleves[classe_id].add(groupe['eleve_id'])
        row['total_paye'] += groupe['montant'] or Decimal('0')
        grille = grilles.get(groupe['grille_id'])
        if not grille or groupe['periodicite'] not in {'ANNUEL', 'T1', 'T2', 'T3'}:
            row['total_du'] = row['reste'] = None
            continue
        key = (classe_id, groupe['eleve_id'], grille.pk)
        grilles_eleves.setdefault(key, {})[groupe['periodicite']] = groupe['montant']
    for (classe_id, _eleve_id, grille_id), montants in grilles_eleves.items():
        situation = grilles[grille_id].situation_depuis_totaux(montants)['ANNUEL']
        row = classes[classe_id]
        if row['total_du'] is not None:
            row['total_du'] += situation['du']
            row['reste'] += situation['reste']
    for classe_id, row in classes.items():
        row['nb_abonnes'] = len(eleves[classe_id])
    lignes = sorted(classes.values(), key=lambda row: row['classe'])
    totals = {
        'nb_abonnes': sum(row['nb_abonnes'] for row in lignes),
        'total_paye': sum((row['total_paye'] for row in lignes), Decimal('0')),
    }
    for field in ('total_du', 'reste'):
        totals[field] = (
            None if any(row[field] is None for row in lignes)
            else sum((row[field] for row in lignes), Decimal('0'))
        )
    return lignes, totals
