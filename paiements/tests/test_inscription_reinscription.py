from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire, Responsable
from paiements.allocation import payment_type_plan
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import _allocate_combined_payment, ensure_echeancier_for_eleve


class PaymentTypePlanTests(SimpleTestCase):
    def test_variantes_de_libelles_sont_reconnues(self):
        scenarios = (
            ("Réinscription + Tranche 1", "reinscription", (1,)),
            ("REINSCRIPTION + 1ere tranche + 2ème tranche", "reinscription", (1, 2)),
            ("Frais d'inscription + Annuel", "inscription", (1, 2, 3)),
            ("Scolarité - T2", None, (2,)),
            ("Scolarité annuelle", None, (1, 2, 3)),
            ("Première tranche + troisième tranche", None, (1, 3)),
            ("Deuxième tranche", None, (2,)),
        )
        for label, kind, tranches in scenarios:
            with self.subTest(label=label):
                plan = payment_type_plan(label)
                self.assertEqual(plan["registration_kind"], kind)
                self.assertEqual(plan["tranches"], tranches)


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class InscriptionReinscriptionIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin_admission",
            email="admin-admission@example.com",
            password=None,
        )
        self.client.force_login(self.user)

        self.ecole = Ecole.objects.create(
            nom="École ventilation admission",
            adresse="Conakry",
            telephone="+224620000101",
            directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="6ème test",
            niveau="PRIMAIRE_6",
            annee_scolaire="2024-2025",
        )
        self.grille = GrilleTarifaire.objects.create(
            ecole=self.ecole,
            niveau=self.classe.niveau,
            annee_scolaire="2024-2025",
            frais_inscription=Decimal("30000"),
            frais_reinscription=Decimal("20000"),
            tranche_1=Decimal("100000"),
            tranche_2=0,
            tranche_3=0,
        )
        self.responsable = Responsable.objects.create(
            prenom="Parent",
            nom="Test",
            relation="PERE",
            telephone="+224620000102",
            adresse="Conakry",
        )
        self.eleve_inscription = self._create_eleve("ADM-I", "Inscrit")
        self.eleve_reinscription = self._create_eleve("ADM-R", "Réinscrit")
        self.echeancier_inscription = self._create_echeancier(
            self.eleve_inscription,
            EcheancierPaiement.NATURE_INSCRIPTION,
            Decimal("30000"),
        )
        self.echeancier_reinscription = self._create_echeancier(
            self.eleve_reinscription,
            EcheancierPaiement.NATURE_REINSCRIPTION,
            Decimal("20000"),
        )
        self.type_reinscription_t1 = TypePaiement.objects.create(
            nom="Réinscription + Tranche 1"
        )
        self.mode = ModePaiement.objects.create(nom="Espèces admission")

    def _create_eleve(self, matricule, prenom):
        return Eleve.objects.create(
            matricule=matricule,
            prenom=prenom,
            nom="Test",
            sexe="F",
            date_naissance=date(2015, 1, 1),
            lieu_naissance="Conakry",
            classe=self.classe,
            date_inscription=date(2024, 9, 1),
            responsable_principal=self.responsable,
        )

    def _create_echeancier(self, eleve, nature, frais):
        return EcheancierPaiement.objects.create(
            eleve=eleve,
            annee_scolaire="2024-2025",
            nature_frais=nature,
            frais_inscription_du=frais,
            tranche_1_due=Decimal("100000"),
            tranche_2_due=0,
            tranche_3_due=0,
            date_echeance_inscription=date(2024, 9, 30),
            date_echeance_tranche_1=date(2025, 1, 10),
            date_echeance_tranche_2=date(2025, 3, 5),
            date_echeance_tranche_3=date(2025, 4, 6),
        )

    def test_nature_reinscription_est_persistee_meme_si_les_tarifs_sont_identiques(self):
        self.grille.frais_inscription = Decimal("20000")
        self.grille.save(update_fields=["frais_inscription"])

        echeancier = ensure_echeancier_for_eleve(
            self.eleve_inscription,
            registration_kind="reinscription",
        )
        echeancier.refresh_from_db()

        self.assertEqual(
            echeancier.nature_frais,
            EcheancierPaiement.NATURE_REINSCRIPTION,
        )
        self.assertEqual(echeancier.frais_inscription_du, Decimal("20000"))
        self.assertEqual(echeancier.libelle_frais_admission, "Frais de réinscription")

    def test_reinscription_plus_t1_est_repartie_dans_le_bon_ordre(self):
        paiement = Paiement.objects.create(
            eleve=self.eleve_reinscription,
            type_paiement=self.type_reinscription_t1,
            mode_paiement=self.mode,
            montant=Decimal("120000"),
            date_paiement=date(2024, 9, 30),
            statut="VALIDE",
            numero_recu="REC-ADM-R",
        )

        allocation = _allocate_combined_payment(
            paiement,
            self.echeancier_reinscription,
        )
        self.echeancier_reinscription.refresh_from_db()

        self.assertEqual(allocation["inscription"], Decimal("20000"))
        self.assertEqual(allocation["tranche_1"], Decimal("100000"))
        self.assertEqual(allocation["tranche_2"], Decimal("0"))
        self.assertEqual(
            self.echeancier_reinscription.nature_frais,
            EcheancierPaiement.NATURE_REINSCRIPTION,
        )

    def test_suggestion_reinscription_est_exacte_et_sans_effet_de_bord(self):
        response = self.client.post(
            reverse("paiements:ajax_montant_suggere"),
            {
                "eleve_id": self.eleve_inscription.pk,
                "type_id": self.type_reinscription_t1.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["suggested"], 120000)
        self.assertEqual(payload["breakdown"]["fi_restant"], 20000)
        self.assertEqual(
            payload["breakdown"]["frais_admission_label"],
            "Réinscription",
        )
        self.echeancier_inscription.refresh_from_db()
        self.assertEqual(
            self.echeancier_inscription.nature_frais,
            EcheancierPaiement.NATURE_INSCRIPTION,
        )
        self.assertEqual(
            self.echeancier_inscription.frais_inscription_du,
            Decimal("30000"),
        )

    def test_suggestion_ne_cree_pas_un_echeancier(self):
        eleve_sans_echeancier = self._create_eleve("ADM-S", "Sans échéancier")
        count_before = EcheancierPaiement.objects.count()

        response = self.client.post(
            reverse("paiements:ajax_montant_suggere"),
            {
                "eleve_id": eleve_sans_echeancier.pk,
                "type_id": self.type_reinscription_t1.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggested"], 120000)
        self.assertEqual(EcheancierPaiement.objects.count(), count_before)
        self.assertFalse(
            EcheancierPaiement.objects.filter(eleve=eleve_sans_echeancier).exists()
        )

    def test_liste_separe_strictement_inscription_et_reinscription(self):
        response = self.client.get(
            reverse("paiements:liste_paiements"),
            {"annee": "2024-2025"},
        )

        self.assertEqual(response.status_code, 200)
        totals = response.context["totaux_du"]
        self.assertEqual(totals["du_sco_net"], 200000)
        self.assertEqual(totals["frais_inscription_total"], 30000)
        self.assertEqual(totals["frais_reinscription_total"], 20000)
        self.assertEqual(totals["du_global_net"], 250000)
        self.assertEqual(totals["frais_reinscription_pct"], 40.0)

        rows = response.context["totaux_du_detail_classes"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["frais_inscription_total"], 30000)
        self.assertEqual(rows[0]["frais_reinscription_total"], 20000)
        self.assertEqual(rows[0]["du_global_net"], 250000)

    def test_export_excel_conserve_la_meme_ventilation(self):
        response = self.client.get(reverse("paiements:export_recap_par_classe_excel"))

        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        values = list(workbook.active.iter_rows(min_row=2, max_row=2, values_only=True))[0]
        self.assertEqual(values[4], 30000)
        self.assertEqual(values[5], 20000)
        self.assertEqual(values[6], 40.0)
        self.assertEqual(values[7], 250000)

    def test_plusieurs_remises_ne_multiplient_pas_les_montants_dus(self):
        paiement = Paiement.objects.create(
            eleve=self.eleve_inscription,
            type_paiement=self.type_reinscription_t1,
            mode_paiement=self.mode,
            montant=Decimal("50000"),
            date_paiement=date(2024, 10, 1),
            statut="VALIDE",
            numero_recu="REC-REMISES",
        )
        for index, montant in enumerate((Decimal("5000"), Decimal("10000")), start=1):
            remise = RemiseReduction.objects.create(
                nom=f"Remise {index}",
                type_remise="MONTANT_FIXE",
                valeur=montant,
                motif="AUTRE",
                date_debut=date(2024, 9, 1),
                date_fin=date(2025, 8, 31),
            )
            PaiementRemise.objects.create(
                paiement=paiement,
                remise=remise,
                montant_remise=montant,
            )

        response = self.client.get(
            reverse("paiements:liste_paiements"),
            {"annee": "2024-2025"},
        )

        totals = response.context["totaux_du"]
        self.assertEqual(totals["du_sco_net"], 185000)
        self.assertEqual(totals["frais_inscription_total"], 30000)
        self.assertEqual(totals["frais_reinscription_total"], 20000)
        self.assertEqual(totals["du_global_net"], 235000)

    def test_echeancier_affiche_le_libelle_reinscription(self):
        response = self.client.get(
            reverse(
                "paiements:echeancier_eleve",
                kwargs={"eleve_id": self.eleve_reinscription.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Frais de réinscription")
