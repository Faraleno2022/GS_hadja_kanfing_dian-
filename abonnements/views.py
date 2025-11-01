from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from .models import (
    TypeAbonnement, Itineraire, MenuCantine,
    AbonnementBus, AbonnementCantine, PresenceCantine
)
from eleves.models import Eleve


@login_required
def tableau_bord_abonnements(request):
    """Tableau de bord des abonnements"""
    
    # Statistiques bus
    abonnements_bus_actifs = AbonnementBus.objects.filter(statut='ACTIF').count()
    abonnements_bus_total = AbonnementBus.objects.count()
    
    # Statistiques cantine
    abonnements_cantine_actifs = AbonnementCantine.objects.filter(statut='ACTIF').count()
    abonnements_cantine_total = AbonnementCantine.objects.count()
    
    # Itinéraires
    itineraires = Itineraire.objects.filter(actif=True)
    
    # Menus de la semaine
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    menus_semaine = MenuCantine.objects.filter(
        date_menu__gte=monday,
        date_menu__lt=monday + timedelta(days=7),
        actif=True
    ).order_by('date_menu')
    
    context = {
        'titre_page': 'Abonnements Bus & Cantine',
        'abonnements_bus_actifs': abonnements_bus_actifs,
        'abonnements_bus_total': abonnements_bus_total,
        'abonnements_cantine_actifs': abonnements_cantine_actifs,
        'abonnements_cantine_total': abonnements_cantine_total,
        'itineraires': itineraires,
        'menus_semaine': menus_semaine,
    }
    return render(request, 'abonnements/tableau_bord.html', context)


@login_required
def liste_abonnements_bus(request):
    """Liste des abonnements bus"""
    
    # Filtres
    itineraire_id = request.GET.get('itineraire')
    statut = request.GET.get('statut')
    search = request.GET.get('search')
    
    abonnements = AbonnementBus.objects.select_related('eleve', 'itineraire').all()
    
    if itineraire_id:
        abonnements = abonnements.filter(itineraire_id=itineraire_id)
    
    if statut:
        abonnements = abonnements.filter(statut=statut)
    
    if search:
        abonnements = abonnements.filter(
            Q(eleve__nom__icontains=search) |
            Q(eleve__prenom__icontains=search) |
            Q(eleve__matricule__icontains=search)
        )
    
    abonnements = abonnements.order_by('-date_creation')
    
    # Pour les filtres
    itineraires = Itineraire.objects.filter(actif=True)
    
    context = {
        'titre_page': 'Abonnements Bus',
        'abonnements': abonnements,
        'itineraires': itineraires,
        'itineraire_selectionne': itineraire_id,
        'statut_selectionne': statut,
        'search': search,
    }
    return render(request, 'abonnements/liste_bus.html', context)


@login_required
def creer_abonnement_bus(request):
    """Créer un abonnement bus"""
    
    if request.method == 'POST':
        eleve_id = request.POST.get('eleve')
        itineraire_id = request.POST.get('itineraire')
        duree = request.POST.get('duree')
        point_montee = request.POST.get('point_montee')
        point_descente = request.POST.get('point_descente')
        contact_urgence = request.POST.get('contact_urgence')
        observations = request.POST.get('observations', '')
        
        try:
            eleve = Eleve.objects.get(id=eleve_id)
            itineraire = Itineraire.objects.get(id=itineraire_id)
            type_bus = TypeAbonnement.objects.get(nom='BUS')
            
            # Calculer les dates et montant
            date_debut = date.today()
            if duree == 'MENSUEL':
                date_fin = date_debut + relativedelta(months=1)
                montant = type_bus.tarif_mensuel
            elif duree == 'TRIMESTRIEL':
                date_fin = date_debut + relativedelta(months=3)
                montant = type_bus.tarif_trimestriel
            else:  # ANNUEL
                date_fin = date_debut + relativedelta(years=1)
                montant = type_bus.tarif_annuel
            
            # Créer l'abonnement
            abonnement = AbonnementBus.objects.create(
                eleve=eleve,
                itineraire=itineraire,
                duree=duree,
                date_debut=date_debut,
                date_fin=date_fin,
                montant=montant,
                point_montee=point_montee,
                point_descente=point_descente,
                contact_urgence=contact_urgence,
                observations=observations,
                cree_par=request.user
            )
            
            messages.success(request, f'✅ Abonnement bus créé pour {eleve.nom_complet}')
            return redirect('abonnements:liste_bus')
            
        except Exception as e:
            messages.error(request, f'❌ Erreur: {str(e)}')
    
    # GET
    eleves = Eleve.objects.filter(statut='ACTIF').order_by('nom', 'prenom')
    itineraires = Itineraire.objects.filter(actif=True)
    type_bus = TypeAbonnement.objects.filter(nom='BUS').first()
    
    context = {
        'titre_page': 'Nouvel Abonnement Bus',
        'eleves': eleves,
        'itineraires': itineraires,
        'type_bus': type_bus,
    }
    return render(request, 'abonnements/creer_bus.html', context)


