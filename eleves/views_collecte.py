"""Liens de collecte et réception des propositions de classe."""
from datetime import timedelta
from functools import wraps
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from utilisateurs.utils import filter_by_user_school
from .collecte_permissions import peut_gerer_collecte
from .forms_collecte import (
    CHAMPS_ELEVE, CreerLienCollecteForm, DecisionCollecteForm, EnvoiCollecteForm,
    ExpirationCollecteForm, PropositionEleveForm, PropositionsFormSet,
)
from .models import Classe, Eleve
from .models_collecte import EnvoiCollecteEleves, LienCollecteEleves, PropositionEleve
from .services_collecte import decider_proposition, homonymes
from .suivi_listes import classes_visibles


def gestion_requise(view):
    @login_required
    @never_cache
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not peut_gerer_collecte(request.user):
            raise PermissionDenied("Vous n'avez pas la permission de gérer la collecte des élèves.")
        return view(request, *args, **kwargs)
    return wrapped


def liens_visibles(user):
    return filter_by_user_school(LienCollecteEleves.objects.select_related(
        'classe', 'ecole', 'cree_par__profil',
    ), user, 'ecole')


def url_publique(request, lien):
    return request.build_absolute_uri(reverse('collecte_eleves_public', args=[lien.token]))


@gestion_requise
@require_http_methods(['GET', 'POST'])
def gestion_collecte(request):
    form = CreerLienCollecteForm(
        request.POST if request.method == 'POST' else None, classes=classes_visibles(request),
        initial={'classe': request.GET.get('classe_id')},
    )
    if request.method == 'POST' and form.is_valid():
        lien = form.save(commit=False)
        lien.ecole = lien.classe.ecole
        lien.annee_scolaire = lien.classe.annee_scolaire
        lien.cree_par = request.user
        lien.save()
        messages.success(request, "Le lien est prêt à être partagé avec l'enseignant.")
        return redirect('eleves:detail_collecte', pk=lien.pk)
    liens = liens_visibles(request.user).annotate(
        nb_propositions=Count('envois__propositions'),
        nb_attente=Count('envois__propositions',
            filter=Q(envois__propositions__statut='EN_ATTENTE')),
    )
    page = Paginator(liens, 20).get_page(request.GET.get('page'))
    attente = PropositionEleve.objects.filter(envoi__lien__in=liens, statut='EN_ATTENTE').count()
    return render(request, 'eleves/collecte/gestion.html', {
        'form': form, 'page_obj': page, 'attente': attente,
    }, status=400 if request.method == 'POST' and form.errors else 200)


@gestion_requise
@require_http_methods(['GET', 'POST'])
def detail_collecte(request, pk):
    lien = get_object_or_404(liens_visibles(request.user), pk=pk)
    propositions = PropositionEleve.objects.filter(envoi__lien=lien).select_related(
        'envoi', 'eleve', 'traite_par',
    )
    expiration = ExpirationCollecteForm(instance=lien)
    decision = DecisionCollecteForm(propositions=propositions)
    status = 200
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('expiration', 'revoquer'):
            with transaction.atomic():
                lien = LienCollecteEleves.objects.select_for_update().get(pk=lien.pk)
                if action == 'revoquer':
                    if not lien.revoque_le:
                        lien.revoque_le = timezone.now()
                        lien.save(update_fields=['revoque_le'])
                    messages.success(request, "Lien révoqué. Les propositions déjà reçues restent disponibles.")
                    return redirect('eleves:detail_collecte', pk=lien.pk)
                if lien.revoque_le:
                    messages.error(request, "Ce lien a été révoqué. Créez un nouveau lien pour reprendre la collecte.")
                    return redirect('eleves:detail_collecte', pk=lien.pk)
                expiration = ExpirationCollecteForm(request.POST, instance=lien)
                if expiration.is_valid():
                    expiration.save()
                    messages.success(request, "La date de fin du lien a été mise à jour.")
                    return redirect('eleves:detail_collecte', pk=lien.pk)
                status = 400
        elif action in ('accepter', 'refuser'):
            decision = DecisionCollecteForm(request.POST, propositions=propositions)
            if decision.is_valid():
                nombre, erreurs = 0, []
                for proposition in decision.cleaned_data['propositions'].order_by('pk'):
                    try:
                        resultat = decider_proposition(
                            proposition.pk, request.user, action,
                            decision.cleaned_data['verrouiller'],
                            decision.cleaned_data['confirmer_homonymes'],
                        )
                        nombre += int(resultat is not None)
                    except ValidationError as exc:
                        erreurs.extend(exc.messages)
                if nombre:
                    messages.success(request, f"{nombre} proposition(s) {'acceptée(s)' if action == 'accepter' else 'refusée(s)'}.")
                elif not erreurs:
                    messages.info(request, "Ces propositions ont déjà été traitées.")
                for erreur in erreurs[:5]:
                    messages.error(request, erreur)
                return redirect('eleves:detail_collecte', pk=lien.pk)
            status = 400
        else:
            raise Http404
    statut = request.GET.get('statut', 'EN_ATTENTE')
    if statut in PropositionEleve.Statut.values:
        propositions = propositions.filter(statut=statut)
    elif statut != 'tous':
        raise Http404
    page = Paginator(propositions.order_by('-envoi__recu_le', 'pk'), 50).get_page(request.GET.get('page'))
    eleves = list(Eleve.objects.filter(
        classe_id=lien.classe_id, classe__ecole_id=lien.ecole_id,
    ).only('id', 'prenom', 'nom'))
    for proposition in page:
        proposition.homonymes = homonymes(proposition, eleves) if proposition.statut == 'EN_ATTENTE' else []
    return render(request, 'eleves/collecte/detail.html', {
        'lien': lien, 'lien_url': url_publique(request, lien),
        'expiration': expiration, 'decision': decision, 'page_obj': page,
        'statut_selectionne': statut, 'choix_statuts': PropositionEleve.Statut.choices,
    }, status=status)


