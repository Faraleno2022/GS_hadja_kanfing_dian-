"""Régressions liées aux responsables pendant l'import groupé des élèves."""

import pandas as pd
from django.test import TestCase

from eleves.import_eleves import ImportElevesProcessor
from eleves.models import Classe, Ecole, Eleve, Responsable


class ImportResponsablesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ecole = Ecole.objects.create(
            nom='École Responsables',
            adresse='Conakry',
            telephone='+224622000021',
            directeur='Direction',
        )
        cls.classe = Classe.objects.create(
            ecole=cls.ecole,
            nom='7ème Année',
            niveau='COLLEGE_7',
            annee_scolaire='2026-2027',
        )

    def importer(self, lignes):
        return ImportElevesProcessor(
            pd.DataFrame(lignes),
            self.classe.id,
            generer_matricules=True,
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
        self.assertEqual(
            Responsable.objects.filter(telephone=telephone).count(), 1
        )
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
            matricule='EXIST-001',
            prenom='Awa',
            nom='DIALLO',
            sexe='F',
            classe=self.classe,
        )

        stats = self.importer([
            self.ligne('NOUVEAU-001', 'Awa', 'Diallo', '+224622123457'),
        ])

        self.assertEqual(stats['modifies'], 1)
        eleve.refresh_from_db()
        self.assertIsNotNone(eleve.responsable_principal_id)
        self.assertEqual(
            eleve.responsable_principal.telephone,
            '+224622123457',
        )
