from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eleves.models import Ecole, Classe, Responsable, Eleve
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)
from paiements.tests.support import TEST_MIDDLEWARE


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class AppliquerRemiseParTrancheTests(TestCase):
    """La remise porte sur les tranches choisies, jamais sur l'inscription."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass1234"
        )
        self.client.force_login(self.user)

        self.ecole = Ecole.objects.create(
            nom="Ecole Test",
            adresse="Addr",
            telephone="+224123456789",
            email="ecole@test.com",
            directeur="Dir",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="7ème année",
            niveau="COLLEGE_7",
            annee_scolaire="2024-2025",
            capacite_max=40,
        )
        self.responsable = Responsable.objects.create(
            prenom="Jean",
            nom="Doe",
            relation="PERE",
            telephone="+224123456789",
            email="p@example.com",
            adresse="Addr",
        )
        self.eleve = Eleve.objects.create(
            matricule="TEMP-100",
            prenom="Alice",
            nom="Test",
            sexe="F",
            date_naissance=date(2012, 5, 4),
            lieu_naissance="Ville",
            classe=self.classe,
            date_inscription=timezone.now().date(),
            statut="ACTIF",
            responsable_principal=self.responsable,
        )
        self.today = timezone.now().date()
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire="2024-2025",
            frais_inscription_du=Decimal("30000"),
            tranche_1_due=Decimal("400000"),
            tranche_2_due=Decimal("300000"),
            tranche_3_due=Decimal("200000"),
            date_echeance_inscription=self.today,
            date_echeance_tranche_1=self.today + timedelta(days=30),
            date_echeance_tranche_2=self.today + timedelta(days=60),
            date_echeance_tranche_3=self.today + timedelta(days=90),
        )
        self.mode = ModePaiement.objects.create(nom="Espèces")
        self.type = TypePaiement.objects.create(nom="Scolarité")

        self.paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type,
            mode_paiement=self.mode,
            montant=Decimal("100000"),
            date_paiement=self.today,
            statut="EN_ATTENTE",
            numero_recu="",
        )
        self.url = reverse(
            "paiements:appliquer_remise", kwargs={"paiement_id": self.paiement.id}
        )

    def _remise_pourcentage(self, valeur=10):
        return RemiseReduction.objects.create(
            nom=f"Remise fratrie {valeur}%",
            type_remise="POURCENTAGE",
            valeur=valeur,
            motif="FRATRIE",
            date_debut=self.today - timedelta(days=30),
            date_fin=self.today + timedelta(days=180),
            actif=True,
        )

    def test_remise_sur_une_seule_tranche(self):
        remise = self._remise_pourcentage(10)
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "remises": [remise.id],
                "tranches": ["1"],
                "base_calcul": "TRANCHE",
                "motif": "GESTE_COMMERCIAL",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement, remise=remise)
        # 10% de la seule tranche 1 (400 000), pas de T2/T3 ni inscription
        self.assertEqual(lien.montant_remise, Decimal("40000"))
        self.assertEqual(lien.montant_base, Decimal("400000"))
        self.assertEqual(lien.tranches_appliquees, [1])
        self.assertEqual(lien.libelle_portee, "T1")

    def test_remise_sur_tranches_2_et_3(self):
        remise = self._remise_pourcentage(10)
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "remises": [remise.id],
                "tranches": ["2", "3"],
                "base_calcul": "TRANCHE",
                "motif": "GESTE_COMMERCIAL",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement, remise=remise)
        # 10% de (300 000 + 200 000)
        self.assertEqual(lien.montant_remise, Decimal("50000"))
        self.assertEqual(lien.tranches_appliquees, [2, 3])

    def test_pourcentage_scolarite_sur_les_trois_tranches(self):
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "pourcentage_scolarite": "50",
                "tranches": ["1", "2", "3"],
                "base_calcul": "TRANCHE",
                "motif": "GESTE_COMMERCIAL",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        # 50% de 900 000 : la remise n'est plus plafonnée au montant du reçu
        self.assertEqual(lien.montant_remise, Decimal("450000"))
        self.assertEqual(lien.libelle_portee, "T1 + T2 + T3")

    def test_base_echeance_utilise_la_part_scolarite_du_paiement(self):
        """Un paiement d'inscription de 130 000 laisse 100 000 sur la tranche 1."""
        type_inscription = TypePaiement.objects.create(nom="Inscription")
        paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=type_inscription,
            mode_paiement=self.mode,
            montant=Decimal("130000"),
            date_paiement=self.today,
            statut="EN_ATTENTE",
            numero_recu="",
        )
        remise = self._remise_pourcentage(10)
        url = reverse("paiements:appliquer_remise", kwargs={"paiement_id": paiement.id})
        resp = self.client.post(
            url,
            {
                "montant_original": paiement.montant,
                "remises": [remise.id],
                "tranches": ["1"],
                "base_calcul": "ECHEANCE",
                "motif": "GESTE_COMMERCIAL",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=paiement, remise=remise)
        # Base = 100 000 (part T1) et non 130 000 : les 30 000 d'inscription sont exclus
        self.assertEqual(lien.montant_base, Decimal("100000"))
        self.assertEqual(lien.montant_remise, Decimal("10000"))
        self.assertEqual(lien.base_calcul, "ECHEANCE")

    def test_aucune_tranche_cochee_est_refuse(self):
        remise = self._remise_pourcentage(10)
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "remises": [remise.id],
                "base_calcul": "TRANCHE",
                "motif": "GESTE_COMMERCIAL",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PaiementRemise.objects.filter(paiement=self.paiement).exists())
        self.assertContains(resp, "Sélectionnez au moins une tranche")

    def test_tranche_sans_montant_du_est_refusee(self):
        self.echeancier.tranche_3_due = Decimal("0")
        self.echeancier.save()
        remise = self._remise_pourcentage(10)
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "remises": [remise.id],
                "tranches": ["3"],
                "base_calcul": "TRANCHE",
                "motif": "GESTE_COMMERCIAL",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PaiementRemise.objects.filter(paiement=self.paiement).exists())


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class MotifRemiseObligatoireTests(AppliquerRemiseParTrancheTests):
    """Toute remise doit porter un motif; certains motifs fixent le pourcentage."""

    def test_sans_motif_la_remise_est_refusee(self):
        remise = self._remise_pourcentage(10)
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "remises": [remise.id],
                "tranches": ["1"],
                "base_calcul": "TRANCHE",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PaiementRemise.objects.filter(paiement=self.paiement).exists())
        self.assertContains(resp, "Le motif de la remise est obligatoire.")

    def test_motif_enregistre_sur_la_remise(self):
        remise = self._remise_pourcentage(10)
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "remises": [remise.id],
                "tranches": ["1"],
                "base_calcul": "TRANCHE",
                "motif": "CLIENT_FIDELE",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement, remise=remise)
        self.assertEqual(lien.motif, "CLIENT_FIDELE")
        self.assertEqual(lien.libelle_motif, "Client fidèle")

    def test_motif_ne_paie_rien_applique_cent_pour_cent(self):
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "tranches": ["1", "2", "3"],
                "base_calcul": "TRANCHE",
                "motif": "NE_PAIE_RIEN",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        # 100% de 400 000 + 300 000 + 200 000, l'inscription restant due
        self.assertEqual(lien.montant_remise, Decimal("900000"))
        self.assertEqual(lien.motif, "NE_PAIE_RIEN")

    def test_motif_la_moitie_applique_cinquante_pour_cent(self):
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "tranches": ["1"],
                "base_calcul": "TRANCHE",
                "motif": "LA_MOITIE",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertEqual(lien.montant_remise, Decimal("200000"))

    def test_pourcentage_choisi_prime_sur_celui_du_motif(self):
        resp = self.client.post(
            self.url,
            {
                "montant_original": self.paiement.montant,
                "pourcentage_scolarite": "10",
                "tranches": ["1"],
                "base_calcul": "TRANCHE",
                "motif": "LA_MOITIE",
            },
        )
        self.assertEqual(resp.status_code, 302)
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertEqual(lien.montant_remise, Decimal("40000"))
