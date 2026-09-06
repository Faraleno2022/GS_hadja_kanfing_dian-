"""Affectation des élèves importés avant leur premier paiement."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from utilisateurs.utils import filter_by_user_school
from .models import Classe, Eleve
from .views_import import peut_importer_eleves


@login_required
@require_http_methods(['GET', 'POST'])
def repartir_importes(request):
    if not peut_importer_eleves(request.user):
        raise PermissionDenied("Vous n'avez pas la permission de répartir les élèves importés.")
    eleves = filter_by_user_school(
        Eleve.objects.filter(import_verrouille=True).select_related('classe__ecole'),
        request.user, 'classe__ecole',
    )
    if request.method == 'POST':
        if not all(request.POST.get(key, '').isdigit() for key in ('eleve_id', 'classe_id')):
            raise Http404("Élève ou classe introuvable.")
        with transaction.atomic():
            eleve = get_object_or_404(eleves.select_for_update(), pk=request.POST.get('eleve_id'))
            classe = get_object_or_404(Classe.objects.filter(
                ecole_id=eleve.classe.ecole_id, niveau=eleve.classe.niveau,
                annee_scolaire=eleve.classe.annee_scolaire,
            ), pk=request.POST.get('classe_id'))
            if classe.pk != eleve.classe_id:
                if eleve.paiements.exclude(statut__in=['REJETE', 'REMBOURSE']).exists():
                    messages.error(request, "Un paiement est déjà enregistré. Corrigez ce paiement avant de changer la classe.")
                    return redirect('eleves:repartir_importes')
                eleve.classe = classe
                eleve._current_user = request.user
                eleve._skip_matricule_generation = True
                eleve.save()
            messages.success(request, f"{eleve.nom_complet} affecté à {classe.nom}. Le dossier reste verrouillé jusqu'au premier paiement validé.")
            if request.POST.get('action') == 'payer':
                return redirect('paiements:ajouter_paiement_eleve', eleve_id=eleve.pk)
        return redirect('eleves:repartir_importes')

    recherche = request.GET.get('q', '').strip()
    if recherche:
        eleves = eleves.filter(Q(nom__icontains=recherche) | Q(prenom__icontains=recherche) | Q(matricule__icontains=recherche))
    page = Paginator(eleves.order_by('classe__ecole__nom', 'classe__niveau', 'nom', 'prenom'), 30).get_page(request.GET.get('page'))
    groupes = {}
    for eleve in page:
        key = (eleve.classe.ecole_id, eleve.classe.niveau, eleve.classe.annee_scolaire)
        if key not in groupes:
            groupes[key] = list(Classe.objects.filter(ecole_id=key[0], niveau=key[1], annee_scolaire=key[2]).order_by('nom'))
        eleve.classes_proposees = groupes[key]
    return render(request, 'eleves/repartir_importes.html', {'page_obj': page, 'recherche': recherche})
