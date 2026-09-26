"""Vues : abonnements d'un élève, exports, carnet et aides au réabonnement."""

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from eleves.models import Classe, Eleve
from utilisateurs.utils import filter_by_user_school

from . import abonnements_eleve as service_abonnements
from .models import AbonnementBus, AbonnementCantine

STATUTS_SORTIS = ('EXCLU', 'TRANSFERE', 'DIPLOME')


def _eleves_autorises(user):
    return filter_by_user_school(
        Eleve.objects.select_related('classe', 'classe__ecole', 'responsable_principal'),
        user,
        'classe__ecole',
    )


def classes_autorisees(user):
    """Classes de l'école de l'utilisateur, pour le choix Classe → Élève."""
    return filter_by_user_school(
        Classe.objects.select_related('ecole'), user, 'ecole'
    ).order_by('-annee_scolaire', 'nom')


def _service(request):
    service = (request.GET.get('type') or 'tous').lower()
    return service if service in ('tous', 'bus', 'cantine') else 'tous'


def _nom_fichier(prefixe, eleve, extension):
    return f"{prefixe}_{eleve.matricule}_{timezone.localdate():%Y%m%d}.{extension}"


@login_required
def choisir_eleve(request):
    return render(request, 'bus/abonnements_eleve_choix.html', {
        'titre_page': "Abonnements d'un élève",
        'classes': classes_autorisees(request.user),
    })


@login_required
def abonnements_eleve(request, eleve_id):
    eleve = get_object_or_404(_eleves_autorises(request.user), pk=eleve_id)
    service = _service(request)
    lignes = service_abonnements.lignes_abonnements(eleve, service)
    return render(request, 'bus/abonnements_eleve.html', {
        'titre_page': f"Abonnements de {eleve.nom_complet}",
        'eleve': eleve,
        'lignes': lignes,
        'totaux': service_abonnements.totaux(lignes),
        'service': service,
    })


@login_required
def abonnements_eleve_excel(request, eleve_id):
    eleve = get_object_or_404(_eleves_autorises(request.user), pk=eleve_id)
    lignes = service_abonnements.lignes_abonnements(eleve, _service(request))
    response = HttpResponse(
        service_abonnements.construire_excel(eleve, lignes),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{_nom_fichier("abonnements", eleve, "xlsx")}"'
    )
    return response


def _reponse_pdf(request, eleve_id, carnet):
    eleve = get_object_or_404(_eleves_autorises(request.user), pk=eleve_id)
    service = _service(request)
    lignes = service_abonnements.lignes_abonnements(eleve, service)
    pdf = service_abonnements.construire_pdf(eleve, lignes, carnet=carnet, service=service)
    response = HttpResponse(pdf, content_type='application/pdf')
    prefixe = 'carnet_abonnement' if carnet else 'abonnements'
    response['Content-Disposition'] = f'inline; filename="{_nom_fichier(prefixe, eleve, "pdf")}"'
    return response


@login_required
def abonnements_eleve_pdf(request, eleve_id):
    return _reponse_pdf(request, eleve_id, carnet=False)


@login_required
def carnet_abonnement_pdf(request, eleve_id):
    return _reponse_pdf(request, eleve_id, carnet=True)


@login_required
def eleves_classe_json(request, classe_id):
    """Élèves d'une classe, avec l'indication des abonnements déjà existants."""
    classe = get_object_or_404(classes_autorisees(request.user), pk=classe_id)
    eleves = list(
        Eleve.objects.filter(classe=classe)
        .exclude(statut__in=STATUTS_SORTIS)
        .order_by('nom', 'prenom')
        .values('id', 'nom', 'prenom', 'matricule')
    )
    ids = [e['id'] for e in eleves]
    avec_bus = set(AbonnementBus.objects.filter(eleve_id__in=ids).values_list('eleve_id', flat=True))
    avec_cantine = set(
        AbonnementCantine.objects.filter(eleve_id__in=ids).values_list('eleve_id', flat=True)
    )
    return JsonResponse({'eleves': [
        {
            'id': e['id'],
            'nom_complet': f"{e['nom']} {e['prenom']}",
            'matricule': e['matricule'],
            'abonne_bus': e['id'] in avec_bus,
            'abonne_cantine': e['id'] in avec_cantine,
        }
        for e in eleves
    ]})


@login_required
def reprise_abonnement_json(request, eleve_id, service):
    """Informations du dernier abonnement, pour éviter de les ressaisir."""
    eleve = get_object_or_404(_eleves_autorises(request.user), pk=eleve_id)
    if service == 'cantine':
        donnees = service_abonnements.reprise_cantine(eleve)
    elif service == 'bus':
        donnees = service_abonnements.reprise_bus(eleve)
    else:
        raise Http404
    donnees.update({
        'success': True,
        'eleve': {
            'id': eleve.pk,
            'nom_complet': eleve.nom_complet,
            'matricule': eleve.matricule,
            'classe': getattr(eleve.classe, 'nom', ''),
            'classe_id': eleve.classe_id,
        },
    })
    return JsonResponse(donnees)