@gestion_requise
@require_http_methods(['GET', 'POST'])
def verifier_proposition(request, pk):
    selection = PropositionEleve.objects.filter(
        envoi__lien__in=liens_visibles(request.user),
    ).select_related('envoi__lien__classe', 'eleve')
    proposition = get_object_or_404(selection, pk=pk)
    form = PropositionEleveForm(instance=proposition)
    status = 200
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in ('enregistrer', 'accepter', 'refuser'):
            raise Http404
        with transaction.atomic():
            Classe.objects.select_for_update().get(pk=proposition.envoi.lien.classe_id)
            # Éviter une jointure externe sous verrou sur l'élève facultatif.
            proposition = PropositionEleve.objects.select_for_update().get(pk=proposition.pk)
            if proposition.statut != 'EN_ATTENTE':
                messages.info(request, "Cette proposition a déjà été traitée.")
                return redirect('eleves:detail_collecte', pk=proposition.envoi.lien_id)
            form = PropositionEleveForm(request.POST, instance=proposition)
            if action == 'refuser' or form.is_valid():
                try:
                    with transaction.atomic():
                        if action != 'refuser':
                            form.save()
                        if action != 'enregistrer':
                            decider_proposition(
                                proposition.pk, request.user, action,
                                request.POST.get('verrouiller') == 'on',
                                request.POST.get('confirmer_homonymes') == 'on',
                            )
                    messages.success(request, "Proposition mise à jour." if action == 'enregistrer' else "Décision enregistrée.")
                    return redirect('eleves:detail_collecte', pk=proposition.envoi.lien_id)
                except ValidationError as exc:
                    form.add_error(None, exc)
            status = 400
    return render(request, 'eleves/collecte/verifier.html', {
        'proposition': proposition, 'form': form,
        'homonymes': homonymes(proposition),
        'verrouiller': request.method != 'POST' or request.POST.get('verrouiller') == 'on',
        'confirmer_homonymes': request.POST.get('confirmer_homonymes') == 'on',
    }, status=status)


def reponse_publique(request, context, status=200):
    response = render(request, 'eleves/collecte/public.html', context, status=status)
    response['Cache-Control'] = 'private, no-store, max-age=0'
    response['Referrer-Policy'] = 'strict-origin'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@never_cache
@require_http_methods(['GET', 'POST'])
@csrf_protect
@sensitive_post_parameters()
def collecte_publique(request, token):
    lien = get_object_or_404(LienCollecteEleves.objects.select_related(
        'classe', 'ecole', 'cree_par__profil',
    ), token=token)
    if not lien.est_actif:
        return reponse_publique(request, {'indisponible': True}, status=410)
    donnees = request.POST if request.method == 'POST' else None
    form = EnvoiCollecteForm(donnees, initial={'auteur': lien.destinataire, 'identifiant': uuid.uuid4()})
    formset = PropositionsFormSet(donnees, prefix='eleves')
    status, erreur = 200, ''
    if request.method == 'POST':
        valide, lignes_valides = form.is_valid(), formset.is_valid()
        if valide and lignes_valides:
            with transaction.atomic():
                # La révocation et la réception sont sérialisées sur ce lien.
                lien = LienCollecteEleves.objects.select_for_update().get(pk=lien.pk)
                if not lien.est_actif:
                    return reponse_publique(request, {'indisponible': True}, status=410)
                if EnvoiCollecteEleves.objects.filter(
                    lien=lien, identifiant=form.cleaned_data['identifiant'],
                ).exists():
                    return redirect(reverse('collecte_eleves_public', args=[token]) + '?envoye=1')
                lignes = [f.cleaned_data for f in formset if f.cleaned_data]
                if PropositionEleve.objects.filter(envoi__lien=lien).count() + len(lignes) > 1000:
                    erreur = "La limite de ce lien est atteinte. Demandez un nouveau lien à l'établissement."
                    status = 429
                else:
                    # Compteur en base sous verrou : partagé entre processus web.
                    if EnvoiCollecteEleves.objects.filter(
                        lien=lien, recu_le__gte=timezone.now() - timedelta(hours=1),
                    ).count() >= 30:
                        erreur = "Trop d'envois rapprochés. Réessayez dans une heure."
                        status = 429
                    else:
                        envoi = EnvoiCollecteEleves.objects.create(lien=lien, **form.cleaned_data)
                        PropositionEleve.objects.bulk_create([
                            PropositionEleve(envoi=envoi, **{k: ligne.get(k) for k in CHAMPS_ELEVE})
                            for ligne in lignes
                        ])
                        return redirect(reverse('collecte_eleves_public', args=[token]) + '?envoye=1')
        else:
            status = 400
    response = reponse_publique(request, {
        'lien': lien, 'form': form, 'formset': formset, 'erreur': erreur,
        'envoye': request.method == 'GET' and request.GET.get('envoye') == '1',
    }, status=status)
    if status == 429:
        response['Retry-After'] = '3600'
    return response
