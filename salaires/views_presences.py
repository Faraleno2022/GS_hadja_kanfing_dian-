from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal
import csv

from .models import Enseignant, PresenceEnseignant
from .forms import PresenceForm
from utilisateurs.utils import user_school, user_is_admin


@login_required
def liste_presences(request):
    """Liste des présences avec filtres"""
    user_school_obj = user_school(request.user)
    
    # Filtres
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    enseignant_id = request.GET.get('enseignant')
    statut = request.GET.get('statut')
    
    # Date par défaut: aujourd'hui
    if not date_debut:
        date_debut = date.today().strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = date.today().strftime('%Y-%m-%d')
    
    # Requête de base
    presences = PresenceEnseignant.objects.filter(
        enseignant__ecole=user_school_obj
    ).select_related('enseignant', 'pointe_par')
    
    # Appliquer les filtres
    if date_debut:
        presences = presences.filter(date__gte=date_debut)
    if date_fin:
        presences = presences.filter(date__lte=date_fin)
    if enseignant_id:
        presences = presences.filter(enseignant_id=enseignant_id)
    if statut:
        presences = presences.filter(statut=statut)
    
    # Statistiques
    stats = presences.aggregate(
        total=Count('id'),
        presents=Count('id', filter=Q(statut='PRESENT')),
        absents=Count('id', filter=Q(statut='ABSENT')),
        retards=Count('id', filter=Q(statut='RETARD')),
        total_heures=Sum('heures_travaillees')
    )
    
    # Liste des enseignants pour le filtre
    enseignants = Enseignant.objects.filter(
        ecole=user_school_obj,
        statut='ACTIF'
    ).order_by('nom', 'prenoms')
    
    context = {
        'presences': presences,
        'stats': stats,
        'enseignants': enseignants,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'enseignant_id': enseignant_id,
        'statut': statut,
        'statuts': PresenceEnseignant.STATUT_CHOICES,
    }
    
    return render(request, 'salaires/presences/liste.html', context)


