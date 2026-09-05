from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import resolve, Resolver404

from .acces_enseignants import verifier_session
from .models import AccesEnseignantTemporaire


class AccesEnseignantMiddleware:
    """Les comptes temporaires ne peuvent utiliser aucun autre écran/API."""

    allowed = {
        'notes:enseignant_accueil', 'notes:enseignant_saisie', 'notes:enseignant_import',
        'notes:enseignant_template', 'notes:enseignant_lien', 'notes:enseignant_deconnexion',
        'notes:enseignant_connexion',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and AccesEnseignantTemporaire.objects.filter(utilisateur=request.user).exists():
            try:
                route = resolve(request.path_info).view_name
            except Resolver404:
                route = ''
            try:
                request.acces_enseignant = verifier_session(request)
                if request.path_info == '/':
                    return redirect('notes:enseignant_accueil')
                if route not in self.allowed:
                    raise PermissionDenied('Ce compte est réservé à la saisie des notes dans votre espace enseignant.')
            except PermissionDenied as exc:
                # Une session révoquée doit cesser d'être authentifiée immédiatement.
                if not hasattr(request, 'acces_enseignant'):
                    logout(request)
                if route not in ('notes:enseignant_lien', 'notes:enseignant_connexion'):
                    response = render(request, 'notes/enseignants/message.html', {'erreur': str(exc)}, status=403)
                    response['Cache-Control'] = 'no-store, private'
                    response['Referrer-Policy'] = 'strict-origin'
                    return response
        # Le domaine seul permet le contrôle CSRF HTTPS sans transmettre
        # le chemin du lien personnel ni son jeton dans le Referer.
        response = self.get_response(request)
        if request.path_info.startswith('/notes/enseignant') or request.path_info.startswith('/notes/acces-enseignants'):
            response['Cache-Control'] = 'no-store, private'
            response['Referrer-Policy'] = 'strict-origin'
            response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
