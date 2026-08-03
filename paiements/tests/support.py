from django.conf import settings


LICENCE_MIDDLEWARE = "ecole_moderne.licence_middleware.LicenceMiddleware"

# Les tests fonctionnels ne doivent pas dépendre d'une licence installée sur
# la machine qui exécute la suite. Les tests propres au middleware de licence
# restent responsables de le tester explicitement.
MIDDLEWARE_SANS_LICENCE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
]
