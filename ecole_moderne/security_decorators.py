"""
Décorateurs de sécurité pour protéger les vues contre les attaques
"""
import functools
import logging
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
import time

logger = logging.getLogger(__name__)
User = get_user_model()

def admin_required(view_func):
    """
    Décorateur pour restreindre l'accès aux administrateurs uniquement
    """
    @functools.wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            logger.warning(f"Tentative d'accès admin non autorisée par: {request.user.username}")
            return HttpResponseForbidden("Accès réservé aux administrateurs.")
        return view_func(request, *args, **kwargs)
    return wrapper

def delete_permission_required(allowed_username="FELIXSUZANELENO", confirm_value="FELIXSUZANELENO", confirm_field="confirm_name"):
    """
    Décorateur pour restreindre toute opération de suppression à un seul utilisateur
    spécifique (par défaut 'FELIXSUZANELENO') et exiger une confirmation explicite
    du même nom en saisie.

    Comportement:
    - Si l'utilisateur courant n'est pas `allowed_username` -> 403
    - GET  -> affiche une page de confirmation avec champ texte à saisir
    - POST -> vérifie que request.POST[confirm_field] == confirm_value (casse stricte)

    La vue décorée ne doit contenir que la logique de suppression. Ce décorateur
    garantit que seule une requête POST confirmée atteint la vue.
    """
    from django.shortcuts import render
    from django.views.decorators.csrf import csrf_protect
    from django.utils.decorators import method_decorator

    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        @csrf_protect
        def wrapper(request, *args, **kwargs):
            # Refuser tout utilisateur autre que celui autorisé
            if request.user.username != allowed_username:
                logger.warning(
                    f"Suppression refusée: user={request.user.username}, ip={get_client_ip(request)}"
                )
                return HttpResponseForbidden("Suppression réservée à l'administrateur principal.")

            # Confirmation requise
            if request.method == 'GET':
                context = {
                    'confirm_value': confirm_value,
                    'confirm_field': confirm_field,
                    'action_url': request.get_full_path(),
                    'username': request.user.username,
                }
                return render(request, 'administration/confirm_delete.html', context)

            if request.method == 'POST':
                provided = request.POST.get(confirm_field, '')
                if provided != confirm_value:
                    # Si AJAX, renvoyer un JSON 403
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': 'Confirmation invalide.'}, status=403)
                    context = {
                        'confirm_value': confirm_value,
                        'confirm_field': confirm_field,
                        'action_url': request.get_full_path(),
                        'username': request.user.username,
                        'error': "Le nom de confirmation est incorrect."
                    }
                    return render(request, 'administration/confirm_delete.html', context, status=403)

                # Confirmation réussie -> exécuter la vue de suppression
                return view_func(request, *args, **kwargs)

            # Toute autre méthode refusée
            return HttpResponseForbidden("Méthode non autorisée.")

        return wrapper
    return decorator

