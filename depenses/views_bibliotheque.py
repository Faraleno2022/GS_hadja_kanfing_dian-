from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal

from .models_bibliotheque import (
    CategorieLivre, Livre, Emprunt, Reservation,
    HistoriqueLivre, ParametreBibliotheque
)
from .forms import ReservationForm
from eleves.models import Eleve


def _livres_pour_utilisateur(user, actifs_seulement=True):
    from utilisateurs.utils import filter_by_user_school

    livres = Livre.objects.select_related('categorie')
    if actifs_seulement:
        livres = livres.filter(actif=True)
    return filter_by_user_school(livres, user, 'cree_par__profil__ecole')


def _eleves_pour_utilisateur(user):
    from utilisateurs.utils import filter_by_user_school

    eleves = Eleve.objects.filter(statut='ACTIF').select_related('classe', 'classe__ecole')
    return filter_by_user_school(eleves, user, 'classe__ecole')


def _reservations_pour_utilisateur(user):
    from utilisateurs.utils import filter_by_user_school

    reservations = Reservation.objects.select_related(
        'livre', 'eleve', 'eleve__classe', 'eleve__classe__ecole', 'cree_par'
    )
    return filter_by_user_school(reservations, user, 'eleve__classe__ecole')


def _parametres_bibliotheque():
    return ParametreBibliotheque.objects.first()


def _duree_reservation():
    parametres = _parametres_bibliotheque()
    return parametres.duree_reservation_defaut if parametres else 7


def _prochain_numero(modele, champ, prefixe):
    base = f"{prefixe}-{date.today().strftime('%Y%m%d')}"
    dernier = modele.objects.filter(
        **{f'{champ}__startswith': base}
    ).order_by(f'-{champ}').first()
    numero = 1
    if dernier:
        try:
            numero = int(getattr(dernier, champ).split('-')[-1]) + 1
        except (ValueError, IndexError):
            pass
    return f'{base}-{numero:04d}'


def _synchroniser_statut_livre(livre):
    if livre.exemplaires_disponibles > 0:
        livre.statut = 'DISPONIBLE'
    elif livre.reservations.filter(statut='DISPONIBLE').exists():
        livre.statut = 'RESERVE'
    elif livre.emprunts.filter(statut__in=['EN_COURS', 'EN_RETARD']).exists():
        livre.statut = 'EMPRUNTE'
    else:
        livre.statut = 'DISPONIBLE'


def _attribuer_reservations_en_attente(livre):
    """Reserve les exemplaires disponibles aux premiers eleves de la file."""
    if livre.statut in ['PERDU', 'EN_REPARATION', 'RETIRE']:
        return []

    maintenant = timezone.now()
    Reservation.objects.filter(
        livre=livre,
        statut='EN_ATTENTE',
        date_expiration__lte=maintenant,
    ).update(statut='EXPIREE')
    a_notifier = list(
        Reservation.objects.select_for_update().filter(
            livre=livre,
            statut='EN_ATTENTE',
            date_expiration__gt=maintenant,
        ).order_by('date_reservation')[:livre.exemplaires_disponibles]
    )
    expiration = maintenant + timedelta(days=_duree_reservation())
    for reservation in a_notifier:
        reservation.statut = 'DISPONIBLE'
        reservation.date_notification = maintenant
        reservation.date_expiration = expiration
        reservation.save(update_fields=['statut', 'date_notification', 'date_expiration'])
        livre.exemplaires_disponibles -= 1

    _synchroniser_statut_livre(livre)
    livre.save(update_fields=['exemplaires_disponibles', 'statut'])
    return a_notifier


def _actualiser_reservations_expirees(user):
    maintenant = timezone.now()
    ids = list(
        _reservations_pour_utilisateur(user).filter(
            statut__in=['EN_ATTENTE', 'DISPONIBLE'],
            date_expiration__lte=maintenant,
        ).values_list('pk', flat=True)
    )
    for reservation_id in ids:
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
            if reservation.statut not in ['EN_ATTENTE', 'DISPONIBLE']:
                continue
            livre = Livre.objects.select_for_update().get(pk=reservation.livre_id)
            etait_reservee = reservation.statut == 'DISPONIBLE'
            reservation.statut = 'EXPIREE'
            reservation.save(update_fields=['statut'])
            if etait_reservee:
                livre.exemplaires_disponibles = min(
                    livre.nombre_exemplaires,
                    livre.exemplaires_disponibles + 1,
                )
                _attribuer_reservations_en_attente(livre)
    return len(ids)


