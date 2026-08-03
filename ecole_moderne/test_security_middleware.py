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
