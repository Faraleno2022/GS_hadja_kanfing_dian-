"""Importation multi-classes, rejet des doublons et cloisonnement des écoles."""
from datetime import date

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase, modify_settings
from django.urls import reverse

from eleves.import_eleves import COLONNES_TRANSFERT, ImportElevesProcessor
from eleves.models import Classe, Ecole, Eleve


def ligne(classe, matricule, prenom, nom, sexe='M', annee='2025-2026'):
    """Ligne au format de transfert (celui de l'export multi-classes)."""
    donnees = {col: '' for col in COLONNES_TRANSFERT}
    donnees.update({
        'École': 'Groupe Scolaire Exemple',
        'Classe': classe,
        'Année scolaire': annee,
        'Matricule': matricule,
        'Prénom': prenom,
        'Nom': nom,
        'Sexe': sexe,
    })
    return donnees


class ImportMultiClassesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ecole = Ecole.objects.create(
            nom='Groupe Scolaire Exemple',
            adresse='Conakry',
            telephone='+224622000001',
            directeur='Direction',
        )
        cls.grande_section = Classe.objects.create(
            ecole=cls.ecole, nom='GRANDE SECTION',
            niveau='MATERNELLE', annee_scolaire='2025-2026',
        )
        cls.petite_section = Classe.objects.create(
            ecole=cls.ecole, nom='PETITE SECTION',
            niveau='MATERNELLE', annee_scolaire='2025-2026',
        )
        cls.huitieme = Classe.objects.create(
            ecole=cls.ecole, nom='8ÈME ANNÉE',
            niveau='COLLEGE_8', annee_scolaire='2025-2026',
        )

    def importer(self, lignes, classe_defaut=None, generer_matricules=True):
        processeur = ImportElevesProcessor(
            df=pd.DataFrame(lignes, columns=COLONNES_TRANSFERT),
            classe_id=(classe_defaut or self.grande_section).id,
            generer_matricules=generer_matricules,
        )
        return processeur.importer()

    def test_toutes_les_classes_du_fichier_sont_honorees(self):
        stats = self.importer([
            ligne('GRANDE SECTION', 'GS-001', 'Youssouf', 'BAH'),
            ligne('PETITE SECTION', 'PS-001', 'Mariam', 'CAMARA', sexe='F'),
            ligne('8ÈME ANNÉE', 'C8-001', 'Ibrahim', 'DIALLO'),
        ])

        self.assertEqual(stats['crees'], 3)
        self.assertEqual(stats['classes_ciblees'], 3)
        self.assertEqual(stats['classes_introuvables'], [])
        self.assertEqual(
            Eleve.objects.get(matricule='PS-001').classe, self.petite_section
        )
        self.assertEqual(
            Eleve.objects.get(matricule='C8-001').classe, self.huitieme
        )

    def test_matricule_deja_en_base_rejete_sans_creer_de_doublon(self):
        Eleve.objects.create(
            matricule='GS-001', prenom='Youssouf', nom='BAH', sexe='M',
            date_naissance=date(2020, 1, 1), classe=self.grande_section,
            statut='ACTIF',
        )

        stats = self.importer([
            ligne('GRANDE SECTION', 'GS-001', 'Youssouf', 'BAH'),
            ligne('PETITE SECTION', 'PS-002', 'Aïcha', 'SOW', sexe='F'),
        ])

        self.assertEqual(stats['doublons_ignores'], 1)
        self.assertEqual(stats['crees'], 1)
        self.assertEqual(Eleve.objects.filter(matricule='GS-001').count(), 1)
        self.assertEqual(Eleve.objects.count(), 2)
        self.assertIn('GS-001', stats['doublons_details'][0])

    def test_matricule_repete_dans_le_fichier_nest_importe_quune_fois(self):
        stats = self.importer([
            ligne('GRANDE SECTION', 'GS-010', 'Youssouf', 'BAH'),
            ligne('PETITE SECTION', 'GS-010', 'Autre', 'ELEVE'),
        ])

        self.assertEqual(stats['crees'], 1)
        self.assertEqual(stats['doublons_ignores'], 1)
        self.assertEqual(Eleve.objects.filter(matricule='GS-010').count(), 1)

    def test_doublon_detecte_malgre_casse_et_espaces(self):
        Eleve.objects.create(
            matricule='GS-001', prenom='Youssouf', nom='BAH', sexe='M',
            date_naissance=date(2020, 1, 1), classe=self.grande_section,
            statut='ACTIF',
        )

        stats = self.importer([ligne('GRANDE SECTION', '  gs-001 ', 'Youssouf', 'BAH')])

        self.assertEqual(stats['doublons_ignores'], 1)
        self.assertEqual(stats['crees'], 0)
        self.assertEqual(Eleve.objects.count(), 1)

    def test_matricule_vide_reste_genere_automatiquement(self):
        stats = self.importer([ligne('8ÈME ANNÉE', '', 'Ibrahim', 'DIALLO')])

        self.assertEqual(stats['crees'], 1)
        self.assertEqual(stats['matricules_generes'], 1)
        self.assertEqual(stats['doublons_ignores'], 0)
        self.assertTrue(Eleve.objects.get(prenom='Ibrahim').matricule)

    def test_reimport_du_meme_fichier_ne_cree_aucun_eleve(self):
        lignes = [
            ligne('GRANDE SECTION', 'GS-001', 'Youssouf', 'BAH'),
            ligne('PETITE SECTION', 'PS-001', 'Mariam', 'CAMARA', sexe='F'),
            ligne('8ÈME ANNÉE', 'C8-001', 'Ibrahim', 'DIALLO'),
        ]
        self.importer(lignes)

        stats = self.importer(lignes)

        self.assertEqual(stats['crees'], 0)
        self.assertEqual(stats['doublons_ignores'], 3)
        self.assertEqual(Eleve.objects.count(), 3)

    def test_classe_absente_de_lecole_rejette_la_ligne(self):
        """Un lycéen ne doit pas atterrir en maternelle : la ligne est rejetée."""
        stats = self.importer([
            ligne('11 SÉRIE SCIENTIFIQUE', 'L11-001', 'Sekou', 'KEITA'),
        ])

        self.assertEqual(stats['crees'], 0)
        self.assertEqual(stats['lignes_classes_rejetees'], 1)
        self.assertEqual(len(stats['classes_introuvables']), 1)
        self.assertFalse(Eleve.objects.filter(matricule='L11-001').exists())

    def test_compte_administrateur_traite_un_export_multi_ecoles(self):
        autre_ecole = Ecole.objects.create(
            nom='École Test Maternelle', adresse='Conakry',
            telephone='+224622000009', directeur='Direction',
        )
        classe_autre = Classe.objects.create(
            ecole=autre_ecole, nom='MATERNELLE 1 - PETITE SECTION',
            niveau='MATERNELLE', annee_scolaire='2025-2026',
        )
        lignes = [
            ligne('GRANDE SECTION', 'GS-001', 'Youssouf', 'BAH'),
            ligne('MATERNELLE 1 - PETITE SECTION', 'MP-001', 'Aïcha', 'SOW', sexe='F'),
        ]
        lignes[1]['École'] = 'École Test Maternelle'

        processeur = ImportElevesProcessor(
            df=pd.DataFrame(lignes, columns=COLONNES_TRANSFERT),
            classe_id=self.grande_section.id,
            user=get_user_model().objects.create_superuser(
                username='admin-import', password='secret-test',
                email='admin@example.com',
            ),
        )
        stats = processeur.importer()

        self.assertEqual(stats['crees'], 2)
        self.assertEqual(stats['lignes_classes_rejetees'], 0)
        self.assertEqual(Eleve.objects.get(matricule='MP-001').classe, classe_autre)

    def test_meme_eleve_sous_un_autre_matricule_est_mis_a_jour_pas_duplique(self):
        Eleve.objects.create(
            matricule='GS-999', prenom='Youssouf', nom='BAH', sexe='M',
            date_naissance=date(2020, 1, 1), classe=self.grande_section,
            statut='ACTIF',
        )

        stats = self.importer([ligne('GRANDE SECTION', 'GS-001', 'Youssouf', 'BAH')])

        self.assertEqual(stats['crees'], 0)
        self.assertEqual(stats['modifies'], 1)
        self.assertEqual(
            Eleve.objects.filter(classe=self.grande_section, nom='BAH').count(), 1
        )


