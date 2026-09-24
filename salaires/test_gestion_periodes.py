from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Ecole

from .models import PeriodeSalaire


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class GestionPeriodesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='periodes-salaire',
            email='periodes@example.com',
            password='mot-de-passe-test',
        )
        self.ecole = Ecole.objects.create(
            nom='École périodes',
            adresse='Conakry',
            telephone='+224610000020',
            directeur='Direction',
        )
        PeriodeSalaire.objects.create(
            mois=9,
            annee=2026,
            ecole=self.ecole,
            nombre_semaines=Decimal('4.33'),
            cree_par=self.user,
        )
        self.client.force_login(self.user)

    def test_liste_periodes_utilise_les_statistiques_sans_erreur_count(self):
        response = self.client.get(reverse('salaires:gestion_periodes'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Septembre 2026')