@login_required
def dashboard_bibliotheque(request):
    """Dashboard principal de la bibliothèque"""
    from utilisateurs.utils import user_school

    ecole = user_school(request.user)

    # Filtres de base par école
    livres_qs = Livre.objects.filter(actif=True)
    emprunts_qs = Emprunt.objects.all()
    reservations_qs = Reservation.objects.all()
    if ecole:
        livres_qs = livres_qs.filter(cree_par__profil__ecole=ecole)
        emprunts_qs = emprunts_qs.filter(cree_par__profil__ecole=ecole)
        reservations_qs = reservations_qs.filter(cree_par__profil__ecole=ecole)

    # Statistiques générales
    total_livres = livres_qs.count()
    total_exemplaires = livres_qs.aggregate(
        total=Sum('nombre_exemplaires')
    )['total'] or 0

    livres_disponibles = livres_qs.filter(
        statut='DISPONIBLE',
        exemplaires_disponibles__gt=0
    ).count()

    # Emprunts
    emprunts_en_cours = emprunts_qs.filter(statut='EN_COURS').count()
    emprunts_en_retard = emprunts_qs.filter(statut='EN_RETARD').count()

    # Réservations
    reservations_actives = reservations_qs.filter(
        statut__in=['EN_ATTENTE', 'DISPONIBLE']
    ).count()

    # Pénalités à recouvrer
    penalites_total = emprunts_qs.filter(
        penalite_payee=False,
        montant_penalite__gt=0
    ).aggregate(total=Sum('montant_penalite'))['total'] or 0

    # Derniers emprunts
    derniers_emprunts = emprunts_qs.select_related(
        'livre', 'eleve', 'cree_par'
    ).order_by('-date_emprunt')[:10]

    # Livres les plus empruntés
    livres_populaires = livres_qs.annotate(
        nb_emprunts=Count('emprunts')
    ).order_by('-nb_emprunts')[:10]

    # Répartition par catégorie
    repartition_categories = CategorieLivre.objects.annotate(
        nb_livres=Count('livres')
    ).filter(actif=True)
    
    context = {
        'titre_page': 'Dashboard Bibliothèque',
        'total_livres': total_livres,
        'total_exemplaires': total_exemplaires,
        'livres_disponibles': livres_disponibles,
        'emprunts_en_cours': emprunts_en_cours,
        'emprunts_en_retard': emprunts_en_retard,
        'reservations_actives': reservations_actives,
        'penalites_total': penalites_total,
        'derniers_emprunts': derniers_emprunts,
        'livres_populaires': livres_populaires,
        'repartition_categories': repartition_categories,
    }
    
    return render(request, 'depenses/bibliotheque/dashboard.html', context)


@login_required
def catalogue_livres(request):
    """Catalogue des livres"""
    from utilisateurs.utils import user_school

    # Filtres
    q = request.GET.get('q', '')
    categorie_id = request.GET.get('categorie', '')
    statut = request.GET.get('statut', '')
    langue = request.GET.get('langue', '')

    livres = Livre.objects.select_related('categorie').filter(actif=True)
    # Sécurité : filtrer par école
    ecole = user_school(request.user)
    if ecole:
        livres = livres.filter(cree_par__profil__ecole=ecole)
    
    if q:
        livres = livres.filter(
            Q(code_livre__icontains=q) |
            Q(isbn__icontains=q) |
            Q(titre__icontains=q) |
            Q(auteur__icontains=q) |
            Q(editeur__icontains=q) |
            Q(mots_cles__icontains=q)
        )
    
    if categorie_id:
        livres = livres.filter(categorie_id=categorie_id)
    
    if statut:
        livres = livres.filter(statut=statut)
    
    if langue:
        livres = livres.filter(langue=langue)
    
    categories = CategorieLivre.objects.filter(actif=True)
    
    context = {
        'titre_page': 'Catalogue de Livres',
        'livres': livres,
        'categories': categories,
        'q': q,
        'categorie_id': categorie_id,
        'statut': statut,
        'langue': langue,
    }
    
    return render(request, 'depenses/bibliotheque/catalogue.html', context)


