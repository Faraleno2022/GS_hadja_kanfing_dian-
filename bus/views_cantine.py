"""
Vues pour la gestion des abonnements à la cantine scolaire
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
import io

from eleves.models import Eleve
from .models import AbonnementCantine
from .forms import AbonnementCantineForm
from utilisateurs.utils import user_is_admin, filter_by_user_school
from ecole_moderne.security_decorators import require_school_object


@login_required
def tableau_bord_cantine(request):
    """Tableau de bord des abonnements cantine avec alertes"""
    qs = AbonnementCantine.objects.select_related('eleve', 'eleve__classe', 'eleve__classe__ecole')
    if not user_is_admin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')
    
    # Statistiques générales
    total = qs.count()
    actifs = qs.filter(statut='ACTIF').count()
    expires = qs.filter(statut='EXPIRE').count()
    suspendus = qs.filter(statut='SUSPENDU').count()
    
    # Alertes
    today = timezone.localdate()
    
    # Abonnements expirés (non marqués comme EXPIRE)
    abonnements_expires = [a for a in qs.filter(statut='ACTIF') if a.est_expire]
    
    # Abonnements proches de l'expiration (dans les 7 jours)
    abonnements_proche_expiration = [a for a in qs.filter(statut='ACTIF') if a.est_proche_expiration and not a.est_expire]
    
    # Abonnements critiques (expire dans 3 jours ou moins)
    abonnements_critiques = [a for a in abonnements_proche_expiration if a.jours_restants <= 3]
    
    # Statistiques par type de repas
    stats_type_repas = {
        'dejeuner': qs.filter(type_repas='DEJEUNER', statut='ACTIF').count(),
        'gouter': qs.filter(type_repas='GOUTER', statut='ACTIF').count(),
        'complet': qs.filter(type_repas='COMPLET', statut='ACTIF').count(),
    }
    
    # Revenus mensuels estimés
    revenus_mensuel = qs.filter(
        statut='ACTIF',
        periodicite='MENSUEL'
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    context = {
        'titre_page': 'Gestion Cantine Scolaire',
        'total': total,
        'actifs': actifs,
        'expires': expires,
        'suspendus': suspendus,
        'abonnements_expires': abonnements_expires,
        'abonnements_proche_expiration': abonnements_proche_expiration,
        'abonnements_critiques': abonnements_critiques,
        'nb_expires': len(abonnements_expires),
        'nb_proche_expiration': len(abonnements_proche_expiration),
        'nb_critiques': len(abonnements_critiques),
        'stats_type_repas': stats_type_repas,
        'revenus_mensuel': revenus_mensuel,
    }
    return render(request, 'bus/cantine/tableau_bord.html', context)


@login_required
def liste_abonnements_cantine(request):
    """Liste des abonnements cantine avec filtres et recherche"""
    qs = AbonnementCantine.objects.select_related('eleve', 'eleve__classe', 'eleve__classe__ecole')
    if not user_is_admin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')
    
    # Recherche
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__matricule__icontains=q) |
            Q(contact_parent__icontains=q)
        )
    
    # Filtres
    filtre = (request.GET.get('filtre') or '').strip().lower()
    if filtre == 'actif':
        qs = qs.filter(statut='ACTIF')
    elif filtre == 'expire':
        qs = qs.filter(statut='EXPIRE')
    elif filtre == 'suspendu':
        qs = qs.filter(statut='SUSPENDU')
    elif filtre == 'proche_expiration':
        today = timezone.localdate()
        date_limite = today + timedelta(days=7)
        qs = qs.filter(statut='ACTIF', date_expiration__lte=date_limite, date_expiration__gte=today)
    elif filtre == 'critique':
        today = timezone.localdate()
        date_limite = today + timedelta(days=3)
        qs = qs.filter(statut='ACTIF', date_expiration__lte=date_limite, date_expiration__gte=today)
    
    # Filtre par type de repas
    type_repas = request.GET.get('type_repas')
    if type_repas:
        qs = qs.filter(type_repas=type_repas)
    
    # Filtre par classe
    classe_id = request.GET.get('classe')
    if classe_id:
        qs = qs.filter(eleve__classe_id=classe_id)
    
    # Tri
    qs = qs.order_by('-date_expiration', 'eleve__nom')
    
    context = {
        'titre_page': 'Liste des Abonnements Cantine',
        'abonnements': qs,
        'q': q,
        'filtre': filtre,
        'type_repas': type_repas,
    }
    return render(request, 'bus/cantine/liste.html', context)


@login_required
def creer_abonnement_cantine(request):
    """Créer un nouvel abonnement cantine"""
    if request.method == 'POST':
        form = AbonnementCantineForm(request.POST)
        if form.is_valid():
            abonnement = form.save()
            messages.success(request, f"Abonnement cantine créé pour {abonnement.eleve}")
            return redirect('bus:liste_abonnements_cantine')
    else:
        form = AbonnementCantineForm()
        
        # Pré-remplir l'élève si fourni dans l'URL
        eleve_id = request.GET.get('eleve')
        if eleve_id:
            try:
                eleve = Eleve.objects.get(pk=eleve_id)
                form.initial['eleve'] = eleve
                if eleve.responsable_principal:
                    form.initial['contact_parent'] = eleve.responsable_principal.telephone
            except Eleve.DoesNotExist:
                pass
    
    # Filtrer les élèves par école de l'utilisateur
    if not user_is_admin(request.user):
        form.fields['eleve'].queryset = filter_by_user_school(
            Eleve.objects.all(), 
            request.user, 
            'classe__ecole'
        )
    
    context = {
        'titre_page': 'Nouvel Abonnement Cantine',
        'form': form,
    }
    return render(request, 'bus/cantine/form.html', context)


@login_required
@require_school_object(model=AbonnementCantine, pk_kwarg='pk', field_path='eleve__classe__ecole')
def modifier_abonnement_cantine(request, pk):
    """Modifier un abonnement cantine existant"""
    abonnement = get_object_or_404(AbonnementCantine, pk=pk)
    
    if request.method == 'POST':
        form = AbonnementCantineForm(request.POST, instance=abonnement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Abonnement cantine modifié pour {abonnement.eleve}")
            return redirect('bus:liste_abonnements_cantine')
    else:
        form = AbonnementCantineForm(instance=abonnement)
    
    # Filtrer les élèves par école de l'utilisateur
    if not user_is_admin(request.user):
        form.fields['eleve'].queryset = filter_by_user_school(
            Eleve.objects.all(), 
            request.user, 
            'classe__ecole'
        )
    
    context = {
        'titre_page': 'Modifier Abonnement Cantine',
        'form': form,
        'abonnement': abonnement,
    }
    return render(request, 'bus/cantine/form.html', context)


@login_required
@require_school_object(model=AbonnementCantine, pk_kwarg='pk', field_path='eleve__classe__ecole')
def supprimer_abonnement_cantine(request, pk):
    """Supprimer un abonnement cantine"""
    abonnement = get_object_or_404(AbonnementCantine, pk=pk)
    
    if request.method == 'POST':
        eleve_nom = str(abonnement.eleve)
        abonnement.delete()
        messages.success(request, f"Abonnement cantine supprimé pour {eleve_nom}")
        return redirect('bus:liste_abonnements_cantine')
    
    context = {
        'titre_page': 'Supprimer Abonnement Cantine',
        'abonnement': abonnement,
    }
    return render(request, 'bus/cantine/confirmer_suppression.html', context)


@login_required
def export_cantine_excel(request):
    """Exporter la liste des abonnements cantine en Excel"""
    qs = AbonnementCantine.objects.select_related('eleve', 'eleve__classe')
    if not user_is_admin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')
    
    # Appliquer les mêmes filtres que la liste
    filtre = request.GET.get('filtre', '').strip().lower()
    if filtre == 'actif':
        qs = qs.filter(statut='ACTIF')
    elif filtre == 'expire':
        qs = qs.filter(statut='EXPIRE')
    elif filtre == 'proche_expiration':
        today = timezone.localdate()
        date_limite = today + timedelta(days=7)
        qs = qs.filter(statut='ACTIF', date_expiration__lte=date_limite, date_expiration__gte=today)
    
    # Créer le workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Abonnements Cantine"
    
    # En-têtes
    headers = [
        'Matricule', 'Nom', 'Prénom', 'Classe', 'Type Repas', 'Périodicité', 
        'Montant (GNF)', 'Date Début', 'Date Expiration', 'Jours Restants', 
        'Statut', 'Régime Alimentaire', 'Allergies', 'Contact Parent'
    ]
    ws.append(headers)
    
    # Données
    for abo in qs:
        ws.append([
            abo.eleve.matricule or '',
            abo.eleve.nom,
            abo.eleve.prenom,
            abo.eleve.classe.nom if abo.eleve.classe else '',
            abo.get_type_repas_display(),
            abo.get_periodicite_display(),
            float(abo.montant),
            abo.date_debut.strftime('%d/%m/%Y'),
            abo.date_expiration.strftime('%d/%m/%Y'),
            abo.jours_restants,
            abo.get_statut_display(),
            abo.regime_alimentaire or '',
            abo.allergies or '',
            abo.contact_parent or '',
        ])
    
    # Ajuster la largeur des colonnes
    for i, col in enumerate(ws.columns, 1):
        ws.column_dimensions[get_column_letter(i)].width = 15
    
    # Sauvegarder dans un buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    # Réponse HTTP
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="abonnements_cantine_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


@login_required
def alertes_cantine_json(request):
    """API JSON pour récupérer les alertes cantine (pour dashboard)"""
    qs = AbonnementCantine.objects.select_related('eleve', 'eleve__classe')
    if not user_is_admin(request.user):
        qs = filter_by_user_school(qs, request.user, 'eleve__classe__ecole')
    
    # Abonnements expirés
    expires = [a for a in qs.filter(statut='ACTIF') if a.est_expire]
    
    # Abonnements proches de l'expiration
    proche_expiration = [a for a in qs.filter(statut='ACTIF') if a.est_proche_expiration and not a.est_expire]
    
    # Abonnements critiques (3 jours ou moins)
    critiques = [a for a in proche_expiration if a.jours_restants <= 3]
    
    data = {
        'total': qs.count(),
        'actifs': qs.filter(statut='ACTIF').count(),
        'expires': {
            'count': len(expires),
            'abonnements': [
                {
                    'id': a.id,
                    'eleve': str(a.eleve),
                    'classe': a.eleve.classe.nom if a.eleve.classe else '',
                    'date_expiration': a.date_expiration.strftime('%d/%m/%Y'),
                    'jours_restants': a.jours_restants,
                }
                for a in expires[:10]  # Limiter à 10
            ]
        },
        'proche_expiration': {
            'count': len(proche_expiration),
            'abonnements': [
                {
                    'id': a.id,
                    'eleve': str(a.eleve),
                    'classe': a.eleve.classe.nom if a.eleve.classe else '',
                    'date_expiration': a.date_expiration.strftime('%d/%m/%Y'),
                    'jours_restants': a.jours_restants,
                }
                for a in proche_expiration[:10]
            ]
        },
        'critiques': {
            'count': len(critiques),
            'abonnements': [
                {
                    'id': a.id,
                    'eleve': str(a.eleve),
                    'classe': a.eleve.classe.nom if a.eleve.classe else '',
                    'date_expiration': a.date_expiration.strftime('%d/%m/%Y'),
                    'jours_restants': a.jours_restants,
                }
                for a in critiques
            ]
        }
    }
    
    return JsonResponse(data)


@login_required
def get_eleve_info_json(request, eleve_id):
    """API JSON pour récupérer les informations d'un élève"""
    import os
    
    try:
        eleve = Eleve.objects.select_related('classe', 'responsable_principal').get(pk=eleve_id)
        
        # Vérifier les permissions
        if not user_is_admin(request.user):
            eleves_qs = filter_by_user_school(Eleve.objects.all(), request.user, 'classe__ecole')
            if not eleves_qs.filter(pk=eleve_id).exists():
                return JsonResponse({'error': 'Permission refusée'}, status=403)
        
        # Gérer la photo de manière sécurisée
        photo_url = None
        if eleve.photo:
            try:
                # Vérifier que le fichier existe physiquement
                if hasattr(eleve.photo, 'path') and os.path.exists(eleve.photo.path):
                    photo_url = eleve.photo.url
                elif hasattr(eleve.photo, 'url'):
                    # Si pas de path (stockage distant), utiliser l'URL directement
                    photo_url = eleve.photo.url
            except Exception as e:
                # En cas d'erreur, on ignore simplement la photo
                print(f"Erreur lors de la récupération de la photo pour l'élève {eleve_id}: {e}")
                photo_url = None
        
        data = {
            'success': True,
            'nom_complet': f"{eleve.nom} {eleve.prenom}",
            'nom': eleve.nom,
            'prenom': eleve.prenom,
            'matricule': eleve.matricule or '',
            'classe': eleve.classe.nom if eleve.classe else '',
            'classe_id': eleve.classe.id if eleve.classe else None,
            'telephone_parent': eleve.responsable_principal.telephone if eleve.responsable_principal else '',
            'email_parent': eleve.responsable_principal.email if eleve.responsable_principal else '',
            'photo_url': photo_url,
        }
        return JsonResponse(data)
    except Eleve.DoesNotExist:
        return JsonResponse({'error': 'Élève non trouvé'}, status=404)
