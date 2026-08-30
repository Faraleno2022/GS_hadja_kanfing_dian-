from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from ecole_moderne.licence_middleware import LicenceMiddleware


class LicenceMiddlewareProductionTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get('/eleves/')
        self.middleware = LicenceMiddleware(lambda _request: HttpResponse('application'))

    @override_settings(DEBUG=False)
    @patch('ecole_moderne.licence_middleware._check_license_cached')
    @patch('ecole_moderne.licence_middleware._check_integrity_cached')
    def test_production_ignore_essai_expire_sans_avertissement_ni_blocage(
        self,
        check_integrity,
        check_license,
    ):
        check_integrity.return_value = {'valid': True, 'reason': ''}
        check_license.return_value = {
            'valid': False,
            'trial': True,
            'days_left': 0,
        }

        response = self.middleware(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'application')
        check_license.assert_not_called()

    @override_settings(DEBUG=True)
    @patch('ecole_moderne.licence_middleware._check_license_cached')
    @patch('ecole_moderne.licence_middleware._check_integrity_cached')
    def test_application_locale_conserve_le_controle_de_licence(
        self,
        check_integrity,
        check_license,
    ):
        check_integrity.return_value = {'valid': True, 'reason': ''}
        check_license.return_value = {
            'valid': False,
            'trial': True,
            'days_left': 0,
        }

        response = self.middleware(self.request)

        self.assertEqual(response.status_code, 403)
        self.assertIn(b"p\xc3\xa9riode d'essai", response.content)