@login_required
def liste_emprunts(request):
    """Liste des emprunts"""
    from utilisateurs.utils import user_school

    # Filtres
    statut = request.GET.get('statut', '')
    eleve_id = request.GET.get('eleve', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')

    emprunts = Emprunt.objects.select_related(
        'livre', 'eleve', 'eleve__classe', 'cree_par'
    ).all()
    # Sécurité : filtrer par école
    ecole = user_school(request.user)
    if ecole:
        emprunts = emprunts.filter(cree_par__profil__ecole=ecole)
    
    if statut:
        emprunts = emprunts.filter(statut=statut)
    
    if eleve_id:
        emprunts = emprunts.filter(eleve_id=eleve_id)
    
    if date_debut:
        emprunts = emprunts.filter(date_emprunt__gte=date_debut)
    
    if date_fin:
        emprunts = emprunts.filter(date_emprunt__lte=date_fin)
    
    context = {
        'titre_page': 'Emprunts',
        'emprunts': emprunts,
        'statut': statut,
        'eleve_id': eleve_id,
        'date_debut': date_debut,
        'date_fin': date_fin,
    }
    
    return render(request, 'depenses/bibliotheque/liste_emprunts.html', context)


@login_required
def creer_emprunt(request):
    """Créer un emprunt"""
    from utilisateurs.utils import user_school
    from django.db import transaction

    ecole = user_school(request.user)

    if request.method == 'POST':
        livre_id = request.POST.get('livre')
        eleve_id = request.POST.get('eleve')
        try:
            duree_jours = int(request.POST.get('duree_jours', 14))
        except (ValueError, TypeError):
            duree_jours = 14

        livre = get_object_or_404(Livre, pk=livre_id)
        eleve = get_object_or_404(Eleve.objects.select_related('classe', 'classe__ecole'), pk=eleve_id)

        # Sécurité : vérifier que le livre et l'élève appartiennent à l'école
        if ecole:
            livre_profil = getattr(getattr(livre, 'cree_par', None), 'profil', None)
            if livre_profil and livre_profil.ecole != ecole:
                messages.error(request, "Accès refusé : ce livre n'appartient pas à votre école.")
                return redirect('depenses:creer_emprunt')
            if eleve.classe and eleve.classe.ecole != ecole:
                messages.error(request, "Accès refusé : cet élève n'appartient pas à votre école.")
                return redirect('depenses:creer_emprunt')

        # Vérifier le nombre d'emprunts de l'élève
        params = ParametreBibliotheque.objects.first()
        if params:
            emprunts_actifs = Emprunt.objects.filter(
                eleve=eleve,
                statut='EN_COURS'
            ).count()

            if emprunts_actifs >= params.nombre_emprunts_max:
                messages.error(
                    request,
                    f'L\'élève a déjà atteint le nombre maximum d\'emprunts ({params.nombre_emprunts_max}).'
                )
                return redirect('depenses:creer_emprunt')

        with transaction.atomic():
            # Verrouiller le livre pour éviter la race condition sur les exemplaires
            livre_locked = Livre.objects.select_for_update().get(pk=livre.pk)

            # Vérifier la disponibilité (après verrouillage)
            if not livre_locked.est_disponible:
                messages.error(request, 'Ce livre n\'est pas disponible.')
                return redirect('depenses:creer_emprunt')

            # Créer l'emprunt
            today = date.today()
            prefix = f"EMP-{today.strftime('%Y%m%d')}"
            last_emp = Emprunt.objects.filter(
                numero_emprunt__startswith=prefix
            ).order_by('-numero_emprunt').first()

            if last_emp:
                last_num = int(last_emp.numero_emprunt.split('-')[-1])
                numero_emprunt = f"{prefix}-{last_num + 1:04d}"
            else:
                numero_emprunt = f"{prefix}-0001"

            emprunt = Emprunt.objects.create(
                numero_emprunt=numero_emprunt,
                livre=livre_locked,
                eleve=eleve,
                date_emprunt=today,
                date_retour_prevue=today + timedelta(days=duree_jours),
                etat_livre_emprunt=livre_locked.etat,
                cree_par=request.user
            )

            # Mettre à jour le livre
            livre_locked.exemplaires_disponibles -= 1
            if livre_locked.exemplaires_disponibles == 0:
                livre_locked.statut = 'EMPRUNTE'
            livre_locked.save()

            # Historique
            HistoriqueLivre.objects.create(
                livre=livre_locked,
                action='EMPRUNT',
                description=f'Emprunté par {eleve} - {numero_emprunt}',
                utilisateur=request.user
            )

        messages.success(request, f'Emprunt créé avec succès. N° {numero_emprunt}')
        return redirect('depenses:liste_emprunts')

    livres = Livre.objects.filter(actif=True, statut='DISPONIBLE')
    eleves = Eleve.objects.filter(statut='ACTIF').select_related('classe')
    # Sécurité : filtrer par école
    if ecole:
        livres = livres.filter(cree_par__profil__ecole=ecole)
        eleves = eleves.filter(classe__ecole=ecole)
    params = ParametreBibliotheque.objects.first()

    context = {
        'titre_page': 'Nouvel Emprunt',
        'livres': livres,
        'eleves': eleves,
        'params': params,
    }

    return render(request, 'depenses/bibliotheque/form_emprunt.html', context)


@login_required
def retourner_livre(request, emprunt_id):
    """Retourner un livre"""
    from utilisateurs.utils import user_school
    from django.db import transaction

    emprunt = get_object_or_404(
        Emprunt.objects.select_related('livre', 'eleve', 'eleve__classe', 'eleve__classe__ecole'),
        pk=emprunt_id
    )

    # Sécurité : vérifier l'appartenance à l'école
    ecole = user_school(request.user)
    if ecole and emprunt.eleve.classe and emprunt.eleve.classe.ecole != ecole:
        messages.error(request, "Accès refusé : cet emprunt n'appartient pas à votre école.")
        return redirect('depenses:liste_emprunts')

    if request.method == 'POST':
        etat_retour = request.POST.get('etat_retour')
        observations = request.POST.get('observations', '')
        reservations_notifiees = []

        with transaction.atomic():
            # Verrouiller l'emprunt pour éviter le double retour
            emprunt_locked = Emprunt.objects.select_for_update().get(pk=emprunt.pk)

            if emprunt_locked.statut == 'RETOURNE':
                messages.warning(request, 'Ce livre a déjà été retourné.')
                return redirect('depenses:liste_emprunts')

            # Mettre à jour l'emprunt
            emprunt_locked.date_retour_effectif = date.today()
            emprunt_locked.etat_livre_retour = etat_retour
            emprunt_locked.observations_retour = observations
            emprunt_locked.statut = 'RETOURNE'
            emprunt_locked.traite_par = request.user

            # Calculer les pénalités
            params = ParametreBibliotheque.objects.first()
            if params:
                emprunt_locked.calculer_penalite(params.penalite_retard_journalier)
            else:
                emprunt_locked.calculer_penalite()

            emprunt_locked.save()

            # Mettre à jour le livre (verrouillé aussi)
            livre = Livre.objects.select_for_update().get(pk=emprunt_locked.livre_id)
            livre.exemplaires_disponibles += 1
            livre.statut = 'DISPONIBLE'
            livre.etat = etat_retour
            livre.save()
            reservations_notifiees = _attribuer_reservations_en_attente(livre)

            # Historique
            HistoriqueLivre.objects.create(
                livre=livre,
                action='RETOUR',
                description=f'Retourné par {emprunt_locked.eleve} - {emprunt_locked.numero_emprunt}',
                utilisateur=request.user
            )

        if emprunt_locked.montant_penalite > 0:
            messages.warning(
                request,
                f'Livre retourné. Pénalité de retard : {emprunt_locked.montant_penalite:,.0f} GNF'
            )
        else:
            messages.success(request, 'Livre retourné avec succès.')

        if reservations_notifiees:
            eleves_notifies = ', '.join(
                str(item.eleve) for item in reservations_notifiees
            )
            messages.info(
                request,
                f'Le livre retourné a été réservé automatiquement pour : {eleves_notifies}.',
            )

        return redirect('depenses:liste_emprunts')

    context = {
        'titre_page': 'Retour de Livre',
        'emprunt': emprunt,
    }

    return render(request, 'depenses/bibliotheque/retour_livre.html', context)


@login_required
def liste_reservations(request):
    """Tableau de suivi des reservations de l'ecole."""
    _actualiser_reservations_expirees(request.user)
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '').strip()
    reservations = _reservations_pour_utilisateur(request.user)
    stats = reservations.aggregate(
        total=Count('id'),
        en_attente=Count('id', filter=Q(statut='EN_ATTENTE')),
        disponibles=Count('id', filter=Q(statut='DISPONIBLE')),
        empruntees=Count('id', filter=Q(statut='EMPRUNTEE')),
        terminees=Count('id', filter=Q(statut__in=['ANNULEE', 'EXPIREE'])),
    )
    if q:
        reservations = reservations.filter(
            Q(numero_reservation__icontains=q)
            | Q(livre__titre__icontains=q)
            | Q(eleve__matricule__icontains=q)
            | Q(eleve__nom__icontains=q)
            | Q(eleve__prenom__icontains=q)
        )
    if statut:
        reservations = reservations.filter(statut=statut)

    return render(request, 'depenses/bibliotheque/liste_reservations.html', {
        'titre_page': 'Réservations de livres',
        'reservations': reservations.order_by('-date_reservation'),
        'stats': stats,
        'q': q,
        'statut': statut,
        'statut_choices': Reservation.STATUT_CHOICES,
    })


