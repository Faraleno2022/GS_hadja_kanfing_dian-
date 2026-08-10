"""Garde-fous sur l'année scolaire, qui apparie paiements et échéanciers.

Une grille tarifaire saisie « 2025-2027 » a déjà fait porter cette année aux
échéanciers, tandis que les paiements portaient « 2025-2026 ». Le moteur
n'appariant que les années identiques, plus aucun encaissement n'était retenu :
les reçus annonçaient le dû intégral à des familles à jour de leurs paiements.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from ecole_moderne.validators import (
    normaliser_annee_scolaire,
    valider_annee_scolaire,
)
from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire, Responsable
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    TypePaiement,
)
from paiements.payment_engine import situation_echeancier
from paiements.tests.support import TEST_MIDDLEWARE
from paiements.views import ensure_echeancier_for_eleve


class ValidateurAnneeScolaireTests(TestCase):
    def test_annee_bien_formee_acceptee(self):
        self.assertIsNone(valider_annee_scolaire('2025-2026'))

    def test_fin_non_consecutive_refusee(self):
        with self.assertRaises(ValidationError) as contexte:
            valider_annee_scolaire('2025-2027')
        self.assertEqual(
            contexte.exception.code, 'annee_scolaire_intervalle'
        )

    def test_format_libre_refuse(self):
        for valeur in ('2025', '25-26', '2025/2026', 'inconnue'):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValidationError):
                    valider_annee_scolaire(valeur)

    def test_valeur_vide_toleree(self):
        # Un paiement importé sans année reste traité par le repli historique.
        self.assertIsNone(valider_annee_scolaire(''))

    def test_normalisation_depuis_annee_de_debut(self):
        self.assertEqual(normaliser_annee_scolaire('2025-2027'), '2025-2026')
        self.assertEqual(normaliser_annee_scolaire('2024'), '2024-2025')
        self.assertEqual(normaliser_annee_scolaire('n/a'), '')

    def test_grille_refusee_a_la_validation(self):
        ecole = Ecole.objects.create(
            nom='Ecole validateur', adresse='Conakry',
            telephone='+224620000010', directeur='Direction',
        )
        grille = GrilleTarifaire(
            ecole=ecole, niveau='COLLEGE_8', annee_scolaire='2025-2027',
        )
        with self.assertRaises(ValidationError):
            grille.full_clean()


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class EcheancierSuitAnneeDeLaClasseTests(TestCase):
    """L'échéancier ne doit jamais emprunter l'année de la grille tarifaire.

    La grille n'est qu'un barème : elle est retenue par repli sur « la plus
    récente » quand aucune ne correspond à l'année de la classe, et peut donc
    porter une année sans rapport avec l'élève.
    """

    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='Ecole annee', adresse='Conakry', telephone='+224620000003',
            directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='8e', niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Annee', relation='PERE',
            telephone='+224620000004', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='ANN-001', prenom='Faya', nom='Test', sexe='M',
            date_naissance=date(2012, 1, 1), lieu_naissance='Conakry',
            classe=self.classe, date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        # Grille mal étiquetée, telle qu'on la trouve dans les bases existantes.
        # save() court-circuite full_clean() : le validateur protège les
        # saisies futures, pas les données déjà en place.
        self.grille = GrilleTarifaire.objects.create(
            ecole=self.ecole, niveau='COLLEGE_8', annee_scolaire='2025-2027',
            frais_inscription=Decimal('30000'),
            frais_reinscription=Decimal('20000'),
            tranche_1=Decimal('500000'),
            tranche_2=Decimal('600000'),
            tranche_3=Decimal('400000'),
        )

    def test_echeancier_cree_porte_l_annee_de_la_classe(self):
        echeancier = ensure_echeancier_for_eleve(self.eleve)

        self.assertEqual(echeancier.annee_scolaire, '2025-2026')
        # Les montants, eux, viennent bien de la grille retenue.
        self.assertEqual(echeancier.tranche_1_due, Decimal('500000'))

    def test_paiement_reste_apparie_malgre_la_grille_mal_etiquetee(self):
        echeancier = ensure_echeancier_for_eleve(self.eleve)
        paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=TypePaiement.objects.create(nom='Tranche 1'),
            mode_paiement=ModePaiement.objects.create(nom='Espèces'),
            montant=Decimal('500000'),
            date_paiement=date(2026, 1, 10),
            statut='VALIDE',
        )

        self.assertEqual(paiement.annee_scolaire, echeancier.annee_scolaire)

        situation = situation_echeancier(echeancier, date_reference=date(2026, 1, 31))
        self.assertEqual(situation['total_encaisse'], Decimal('500000'))
        self.assertEqual(situation['paiements_ecartes_annee'], [])


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PaiementsEcartesParAnneeTests(TestCase):
    """Un solde calculé sans les paiements de la période doit être signalé."""

    def setUp(self):
        ecole = Ecole.objects.create(
            nom='Ecole ecart', adresse='Conakry', telephone='+224620000005',
            directeur='Direction',
        )
        classe = Classe.objects.create(
            ecole=ecole, nom='8e', niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Ecart', relation='MERE',
            telephone='+224620000006', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='ECA-001', prenom='Alia', nom='Test', sexe='F',
            date_naissance=date(2012, 1, 1), lieu_naissance='Conakry',
            classe=classe, date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2025-2027',
            frais_inscription_du=Decimal('20000'),
            tranche_1_due=Decimal('500000'),
            tranche_2_due=Decimal('600000'),
            tranche_3_due=Decimal('400000'),
            date_echeance_inscription=date(2025, 9, 15),
            date_echeance_tranche_1=date(2025, 12, 15),
            date_echeance_tranche_2=date(2026, 3, 15),
            date_echeance_tranche_3=date(2026, 6, 15),
        )
        self.paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=TypePaiement.objects.create(nom='Tranche 1'),
            mode_paiement=ModePaiement.objects.create(nom='Espèces'),
            montant=Decimal('520000'),
            date_paiement=date(2026, 1, 10),
            statut='VALIDE',
        )

    def test_incoherence_remontee_dans_la_situation(self):
        situation = situation_echeancier(
            self.echeancier, date_reference=date(2026, 1, 31)
        )

        # Le solde reste celui du périmètre déclaré, mais l'anomalie est
        # exposée pour que l'appelant puisse alerter au lieu d'afficher en
        # silence un dû intégral.
        self.assertEqual(situation['total_encaisse'], Decimal('0'))
        self.assertEqual(
            [p.pk for p in situation['paiements_ecartes_annee']],
            [self.paiement.pk],
        )
