"""Outils partagés par les tests de l'application paiements.

Deux contraintes d'environnement doivent être neutralisées pour que la suite
soit reproductible sur n'importe quelle machine :

* ``LicenceMiddleware`` renvoie une page 403 tant qu'aucune licence (ou période
  d'essai) valide n'est trouvée. Sans neutralisation, les tests passent sur un
  poste de développement licencié et échouent partout ailleurs.
* ``django-axes`` impose un objet ``request`` à ``authenticate()``. Le client de
  test n'en fournit pas via ``login()`` : il faut utiliser ``force_login()``.
"""

from django.conf import settings


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'

# Middlewares de test : identiques à la production, sans le verrou de licence.
TEST_MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
]