@login_required
def creer_reservation(request):
    """Ajouter un eleve a la file de reservation d'un livre."""
    kwargs = {'user': request.user}
    if request.method == 'POST':
        form = ReservationForm(request.POST, **kwargs)
        if form.is_valid():
            reservation = None
            with transaction.atomic():
                livre = get_object_or_404(
                    _livres_pour_utilisateur(request.user).select_for_update(),
                    pk=form.cleaned_data['livre'].pk,
                )
                eleve = get_object_or_404(
                    _eleves_pour_utilisateur(request.user),
                    pk=form.cleaned_data['eleve'].pk,
                )
                actives = Reservation.objects.select_for_update().filter(
                    eleve=eleve,
                    statut__in=['EN_ATTENTE', 'DISPONIBLE'],
                )
                parametres = _parametres_bibliotheque()
                limite = parametres.nombre_reservations_max if parametres else 2
                if actives.filter(livre=livre).exists():
                    form.add_error('livre', "Cet élève a déjà une réservation active pour ce livre.")
                elif actives.count() >= limite:
                    form.add_error(
                        'eleve',
                        f"Cet élève a atteint la limite de {limite} réservation(s) active(s).",
                    )
                else:
                    reservation = Reservation.objects.create(
                        numero_reservation=_prochain_numero(
                            Reservation, 'numero_reservation', 'RES'
                        ),
                        livre=livre,
                        eleve=eleve,
                        date_expiration=timezone.now() + timedelta(days=_duree_reservation()),
                        statut='EN_ATTENTE',
                        observations=form.cleaned_data.get('observations', ''),
                        cree_par=request.user,
                    )
                    _attribuer_reservations_en_attente(livre)
                    reservation.refresh_from_db()
                    HistoriqueLivre.objects.create(
                        livre=livre,
                        action='RESERVATION',
                        description=(
                            f'Réservation par {eleve} - {reservation.numero_reservation}'
                        ),
                        utilisateur=request.user,
                    )
            if reservation:
                if reservation.statut == 'DISPONIBLE':
                    messages.success(
                        request,
                        f'Réservation {reservation.numero_reservation} créée. '
                        'Un exemplaire est réservé et disponible pour cet élève.',
                    )
                else:
                    messages.success(
                        request,
                        f'Réservation {reservation.numero_reservation} ajoutée à la file d’attente.',
                    )
                return redirect('depenses:liste_reservations')
    else:
        initial = {}
        if request.GET.get('livre'):
            initial['livre'] = request.GET['livre']
        if request.GET.get('eleve'):
            initial['eleve'] = request.GET['eleve']
        form = ReservationForm(initial=initial, **kwargs)

    return render(request, 'depenses/bibliotheque/form_reservation.html', {
        'titre_page': 'Nouvelle réservation',
        'form': form,
        'parametres': _parametres_bibliotheque(),
        'duree_reservation': _duree_reservation(),
    })


