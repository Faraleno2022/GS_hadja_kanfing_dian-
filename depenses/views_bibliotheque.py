from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal

from .models_bibliotheque import (
    CategorieLivre, Livre, Emprunt, Reservation,
    HistoriqueLivre, ParametreBibliotheque
)
from eleves.models import Eleve


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
    
    if request.method == 'POST':
        livre_id = request.POST.get('livre')
        eleve_id = request.POST.get('eleve')
        duree_jours = int(request.POST.get('duree_jours', 14))
        
        livre = get_object_or_404(Livre, pk=livre_id)
        eleve = get_object_or_404(Eleve, pk=eleve_id)
        
        # Vérifier la disponibilité
        if not livre.est_disponible:
            messages.error(request, 'Ce livre n\'est pas disponible.')
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
            livre=livre,
            eleve=eleve,
            date_emprunt=today,
            date_retour_prevue=today + timedelta(days=duree_jours),
            etat_livre_emprunt=livre.etat,
            cree_par=request.user
        )
        
        # Mettre à jour le livre
        livre.exemplaires_disponibles -= 1
        if livre.exemplaires_disponibles == 0:
            livre.statut = 'EMPRUNTE'
        livre.save()
        
        # Historique
        HistoriqueLivre.objects.create(
            livre=livre,
            action='EMPRUNT',
            description=f'Emprunté par {eleve} - {numero_emprunt}',
            utilisateur=request.user
        )
        
        messages.success(request, f'Emprunt créé avec succès. N° {numero_emprunt}')
        return redirect('depenses:liste_emprunts')
    
    livres = Livre.objects.filter(actif=True, statut='DISPONIBLE')
    eleves = Eleve.objects.filter(statut='ACTIF').select_related('classe')
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
    
    emprunt = get_object_or_404(Emprunt, pk=emprunt_id)
    
    if request.method == 'POST':
        etat_retour = request.POST.get('etat_retour')
        observations = request.POST.get('observations', '')
        
        # Mettre à jour l'emprunt
        emprunt.date_retour_effectif = date.today()
        emprunt.etat_livre_retour = etat_retour
        emprunt.observations_retour = observations
        emprunt.statut = 'RETOURNE'
        emprunt.traite_par = request.user
        
        # Calculer les pénalités
        params = ParametreBibliotheque.objects.first()
        if params:
            emprunt.calculer_penalite(params.penalite_retard_journalier)
        else:
            emprunt.calculer_penalite()
        
        emprunt.save()
        
        # Mettre à jour le livre
        livre = emprunt.livre
        livre.exemplaires_disponibles += 1
        livre.statut = 'DISPONIBLE'
        livre.etat = etat_retour
        livre.save()
        
        # Historique
        HistoriqueLivre.objects.create(
            livre=livre,
            action='RETOUR',
            description=f'Retourné par {emprunt.eleve} - {emprunt.numero_emprunt}',
            utilisateur=request.user
        )
        
        if emprunt.montant_penalite > 0:
            messages.warning(
                request,
                f'Livre retourné. Pénalité de retard : {emprunt.montant_penalite:,.0f} GNF'
            )
        else:
            messages.success(request, 'Livre retourné avec succès.')
        
        return redirect('depenses:liste_emprunts')
    
    context = {
        'titre_page': 'Retour de Livre',
        'emprunt': emprunt,
    }
    
    return render(request, 'depenses/bibliotheque/retour_livre.html', context)


@login_required
def liste_reservations(request):
    """Liste des réservations"""
    
    reservations = Reservation.objects.select_related(
        'livre', 'eleve', 'eleve__classe', 'cree_par'
    ).order_by('-date_reservation')
    
    context = {
        'titre_page': 'Réservations',
        'reservations': reservations,
    }
    
    return render(request, 'depenses/bibliotheque/liste_reservations.html', context)


@login_required
def statistiques_bibliotheque(request):
    """Statistiques de la bibliothèque"""
    
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
    
    # Statistiques
    stats = {
        'total_emprunts': emprunts.count(),
        'emprunts_retournes': emprunts.filter(statut='RETOURNE').count(),
        'emprunts_en_cours': emprunts.filter(statut='EN_COURS').count(),
        'emprunts_en_retard': emprunts.filter(statut='EN_RETARD').count(),
        'total_penalites': emprunts.aggregate(total=Sum('montant_penalite'))['total'] or 0,
    }
    
    # Livres les plus empruntés
    livres_populaires = Livre.objects.filter(
        emprunts__date_emprunt__gte=date_debut,
        emprunts__date_emprunt__lte=date_fin
    ).annotate(
        nb_emprunts=Count('emprunts')
    ).order_by('-nb_emprunts')[:10]
    
    # Élèves les plus actifs
    eleves_actifs = Eleve.objects.filter(
        emprunts_livres__date_emprunt__gte=date_debut,
        emprunts_livres__date_emprunt__lte=date_fin
    ).annotate(
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
