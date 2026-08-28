"""Deux garde-fous de saisie ajoutés côté paiements.

* la remise peut être déduite du reçu, sans jamais l'être deux fois ;
* un montant supérieur au type sélectionné exige une confirmation.
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
    RemiseReduction,
    TypePaiement,
)
from paiements.tests.support import TEST_MIDDLEWARE


class _BaseScolarite(TestCase):
    """Dossier commun : inscription 30 000, tranches 400/300/200 000."""

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


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class RemiseDeduiteDuRecuTests(_BaseScolarite):
    """La remise peut ramener le reçu au net, une seule fois."""

    def setUp(self):
        super().setUp()
        self.type = TypePaiement.objects.create(nom="Scolarité")
        self.paiement = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type,
            mode_paiement=self.mode,
            montant=Decimal("400000"),
            date_paiement=self.today,
            statut="EN_ATTENTE",
            numero_recu="",
        )
        self.url = reverse(
            "paiements:appliquer_remise", kwargs={"paiement_id": self.paiement.id}
        )

    def _post(self, deduire, pourcentage="10"):
        donnees = {
            "montant_original": "400000",
            "pourcentage_scolarite": pourcentage,
            "tranches": ["1"],
            "base_calcul": "TRANCHE",
            "motif": "GESTE_COMMERCIAL",
        }
        if deduire:
            donnees["deduire_du_paiement"] = "1"
        return self.client.post(self.url, donnees)

    def test_sans_option_le_recu_reste_au_brut(self):
        resp = self._post(deduire=False)
        self.assertEqual(resp.status_code, 302)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("400000"))
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertFalse(lien.deduite_du_paiement)

    def test_option_cochee_ramene_le_recu_au_net(self):
        # 10 % de la tranche 1 (400 000) = 40 000
        resp = self._post(deduire=True)
        self.assertEqual(resp.status_code, 302)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("360000"))
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertEqual(lien.montant_remise, Decimal("40000"))
        self.assertTrue(lien.deduite_du_paiement)

    def test_rejouer_l_ecran_ne_deduit_pas_deux_fois(self):
        self._post(deduire=True)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("360000"))

        # Même remise resoumise : le brut est reconstitué avant recalcul.
        self._post(deduire=True)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("360000"))

    def test_decocher_l_option_restaure_le_brut(self):
        self._post(deduire=True)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("360000"))

        self._post(deduire=False)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("400000"))
        self.assertFalse(
            PaiementRemise.objects.get(paiement=self.paiement).deduite_du_paiement
        )

    def test_annuler_la_remise_rend_le_montant_au_recu(self):
        self._post(deduire=True)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("360000"))

        resp = self.client.post(
            reverse(
                "paiements:annuler_remise_paiement",
                kwargs={"paiement_id": self.paiement.id},
            )
        )
        self.assertEqual(resp.status_code, 302)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("400000"))
        self.assertFalse(PaiementRemise.objects.filter(paiement=self.paiement).exists())

    def test_le_recalcul_re_derive_le_recu(self):
        """Corriger un paiement doit garder net = brut − remise."""
        from paiements.payment_engine import recalculer_remises_paiement

        self._post(deduire=True)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal("360000"))

        # La tranche 1 est corrigée: la remise de 10 % vaut désormais 20 000
        self.echeancier.tranche_1_due = Decimal("200000")
        self.echeancier.save()
        recalculer_remises_paiement(self.paiement)

        self.paiement.refresh_from_db()
        lien = PaiementRemise.objects.get(paiement=self.paiement)
        self.assertEqual(lien.montant_remise, Decimal("20000"))
        self.assertEqual(self.paiement.montant, Decimal("380000"))

    def test_le_recu_ne_deduit_pas_la_remise_deux_fois(self):
        """Reçu : brut 400 000, remise 40 000, net 360 000 — pas 320 000."""
        from paiements.remise_utils import montant_brut_paiement

        self._post(deduire=True)
        self.paiement.refresh_from_db()

        brut = montant_brut_paiement(self.paiement)
        remises = sum(
            lien.montant_remise
            for lien in PaiementRemise.objects.filter(paiement=self.paiement)
        )
        self.assertEqual(brut, Decimal("400000"))
        self.assertEqual(remises, Decimal("40000"))
        self.assertEqual(brut - remises, self.paiement.montant)

    def test_le_formulaire_propose_l_option(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "deduire_du_paiement")
        self.assertContains(resp, "Déduire la remise du montant du reçu")


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class MontantSuperieurAuTypeTests(_BaseScolarite):
    """Un montant au-dessus du type ne part plus sans confirmation."""

    def setUp(self):
        super().setUp()
        # Type combiné : inscription (30 000) + T1 (400 000) = 430 000 attendus
        self.type = TypePaiement.objects.create(nom="Inscription + Tranche 1")
        self.url = reverse("paiements:ajouter_paiement")

    def _donnees(self, montant, **extra):
        donnees = {
            "eleve": self.eleve.id,
            "type_paiement": self.type.id,
            "mode_paiement": self.mode.id,
            "montant": str(montant),
            "date_paiement": self.today.isoformat(),
            "observations": "",
            "reference_externe": "",
        }
        donnees.update(extra)
        return donnees

    def test_montant_superieur_demande_confirmation(self):
        resp = self.client.post(self.url, self._donnees(500000))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["show_superior_confirmation"])
        self.assertFalse(Paiement.objects.exists())

    def test_la_repartition_reelle_est_affichee(self):
        resp = self.client.post(self.url, self._donnees(500000))
        repartition = {
            ligne["label"]: ligne["montant"] for ligne in resp.context["repartition"]
        }
        # 30 000 d'inscription, 400 000 sur T1, le reste en acompte T2
        self.assertEqual(repartition["Inscription"], 30000)
        self.assertEqual(repartition["1ère tranche"], 400000)
        self.assertEqual(repartition["2ème tranche"], 70000)

    def test_confirmation_cochee_enregistre_le_paiement(self):
        resp = self.client.post(
            self.url,
            self._donnees(500000, confirmation_paiement_superieur="1"),
        )
        self.assertEqual(resp.status_code, 302)
        paiement = Paiement.objects.get()
        self.assertEqual(paiement.montant, Decimal("500000"))

    def test_montant_exact_passe_sans_confirmation(self):
        resp = self.client.post(self.url, self._donnees(430000))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Paiement.objects.count(), 1)

    def test_montant_inferieur_demande_toujours_confirmation(self):
        """L'asymétrie corrigée ne doit pas retirer le contrôle existant."""
        resp = self.client.post(self.url, self._donnees(100000))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["show_partial_confirmation"])
        self.assertFalse(Paiement.objects.exists())