@login_required
def annuler_reservation(request, reservation_id):
    if request.method != 'POST':
        return redirect('depenses:liste_reservations')

    reservation_visible = _reservations_pour_utilisateur(request.user).filter(
        pk=reservation_id
    ).exists()
    if not reservation_visible:
        messages.error(request, "Cette réservation n’appartient pas à votre école.")
        return redirect('depenses:liste_reservations')

    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
        if reservation.statut not in ['EN_ATTENTE', 'DISPONIBLE']:
            messages.warning(request, 'Cette réservation est déjà clôturée.')
            return redirect('depenses:liste_reservations')
        livre = Livre.objects.select_for_update().get(pk=reservation.livre_id)
        exemplaire_bloque = reservation.statut == 'DISPONIBLE'
        reservation.statut = 'ANNULEE'
        reservation.save(update_fields=['statut'])
        if exemplaire_bloque:
            livre.exemplaires_disponibles = min(
                livre.nombre_exemplaires,
                livre.exemplaires_disponibles + 1,
            )
            _attribuer_reservations_en_attente(livre)
        HistoriqueLivre.objects.create(
            livre=livre,
            action='RESERVATION',
            description=f'Réservation annulée - {reservation.numero_reservation}',
            utilisateur=request.user,
        )
    messages.success(request, f'Réservation {reservation.numero_reservation} annulée.')
    return redirect('depenses:liste_reservations')


