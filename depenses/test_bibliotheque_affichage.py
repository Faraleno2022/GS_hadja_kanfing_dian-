from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(
    middleware for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class BibliothequeAffichageTests(TestCase):
    def test_dashboard_desktop_se_rend_sans_url_invalide(self):
        user = get_user_model().objects.create_superuser(
            username='admin-bibliotheque-ui',
            email='bibliotheque-ui@example.com',
            password='mot-de-passe-test',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('depenses:dashboard_bibliotheque'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bibliotheque-desktop')
        self.assertContains(response, 'Ajouter un livre', count=1)