def rate_limit(max_requests=10, window=60):
    """
    Décorateur pour limiter le nombre de requêtes par utilisateur
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                cache_key = f"rate_limit_user_{request.user.id}_{view_func.__name__}"
            else:
                client_ip = get_client_ip(request)
                cache_key = f"rate_limit_ip_{client_ip}_{view_func.__name__}"
            
            requests = cache.get(cache_key, 0)
            if requests >= max_requests:
                logger.warning(f"Rate limit dépassé pour {cache_key}")
                return HttpResponseForbidden("Trop de requêtes. Veuillez patienter.")
            
            cache.set(cache_key, requests + 1, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def secure_view(require_post=False, admin_only=False, rate_limit_requests=None):
    """
    Décorateur combiné pour sécuriser une vue
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        @csrf_protect
        def wrapper(request, *args, **kwargs):
            # Vérifier si admin requis
            if admin_only and not (request.user.is_staff or request.user.is_superuser):
                logger.warning(f"Accès admin refusé à: {request.user.username}")
                return HttpResponseForbidden("Accès réservé aux administrateurs.")
            
            # Vérifier la méthode HTTP
            if require_post and request.method != 'POST':
                return HttpResponseForbidden("Méthode non autorisée.")
            
            # Appliquer le rate limiting si spécifié
            if rate_limit_requests:
                cache_key = f"rate_limit_user_{request.user.id}_{view_func.__name__}"
                requests = cache.get(cache_key, 0)
                if requests >= rate_limit_requests:
                    logger.warning(f"Rate limit dépassé pour utilisateur: {request.user.username}")
                    return HttpResponseForbidden("Trop de requêtes. Veuillez patienter.")
                cache.set(cache_key, requests + 1, 60)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def audit_log(action_type):
    """
    Décorateur pour enregistrer les actions sensibles
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            client_ip = get_client_ip(request)
            
            try:
                response = view_func(request, *args, **kwargs)
                
                # Log de l'action réussie
                logger.info(f"ACTION: {action_type} | USER: {getattr(request.user, 'username', 'Anonymous')} | "
                           f"IP: {client_ip} | STATUS: SUCCESS | TIME: {time.time() - start_time:.2f}s")
                
                return response
                
            except Exception as e:
                # Log de l'erreur
                logger.error(f"ACTION: {action_type} | USER: {getattr(request.user, 'username', 'Anonymous')} | "
                            f"IP: {client_ip} | STATUS: ERROR | ERROR: {str(e)} | TIME: {time.time() - start_time:.2f}s")
                raise
                
        return wrapper
    return decorator

def validate_permissions(required_permissions):
    """
    Décorateur pour vérifier les permissions spécifiques
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perms(required_permissions):
                logger.warning(f"Permissions insuffisantes pour {request.user.username}: {required_permissions}")
                return HttpResponseForbidden("Permissions insuffisantes.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def prevent_brute_force(max_attempts=5, lockout_time=300):
    """
    Décorateur pour prévenir les attaques par force brute
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            client_ip = get_client_ip(request)
            cache_key = f"brute_force_{client_ip}_{view_func.__name__}"
            
            attempts = cache.get(cache_key, 0)
            if attempts >= max_attempts:
                logger.warning(f"Tentative de force brute bloquée pour IP: {client_ip}")
                return HttpResponseForbidden("Trop de tentatives. Compte temporairement bloqué.")
            
            try:
                response = view_func(request, *args, **kwargs)
                
                # Si la vue réussit, réinitialiser le compteur
                if hasattr(response, 'status_code') and response.status_code == 200:
                    cache.delete(cache_key)
                
                return response
                
            except Exception as e:
                # Incrémenter le compteur en cas d'échec
                cache.set(cache_key, attempts + 1, lockout_time)
                raise
                
        return wrapper
    return decorator

def sanitize_input(view_func):
    """
    Décorateur pour nettoyer les entrées utilisateur
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method == 'POST':
            # Nettoyer les données POST
            cleaned_post = request.POST.copy()
            for key, value in cleaned_post.items():
                if isinstance(value, str):
                    # Supprimer les caractères dangereux
                    cleaned_value = sanitize_string(value)
                    cleaned_post[key] = cleaned_value
            
            request.POST = cleaned_post
        
        return view_func(request, *args, **kwargs)
    return wrapper

def get_client_ip(request):
    """Obtient l'adresse IP réelle du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def sanitize_string(value):
    """
    Nettoie une chaîne de caractères des éléments dangereux
    """
    import re
    
    # Supprimer les balises HTML/JavaScript
    value = re.sub(r'<[^>]*>', '', value)
    
    # Supprimer les caractères de contrôle
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # Échapper les caractères SQL dangereux
    dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    for char in dangerous_chars:
        value = value.replace(char, '')
    
    return value.strip()

def require_ajax(view_func):
    """
    Décorateur pour s'assurer qu'une vue n'est accessible que via AJAX
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            logger.warning(f"Tentative d'accès non-AJAX à une vue AJAX depuis IP: {get_client_ip(request)}")
            return HttpResponseForbidden("Cette vue n'est accessible que via AJAX.")
        return view_func(request, *args, **kwargs)
    return wrapper

def check_user_agent(view_func):
    """
    Décorateur pour vérifier le User-Agent
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        # Liste des User-Agents suspects
        suspicious_agents = ['sqlmap', 'nikto', 'nmap', 'masscan', 'nessus', 'openvas']
        
        if any(agent in user_agent for agent in suspicious_agents):
            client_ip = get_client_ip(request)
            logger.critical(f"User-Agent suspect détecté: {user_agent} depuis IP: {client_ip}")
            return HttpResponseForbidden("User-Agent non autorisé.")
        
        return view_func(request, *args, **kwargs)
    return wrapper