@login_required
def emprunter_reservation(request, reservation_id):
    """Transformer un exemplaire deja bloque en emprunt, sans double retrait."""
    if request.method != 'POST':
        return redirect('depenses:liste_reservations')

    reservation_visible = _reservations_pour_utilisateur(request.user).filter(
        pk=reservation_id
    ).exists()
    if not reservation_visible:
        messages.error(request, "Cette réservation n’appartient pas à votre école.")
        return redirect('depenses:liste_reservations')

    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().select_related(
            'eleve', 'livre'
        ).get(pk=reservation_id)
        livre = Livre.objects.select_for_update().get(pk=reservation.livre_id)
        if reservation.est_expiree:
            reservation.statut = 'EXPIREE'
            reservation.save(update_fields=['statut'])
            livre.exemplaires_disponibles = min(
                livre.nombre_exemplaires,
                livre.exemplaires_disponibles + 1,
            )
            _attribuer_reservations_en_attente(livre)
            messages.error(request, 'Cette réservation a expiré.')
            return redirect('depenses:liste_reservations')
        if reservation.statut != 'DISPONIBLE':
            messages.error(request, "Le livre n’est pas encore disponible pour cette réservation.")
            return redirect('depenses:liste_reservations')

        parametres = _parametres_bibliotheque()
        limite = parametres.nombre_emprunts_max if parametres else 3
        emprunts_actifs = Emprunt.objects.filter(
            eleve=reservation.eleve,
            statut__in=['EN_COURS', 'EN_RETARD'],
        )
        if emprunts_actifs.count() >= limite:
            messages.error(
                request,
                f"L’élève a atteint la limite de {limite} emprunt(s) actif(s).",
            )
            return redirect('depenses:liste_reservations')
        if emprunts_actifs.filter(livre=livre).exists():
            messages.error(request, 'Cet élève possède déjà un emprunt actif pour ce livre.')
            return redirect('depenses:liste_reservations')

        duree = parametres.duree_emprunt_defaut if parametres else 14
        numero_emprunt = _prochain_numero(Emprunt, 'numero_emprunt', 'EMP')
        emprunt = Emprunt.objects.create(
            numero_emprunt=numero_emprunt,
            livre=livre,
            eleve=reservation.eleve,
            date_emprunt=date.today(),
            date_retour_prevue=date.today() + timedelta(days=duree),
            etat_livre_emprunt=livre.etat,
            observations_emprunt=f'Issu de {reservation.numero_reservation}',
            cree_par=request.user,
        )
        reservation.statut = 'EMPRUNTEE'
        reservation.save(update_fields=['statut'])
        _synchroniser_statut_livre(livre)
        livre.save(update_fields=['statut'])
        HistoriqueLivre.objects.create(
            livre=livre,
            action='EMPRUNT',
            description=f'Réservation convertie en emprunt - {numero_emprunt}',
            utilisateur=request.user,
        )

    messages.success(request, f'Emprunt {emprunt.numero_emprunt} créé avec succès.')
    return redirect('depenses:liste_emprunts')


@login_required
def liste_reservations_ancienne(request):
    """Liste des réservations"""
    from utilisateurs.utils import user_school

    ecole = user_school(request.user)

    reservations = Reservation.objects.select_related(
        'livre', 'eleve', 'eleve__classe', 'cree_par'
    ).order_by('-date_reservation')
    # Sécurité : filtrer par école
    if ecole:
        reservations = reservations.filter(cree_par__profil__ecole=ecole)

    context = {
        'titre_page': 'Réservations',
        'reservations': reservations,
    }

    return render(request, 'depenses/bibliotheque/liste_reservations.html', context)


@login_required
def statistiques_bibliotheque(request):
    """Statistiques de la bibliothèque"""
    from utilisateurs.utils import user_school

    ecole = user_school(request.user)

    # Période
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')

    if not date_debut:
        date_debut = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = date.today().strftime('%Y-%m-%d')

    # Emprunts par période
    emprunts = Emprunt.objects.filter(
        date_emprunt__gte=date_debut,
        date_emprunt__lte=date_fin
    )
    # Sécurité : filtrer par école
    if ecole:
        emprunts = emprunts.filter(cree_par__profil__ecole=ecole)

    # Pénalités = cumulatives (indépendantes de la fenêtre de dates d'emprunt).
    # On somme toutes les pénalités de l'école, sinon une pénalité sur un livre
    # emprunté il y a plus de 30 jours n'apparaîtrait jamais.
    penalites_qs = Emprunt.objects.filter(montant_penalite__gt=0)
    if ecole:
        penalites_qs = penalites_qs.filter(cree_par__profil__ecole=ecole)
    total_penalites = penalites_qs.aggregate(total=Sum('montant_penalite'))['total'] or 0
    penalites_impayees = penalites_qs.filter(penalite_payee=False).aggregate(
        total=Sum('montant_penalite'))['total'] or 0

    # Statistiques
    stats = {
        'total_emprunts': emprunts.count(),
        'emprunts_retournes': emprunts.filter(statut='RETOURNE').count(),
        'emprunts_en_cours': emprunts.filter(statut='EN_COURS').count(),
        'emprunts_en_retard': emprunts.filter(statut='EN_RETARD').count(),
        'total_penalites': total_penalites,
        'penalites_impayees': penalites_impayees,
    }

    # Livres les plus empruntés
    livres_populaires = Livre.objects.filter(
        emprunts__date_emprunt__gte=date_debut,
        emprunts__date_emprunt__lte=date_fin
    )
    if ecole:
        livres_populaires = livres_populaires.filter(cree_par__profil__ecole=ecole)
    livres_populaires = livres_populaires.annotate(
        nb_emprunts=Count('emprunts')
    ).order_by('-nb_emprunts')[:10]

    # Élèves les plus actifs
    eleves_actifs = Eleve.objects.filter(
        emprunts_livres__date_emprunt__gte=date_debut,
        emprunts_livres__date_emprunt__lte=date_fin
    )
    if ecole:
        eleves_actifs = eleves_actifs.filter(classe__ecole=ecole)
    eleves_actifs = eleves_actifs.annotate(
        nb_emprunts=Count('emprunts_livres')
    ).order_by('-nb_emprunts')[:10]

    context = {
        'titre_page': 'Statistiques Bibliothèque',
        'date_debut': date_debut,
        'date_fin': date_fin,
        'stats': stats,
        'livres_populaires': livres_populaires,
        'eleves_actifs': eleves_actifs,
    }

    return render(request, 'depenses/bibliotheque/statistiques.html', context)


