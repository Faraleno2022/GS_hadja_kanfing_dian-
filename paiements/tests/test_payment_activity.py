from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.activity_metrics import build_payment_activity_metrics
from paiements.models import EcheancierPaiement, ModePaiement, Paiement, TypePaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import _valider_paiement_impl


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class PaymentActivityTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.school_year = f"{self.today.year}-{self.today.year + 1}"
        self.user = get_user_model().objects.create_superuser(
            username="admin-activite-paiements",
            email="activite@example.com",
            password="mot-de-passe-test",
        )
        self.client.force_login(self.user)
        self.school = Ecole.objects.create(
            nom="École audit paiements",
            adresse="Conakry",
            telephone="+224620001601",
            directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.school,
            nom="7ème Audit",
            niveau="COLLEGE_7",
            annee_scolaire=self.school_year,
        )
        self.responsable = Responsable.objects.create(
            prenom="Fatoumata",
            nom="Diallo",
            relation="MERE",
            telephone="+224620001602",
            adresse="Conakry",
        )
        self.eleve = Eleve.objects.create(
            matricule="AUD-PAY-001",
            prenom="Mariam",
            nom="Camara",
            sexe="F",
            date_naissance=date(2013, 4, 12),
            classe=self.classe,
            date_inscription=self.today,
            responsable_principal=self.responsable,
        )
        self.type_paiement = TypePaiement.objects.create(nom="Tranche 1 audit")
        self.mode_paiement = ModePaiement.objects.create(nom="Espèces audit")
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire=self.school_year,
            frais_inscription_du=Decimal("0"),
            tranche_1_due=Decimal("400000"),
            tranche_2_due=Decimal("0"),
            tranche_3_due=Decimal("0"),
            date_echeance_inscription=self.today,
            date_echeance_tranche_1=self.today,
            date_echeance_tranche_2=self.today,
            date_echeance_tranche_3=self.today,
        )

    def _payment(self, amount, receipt):
        payment = Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement,
            numero_recu=receipt,
            montant=Decimal(amount),
            annee_scolaire=self.school_year,
            date_paiement=self.today,
            statut="EN_ATTENTE",
            cree_par=self.user,
        )
        _valider_paiement_impl(payment, self.user)
        payment.refresh_from_db()
        return payment

    def test_modification_recalcule_echeancier_cartes_et_activite(self):
        payment = self._payment("120000", "AUD-MOD-001")

        response = self.client.post(
            reverse("paiements:modifier_paiement", args=[payment.pk]),
            {
                "type_paiement": self.type_paiement.pk,
                "mode_paiement": self.mode_paiement.pk,
                "montant": "175000",
                "date_paiement": self.today.isoformat(),
                "reference_externe": "REF-CORRECTION",
                "observations": "",
                "motif_modification": "Correction du montant du reçu",
            },
        )

        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(payment.montant, Decimal("175000"))
        self.assertEqual(payment.statut, "EN_ATTENTE")
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal("0"))

        metrics = build_payment_activity_metrics(self.user, today=self.today)
        today_metrics = metrics["values"]["today"]
        self.assertEqual(today_metrics["modified_count"], 1)
        self.assertEqual(today_metrics["modified_before"], 120000)
        self.assertEqual(today_metrics["modified_after"], 175000)
        self.assertEqual(today_metrics["modified_delta"], 55000)
        self.assertEqual(metrics["values"]["week"]["modified_count"], 1)
        self.assertEqual(metrics["values"]["month"]["modified_count"], 1)
        self.assertEqual(metrics["values"]["year"]["modified_count"], 1)

        ajax = self.client.get(reverse("paiements:ajax_statistiques_paiements"))
        self.assertEqual(ajax.status_code, 200)
        payload = ajax.json()
        self.assertEqual(payload["stats"]["paiements_en_attente"], 1)
        self.assertEqual(
            payload["payment_activity_metrics"]["values"]["today"]["net_impact"],
            55000,
        )
        scolarite = next(
            category
            for category in payload["financial_metrics"]["categories"]
            if category["key"] == "scolarite"
        )
        self.assertEqual(scolarite["values"]["today"]["amount"], 0)

    def test_suppression_recalcule_tout_et_affiche_le_motif(self):
        deleted_payment = self._payment("120000", "AUD-DEL-001")
        self._payment("30000", "AUD-KEEP-001")

        response = self.client.post(
            reverse("paiements:supprimer_paiement", args=[deleted_payment.pk]),
            {"motif": "Reçu annulé après contrôle de caisse"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Paiement.objects.filter(pk=deleted_payment.pk).exists())
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal("30000"))

        metrics = build_payment_activity_metrics(self.user, today=self.today)
        today_metrics = metrics["values"]["today"]
        self.assertEqual(today_metrics["deleted_count"], 1)
        self.assertEqual(today_metrics["deleted_amount"], 120000)
        self.assertEqual(today_metrics["net_impact"], -120000)

        history = self.client.get(reverse("paiements:historique_activite"))
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, "AUD-DEL-001")
        self.assertContains(history, "Reçu annulé après contrôle de caisse")

        ajax = self.client.get(reverse("paiements:ajax_statistiques_paiements"))
        self.assertEqual(ajax.status_code, 200)
        scolarite = next(
            category
            for category in ajax.json()["financial_metrics"]["categories"]
            if category["key"] == "scolarite"
        )
        self.assertEqual(scolarite["values"]["today"]["amount"], 30000)

    def test_tableau_de_bord_expose_la_carte_et_le_bouton(self):
        response = self.client.get(reverse("paiements:tableau_bord"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Montants modifiés et supprimés")
        self.assertContains(response, "Afficher la liste et les motifs")
        self.assertContains(response, reverse("paiements:historique_activite"))
