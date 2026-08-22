from datetime import date

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase

from eleves.import_eleves import ImportElevesProcessor
from eleves.models import Classe, Ecole, Eleve


class ImportElevesMultiClassesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ecole_a = Ecole.objects.create(
            nom='École A', adresse='Conakry', telephone='+224620000101',
            directeur='Direction A',
        )
        cls.ecole_b = Ecole.objects.create(
            nom='École B', adresse='Conakry', telephone='+224620000102',
            directeur='Direction B',
        )
        cls.classe_a1 = Classe.objects.create(
            ecole=cls.ecole_a, nom='8ème Année', niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
        )
        cls.classe_a2 = Classe.objects.create(
            ecole=cls.ecole_a, nom='10ème Année', niveau='COLLEGE_10',
            annee_scolaire='2026-2027',
        )
        cls.classe_b1 = Classe.objects.create(
            ecole=cls.ecole_b, nom='Petite Section', niveau='MATERNELLE',
            annee_scolaire='2026-2027',
        )
        cls.superuser = get_user_model().objects.create_superuser(
            username='admin-import-global', password='secret-test',
            email='admin@example.com',
        )
        cls.utilisateur_ecole = get_user_model().objects.create_user(
            username='import-ecole-a', password='secret-test',
        )

    @staticmethod
    def _ligne(ecole, classe, matricule, prenom, nom, annee='2026-2027'):
        return {
            'École': ecole,
            'Classe': classe,
            'Année scolaire': annee,
            'Matricule': matricule,
            'Prénom': prenom,
            'Nom': nom,
            'Sexe': 'F',
            'Date de Naissance': '15/01/2015',
            'Lieu de Naissance': 'Conakry',
            'Nom du Père/Tuteur': '',
            'Prénom du Père/Tuteur': '',
            'Téléphone Principal': '',
            'Adresse': '',
            'Nom de la Mère': '',
            'Prénom de la Mère': '',
            'Téléphone Secondaire': '',
            'Email': '',
        }

    def _importer(self, lignes, user=None):
        return ImportElevesProcessor(
            df=pd.DataFrame(lignes),
            classe_id=self.classe_a1.id,
            user=user or self.superuser,
            generer_matricules=True,
        ).importer()

    def test_import_global_repartit_les_eleves_dans_toutes_les_classes(self):
        stats = self._importer([
            self._ligne('École A', '8ème Année', 'A8-001', 'Awa', 'Diallo'),
            self._ligne('École A', '10ème Année', 'A10-001', 'Mariam', 'Bah'),
            self._ligne('École B', 'Petite Section', 'BPS-001', 'Fatou', 'Camara'),
        ])

        self.assertEqual(stats['crees'], 3)
        self.assertEqual(stats['classes_ciblees'], 3)
        self.assertEqual(Eleve.objects.get(matricule='A8-001').classe, self.classe_a1)
        self.assertEqual(Eleve.objects.get(matricule='A10-001').classe, self.classe_a2)
        self.assertEqual(Eleve.objects.get(matricule='BPS-001').classe, self.classe_b1)

    def test_import_ecole_ne_peut_pas_placer_un_eleve_dans_une_autre_ecole(self):
        stats = self._importer(
            [self._ligne('École B', 'Petite Section', 'BPS-002', 'Nene', 'Sow')],
            user=self.utilisateur_ecole,
        )

        self.assertEqual(stats['crees'], 0)
        self.assertEqual(stats['lignes_classes_rejetees'], 1)
        self.assertEqual(stats['erreurs'], 1)
        self.assertFalse(Eleve.objects.filter(matricule='BPS-002').exists())

    def test_matricules_doublons_base_et_fichier_sont_rejetes(self):
        Eleve.objects.create(
            matricule='MAT-001', prenom='Aminata', nom='Barry', sexe='F',
            date_naissance=date(2015, 1, 15), classe=self.classe_a1,
        )

        stats = self._importer([
            self._ligne('École A', '8ème Année', ' mat-001 ', 'Autre', 'Élève'),
            self._ligne('École A', '8ème Année', 'LOT-001', 'Sira', 'Keita'),
            self._ligne('École A', '8ème Année', ' lot-001 ', 'Kadiatou', 'Sylla'),
            self._ligne('École A', '8ème Année', 'MAT-002', 'Aminata', 'Barry'),
        ])

        self.assertEqual(stats['crees'], 1)
        self.assertEqual(stats['modifies'], 1)
        self.assertEqual(stats['doublons_ignores'], 2)
        self.assertEqual(len(stats['doublons_details']), 2)
        self.assertEqual(Eleve.objects.filter(matricule='MAT-001').count(), 1)
        self.assertTrue(Eleve.objects.filter(matricule='LOT-001').exists())
        self.assertFalse(Eleve.objects.filter(matricule='MAT-002').exists())
        self.assertEqual(
            Eleve.objects.get(matricule='MAT-001').prenom.casefold(),
            'aminata',
        )

    def test_classe_introuvable_est_rejetee_sans_repli_sur_classe_defaut(self):
        stats = self._importer([
            self._ligne('École A', 'Classe Inconnue', 'INCONNU-001', 'Aïcha', 'Bangoura'),
        ])

        self.assertEqual(stats['crees'], 0)
        self.assertEqual(stats['lignes_classes_rejetees'], 1)
        self.assertEqual(stats['classes_ciblees'], 0)
        self.assertFalse(Eleve.objects.filter(matricule='INCONNU-001').exists())
