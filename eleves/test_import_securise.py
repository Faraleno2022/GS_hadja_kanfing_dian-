"""Régressions de l'import global et du contrôle des matricules."""

from datetime import date

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, modify_settings
from django.urls import reverse

from eleves.import_eleves import ImportElevesProcessor
from eleves.models import Classe, Ecole, Eleve, Responsable


class RejetDoublonsMatriculeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ecole = Ecole.objects.create(
            nom='École Import', adresse='Conakry',
            telephone='+224622000001', directeur='Direction',
        )
        cls.classe = Classe.objects.create(
            ecole=cls.ecole, nom='8ème Année', niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
        )

    def importer(self, lignes):
        return ImportElevesProcessor(
            pd.DataFrame(lignes), self.classe.id, generer_matricules=True
        ).importer()

    def test_doublons_base_et_fichier_sont_rejetes(self):
        Eleve.objects.create(
            matricule='MAT-001', prenom='Aminata', nom='BARRY', sexe='F',
            date_naissance=date(2015, 1, 15), classe=self.classe,
        )

        stats = self.importer([
            {'Matricule': ' mat-001 ', 'Prénom': 'Autre', 'Nom': 'Élève', 'Sexe': 'M'},
            {'Matricule': 'LOT-001', 'Prénom': 'Sira', 'Nom': 'Keita', 'Sexe': 'F'},
            {'Matricule': ' lot-001 ', 'Prénom': 'Kadiatou', 'Nom': 'Sylla', 'Sexe': 'F'},
        ])

        self.assertEqual(stats['crees'], 1)
        self.assertEqual(stats['doublons_ignores'], 2)
        self.assertEqual(Eleve.objects.filter(matricule='MAT-001').count(), 1)
        self.assertTrue(Eleve.objects.filter(matricule='LOT-001').exists())

    def test_matricule_vide_est_genere(self):
        stats = self.importer([
            {'Matricule': '', 'Prénom': 'Ibrahim', 'Nom': 'Diallo', 'Sexe': 'M'},
        ])

        self.assertEqual(stats['crees'], 1)
        self.assertEqual(stats['matricules_generes'], 1)
        self.assertEqual(stats['doublons_ignores'], 0)
        self.assertTrue(Eleve.objects.get(prenom='Ibrahim').matricule)


class ImportResponsablesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ecole = Ecole.objects.create(
            nom='École Responsables', adresse='Conakry',
            telephone='+224622000021', directeur='Direction',
        )
        cls.classe = Classe.objects.create(
            ecole=cls.ecole, nom='7ème Année', niveau='COLLEGE_7',
            annee_scolaire='2026-2027',
        )

    def importer(self, lignes):
        return ImportElevesProcessor(
            pd.DataFrame(lignes), self.classe.id, generer_matricules=True
        ).importer()

    @staticmethod
    def ligne(matricule, prenom, nom, telephone='+224622123456'):
        return {
            'Matricule': matricule,
            'Prénom': prenom,
            'Nom': nom,
            'Sexe': 'F',
            'Téléphone Principal': telephone,
            'Nom du Père/Tuteur': 'DIALLO',
            'Prénom du Père/Tuteur': 'Mamadou',
            'Adresse': 'Conakry',
        }

    def test_deux_eleves_peuvent_partager_un_nouveau_responsable(self):
        telephone = '+224622123456'

        stats = self.importer([
            self.ligne('RESP-001', 'Aïssatou', 'Diallo', telephone),
            self.ligne('RESP-002', 'Fatoumata', 'Diallo', telephone),
        ])

        self.assertEqual(stats['crees'], 2)
        self.assertEqual(Responsable.objects.filter(telephone=telephone).count(), 1)
        eleves = list(
            Eleve.objects.filter(matricule__in=['RESP-001', 'RESP-002'])
            .order_by('matricule')
        )
        self.assertEqual(len(eleves), 2)
        self.assertIsNotNone(eleves[0].responsable_principal_id)
        self.assertEqual(
            eleves[0].responsable_principal_id,
            eleves[1].responsable_principal_id,
        )

    def test_eleve_existant_recoit_un_nouveau_responsable(self):
        eleve = Eleve.objects.create(
            matricule='EXIST-001', prenom='Awa', nom='DIALLO', sexe='F',
            classe=self.classe,
        )

        stats = self.importer([
            self.ligne('NOUVEAU-001', 'Awa', 'Diallo', '+224622123457'),
        ])

        self.assertEqual(stats['modifies'], 1)
        eleve.refresh_from_db()
        self.assertIsNotNone(eleve.responsable_principal_id)
        self.assertEqual(
            eleve.responsable_principal.telephone, '+224622123457'
        )


