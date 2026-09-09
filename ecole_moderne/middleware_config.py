"""Order production security middleware after authentication and teacher access."""
SESSION_SECURITY = 'ecole_moderne.security_middleware.SessionSecurityMiddleware'
SECURITY = 'ecole_moderne.security_middleware.SecurityMiddleware'
CSRF_LOGGING = 'ecole_moderne.security_middleware.CSRFSecurityMiddleware'
CSP = 'ecole_moderne.security_middleware.CSPMiddleware'


def production_middlewares(middlewares):
    production_only = {SESSION_SECURITY, SECURITY, CSRF_LOGGING, CSP}
    result = [m for m in middlewares if m not in production_only
              and m != 'ecole_moderne.image_cache_middleware.ImageCacheMiddleware']
    result.insert(1, SECURITY)
    result.insert(result.index('utilisateurs.middleware.ProfilAccessMiddleware') + 1, SESSION_SECURITY)
    result.insert(result.index('django.middleware.csrf.CsrfViewMiddleware') + 1, CSRF_LOGGING)
    result.append(CSP)
    return result
