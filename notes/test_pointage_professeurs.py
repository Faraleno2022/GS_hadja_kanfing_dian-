from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Ecole
from salaires.models import Enseignant, PresenceEnseignant, TypeEnseignant


LICENCE_MIDDLEWARE = 'ecole_moderne.licence_middleware.LicenceMiddleware'
TEST_MIDDLEWARE = tuple(
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != LICENCE_MIDDLEWARE
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PointageProfesseursTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='pointage-notes',
            email='pointage@example.com',
            password='mot-de-passe-test',
        )
        self.ecole = Ecole.objects.create(
            nom='École pointage',
            adresse='Conakry',
            telephone='+224610000010',
            directeur='Direction',
        )
        self.user.profil.ecole = self.ecole
        self.user.profil.role = 'ADMIN'
        self.user.profil.is_validated = True
        self.user.profil.save()
        self.enseignant = Enseignant.objects.create(
            nom='Camara',
            prenoms='Mamadou',
            ecole=self.ecole,
            type_enseignant=TypeEnseignant.SECONDAIRE,
            statut='ACTIF',
            taux_horaire=Decimal('10000'),
            date_embauche=date(2025, 1, 1),
            cree_par=self.user,
        )
        self.client.force_login(self.user)

    def test_pointage_enregistre_auteur_et_calcule_heures(self):
        response = self.client.post(
            reverse('notes:pointage_professeurs'),
            {
                'date': '2026-09-03',
                f'statut_{self.enseignant.id}': 'PRESENT',
                f'arrivee_{self.enseignant.id}': '08:00',
                f'depart_{self.enseignant.id}': '16:30',
                f'heures_travaillees_{self.enseignant.id}': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        presence = PresenceEnseignant.objects.get(
            enseignant=self.enseignant,
            date=date(2026, 9, 3),
        )
        self.assertEqual(presence.pointe_par, self.user)
        self.assertEqual(presence.heures_travaillees, Decimal('8.50'))

    def test_pointage_incomplet_affiche_un_message_sans_erreur_serveur(self):
        response = self.client.post(
            reverse('notes:pointage_professeurs'),
            {
                'date': '2026-09-03',
                f'statut_{self.enseignant.id}': 'PRESENT',
                f'arrivee_{self.enseignant.id}': '08:00',
                f'depart_{self.enseignant.id}': '',
                f'heures_travaillees_{self.enseignant.id}': '',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pointage non enregistré')
        self.assertFalse(
            PresenceEnseignant.objects.filter(
                enseignant=self.enseignant,
                date=date(2026, 9, 3),
            ).exists()
        )

    def test_simple_presence_sans_heures_compte_le_jour(self):
        response = self.client.post(
            reverse('notes:pointage_professeurs'),
            {
                'date': '2026-09-03',
                f'statut_{self.enseignant.id}': 'PRESENT',
                f'arrivee_{self.enseignant.id}': '',
                f'depart_{self.enseignant.id}': '',
                f'heures_travaillees_{self.enseignant.id}': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        presence = PresenceEnseignant.objects.get(
            enseignant=self.enseignant,
            date=date(2026, 9, 3),
        )
        self.assertEqual(presence.heures_travaillees, Decimal('0'))
        self.assertEqual(presence.pointe_par, self.user)
