import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from eleves.models import Ecole
from utilisateurs.models import Profil


class SynchronisationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='adminsync', password='secret123')
        self.ecole = Ecole.objects.create(
            nom='Ecole Test',
            adresse='Conakry',
            telephone='+224600000000',
            directeur='Direction',
            etat='VALIDE',
        )
        profil, _ = Profil.objects.get_or_create(user=self.user)
        profil.role = 'ADMIN'
        profil.ecole = self.ecole
        profil.save(update_fields=['role', 'ecole'])
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get(reverse('synchronisation:health'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

    def test_register_device_and_push_change(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('synchronisation:register_device'),
            data=json.dumps({'nom': 'Poste direction'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()

        response = self.client.post(
            reverse('synchronisation:push'),
            data=json.dumps({
                'changes': [
                    {
                        'model': 'eleves.Eleve',
                        'operation': 'CREATE',
                        'payload': {'nom': 'Diallo'},
                    }
                ]
            }),
            content_type='application/json',
            HTTP_X_SYNC_DEVICE=data['device_id'],
            HTTP_X_SYNC_TOKEN=data['sync_token'],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['accepted_count'], 1)
