from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import EcheancierPaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(
    MIDDLEWARE=MIDDLEWARE_SANS_LICENCE,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class AdmissionListsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-admissions",
            email="admissions@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        school = Ecole.objects.create(
            nom="École admissions",
            adresse="Conakry",
            telephone="620000911",
            directeur="Direction",
        )
        classe = Classe.objects.create(
            ecole=school,
            nom="2ème admissions",
            niveau="PRIMAIRE_2",
            annee_scolaire="2026-2027",
        )
        parent = Responsable.objects.create(
            nom="Parent",
            prenom="Admissions",
            relation="MERE",
            telephone="620000912",
            adresse="Conakry",
        )
        self.registered = self._student(classe, parent, "ADM-I-001", "Inscrit")
        self.re_registered = self._student(classe, parent, "ADM-R-001", "Réinscrit")
        self._schedule(self.registered, EcheancierPaiement.NATURE_INSCRIPTION)
        self._schedule(self.re_registered, EcheancierPaiement.NATURE_REINSCRIPTION)

    def _student(self, classe, parent, matricule, prenom):
        return Eleve.objects.create(
            matricule=matricule,
            prenom=prenom,
            nom="Admission",
            sexe="M",
            date_naissance=date(2017, 1, 1),
            classe=classe,
            date_inscription=date(2026, 8, 1),
            responsable_principal=parent,
        )

    def _schedule(self, student, nature):
        return EcheancierPaiement.objects.create(
            eleve=student,
            annee_scolaire="2026-2027",
            nature_frais=nature,
            frais_inscription_du=Decimal("50000"),
            tranche_1_due=Decimal("100000"),
            tranche_2_due=Decimal("0"),
            tranche_3_due=Decimal("0"),
            date_echeance_inscription=date(2026, 8, 1),
            date_echeance_tranche_1=date(2026, 10, 1),
            date_echeance_tranche_2=date(2027, 1, 1),
            date_echeance_tranche_3=date(2027, 3, 1),
        )

    def test_listes_separent_inscrits_et_reinscrits(self):
        registered = self.client.get(
            reverse("paiements:liste_admissions", args=["INSCRIPTION"])
        )
        re_registered = self.client.get(
            reverse("paiements:liste_admissions", args=["REINSCRIPTION"])
        )
        self.assertContains(registered, "ADM-I-001")
        self.assertNotContains(registered, "ADM-R-001")
        self.assertContains(re_registered, "ADM-R-001")
        self.assertNotContains(re_registered, "ADM-I-001")

    def test_exports_pdf_et_excel(self):
        excel = self.client.get(
            reverse("paiements:export_admissions_excel", args=["INSCRIPTION"])
        )
        pdf = self.client.get(
            reverse("paiements:export_admissions_pdf", args=["REINSCRIPTION"])
        )
        self.assertEqual(excel.status_code, 200)
        self.assertTrue(excel.content.startswith(b"PK"))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
