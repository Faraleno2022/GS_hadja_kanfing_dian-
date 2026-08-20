# -*- coding: utf-8 -*-
"""
MySchoolGN - Vues d'activation de licence et création de compte
================================================================
Auteur : GS Hadja Kanfing Dian
"""

import json
import os
import re
from pathlib import Path

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db import transaction

from eleves.models import Ecole
from .models import Profil
from .services import attribuer_compte_principal

User = get_user_model()


# ─── Helpers licence ──────────────────────────────────────────────────────────
def _get_license_status():
    try:
        import license_manager as lm
        status = lm.check_license_or_trial()
        status['machine_id'] = lm.get_machine_id()
        status['machine_short'] = lm.get_machine_id_short()
        return status
    except Exception as e:
        return {'valid': True, 'reason': f'Module licence non disponible : {e}',
                'machine_id': 'N/A', 'machine_short': 'N/A', 'dev_mode': True}


# ─── Page principale d'activation ─────────────────────────────────────────────
@login_required
def activation_page(request):
    """Page d'activation de licence et gestion des comptes admin."""
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur principal.")
        return redirect('/')

    license_status = _get_license_status()

    context = {
        'license_status': license_status,
        'users': User.objects.select_related('profil', 'profil__ecole').all().order_by('-is_superuser', 'username'),
        'ecoles': (
            Ecole.objects
            .filter(etat='VALIDE')
            .exclude(profils__est_compte_principal=True)
            .distinct()
            .order_by('nom')
        ),
        'page_title': 'Activation & Comptes',
    }
    return render(request, 'utilisateurs/activation.html', context)


# ─── Activation de licence ────────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def activer_licence(request):
    """Reçoit un fichier .lic et l'active."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Accès refusé.'}, status=403)

    lic_file = request.FILES.get('lic_file')
    if not lic_file:
        messages.error(request, "Veuillez sélectionner un fichier .lic.")
        return redirect('utilisateurs:activation')

    try:
        content = lic_file.read().decode('utf-8')
        lic_data = json.loads(content)
    except Exception:
        messages.error(request, "Fichier de licence invalide ou corrompu.")
        return redirect('utilisateurs:activation')

    try:
        import license_manager as lm
        result = lm._validate_license_data(lic_data)
        if result['valid']:
            lm.save_license(lic_data)
            school = result.get('school', '')
            days   = result.get('days_left', 0)
            messages.success(request,
                f"✓ Licence activée avec succès ! "
                f"École : {school} | Expire dans {days} jour(s).")
        else:
            messages.error(request, f"Licence invalide : {result.get('reason', 'Erreur inconnue')}")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'activation : {e}")

    return redirect('utilisateurs:activation')


# ─── Création de compte utilisateur ──────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def creer_compte(request):
    """Crée le compte principal d'une école ; les sous-comptes sont ensuite délégués."""
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur principal.")
        return redirect('utilisateurs:activation')

    username   = request.POST.get('username', '').strip()
    password   = request.POST.get('password', '').strip()
    password2  = request.POST.get('password2', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name  = request.POST.get('last_name', '').strip()
    email      = request.POST.get('email', '').strip()
    telephone  = request.POST.get('telephone', '').strip()
    ecole_id   = request.POST.get('ecole', '').strip()

    # Validations
    if not username or not password or not telephone or not ecole_id:
        messages.error(request, "Nom d'utilisateur, téléphone, école et mot de passe sont obligatoires.")
        return redirect('utilisateurs:activation')

    if password != password2:
        messages.error(request, "Les mots de passe ne correspondent pas.")
        return redirect('utilisateurs:activation')

    if len(password) < 12:
        messages.error(request, "Le mot de passe doit contenir au moins 12 caractères.")
        return redirect('utilisateurs:activation')

    if not re.fullmatch(r'\+224\d{8,9}', telephone):
        messages.error(request, "Le téléphone doit respecter le format +224XXXXXXXXX.")
        return redirect('utilisateurs:activation')

    if User.objects.filter(username=username).exists():
        messages.error(request, f"L'utilisateur « {username} » existe déjà.")
        return redirect('utilisateurs:activation')

    try:
        ecole = Ecole.objects.get(pk=ecole_id, etat='VALIDE')
    except (Ecole.DoesNotExist, ValueError):
        messages.error(request, "École invalide ou non validée.")
        return redirect('utilisateurs:activation')

    if Profil.objects.filter(ecole=ecole, est_compte_principal=True).exists():
        messages.error(request, f"L'école « {ecole.nom} » possède déjà un compte principal.")
        return redirect('utilisateurs:activation')

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_staff=False,
                is_active=True,
            )
            profil, _created = Profil.objects.get_or_create(user=user)
            profil.telephone = telephone
            attribuer_compte_principal(profil, ecole)
            if not ecole.created_by_id:
                ecole.created_by = user
                ecole.save(update_fields=['created_by'])
        messages.success(request, f"✓ Compte principal « {username} » créé pour l'école « {ecole.nom} ».")
    except Exception as e:
        messages.error(request, f"Erreur lors de la création : {e}")

    return redirect('utilisateurs:activation')


