"""Montant exact suggéré par type de paiement, et liberté de saisie du montant.

Le caissier choisit un type (« Réinscription + Tranche 1 ») : le moteur doit
retrouver seul le montant restant dû sur ces postes, détail à l'appui, et le
champ montant ne doit refuser aucune écriture usuelle (1 130 500 GNF).
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire, Responsable
from paiements.allocation import payment_type_plan
from paiements.models import (
    EcheancierPaiement, ModePaiement, Paiement, TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


class LectureDesLibellesTests(SimpleTestCase):
    """Les types sont créés à la main par les écoles : toutes les écritures
    rencontrées doivent tomber sur les bons postes."""

    def test_libelles_courants(self):
        scenarios = (
            # libellé, admission attendue, tranches attendues
            ("Réinscription + Tranche 1", True, (1,)),
            ("Inscription + Tranche 1 + Tranche 2 + Tranche 3", True, (1, 2, 3)),
            ("Tranche 1 et 2", False, (1, 2)),
            ("Tranches 1, 2 et 3", False, (1, 2, 3)),
            ("2ème et 3ème tranches", False, (2, 3)),
            ("Tranches 1 à 3", False, (1, 2, 3)),
            ("T1-T3", False, (1, 2, 3)),
            ("T1+T2", False, (1, 2)),
            ("Tranche deux", False, (2,)),
            ("2ème trimestre", False, (2,)),
            ("Versement 1", False, (1,)),
            ("Scolarité annuelle", False, (1, 2, 3)),
            ("Tranche 1 (2025-2026)", False, (1,)),
            # Postes hors échéancier : aucune suggestion possible.
            ("Cantine", False, ()),
            ("Transport scolaire", False, ()),
            ("Uniforme", False, ()),
        )
        for libelle, admission, tranches in scenarios:
            with self.subTest(libelle=libelle):
                plan = payment_type_plan(libelle)
                self.assertEqual(plan["include_registration"], admission)
                self.assertEqual(plan["tranches"], tranches)

    def test_solde_couvre_tout_le_reste(self):
        for libelle in ("Solde de la scolarité", "Reliquat", "Complément", "Paiement total"):
            with self.subTest(libelle=libelle):
                plan = payment_type_plan(libelle)
                self.assertTrue(plan["covers_balance"])
                self.assertTrue(plan["include_registration"])
                self.assertEqual(plan["tranches"], (1, 2, 3))

    def test_poste_nomme_apres_solde_reste_prioritaire(self):
        plan = payment_type_plan("Solde tranche 2")
        self.assertEqual(plan["tranches"], (2,))
        self.assertFalse(plan["include_registration"])

    def test_exclusions_explicites(self):
        sans_inscription = payment_type_plan("Scolarité sans inscription")
        self.assertFalse(sans_inscription["include_registration"])
        self.assertEqual(sans_inscription["tranches"], (1, 2, 3))

        sauf_t3 = payment_type_plan("Annuel sauf tranche 3")
        self.assertEqual(sauf_t3["tranches"], (1, 2))


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class MontantSuggereParTypeTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('caisse_suggestion', 's@s.gn', None)
        self.client.force_login(self.user)

        self.ecole = Ecole.objects.create(
            nom="École suggestion", adresse="Conakry",
            telephone="+224620000201", directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom="6ème S", niveau="PRIMAIRE_6",
            annee_scolaire="2025-2026",
        )
        GrilleTarifaire.objects.create(
            ecole=self.ecole, niveau=self.classe.niveau, annee_scolaire="2025-2026",
            frais_inscription=Decimal("100000"), frais_reinscription=Decimal("60000"),
            tranche_1=Decimal("300000"), tranche_2=Decimal("300000"),
            tranche_3=Decimal("300000"),
        )
        responsable = Responsable.objects.create(
            prenom="Parent", nom="Suggestion", relation="PERE",
            telephone="+224620000202", adresse="Conakry",
        )
        self.eleve = Eleve.objects.create(
            matricule="SUG-001", prenom="Aminata", nom="Bah", sexe="F",
            date_naissance=date(2014, 3, 2), lieu_naissance="Conakry",
            classe=self.classe, date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire="2025-2026",
            nature_frais=EcheancierPaiement.NATURE_REINSCRIPTION,
            frais_inscription_du=Decimal("60000"),
            tranche_1_due=Decimal("300000"),
            tranche_2_due=Decimal("300000"),
            tranche_3_due=Decimal("300000"),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2025, 12, 31),
            date_echeance_tranche_2=date(2026, 3, 31),
            date_echeance_tranche_3=date(2026, 6, 30),
        )
        self.mode = ModePaiement.objects.create(nom="Espèces suggestion")

    def _suggerer(self, libelle_type):
        type_paiement = TypePaiement.objects.create(nom=libelle_type)
        reponse = self.client.post(
            reverse("paiements:ajax_montant_suggere"),
            {"eleve_id": self.eleve.pk, "type_id": type_paiement.pk},
        )
        self.assertEqual(reponse.status_code, 200)
        return reponse.json()

    def test_reinscription_plus_tranche_1(self):
        data = self._suggerer("Réinscription + Tranche 1")

        self.assertTrue(data["ok"])
        self.assertEqual(data["suggested"], 360000)  # 60 000 + 300 000
        self.assertEqual(data["solde_total"], 960000)
        libelles = [ligne["libelle"] for ligne in data["breakdown"]["lignes"]]
        restes = [ligne["reste"] for ligne in data["breakdown"]["lignes"]]
        self.assertEqual(libelles, ["Réinscription", "Tranche 1"])
        self.assertEqual(restes, [60000, 300000])

    def test_deduit_les_encaissements_deja_valides(self):
        Paiement.objects.create(
            eleve=self.eleve, type_paiement=TypePaiement.objects.create(nom="Acompte"),
            mode_paiement=self.mode, montant=Decimal("100000"),
            date_paiement=date(2025, 9, 15), statut="VALIDE",
            annee_scolaire="2025-2026",
        )
        self.echeancier.frais_inscription_paye = Decimal("60000")
        self.echeancier.tranche_1_payee = Decimal("40000")
        self.echeancier.save()

        data = self._suggerer("Réinscription + Tranche 1")

        # Reste : réinscription soldée, tranche 1 à 300 000 - 40 000.
        self.assertEqual(data["suggested"], 260000)

    def test_tranches_enumerees(self):
        self.assertEqual(self._suggerer("Tranches 2 et 3")["suggested"], 600000)

    def test_solde_couvre_toute_l_annee(self):
        data = self._suggerer("Solde de l'année")
        self.assertEqual(data["suggested"], 960000)
        self.assertEqual(data["suggested"], data["solde_total"])

    def test_type_hors_echeancier_ne_suggere_rien(self):
        data = self._suggerer("Cantine")
        self.assertEqual(data["suggested"], 0)
        self.assertFalse(data["breakdown"]["postes_reconnus"])
        self.assertIn("à la main", data["breakdown"]["description"])

    def test_suggestion_ne_modifie_pas_l_echeancier(self):
        avant = EcheancierPaiement.objects.get(pk=self.echeancier.pk)
        self._suggerer("Inscription + Tranche 1")
        apres = EcheancierPaiement.objects.get(pk=self.echeancier.pk)

        self.assertEqual(apres.nature_frais, avant.nature_frais)
        self.assertEqual(apres.frais_inscription_du, avant.frais_inscription_du)


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class SaisieMontantAjoutTests(TestCase):
    """L'écran d'ajout accepte les mêmes écritures que l'écran de correction."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('caisse_ajout', 'a@a.gn', None)
        self.client.force_login(self.user)

        self.ecole = Ecole.objects.create(
            nom="École ajout", adresse="Conakry",
            telephone="+224620000301", directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom="6ème A", niveau="PRIMAIRE_6",
            annee_scolaire="2025-2026",
        )
        responsable = Responsable.objects.create(
            prenom="Parent", nom="Ajout", relation="PERE",
            telephone="+224620000302", adresse="Conakry",
        )
        self.eleve = Eleve.objects.create(
            matricule="AJT-001", prenom="Sekou", nom="Toure", sexe="M",
            date_naissance=date(2013, 5, 4), lieu_naissance="Kankan",
            classe=self.classe, date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire="2025-2026",
            frais_inscription_du=Decimal("100000"),
            tranche_1_due=Decimal("1200000"),
            tranche_2_due=Decimal("0"), tranche_3_due=Decimal("0"),
            date_echeance_inscription=date(2025, 9, 30),
            date_echeance_tranche_1=date(2025, 12, 31),
            date_echeance_tranche_2=date(2026, 3, 31),
            date_echeance_tranche_3=date(2026, 6, 30),
        )
        self.type_p = TypePaiement.objects.create(nom="Tranche 1")
        self.mode_p = ModePaiement.objects.create(nom="Espèces ajout")

    def _ajouter(self, montant):
        return self.client.post(
            reverse("paiements:ajouter_paiement"),
            {
                'eleve': self.eleve.pk,
                'type_paiement': self.type_p.pk,
                'mode_paiement': self.mode_p.pk,
                'montant': montant,
                'date_paiement': '2025-10-05',
                'observations': '',
                'reference_externe': '',
            },
            follow=True,
        )

    def test_montant_hors_multiple_de_mille(self):
        self._ajouter('1130500')
        paiement = Paiement.objects.filter(eleve=self.eleve).first()
        self.assertIsNotNone(paiement, "Le paiement n'a pas été enregistré")
        self.assertEqual(paiement.montant, Decimal('1130500'))

    def test_montant_saisi_avec_espaces_et_sigle(self):
        self._ajouter('1 130 500 GNF')
        paiement = Paiement.objects.filter(eleve=self.eleve).first()
        self.assertIsNotNone(paiement, "Le paiement n'a pas été enregistré")
        self.assertEqual(paiement.montant, Decimal('1130500'))

    def test_champ_montant_sans_pas_de_1000(self):
        reponse = self.client.get(reverse("paiements:ajouter_paiement"))
        self.assertEqual(reponse.status_code, 200)
        contenu = reponse.content.decode()
        self.assertNotIn('step="1000"', contenu)
        self.assertIn('inputmode="numeric"', contenu)