# =====================================================================
#  GESTION DES CATÉGORIES DE LIVRES
# =====================================================================
@login_required
def gestion_categories_livres(request):
    """Lister et créer des catégories de livres."""
    if request.method == 'POST':
        nom = (request.POST.get('nom') or '').strip()
        code = (request.POST.get('code') or '').strip().upper()
        description = (request.POST.get('description') or '').strip()
        if not nom or not code:
            messages.error(request, "Le nom et le code de la catégorie sont obligatoires.")
        elif CategorieLivre.objects.filter(code=code).exists():
            messages.error(request, f"Le code « {code} » existe déjà.")
        else:
            CategorieLivre.objects.create(nom=nom, code=code, description=description, actif=True)
            messages.success(request, f"Catégorie « {nom} » créée.")
        return redirect('depenses:gestion_categories_livres')

    categories = CategorieLivre.objects.annotate(nb_livres=Count('livres')).order_by('nom')
    return render(request, 'depenses/bibliotheque/categories.html', {
        'titre_page': 'Catégories de livres',
        'categories': categories,
    })


@login_required
def modifier_categorie_livre(request, categorie_id):
    categorie = get_object_or_404(CategorieLivre, pk=categorie_id)
    if request.method == 'POST':
        categorie.nom = (request.POST.get('nom') or categorie.nom).strip()
        code = (request.POST.get('code') or categorie.code).strip().upper()
        if code != categorie.code and CategorieLivre.objects.filter(code=code).exclude(pk=categorie.pk).exists():
            messages.error(request, f"Le code « {code} » existe déjà.")
            return redirect('depenses:gestion_categories_livres')
        categorie.code = code
        categorie.description = (request.POST.get('description') or '').strip()
        categorie.actif = request.POST.get('actif') == '1'
        categorie.save()
        messages.success(request, "Catégorie modifiée.")
    return redirect('depenses:gestion_categories_livres')


@login_required
def supprimer_categorie_livre(request, categorie_id):
    categorie = get_object_or_404(CategorieLivre, pk=categorie_id)
    if request.method == 'POST':
        if categorie.livres.exists():
            messages.error(request, "Impossible de supprimer : des livres utilisent cette catégorie.")
        else:
            nom = categorie.nom
            categorie.delete()
            messages.success(request, f"Catégorie « {nom} » supprimée.")
    return redirect('depenses:gestion_categories_livres')


# =====================================================================
#  AJOUT / ÉDITION DE LIVRES
# =====================================================================
def _prochain_code_livre():
    """Génère un code livre unique LIV-0001, LIV-0002, ..."""
    import re as _re
    dernier = Livre.objects.filter(code_livre__startswith='LIV-').order_by('-code_livre').first()
    n = 1
    if dernier:
        m = _re.search(r'(\d+)$', dernier.code_livre)
        if m:
            n = int(m.group(1)) + 1
    return f"LIV-{n:04d}"