# ─── Changer mot de passe admin ───────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def changer_mdp_admin(request):
    """Change le mot de passe du compte admin principal."""
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur principal.")
        return redirect('utilisateurs:activation')

    old_pass  = request.POST.get('old_password', '')
    new_pass  = request.POST.get('new_password', '')
    new_pass2 = request.POST.get('new_password2', '')

    if not request.user.check_password(old_pass):
        messages.error(request, "Mot de passe actuel incorrect.")
        return redirect('utilisateurs:activation')

    if new_pass != new_pass2:
        messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
        return redirect('utilisateurs:activation')

    if len(new_pass) < 6:
        messages.error(request, "Le nouveau mot de passe doit contenir au moins 6 caractères.")
        return redirect('utilisateurs:activation')

    request.user.set_password(new_pass)
    request.user.save()
    update_session_auth_hash(request, request.user)
    messages.success(request, "✓ Mot de passe modifié avec succès.")
    return redirect('utilisateurs:activation')


# ─── Supprimer un utilisateur ─────────────────────────────────────────────────
@login_required
@require_http_methods(["POST"])
def supprimer_compte(request, user_id):
    """Supprime un compte utilisateur (sauf le superuser courant)."""
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect('utilisateurs:activation')

    if user_id == request.user.id:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('utilisateurs:activation')

    try:
        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()
        messages.success(request, f"✓ Compte « {username} » supprimé.")
    except User.DoesNotExist:
        messages.error(request, "Utilisateur introuvable.")

    return redirect('utilisateurs:activation')


@login_required
def toggle_lecture_seule(request, user_id):
    """Active/désactive le mode lecture seule d'un utilisateur (superuser only)."""
    from .models import Profil
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect('utilisateurs:activation')

    if user_id == request.user.id:
        messages.error(request, "Vous ne pouvez pas vous mettre vous-même en lecture seule.")
        return redirect('utilisateurs:activation')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Utilisateur introuvable.")
        return redirect('utilisateurs:activation')

    if user.is_superuser:
        messages.error(request, "Un superutilisateur ne peut pas être mis en lecture seule.")
        return redirect('utilisateurs:activation')

    profil, _ = Profil.objects.get_or_create(
        user=user, defaults={'role': 'SECRETAIRE', 'telephone': '+224000000000'})
    profil.lecture_seule = not profil.lecture_seule
    profil.save(update_fields=['lecture_seule'])

    if profil.lecture_seule:
        messages.success(request, f"🔒 « {user.username} » est maintenant en LECTURE SEULE (consultation uniquement).")
    else:
        messages.success(request, f"🔓 « {user.username} » peut de nouveau effectuer des actions.")
    return redirect('utilisateurs:activation')