@login_required
def liste_abonnements_cantine(request):
    """Liste des abonnements cantine"""
    
    # Filtres
    regime = request.GET.get('regime')
    statut = request.GET.get('statut')
    search = request.GET.get('search')
    
    abonnements = AbonnementCantine.objects.select_related('eleve').all()
    
    if regime:
        abonnements = abonnements.filter(regime_alimentaire=regime)
    
    if statut:
        abonnements = abonnements.filter(statut=statut)
    
    if search:
        abonnements = abonnements.filter(
            Q(eleve__nom__icontains=search) |
            Q(eleve__prenom__icontains=search) |
            Q(eleve__matricule__icontains=search)
        )
    
    abonnements = abonnements.order_by('-date_creation')
    
    context = {
        'titre_page': 'Abonnements Cantine',
        'abonnements': abonnements,
        'regime_selectionne': regime,
        'statut_selectionne': statut,
        'search': search,
    }
    return render(request, 'abonnements/liste_cantine.html', context)


@login_required
def creer_abonnement_cantine(request):
    """Créer un abonnement cantine"""
    
    if request.method == 'POST':
        eleve_id = request.POST.get('eleve')
        duree = request.POST.get('duree')
        regime_alimentaire = request.POST.get('regime_alimentaire')
        allergies = request.POST.get('allergies', '')
        observations = request.POST.get('observations', '')
        
        try:
            eleve = Eleve.objects.get(id=eleve_id)
            type_cantine = TypeAbonnement.objects.get(nom='CANTINE')
            
            # Calculer les dates et montant
            date_debut = date.today()
            if duree == 'MENSUEL':
                date_fin = date_debut + relativedelta(months=1)
                montant = type_cantine.tarif_mensuel
            elif duree == 'TRIMESTRIEL':
                date_fin = date_debut + relativedelta(months=3)
                montant = type_cantine.tarif_trimestriel
            else:  # ANNUEL
                date_fin = date_debut + relativedelta(years=1)
                montant = type_cantine.tarif_annuel
            
            # Créer l'abonnement
            abonnement = AbonnementCantine.objects.create(
                eleve=eleve,
                duree=duree,
                date_debut=date_debut,
                date_fin=date_fin,
                montant=montant,
                regime_alimentaire=regime_alimentaire,
                allergies=allergies,
                observations=observations,
                cree_par=request.user
            )
            
            messages.success(request, f'✅ Abonnement cantine créé pour {eleve.nom_complet}')
            return redirect('abonnements:liste_cantine')
            
        except Exception as e:
            messages.error(request, f'❌ Erreur: {str(e)}')
    
    # GET
    eleves = Eleve.objects.filter(statut='ACTIF').order_by('nom', 'prenom')
    type_cantine = TypeAbonnement.objects.filter(nom='CANTINE').first()
    
    context = {
        'titre_page': 'Nouvel Abonnement Cantine',
        'eleves': eleves,
        'type_cantine': type_cantine,
    }
    return render(request, 'abonnements/creer_cantine.html', context)


@login_required
def gerer_presences_cantine(request):
    """Gérer les présences à la cantine"""
    
    date_selectionnee = request.GET.get('date')
    if date_selectionnee:
        try:
            date_obj = date.fromisoformat(date_selectionnee)
        except:
            date_obj = date.today()
    else:
        date_obj = date.today()
    
    # Abonnements actifs
    abonnements_actifs = AbonnementCantine.objects.filter(
        statut='ACTIF',
        date_debut__lte=date_obj,
        date_fin__gte=date_obj
    ).select_related('eleve')
    
    # Présences du jour
    presences = {}
    for presence in PresenceCantine.objects.filter(date=date_obj):
        presences[presence.abonnement_id] = presence
    
    # Menu du jour
    menu_jour = MenuCantine.objects.filter(date_menu=date_obj, actif=True).first()
    
    context = {
        'titre_page': 'Présences Cantine',
        'date_selectionnee': date_obj,
        'abonnements': abonnements_actifs,
        'presences': presences,
        'menu_jour': menu_jour,
    }
    return render(request, 'abonnements/presences_cantine.html', context)


@login_required
def enregistrer_presence_cantine(request):
    """Enregistrer une présence cantine (AJAX)"""
    
    if request.method == 'POST':
        abonnement_id = request.POST.get('abonnement_id')
        date_str = request.POST.get('date')
        present = request.POST.get('present') == 'true'
        
        try:
            abonnement = AbonnementCantine.objects.get(id=abonnement_id)
            date_obj = date.fromisoformat(date_str)
            
            presence, created = PresenceCantine.objects.update_or_create(
                abonnement=abonnement,
                date=date_obj,
                defaults={
                    'present': present,
                    'enregistre_par': request.user
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Présence enregistrée'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