@modify_settings(MIDDLEWARE={'remove': [
    'ecole_moderne.licence_middleware.LicenceMiddleware',
]})
class CloisonnementEcolesImportTests(TestCase):
    """Une école ne peut pas être importée dans une autre, sauf compte admin.

    Le middleware de licence est retiré : il renvoie 403 hors poste licencié et
    masquerait le comportement de la vue.
    """

    @classmethod
    def setUpTestData(cls):
        from utilisateurs.models import Profil

        cls.ecole_a = Ecole.objects.create(
            nom='École A', adresse='Conakry',
            telephone='+224622000001', directeur='Direction A',
        )
        cls.ecole_b = Ecole.objects.create(
            nom='École B', adresse='Kindia',
            telephone='+224622000002', directeur='Direction B',
        )
        cls.classe_a = Classe.objects.create(
            ecole=cls.ecole_a, nom='GRANDE SECTION',
            niveau='MATERNELLE', annee_scolaire='2025-2026',
        )
        cls.classe_b = Classe.objects.create(
            ecole=cls.ecole_b, nom='PETITE SECTION',
            niveau='MATERNELLE', annee_scolaire='2025-2026',
        )
        # is_staff donne le droit d'importer, sans faire de lui un superadmin :
        # le cloisonnement par école doit donc s'appliquer.
        cls.directeur_a = get_user_model().objects.create_user(
            username='directeur-a', password='secret-test', email='a@example.com',
            is_staff=True,
        )
        # Un signal crée déjà un profil à la création de l'utilisateur.
        Profil.objects.update_or_create(
            user=cls.directeur_a,
            defaults={
                'role': 'ADMIN',
                'telephone': '+224622000003',
                'ecole': cls.ecole_a,
            },
        )

    def test_ligne_visant_une_autre_ecole_est_rejetee(self):
        lignes = [ligne('PETITE SECTION', 'PS-001', 'Aïcha', 'SOW', sexe='F')]
        lignes[0]['École'] = 'École B'

        stats = ImportElevesProcessor(
            df=pd.DataFrame(lignes, columns=COLONNES_TRANSFERT),
            classe_id=self.classe_a.id,
            user=self.directeur_a,
        ).importer()

        self.assertEqual(stats['crees'], 0)
        self.assertEqual(stats['lignes_classes_rejetees'], 1)
        self.assertEqual(Eleve.objects.count(), 0)

    def test_classe_de_destination_dune_autre_ecole_est_refusee(self):
        """La classe cible arrive du POST : elle doit être re-vérifiée."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.directeur_a)

        reponse = self.client.post(
            reverse('eleves:importer_eleves'),
            {
                'classe_id': self.classe_b.id,
                'generer_matricules': 'on',
                'fichier': SimpleUploadedFile(
                    'eleves.csv',
                    'Prénom,Nom,Sexe\nAïcha,SOW,F\n'.encode('utf-8'),
                    content_type='text/csv',
                ),
            },
            follow=True,
        )

        self.assertEqual(Eleve.objects.count(), 0)
        # L'apostrophe est échappée par le template : on cible la fin du message.
        self.assertContains(reponse, "appartient pas à votre école")

    def test_classe_de_sa_propre_ecole_est_acceptee(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.directeur_a)

        self.client.post(
            reverse('eleves:importer_eleves'),
            {
                'classe_id': self.classe_a.id,
                'generer_matricules': 'on',
                'fichier': SimpleUploadedFile(
                    'eleves.csv',
                    'Prénom,Nom,Sexe\nAïcha,SOW,F\n'.encode('utf-8'),
                    content_type='text/csv',
                ),
            },
            follow=True,
        )

        self.assertEqual(Eleve.objects.count(), 1)
        self.assertEqual(Eleve.objects.get().classe, self.classe_a)