@login_required
def ajouter_livre(request):
    """Créer un nouveau livre."""
    categories = CategorieLivre.objects.filter(actif=True).order_by('nom')
    if request.method == 'POST':
        titre = (request.POST.get('titre') or '').strip()
        auteur = (request.POST.get('auteur') or '').strip()
        categorie_id = (request.POST.get('categorie') or '').strip()
        if not (titre and auteur and categorie_id.isdigit()):
            messages.error(request, "Titre, auteur et catégorie sont obligatoires.")
            return redirect('depenses:ajouter_livre')
        categorie = get_object_or_404(CategorieLivre, pk=int(categorie_id))

        def _int(v, defaut=None):
            try:
                return int(v)
            except (TypeError, ValueError):
                return defaut

        nb_ex = _int(request.POST.get('nombre_exemplaires'), 1) or 1
        code_livre = (request.POST.get('code_livre') or '').strip() or _prochain_code_livre()
        if Livre.objects.filter(code_livre=code_livre).exists():
            code_livre = _prochain_code_livre()

        livre = Livre(
            code_livre=code_livre,
            isbn=(request.POST.get('isbn') or '').strip(),
            titre=titre,
            auteur=auteur,
            categorie=categorie,
            editeur=(request.POST.get('editeur') or '').strip(),
            annee_publication=_int(request.POST.get('annee_publication')),
            edition=(request.POST.get('edition') or '').strip(),
            langue=(request.POST.get('langue') or 'Français').strip(),
            nombre_pages=_int(request.POST.get('nombre_pages')),
            resume=(request.POST.get('resume') or '').strip(),
            mots_cles=(request.POST.get('mots_cles') or '').strip(),
            emplacement=(request.POST.get('emplacement') or '').strip(),
            etat=(request.POST.get('etat') or 'BON').strip(),
            statut='DISPONIBLE',
            nombre_exemplaires=nb_ex,
            exemplaires_disponibles=nb_ex,
            actif=True,
            cree_par=request.user,
        )
        if request.FILES.get('couverture'):
            livre.couverture = request.FILES['couverture']
        prix = request.POST.get('prix_acquisition')
        if prix:
            try:
                livre.prix_acquisition = Decimal(prix.replace(',', '.'))
            except Exception:
                pass
        livre.save()
        messages.success(request, f"Livre « {titre} » ajouté au catalogue (code {code_livre}).")
        return redirect('depenses:catalogue_livres')

    return render(request, 'depenses/bibliotheque/livre_form.html', {
        'titre_page': 'Ajouter un livre',
        'categories': categories,
        'etat_choices': Livre.ETAT_CHOICES,
        'code_suggere': _prochain_code_livre(),
        'livre': None,
    })


@login_required
def modifier_livre(request, livre_id):
    livre = get_object_or_404(Livre, pk=livre_id)
    categories = CategorieLivre.objects.filter(actif=True).order_by('nom')
    if request.method == 'POST':
        def _int(v, defaut=None):
            try:
                return int(v)
            except (TypeError, ValueError):
                return defaut
        livre.titre = (request.POST.get('titre') or livre.titre).strip()
        livre.auteur = (request.POST.get('auteur') or livre.auteur).strip()
        cid = request.POST.get('categorie')
        if cid and cid.isdigit():
            livre.categorie_id = int(cid)
        livre.isbn = (request.POST.get('isbn') or '').strip()
        livre.editeur = (request.POST.get('editeur') or '').strip()
        livre.annee_publication = _int(request.POST.get('annee_publication'))
        livre.edition = (request.POST.get('edition') or '').strip()
        livre.langue = (request.POST.get('langue') or livre.langue).strip()
        livre.nombre_pages = _int(request.POST.get('nombre_pages'))
        livre.resume = (request.POST.get('resume') or '').strip()
        livre.mots_cles = (request.POST.get('mots_cles') or '').strip()
        livre.emplacement = (request.POST.get('emplacement') or '').strip()
        livre.etat = (request.POST.get('etat') or livre.etat).strip()
        nb_ex = _int(request.POST.get('nombre_exemplaires'), livre.nombre_exemplaires)
        if nb_ex is not None:
            delta = nb_ex - livre.nombre_exemplaires
            livre.nombre_exemplaires = nb_ex
            livre.exemplaires_disponibles = max(0, livre.exemplaires_disponibles + delta)
        if request.FILES.get('couverture'):
            livre.couverture = request.FILES['couverture']
        livre.save()
        messages.success(request, "Livre modifie.")
        return redirect('depenses:catalogue_livres')

    return render(request, 'depenses/bibliotheque/livre_form.html', {
        'titre_page': 'Modifier le livre',
        'categories': categories,
        'etat_choices': Livre.ETAT_CHOICES,
        'code_suggere': livre.code_livre,
        'livre': livre,
    })


@login_required
def supprimer_livre(request, livre_id):
    livre = get_object_or_404(Livre, pk=livre_id)
    if request.method == 'POST':
        titre = livre.titre
        livre.actif = False
        livre.statut = 'RETIRE'
        livre.save(update_fields=['actif', 'statut'])
        messages.success(request, "Livre retire du catalogue.")
    return redirect('depenses:catalogue_livres')
