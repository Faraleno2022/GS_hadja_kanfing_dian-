"""Listes des élèves actifs selon leurs encaissements scolaires de l'année."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.http import Http404

from .suivi_listes import annoter_presence_paiement, classes_visibles, eleves_visibles


@login_required
def actifs_paiements(request):
    classes = classes_visibles(request)
    base = annoter_presence_paiement(eleves_visibles(request)).filter(
        statut='ACTIF', import_verrouille=False,
    )
    recherche = (request.GET.get('recherche') or '').strip()
    if recherche:
        base = base.filter(
            Q(nom__icontains=recherche) | Q(prenom__icontains=recherche) |
            Q(matricule__icontains=recherche)
        )
    repartition = list(base.order_by().values(
        'classe_id', 'classe__nom', 'classe__ecole__nom', 'classe__annee_scolaire'
    ).annotate(
        total=Count('pk'),
        avec=Count('pk', filter=Q(avec_paiement=True)),
        sans=Count('pk', filter=Q(avec_paiement=False)),
    ).order_by('classe__ecole__nom', 'classe__nom', 'classe__annee_scolaire', 'classe_id'))

    classe = None
    classe_id = request.GET.get('classe_id')
    if classe_id:
        try:
            classe_id = int(classe_id)
        except (TypeError, ValueError):
            raise Http404("Classe invalide.")
        classe = get_object_or_404(classes, pk=classe_id)
        base = base.filter(classe=classe)
    stats = base.aggregate(
        total=Count('pk'),
        avec=Count('pk', filter=Q(avec_paiement=True)),
        sans=Count('pk', filter=Q(avec_paiement=False)),
    )
    paiement = request.GET.get('paiement', 'sans')
    if paiement not in {'avec', 'sans', 'tous'}:
        paiement = 'sans'
    if paiement != 'tous':
        base = base.filter(avec_paiement=paiement == 'avec')

    valides = Q(
        paiements__statut='VALIDE', paiements__montant__gt=0,
        paiements__annee_scolaire=F('classe__annee_scolaire'),
    )
    eleves = base.annotate(
        nombre_paiements=Count('paiements', filter=valides),
        montant_paye=Coalesce(Sum('paiements__montant', filter=valides),
                             Value(0), output_field=DecimalField()),
    ).order_by('classe__ecole__nom', 'classe__nom', 'classe_id', 'nom', 'prenom', 'pk')
    page = Paginator(eleves, 30).get_page(request.GET.get('page'))
    filtres = request.GET.copy()
    filtres.pop('page', None)
    filtres['paiement'] = paiement
    return render(request, 'eleves/actifs_paiements.html', {
        'titre_page': 'Élèves actifs et paiements', 'classes': classes,
        'classe_selectionnee': classe, 'paiement': paiement, 'recherche': recherche,
        'stats': stats, 'repartition': repartition, 'page_obj': page,
        'filtres_url': filtres.urlencode(),
    })
