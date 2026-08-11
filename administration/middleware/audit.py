"""Expose la requête courante aux signaux d'audit.

Les signaux qui alimentent la corbeille mémoire n'ont pas accès à la requête ;
ce middleware la place dans une variable locale au thread pour que l'auteur et
l'adresse IP d'une modification puissent être enregistrés.
"""

import threading


_state = threading.local()


def get_current_request():
    return getattr(_state, 'request', None)


def get_current_user():
    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return None


class AuditContextMiddleware:
    """Mémorise la requête en cours pour la durée du traitement."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _state.request = request
        try:
            return self.get_response(request)
        finally:
            _state.request = None
