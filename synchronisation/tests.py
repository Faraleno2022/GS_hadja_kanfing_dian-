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
        profil.is_validated = True
        profil.save(update_fields=['role', 'ecole', 'is_validated'])
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
                        'model': 'eleves.Ecole',
                        'object_uuid': str(self.ecole.sync_uuid),
                        'operation': 'UPDATE',
                        'payload': {
                            'sync_uuid': str(self.ecole.sync_uuid),
                            'nom': 'Ecole Test Sync',
                            'adresse': 'Conakry',
                            'telephone': '+224600000000',
                            'directeur': 'Direction',
                            'etat': 'VALIDE',
                        },
                    }
                ]
            }),
            content_type='application/json',
            HTTP_X_SYNC_DEVICE=data['device_id'],
            HTTP_X_SYNC_TOKEN=data['sync_token'],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['accepted_count'], 1)

    def test_register_device_with_admin_token_and_pull_other_device_changes(self):
        from django.test import override_settings

        with override_settings(MYSCHOOL_SYNC_ADMIN_TOKEN='bootstrap-secret'):
            response = self.client.post(
                reverse('synchronisation:register_device'),
                data=json.dumps({'nom': 'Poste 1', 'ecole_id': self.ecole.id}),
                content_type='application/json',
                HTTP_X_SYNC_ADMIN_TOKEN='bootstrap-secret',
            )
        self.assertEqual(response.status_code, 201)
        device_one = response.json()

        with override_settings(MYSCHOOL_SYNC_ADMIN_TOKEN='bootstrap-secret'):
            response = self.client.post(
                reverse('synchronisation:register_device'),
                data=json.dumps({'nom': 'Poste 2', 'ecole_id': self.ecole.id}),
                content_type='application/json',
                HTTP_X_SYNC_ADMIN_TOKEN='bootstrap-secret',
            )
        self.assertEqual(response.status_code, 201)
        device_two = response.json()

        response = self.client.post(
            reverse('synchronisation:push'),
            data=json.dumps({
                'changes': [
                    {
                        'model': 'eleves.Ecole',
                        'object_uuid': str(self.ecole.sync_uuid),
                        'operation': 'UPDATE',
                        'payload': {
                            'sync_uuid': str(self.ecole.sync_uuid),
                            'nom': 'Ecole Test Poste 1',
                            'adresse': 'Conakry',
                            'telephone': '+224600000000',
                            'directeur': 'Direction',
                            'etat': 'VALIDE',
                        },
                    }
                ]
            }),
            content_type='application/json',
            HTTP_X_SYNC_DEVICE=device_one['device_id'],
            HTTP_X_SYNC_TOKEN=device_one['sync_token'],
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse('synchronisation:pull'),
            HTTP_X_SYNC_DEVICE=device_two['device_id'],
            HTTP_X_SYNC_TOKEN=device_two['sync_token'],
        )
        self.assertEqual(response.status_code, 200)
        changes = response.json()['changes']
        self.assertEqual(len(changes), 2)  # création web initiale et modification du poste 1
        self.assertTrue(all(row['object_uuid'] == str(self.ecole.sync_uuid) for row in changes))
        self.assertTrue(any(row['device_id'] == device_one['device_id'] for row in changes))


class PushPendingFileTests(TestCase):
    """La file locale ne doit jamais rester bloquee derriere un refus serveur."""

    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='Ecole File', adresse='Conakry', telephone='+224600000001',
            directeur='Direction', etat='VALIDE',
        )

    def _changements(self, nombre):
        from synchronisation.models import SyncChange
        SyncChange.objects.filter(ecole=self.ecole).delete()
        return [
            SyncChange.objects.create(
                ecole=self.ecole, model_label='eleves.Eleve',
                operation=SyncChange.OPERATION_UPDATE, payload={'nom': f'E{i}'},
            )
            for i in range(nombre)
        ]

    def test_un_refus_ne_bloque_pas_les_changements_suivants(self):
        """Avant correction : le lot refuse etait renvoye a l'identique en boucle."""
        from unittest.mock import patch
        from synchronisation.client import push_pending
        from synchronisation.models import SyncChange

        changements = self._changements(3)
        envois = []

        def faux_post(url, device_id, token, payload, timeout=25):
            envois.append([c['payload']['nom'] for c in payload['changes']])
            # Le serveur refuse systematiquement le premier changement recu.
            return {
                'ok': True,
                'accepted': [{'index': i} for i in range(1, len(payload['changes']))],
                'rejected': [{'index': 0, 'error': 'Relation introuvable pour classe.'}],
            }

        with patch('synchronisation.client._post_json', faux_post):
            total = push_pending('https://exemple', 'dev', 'tok', self.ecole, batch_size=2)

        self.assertEqual(envois, [['E0', 'E1'], ['E2']])
        self.assertEqual(total, 1)
        refuse = SyncChange.objects.get(pk=changements[0].pk)
        self.assertEqual(refuse.statut, SyncChange.STATUT_FAILED)
        self.assertIn('Relation introuvable', refuse.erreur)
        self.assertEqual(SyncChange.objects.get(pk=changements[2].pk).statut,
                         SyncChange.STATUT_FAILED)
        self.assertEqual(SyncChange.objects.get(pk=changements[1].pk).statut,
                         SyncChange.STATUT_APPLIED)

    def test_rejouer_refuses_remet_en_file(self):
        from synchronisation.client import rejouer_refuses
        from synchronisation.models import SyncChange

        changements = self._changements(2)
        SyncChange.objects.filter(pk=changements[0].pk).update(
            statut=SyncChange.STATUT_FAILED, erreur='Relation introuvable.')

        self.assertEqual(rejouer_refuses(self.ecole), 1)
        rejoue = SyncChange.objects.get(pk=changements[0].pk)
        self.assertEqual(rejoue.statut, SyncChange.STATUT_PENDING)
        self.assertEqual(rejoue.erreur, '')