@login_required
def pointer_presence(request):
    """Pointer la présence d'un ou plusieurs enseignants"""
    user_school_obj = user_school(request.user)
    
    if request.method == 'POST':
        date_pointage_str = request.POST.get('date')
        enseignants_ids = request.POST.getlist('enseignants')
        
        if not date_pointage_str or not enseignants_ids:
            messages.error(request, "Veuillez sélectionner une date et au moins un enseignant.")
            return redirect('salaires:pointer_presence')
        
        # Convertir la date string en objet date
        try:
            date_pointage = datetime.strptime(date_pointage_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Format de date invalide.")
            return redirect('salaires:pointer_presence')
        
        count_created = 0
        count_updated = 0
        
        for ens_id in enseignants_ids:
            statut = request.POST.get(f'statut_{ens_id}', 'PRESENT')
            heure_arrivee_str = request.POST.get(f'heure_arrivee_{ens_id}') or None
            heure_depart_str = request.POST.get(f'heure_depart_{ens_id}') or None
            heures_travaillees_str = request.POST.get(f'heures_travaillees_{ens_id}') or None
            observations = request.POST.get(f'observations_{ens_id}', '')
            justifie = request.POST.get(f'justifie_{ens_id}') == 'on'
            
            # Convertir les heures en objets time
            heure_arrivee = None
            heure_depart = None
            heures_travaillees = None
            
            if heure_arrivee_str:
                try:
                    heure_arrivee = datetime.strptime(heure_arrivee_str, '%H:%M').time()
                except ValueError:
                    pass
            
            if heure_depart_str:
                try:
                    heure_depart = datetime.strptime(heure_depart_str, '%H:%M').time()
                except ValueError:
                    pass
            
            if heures_travaillees_str:
                try:
                    heures_travaillees = Decimal(heures_travaillees_str)
                except:
                    pass
            
            # Créer ou mettre à jour la présence
            presence, created = PresenceEnseignant.objects.update_or_create(
                enseignant_id=ens_id,
                date=date_pointage,
                defaults={
                    'statut': statut,
                    'heure_arrivee': heure_arrivee,
                    'heure_depart': heure_depart,
                    'heures_travaillees': heures_travaillees,
                    'observations': observations,
                    'justifie': justifie,
                    'pointe_par': request.user,
                }
            )
            
            if created:
                count_created += 1
            else:
                count_updated += 1
        
        messages.success(
            request,
            f"Pointage enregistré: {count_created} nouveau(x), {count_updated} mis à jour."
        )
        return redirect('salaires:liste_presences')
    
    # GET: Afficher le formulaire
    date_pointage = request.GET.get('date', date.today().strftime('%Y-%m-%d'))
    
    # Récupérer les enseignants actifs
    enseignants = Enseignant.objects.filter(
        ecole=user_school_obj,
        statut='ACTIF'
    ).order_by('nom', 'prenoms')
    
    # Récupérer les présences existantes pour cette date
    presences_existantes = {}
    for presence in PresenceEnseignant.objects.filter(date=date_pointage, enseignant__ecole=user_school_obj):
        presences_existantes[presence.enseignant_id] = presence
    
    context = {
        'enseignants': enseignants,
        'date_pointage': date_pointage,
        'presences_existantes': presences_existantes,
        'statuts': PresenceEnseignant.STATUT_CHOICES,
    }
    
    return render(request, 'salaires/presences/pointer.html', context)


@login_required
def modifier_presence(request, presence_id):
    """Modifier une présence existante"""
    user_school_obj = user_school(request.user)
    presence = get_object_or_404(
        PresenceEnseignant,
        id=presence_id,
        enseignant__ecole=user_school_obj
    )
    
    if request.method == 'POST':
        form = PresenceForm(request.POST, instance=presence)
        if form.is_valid():
            presence = form.save(commit=False)
            presence.pointe_par = request.user
            presence.save()
            messages.success(request, "Présence modifiée avec succès.")
            return redirect('salaires:liste_presences')
    else:
        form = PresenceForm(instance=presence)
    
    context = {
        'form': form,
        'presence': presence,
    }
    
    return render(request, 'salaires/presences/modifier.html', context)


@login_required
def supprimer_presence(request, presence_id):
    """Supprimer une présence"""
    user_school_obj = user_school(request.user)
    presence = get_object_or_404(
        PresenceEnseignant,
        id=presence_id,
        enseignant__ecole=user_school_obj
    )
    
    if request.method == 'POST':
        enseignant_nom = presence.enseignant.nom_complet
        date_presence = presence.date
        presence.delete()
        messages.success(
            request,
            f"Présence de {enseignant_nom} du {date_presence} supprimée."
        )
        return redirect('salaires:liste_presences')
    
    context = {
        'presence': presence,
    }
    
    return render(request, 'salaires/presences/supprimer.html', context)


@login_required
def rapport_presences(request):
    """Rapport de présences par enseignant et période"""
    user_school_obj = user_school(request.user)
    
    # Filtres
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    enseignant_id = request.GET.get('enseignant')
    
    # Dates par défaut: mois en cours
    if not date_debut:
        date_debut = date.today().replace(day=1).strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = date.today().strftime('%Y-%m-%d')
    
    # Requête de base
    presences = PresenceEnseignant.objects.filter(
        enseignant__ecole=user_school_obj,
        date__gte=date_debut,
        date__lte=date_fin
    ).select_related('enseignant')
    
    if enseignant_id:
        presences = presences.filter(enseignant_id=enseignant_id)
    
    # Regrouper par enseignant
    from collections import defaultdict
    rapport_par_enseignant = defaultdict(lambda: {
        'presents': 0,
        'absents': 0,
        'retards': 0,
        'conges': 0,
        'maladies': 0,
        'permissions': 0,
        'total_heures': Decimal('0'),
        'absences_injustifiees': 0,
    })
    
    for presence in presences:
        ens = presence.enseignant
        rapport_par_enseignant[ens]['enseignant'] = ens
        
        if presence.statut == 'PRESENT':
            rapport_par_enseignant[ens]['presents'] += 1
        elif presence.statut == 'ABSENT':
            rapport_par_enseignant[ens]['absents'] += 1
            if not presence.justifie:
                rapport_par_enseignant[ens]['absences_injustifiees'] += 1
        elif presence.statut == 'RETARD':
            rapport_par_enseignant[ens]['retards'] += 1
        elif presence.statut == 'CONGE':
            rapport_par_enseignant[ens]['conges'] += 1
        elif presence.statut == 'MALADIE':
            rapport_par_enseignant[ens]['maladies'] += 1
        elif presence.statut == 'PERMISSION':
            rapport_par_enseignant[ens]['permissions'] += 1
        
        if presence.heures_travaillees:
            rapport_par_enseignant[ens]['total_heures'] += presence.heures_travaillees
    
    # Convertir en liste
    rapport = list(rapport_par_enseignant.values())
    
    # Liste des enseignants pour le filtre
    enseignants = Enseignant.objects.filter(
        ecole=user_school_obj
    ).order_by('nom', 'prenoms')
    
    context = {
        'rapport': rapport,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'enseignant_id': enseignant_id,
        'enseignants': enseignants,
    }
    
    return render(request, 'salaires/presences/rapport.html', context)


@login_required
def export_presences_csv(request):
    """Exporter les présences en CSV"""
    user_school_obj = user_school(request.user)
    
    # Filtres
    date_debut = request.GET.get('date_debut', date.today().strftime('%Y-%m-%d'))
    date_fin = request.GET.get('date_fin', date.today().strftime('%Y-%m-%d'))
    enseignant_id = request.GET.get('enseignant')
    
    # Requête
    presences = PresenceEnseignant.objects.filter(
        enseignant__ecole=user_school_obj,
        date__gte=date_debut,
        date__lte=date_fin
    ).select_related('enseignant')
    
    if enseignant_id:
        presences = presences.filter(enseignant_id=enseignant_id)
    
    # Créer le CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="presences_{date_debut}_{date_fin}.csv"'
    response.write('\ufeff')  # BOM UTF-8
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Enseignant', 'Statut', 'Heure arrivée', 'Heure départ',
        'Heures travaillées', 'Justifié', 'Observations'
    ])
    
    for presence in presences:
        writer.writerow([
            presence.date.strftime('%d/%m/%Y'),
            presence.enseignant.nom_complet,
            presence.get_statut_display(),
            presence.heure_arrivee.strftime('%H:%M') if presence.heure_arrivee else '',
            presence.heure_depart.strftime('%H:%M') if presence.heure_depart else '',
            str(presence.heures_travaillees) if presence.heures_travaillees else '',
            'Oui' if presence.justifie else 'Non',
            presence.observations,
        ])
    
    return response
