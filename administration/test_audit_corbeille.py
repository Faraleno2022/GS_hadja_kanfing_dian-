from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.models.deletion import Collector
from django.test import TestCase
from django.utils import timezone

from administration.corbeille import CorbeilleError, enregistrer_suppression, restaurer
from administration.models import ElementCorbeille
from administration.tests_corbeille import _creer_jeu_de_donnees
from eleves.models import Eleve
from paiements.models import Relance


class CorbeilleIntegriteTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('auteur-archive')
        self.ecole, self.classe, self.eleve = _creer_jeu_de_donnees('archive')
        self.relance = Relance.objects.create(
            eleve=self.eleve, canal='SMS', message='Historique', cree_par=self.user,
            solde_estime=45000,
        )

    def test_cascade_directe_conserve_auteur_date_et_identite(self):
        date_creation = timezone.make_aware(datetime(2025, 10, 7, 8, 30))
        Relance.objects.filter(pk=self.relance.pk).update(date_creation=date_creation)
        original = Collector.can_fast_delete

        def fast(collector, objs, from_field=None):
            if getattr(objs, 'model', None) is Relance:
                return True
            return original(collector, objs, from_field=from_field)

        with patch.object(Collector, 'can_fast_delete', fast):
            archive = enregistrer_suppression(self.eleve, user=self.user)
        self.assertIn('paiements.Relance', [obj['model_label'] for obj in archive.objets_lies])
        self.eleve.delete()
        eleve, ignores = restaurer(archive, user=self.user)
        relance = Relance.objects.get(pk=self.relance.pk)
        self.assertEqual(ignores, [])
        self.assertEqual(relance.eleve_id, eleve.pk)
        self.assertEqual(relance.cree_par_id, self.user.pk)
        self.assertEqual(relance.date_creation, date_creation)
        self.assertEqual(relance.sync_uuid, self.relance.sync_uuid)

    def test_echec_enfant_annule_toute_la_restauration(self):
        archive = enregistrer_suppression(self.eleve, user=self.user)
        pk = self.eleve.pk
        self.eleve.delete()
        with patch('administration.corbeille._sauver_archive', wraps=__import__('administration.corbeille', fromlist=['_sauver_archive'])._sauver_archive) as save:
            original = save._mock_wraps

            def fail_child(obj, data):
                if isinstance(obj, Relance):
                    raise ValueError('Échec simulé du stockage')
                return original(obj, data)

            save.side_effect = fail_child
            with self.assertRaises(CorbeilleError):
                restaurer(archive)
        self.assertFalse(Eleve.objects.filter(pk=pk).exists())
        self.assertFalse(Relance.objects.filter(pk=self.relance.pk).exists())
        self.assertFalse(ElementCorbeille.objects.get(pk=archive.pk).restaure)

    def test_archive_ne_tronque_pas_apres_mille_objets(self):
        Relance.objects.bulk_create([
            Relance(eleve=self.eleve, canal='SMS', message=str(i), solde_estime=1)
            for i in range(1001)
        ])
        archive = enregistrer_suppression(self.eleve)
        self.assertEqual(sum(item['model_label'] == 'paiements.Relance' for item in archive.objets_lies), 1002)
