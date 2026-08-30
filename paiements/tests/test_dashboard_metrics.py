from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bus.models import AbonnementBus, AbonnementCantine
from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.dashboard_metrics import build_payment_dashboard_metrics
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    TypePaiement,
)
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class PaymentDashboardMetricsTests(TestCase):
    today = date(2026, 8, 26)

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-dashboard-financier",
            email="dashboard@example.com",
            password="mot-de-passe-test",
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom="École des indicateurs",
            adresse="Conakry",
            telephone="+224620000501",
            directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="8ème Indicateurs",
            niveau="COLLEGE_8",
            annee_scolaire="2026-2027",
        )
        self.responsable = Responsable.objects.create(
            prenom="Mamadou",
            nom="Camara",
            relation="PERE",
            telephone="+224620000502",
            adresse="Conakry",
        )
        self.mode = ModePaiement.objects.create(nom="Espèces indicateurs")
        self.type_inscription = TypePaiement.objects.create(
            nom="Inscription + Tranche 1 indicateurs"
        )
        self.type_reinscription = TypePaiement.objects.create(
            nom="Réinscription + Tranche 1 indicateurs"
        )
        self.type_scolarite = TypePaiement.objects.create(
            nom="Tranche 1 indicateurs"
        )
        self._create_financial_history()

    def _student(self, suffix):
        return Eleve.objects.create(
            matricule=f"MET-{suffix}",
            prenom=f"Élève {suffix}",
            nom="Indicateur",
            sexe="F",
            date_naissance=date(2013, 1, 1),
            classe=self.classe,
            date_inscription=date(2026, 7, 1),
            responsable_principal=self.responsable,
        )

    def _schedule(
        self,
        student,
        *,
        nature=EcheancierPaiement.NATURE_INSCRIPTION,
        admission=0,
        tuition=0,
        tuition_paid=0,
        tuition_due_date=None,
    ):
        future = self.today + timedelta(days=60)
        return EcheancierPaiement.objects.create(
            eleve=student,
            annee_scolaire="2026-2027",
            nature_frais=nature,
            frais_inscription_du=Decimal(admission),
            frais_inscription_paye=Decimal("0"),
            tranche_1_due=Decimal(tuition),
            tranche_1_payee=Decimal(tuition_paid),
            tranche_2_due=Decimal("0"),
            tranche_2_payee=Decimal("0"),
            tranche_3_due=Decimal("0"),
            tranche_3_payee=Decimal("0"),
            date_echeance_inscription=future,
            date_echeance_tranche_1=tuition_due_date or future,
            date_echeance_tranche_2=future,
            date_echeance_tranche_3=future,
        )

    def _payment(self, student, receipt, amount, payment_date, payment_type):
        return Paiement.objects.create(
            eleve=student,
            type_paiement=payment_type,
            mode_paiement=self.mode,
            numero_recu=receipt,
            montant=Decimal(amount),
            annee_scolaire="2026-2027",
            date_paiement=payment_date,
            statut="VALIDE",
            cree_par=self.user,
            valide_par=self.user,
        )

    def _subscription(self, model, student, amount, start, expiration, **extra):
        defaults = {
            "eleve": student,
            "montant": Decimal(amount),
            "date_debut": start,
            "date_expiration": expiration,
            "statut": model.Statut.ACTIF,
        }
        defaults.update(extra)
        return model.objects.create(**defaults)

    def _create_financial_history(self):
        week_start = self.today - timedelta(days=self.today.weekday())
        month_date = self.today.replace(day=5)
        year_date = date(self.today.year, 2, 10)
        future = self.today + timedelta(days=90)

        today_student = self._student("TODAY")
        self._schedule(today_student, admission=50000, tuition=100000)
        self._payment(
            today_student, "MET-REC-001", 150000, self.today,
            self.type_inscription,
        )

        week_student = self._student("WEEK")
        self._schedule(
            week_student,
            nature=EcheancierPaiement.NATURE_REINSCRIPTION,
            admission=30000,
            tuition=70000,
        )
        self._payment(
            week_student, "MET-REC-002", 100000, week_start,
            self.type_reinscription,
        )

        month_student = self._student("MONTH")
        self._schedule(month_student, tuition=200000)
        self._payment(
            month_student, "MET-REC-003", 200000, month_date,
            self.type_scolarite,
        )

        year_student = self._student("YEAR")
        self._schedule(year_student, tuition=300000)
        self._payment(
            year_student, "MET-REC-004", 300000, year_date,
            self.type_scolarite,
        )

        late_student = self._student("LATE-TUITION")
        self._schedule(
            late_student,
            tuition=100000,
            tuition_paid=20000,
            tuition_due_date=self.today - timedelta(days=1),
        )

        bus_student = self._student("BUS-CURRENT")
        for amount, start in (
            (10000, self.today),
            (20000, week_start),
            (30000, month_date),
            (40000, year_date),
        ):
            self._subscription(
                AbonnementBus, bus_student, amount, start, future,
                periodicite=AbonnementBus.Periodicite.MENSUEL,
            )

        late_bus_student = self._student("BUS-LATE")
        self._subscription(
            AbonnementBus,
            late_bus_student,
            10000,
            date(2025, 1, 1),
            date(2025, 2, 1),
        )
        self._subscription(
            AbonnementBus,
            late_bus_student,
            25000,
            date(2025, 12, 1),
            self.today - timedelta(days=1),
        )

        cantine_student = self._student("CANTINE-CURRENT")
        for amount, start in (
            (5000, self.today),
            (15000, week_start),
            (25000, month_date),
            (35000, year_date),
        ):
            self._subscription(
                AbonnementCantine, cantine_student, amount, start, future,
                periodicite=AbonnementCantine.Periodicite.MENSUEL,
                type_repas=AbonnementCantine.TypeRepas.DEJEUNER,
            )

        late_cantine_student = self._student("CANTINE-LATE")
        self._subscription(
            AbonnementCantine,
            late_cantine_student,
            40000,
            date(2025, 12, 1),
            self.today - timedelta(days=1),
        )

    def _metrics_by_key(self):
        metrics = build_payment_dashboard_metrics(self.user, today=self.today)
        categories = {item["key"]: item for item in metrics["categories"]}
        admissions = {item["key"]: item for item in metrics["admissions"]}
        return metrics, categories, admissions

    def test_montants_par_categorie_et_periode_sont_ventiles_sans_double_compte(self):
        _metrics, categories, admissions = self._metrics_by_key()

        self.assertEqual(
            [categories["scolarite"]["values"][key]["amount"] for key in (
                "today", "week", "month", "year"
            )],
            [100000, 170000, 370000, 670000],
        )
        self.assertEqual(
            [categories["bus"]["values"][key]["amount"] for key in (
                "today", "week", "month", "year"
            )],
            [10000, 30000, 60000, 100000],
        )
        self.assertEqual(
            [categories["cantine"]["values"][key]["amount"] for key in (
                "today", "week", "month", "year"
            )],
            [5000, 20000, 45000, 80000],
        )
        self.assertEqual(admissions["inscription"]["values"]["today"], {
            "amount": 50000,
            "count": 1,
        })
        self.assertEqual(admissions["reinscription"]["values"]["today"], {
            "amount": 0,
            "count": 0,
        })
        self.assertEqual(admissions["reinscription"]["values"]["week"], {
            "amount": 30000,
            "count": 1,
        })

    def test_retards_utilisent_scolarite_et_dernier_abonnement_par_eleve(self):
        _metrics, categories, _admissions = self._metrics_by_key()

        self.assertEqual(categories["scolarite"]["late"], {
            "amount": 80000,
            "count": 1,
        })
        self.assertEqual(categories["bus"]["late"], {
            "amount": 25000,
            "count": 1,
        })
        self.assertEqual(categories["cantine"]["late"], {
            "amount": 40000,
            "count": 1,
        })

    @patch("paiements.views.timezone.localdate", return_value=today)
    def test_page_affiche_les_nouvelles_cartes(self, _mock_today):
        response = self.client.get(reverse("paiements:tableau_bord"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Encaissements par catégorie")
        self.assertContains(response, "Bus scolaire")
        self.assertContains(response, "Cantine")
        self.assertContains(response, "Inscriptions et réinscriptions")
        self.assertContains(response, 'data-category-card="scolarite"')
        self.assertContains(response, 'data-admission-card="reinscription"')

    @patch("paiements.views.timezone.localdate", return_value=today)
    def test_ajax_actualise_les_cartes_detaillees(self, _mock_today):
        response = self.client.get(reverse("paiements:ajax_statistiques_paiements"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("stats", payload)
        categories = {
            item["key"]: item
            for item in payload["financial_metrics"]["categories"]
        }
        self.assertEqual(
            categories["scolarite"]["values"]["today"]["amount"], 100000
        )
