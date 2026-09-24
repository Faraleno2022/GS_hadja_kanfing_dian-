"""
Vues pour la gestion des rappels de paiement
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import timedelta

from .models import Relance, EcheancierPaiement
from .rappels import gestionnaire_rappels
from eleves.models import Eleve
from utilisateurs.utils import filter_by_user_school, user_school
from utilisateurs.permissions import any_permission_required

@login_required
@any_permission_required(['peut_valider_paiements', 'peut_consulter_rapports'])
def gerer_rappels(request):
    """Vue principale pour gérer les rappels de paiement"""
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else None
    
    # Filtres
    statut_filtre = request.GET.get('statut', '')
    canal_filtre = request.GET.get('canal', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    rappels = Relance.objects.select_related('eleve', 'eleve__classe', 'cree_par')
    
    # Filtrer par école si nécessaire
    rappels = filter_by_user_school(rappels, request.user, 'eleve__classe__ecole')
    
    # Appliquer les filtres
    if statut_filtre:
        rappels = rappels.filter(statut=statut_filtre)
    
    if canal_filtre:
        rappels = rappels.filter(canal=canal_filtre)
    
    if search:
        rappels = rappels.filter(
            Q(eleve__nom__icontains=search) |
            Q(eleve__prenom__icontains=search) |
            Q(eleve__matricule__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(rappels, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = gestionnaire_rappels.obtenir_statistiques_rappels(utilisateur=request.user)
    
    # Élèves en retard
    eleves_retard = gestionnaire_rappels.detecter_eleves_en_retard()
    eleves_retard = filter_by_user_school(eleves_retard, request.user, 'eleve__classe__ecole')
    
    context = {
        'titre_page': 'Gestion des Rappels de Paiement',
        'page_obj': page_obj,
        'rappels': page_obj,
        'stats': stats,
        'nb_eleves_retard': eleves_retard.count(),
        'statut_filtre': statut_filtre,
        'canal_filtre': canal_filtre,
        'search': search,
        'statut_choices': Relance.STATUT_CHOICES,
        'canal_choices': Relance.CANAL_CHOICES,
    }
    
    return render(request, 'paiements/gerer_rappels.html', context)

@login_required
@any_permission_required(['peut_valider_paiements'])
def creer_rappels_automatiques(request):
    """Crée automatiquement des rappels pour les élèves en retard"""
    if request.method == 'POST':
        canal = request.POST.get('canal', 'SMS')
        try:
            limite = int(request.POST.get('limite', 50))
        except (TypeError, ValueError):
            return HttpResponse("Limite invalide", status=400)
        if not 1 <= limite <= 200 or canal not in dict(Relance.CANAL_CHOICES):
            return HttpResponse("Canal invalide ou limite hors de 1 à 200", status=400)
        
        try:
            # Générer les rappels
            stats = gestionnaire_rappels.generer_rappels_automatiques(
                canal=canal,
                utilisateur=request.user,
                limite=limite
            )
            
            # Message de succès
            if stats['rappels_crees'] > 0:
                messages.success(
                    request,
                    f"✅ {stats['rappels_crees']} rappels créés avec succès via {canal}. "
                    f"{stats['total_eleves_retard']} élèves en retard détectés."
                )
            else:
                messages.info(
                    request,
                    f"ℹ️ Aucun nouveau rappel créé. {stats['total_eleves_retard']} élèves en retard détectés."
                )
            
            if stats['erreurs'] > 0:
                messages.warning(
                    request,
                    f"⚠️ {stats['erreurs']} erreurs lors de la création des rappels."
                )
            
        except Exception as e:
            messages.error(request, f"❌ Erreur lors de la génération des rappels: {e}")
    
    return redirect('paiements:gerer_rappels')

@login_required
@any_permission_required(['peut_valider_paiements'])
def creer_rappel_individuel(request, eleve_id):
    """Crée un rappel pour un élève spécifique"""
    eleve = get_object_or_404(filter_by_user_school(Eleve.objects.all(), request.user, 'classe__ecole'), id=eleve_id)
    
    # Vérifier l'accès à l'école
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else None
    if ecole and eleve.classe.ecole != ecole:
        messages.error(request, "❌ Vous n'avez pas accès à cet élève")
        return redirect('paiements:gerer_rappels')
    
    if request.method == 'POST':
        canal = request.POST.get('canal', 'SMS')
        message_personnalise = request.POST.get('message', '').strip()
        
        try:
            # Créer le rappel
            relance = gestionnaire_rappels.creer_rappel(
                eleve=eleve,
                canal=canal,
                message=message_personnalise if message_personnalise else None,
                utilisateur=request.user
            )
            
            if relance:
                messages.success(
                    request,
                    f"✅ Rappel créé pour {eleve.nom_complet} via {canal}"
                )
            else:
                messages.error(
                    request,
                    f"❌ Impossible de créer le rappel pour {eleve.nom_complet}"
                )
                
        except Exception as e:
            messages.error(request, f"❌ Erreur: {e}")
    
    return redirect('paiements:gerer_rappels')

@login_required
@any_permission_required(['peut_consulter_rapports'])
def eleves_en_retard(request):
    """Liste des élèves en retard de paiement"""
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else None
    
    # Récupérer les élèves en retard
    echeanciers_retard = gestionnaire_rappels.detecter_eleves_en_retard()
    
    echeanciers_retard = filter_by_user_school(echeanciers_retard, request.user, 'eleve__classe__ecole')
    
    # Filtres
    classe_filtre = request.GET.get('classe', '')
    search = request.GET.get('search', '')
    
    if classe_filtre:
        echeanciers_retard = echeanciers_retard.filter(eleve__classe__nom__icontains=classe_filtre)
    
    if search:
        echeanciers_retard = echeanciers_retard.filter(
            Q(eleve__nom__icontains=search) |
            Q(eleve__prenom__icontains=search) |
            Q(eleve__matricule__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(echeanciers_retard, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculer les données supplémentaires
    eleves_data = []
    for echeancier in page_obj:
        jours_retard = gestionnaire_rappels.calculer_jours_retard(echeancier)
        niveau_rappel = gestionnaire_rappels.calculer_niveau_rappel(echeancier.eleve.id)
        
        # Dernier rappel
        dernier_rappel = Relance.objects.filter(
            eleve=echeancier.eleve
        ).order_by('-date_creation').first()
        
        eleves_data.append({
            'echeancier': echeancier,
            'eleve': echeancier.eleve,
            'jours_retard': jours_retard,
            'niveau_rappel': niveau_rappel,
            'dernier_rappel': dernier_rappel,
            'solde_restant': echeancier.solde_restant
        })
    
    context = {
        'titre_page': 'Élèves en Retard de Paiement',
        'page_obj': page_obj,
        'eleves_data': eleves_data,
        'classe_filtre': classe_filtre,
        'search': search,
        'total_eleves_retard': echeanciers_retard.count(),
        'canal_choices': Relance.CANAL_CHOICES,
    }
    
    return render(request, 'paiements/eleves_en_retard.html', context)

@login_required
@any_permission_required(['peut_consulter_rapports'])
def apercu_message_rappel(request, eleve_id):
    """Aperçu du message de rappel pour un élève"""
    eleve = get_object_or_404(filter_by_user_school(Eleve.objects.all(), request.user, 'classe__ecole'), id=eleve_id)
    canal = request.GET.get('canal', 'SMS')
    
    try:
        echeancier = eleve.echeancier
        niveau_rappel = gestionnaire_rappels.calculer_niveau_rappel(eleve.id)
        message = gestionnaire_rappels.generer_message_rappel(
            eleve, echeancier, canal, niveau_rappel
        )
        
        return JsonResponse({
            'success': True,
            'message': message,
            'niveau_rappel': niveau_rappel,
            'solde_restant': float(echeancier.solde_restant),
            'jours_retard': gestionnaire_rappels.calculer_jours_retard(echeancier)
        })
        
    except EcheancierPaiement.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Pas d\'échéancier pour cet élève'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_POST
@any_permission_required(['peut_valider_paiements'])
def marquer_rappel_envoye(request, relance_id):
    """Marque un rappel comme envoyé"""
    get_object_or_404(filter_by_user_school(Relance.objects.all(), request.user, 'eleve__classe__ecole'), pk=relance_id)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or not isinstance(data.get('succes', True), bool):
            return JsonResponse({'success': False, 'error': 'Données invalides'}, status=400)
        succes = data.get('succes', True)
        erreur = data.get('erreur', None)
        
        gestionnaire_rappels.marquer_rappel_envoye(relance_id, succes, erreur)
        
        return JsonResponse({
            'success': True,
            'message': 'Statut mis à jour avec succès'
        })
        
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@any_permission_required(['peut_consulter_rapports', 'peut_valider_paiements'])
def statistiques_rappels(request):
    """Statistiques limitées à l'école de l'utilisateur et à la période choisie."""
    try:
        periode = int(request.GET.get('periode', 30))
    except (TypeError, ValueError):
        return HttpResponse("Période invalide", status=400)
    if not 1 <= periode <= 366:
        return HttpResponse("La période doit être comprise entre 1 et 366 jours", status=400)

    maintenant = timezone.now()
    date_debut = maintenant - timedelta(days=periode)
    rappels = filter_by_user_school(
        Relance.objects.filter(date_creation__gte=date_debut, date_creation__lte=maintenant),
        request.user, 'eleve__classe__ecole',
    )
    stats = {
        'total_rappels': rappels.count(),
        'rappels_envoyes': rappels.filter(statut='ENVOYEE').count(),
        'rappels_en_attente': rappels.filter(statut='ENREGISTREE').count(),
        'rappels_echec': rappels.filter(statut='ECHEC').count(),
        'eleves_concernes': rappels.values('eleve_id').distinct().count(),
    }
    rappels_par_semaine = []
    for i in range(0, periode, 7):
        debut = date_debut + timedelta(days=i)
        fin = min(debut + timedelta(days=7), maintenant)
        semaine = rappels.filter(date_creation__gte=debut)
        semaine = semaine.filter(date_creation__lte=fin) if fin == maintenant else semaine.filter(date_creation__lt=fin)
        rappels_par_semaine.append({
            'semaine': f"{debut.strftime('%d/%m')} - {fin.strftime('%d/%m')}",
            'nb_rappels': semaine.count(),
        })
    top_eleves = (
        rappels.values('eleve_id', 'eleve__nom', 'eleve__prenom', 'eleve__classe__nom')
        .annotate(nb_rappels=Count('id')).order_by('-nb_rappels', 'eleve_id')[:10]
    )
    return render(request, 'paiements/statistiques_rappels.html', {
        'titre_page': 'Statistiques des rappels', 'stats': stats, 'periode': periode,
        'rappels_par_semaine': rappels_par_semaine, 'top_eleves': top_eleves,
    })

@login_required
@any_permission_required(['peut_valider_paiements'])
def supprimer_rappel(request, relance_id):
    """Supprime un rappel"""
    relance = get_object_or_404(filter_by_user_school(Relance.objects.all(), request.user, 'eleve__classe__ecole'), id=relance_id)
    
    # Vérifier l'accès
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else None
    if ecole and relance.eleve.classe.ecole != ecole:
        messages.error(request, "❌ Vous n'avez pas accès à ce rappel")
        return redirect('paiements:gerer_rappels')
    
    if request.method == 'POST':
        eleve_nom = relance.eleve.nom_complet
        relance.delete()
        messages.success(request, f"✅ Rappel pour {eleve_nom} supprimé avec succès")
    
    return redirect('paiements:gerer_rappels')