@modify_settings(MIDDLEWARE={'remove': [
    'ecole_moderne.licence_middleware.LicenceMiddleware',
]})
class ImportGlobalClassesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from utilisateurs.models import Profil

        cls.ecole_a = Ecole.objects.create(
            nom='École A', adresse='Conakry',
            telephone='+224622000011', directeur='Direction A',
        )
        cls.ecole_b = Ecole.objects.create(
            nom='École B', adresse='Kindia',
            telephone='+224622000012', directeur='Direction B',
        )
        cls.classe_a = Classe.objects.create(
            ecole=cls.ecole_a, nom='8ème Année', niveau='COLLEGE_8',
            annee_scolaire='2026-2027',
        )
        cls.classe_b = Classe.objects.create(
            ecole=cls.ecole_b, nom='Petite Section', niveau='MATERNELLE',
            annee_scolaire='2026-2027',
        )
        cls.admin = get_user_model().objects.create_superuser(
            username='admin-import', password='secret-test',
            email='admin@example.com',
        )
        cls.direction_a = get_user_model().objects.create_user(
            username='direction-a', password='secret-test', is_staff=True,
        )
        Profil.objects.update_or_create(
            user=cls.direction_a,
            defaults={'role': 'ADMIN', 'ecole': cls.ecole_a},
        )

    @staticmethod
    def fichier(lignes):
        contenu = pd.DataFrame(lignes).to_csv(index=False).encode('utf-8-sig')
        return SimpleUploadedFile('toutes_classes.csv', contenu, 'text/csv')

    def test_superadmin_importe_toutes_les_classes(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('eleves:importer_eleves'), {
            'repartition_auto': 'on',
            'generer_matricules': 'on',
            'fichier': self.fichier([
                {'École': 'École A', 'Classe': '8ème Année', 'Année scolaire': '2026-2027',
                 'Matricule': 'A8-001', 'Prénom': 'Awa', 'Nom': 'Diallo', 'Sexe': 'F'},
                {'École': 'École B', 'Classe': 'Petite Section', 'Année scolaire': '2026-2027',
                 'Matricule': 'BPS-001', 'Prénom': 'Fatou', 'Nom': 'Camara', 'Sexe': 'F'},
            ]),
        })

        self.assertEqual(Eleve.objects.count(), 2)
        self.assertEqual(Eleve.objects.get(matricule='A8-001').classe, self.classe_a)
        self.assertEqual(Eleve.objects.get(matricule='BPS-001').classe, self.classe_b)

    def test_compte_ecole_ne_peut_pas_importer_dans_une_autre_ecole(self):
        self.client.force_login(self.direction_a)
        self.client.post(reverse('eleves:importer_eleves'), {
            'repartition_auto': 'on',
            'generer_matricules': 'on',
            'fichier': self.fichier([
                {'École': 'École B', 'Classe': 'Petite Section', 'Année scolaire': '2026-2027',
                 'Matricule': 'BPS-002', 'Prénom': 'Nene', 'Nom': 'Sow', 'Sexe': 'F'},
            ]),
        })

        self.assertFalse(Eleve.objects.filter(matricule='BPS-002').exists())
