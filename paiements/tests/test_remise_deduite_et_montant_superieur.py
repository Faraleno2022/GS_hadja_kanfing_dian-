"""Deux garde-fous de saisie:

* une remise peut être déduite du reçu, pour qu'elle remplace l'encaissement
  au lieu de s'y ajouter et de laisser de l'argent sans poste à couvrir ;
* un montant supérieur au type sélectionné doit être confirmé, comme l'est
  déjà depuis toujours un montant inférieur.
"""

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
    TypePaiement,
)
from paiements.tests.support import TEST_MIDDLEWARE


class BaseScolariteTests(TestCase):
    """Élève doté d'un échéancier 30 000 / 400 000 / 300 000 / 200 000."""

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
            matricule="TEMP-200",
            prenom="Marie",
            nom="Bore",
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


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RemiseDeduiteDuRecuTests(BaseScolariteTests):
    """La remise peut ramener le reçu à son montant net."""

    def setUp(self):
        super().setUp()
        self.type = TypePaiement.objects.create(nom="Scolarité")
        self.paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type,
            mode_paiement=self.mode,
            montant=Decimal("900000"),
            date_paiement=self.today,
            statut="EN_ATTENTE",
            numero_recu="",
        )
        self.url = reverse(
            "paiements:appliquer_remise", kwargs={"paiement_id": self.paiement.id}
        )

    def _payload(self, deduire):
        donnees = {
            "montant_original": "900000",
            "pourcentage_scolarite": "10",
            "tranches": ["1"],
            "base_calcul": "TRANCHE",
            "motif": "GESTE_COMMERCIAL",
        }
        if deduire:
            donnees["deduire_du_paiement"] = "1"
        return donnees

    def test_option_cochee_ramene_le_recu_au_net(self):
        resp = self.client.post(self.url, self._payload(deduire=True))
        self.assertEqual(resp.status_code, 302)

        self.paiement.refresh_from_db()
        # 10 % de la tranche 1 (400 000) = 40 000
        self.assertEqual(self.paiement.montant, Decimal("860000"))
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertEqual(lien.montant_remise, Decimal("40000"))
        self.assertTrue(lien.deduite_du_paiement)

    def test_option_non_cochee_laisse_le_recu_intact(self):
        resp = self.client.post(self.url, self._payload(deduire=False))
        self.assertEqual(resp.status_code, 302)

        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("900000"))
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertFalse(lien.deduite_du_paiement)

    def test_rejouer_le_formulaire_ne_deduit_pas_deux_fois(self):
        """Sans la trace du brut, la seconde soumission amputerait à nouveau."""
        self.client.post(self.url, self._payload(deduire=True))
        self.client.post(self.url, self._payload(deduire=True))

        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("860000"))

    def test_decocher_restaure_le_montant_brut(self):
        self.client.post(self.url, self._payload(deduire=True))
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("860000"))

        self.client.post(self.url, self._payload(deduire=False))
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("900000"))

    def test_annuler_la_remise_rend_le_montant_au_recu(self):
        self.client.post(self.url, self._payload(deduire=True))
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("860000"))

        resp = self.client.post(
            reverse(
                "paiements:annuler_remise_paiement",
                kwargs={"paiement_id": self.paiement.id},
            )
        )
        self.assertEqual(resp.status_code, 302)

        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("900000"))
        self.assertFalse(PaiementRemise.objects.filter(paiement=self.paiement).exists())

    def test_le_formulaire_propose_l_option(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "deduire_du_paiement")
        self.assertContains(resp, "Déduire la remise du montant du reçu")


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class MontantSuperieurAuTypeTests(BaseScolariteTests):
    """Un montant au-dessus du type demandé n'est jamais enregistré en silence."""

    def setUp(self):
        super().setUp()
        self.type = TypePaiement.objects.create(nom="Inscription + Tranche 1")
        self.url = reverse("paiements:ajouter_paiement")

    def _payload(self, montant, confirmer=False):
        donnees = {
            "eleve": self.eleve.id,
            "type_paiement": self.type.id,
            "mode_paiement": self.mode.id,
            "montant": str(montant),
            "date_paiement": self.today.isoformat(),
            "observations": "",
            "reference_externe": "",
        }
        if confirmer:
            donnees["confirmation_paiement_superieur"] = "1"
        return donnees

    def test_montant_superieur_demande_confirmation(self):
        # Standard du type = 30 000 + 400 000 = 430 000
        resp = self.client.post(self.url, self._payload(600000))

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get("show_superior_confirmation"))
        self.assertFalse(Paiement.objects.filter(eleve=self.eleve).exists())

    def test_la_repartition_reelle_est_affichee(self):
        resp = self.client.post(self.url, self._payload(600000))

        repartition = resp.context.get("repartition")
        self.assertEqual(
            [(ligne["label"], ligne["montant"]) for ligne in repartition],
            [
                ("Inscription", 30000),
                ("1ère tranche", 400000),
                ("2ème tranche", 170000),
            ],
        )

    def test_confirmation_cochee_enregistre_le_paiement(self):
        resp = self.client.post(self.url, self._payload(600000, confirmer=True))

        self.assertEqual(resp.status_code, 302)
        paiement = Paiement.objects.get(eleve=self.eleve)
        self.assertEqual(paiement.montant, Decimal("600000"))

    def test_montant_exact_passe_sans_confirmation(self):
        resp = self.client.post(self.url, self._payload(430000))

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Paiement.objects.filter(eleve=self.eleve).exists())

    def test_montant_au_dela_du_du_annuel_reste_bloque(self):
        """La confirmation n'ouvre pas la porte au sur-paiement réel."""
        resp = self.client.post(self.url, self._payload(2000000, confirmer=True))

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Paiement.objects.filter(eleve=self.eleve).exists())
