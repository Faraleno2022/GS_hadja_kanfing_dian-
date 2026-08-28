from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase

from .security_middleware import SecurityMiddleware


class PathTraversalDetectionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SecurityMiddleware(lambda request: None)

    def test_slash_encode_dans_une_redirection_legitime_est_accepte(self):
        request = self.factory.get(
            "/utilisateurs/verify-phone/?next=%2Feleves%2Fliste%2F"
        )

        self.assertFalse(self.middleware.detect_path_traversal(request))

    def test_url_encodee_legitime_est_acceptee(self):
        request = self.factory.get(
            "/paiements/ajouter/?retour=https%3A%2F%2Fmyschoolgn.space%2Feleves%2F"
        )

        self.assertFalse(self.middleware.detect_path_traversal(request))

    def test_segment_parent_encode_est_detecte(self):
        request = self.factory.get("/media/?fichier=..%2Fsecret.txt")

        self.assertTrue(self.middleware.detect_path_traversal(request))

    def test_segment_parent_doublement_encode_est_detecte(self):
        request = self.factory.get("/media/?fichier=%252e%252e%252fsecret.txt")

        self.assertTrue(self.middleware.detect_path_traversal(request))

    def test_segment_parent_windows_est_detecte(self):
        request = self.factory.get("/media/?fichier=..%5Csecret.txt")

        self.assertTrue(self.middleware.detect_path_traversal(request))


class ClientIpDetectionTests(SimpleTestCase):
    """Derriere le repartiteur PythonAnywhere, tous les visiteurs partagent
    la meme IP tant que X-Real-IP n'est pas prioritaire sur les autres
    en-tetes (cf. https://help.pythonanywhere.com/pages/WebAppClientIPAddresses)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SecurityMiddleware(lambda request: None)

    def test_x_real_ip_est_prioritaire(self):
        request = self.factory.get(
            "/", HTTP_X_REAL_IP="41.75.10.20", HTTP_X_FORWARDED_FOR="10.0.0.1"
        )
        self.assertEqual(self.middleware.get_client_ip(request), "41.75.10.20")

    def test_repli_sur_x_forwarded_for(self):
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="41.75.10.20, 10.0.0.1")
        self.assertEqual(self.middleware.get_client_ip(request), "41.75.10.20")

    def test_repli_sur_remote_addr(self):
        request = self.factory.get("/")
        self.assertEqual(self.middleware.get_client_ip(request), "127.0.0.1")


class RateLimitTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SecurityMiddleware(lambda request: None)
        cache.clear()
        self.addCleanup(cache.clear)

    def test_static_media_et_api_sont_exemptes(self):
        for path in ("/static/css/app.css", "/media/photos_eleves/x.jpg", "/api/v1/sync/pull/"):
            self.assertTrue(self.middleware._is_rate_limit_exempt(path), path)

    def test_page_dynamique_nest_pas_exemptee(self):
        self.assertFalse(self.middleware._is_rate_limit_exempt("/eleves/liste/"))

    def test_sous_la_limite_les_requetes_passent(self):
        for _ in range(self.middleware.RATE_LIMIT_MAX_REQUESTS):
            limited, _ = self.middleware.check_rate_limit("41.75.10.20")
            self.assertFalse(limited)

    def test_au_dela_de_la_limite_bloque_avec_retry_after(self):
        for _ in range(self.middleware.RATE_LIMIT_MAX_REQUESTS):
            self.middleware.check_rate_limit("41.75.10.21")
        limited, retry_after = self.middleware.check_rate_limit("41.75.10.21")
        self.assertTrue(limited)
        self.assertGreater(retry_after, 0)

    def test_une_ip_differente_nest_pas_affectee(self):
        for _ in range(self.middleware.RATE_LIMIT_MAX_REQUESTS + 5):
            self.middleware.check_rate_limit("41.75.10.22")
        limited, _ = self.middleware.check_rate_limit("41.75.10.23")
        self.assertFalse(limited)

    def test_reponse_429_avec_retry_after(self):
        for _ in range(self.middleware.RATE_LIMIT_MAX_REQUESTS + 1):
            self.middleware.check_rate_limit("41.75.10.24")
        request = self.factory.get("/eleves/liste/", HTTP_X_REAL_IP="41.75.10.24")
        response = self.middleware.process_request(request)
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_trafic_api_continu_ne_declenche_jamais_le_blocage(self):
        """Le poste de synchronisation interroge l'API toutes les ~10s : meme
        avec des centaines d'appels, /api/ ne doit jamais etre bloque."""
        request = self.factory.get(
            "/api/v1/sync/pull/", HTTP_X_REAL_IP="41.75.10.25"
        )
        for _ in range(500):
            response = self.middleware.process_request(request)
            self.assertIsNone(response)
