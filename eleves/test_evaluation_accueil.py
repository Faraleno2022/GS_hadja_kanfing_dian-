from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from paiements.tests.support import MIDDLEWARE_SANS_LICENCE

from .models import Classe, Ecole, Eleve


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class EvaluationAccueilTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-test-accueil",
            email="accueil@example.com",
            password="mot-de-passe-test",
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom="École test accueil",
            adresse="Conakry",
            telephone="+224620000601",
            directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="7ème Accueil",
            niveau="COLLEGE_7",
            annee_scolaire="2026-2027",
        )
        self.ancien = Eleve.objects.create(
            matricule="ACC-001",
            prenom="Ancien",
            nom="Élève",
            sexe="M",
            date_naissance=date(2013, 1, 1),
            classe=self.classe,
        )
        self.recent = Eleve.objects.create(
            matricule="ACC-002",
            prenom="Récent",
            nom="Élève",
            sexe="F",
            date_naissance=date(2014, 1, 1),
            classe=self.classe,
        )

    def test_liste_trie_les_derniers_ajoutes_en_premier(self):
        response = self.client.get(reverse("eleves:liste_eleves"))
        self.assertEqual(response.status_code, 200)
        rows = list(response.context["page_obj"].object_list)
        self.assertEqual(rows[:2], [self.recent, self.ancien])

    def test_pointage_et_exports_evaluation_accueil(self):
        response = self.client.post(
            reverse(
                "eleves:definir_evaluation_accueil",
                args=[self.recent.pk],
            ),
            {"est_evalue": "1"},
        )
        self.assertEqual(response.status_code, 302)
        self.recent.refresh_from_db()
        self.assertTrue(self.recent.evaluation_accueil_effectuee)

        excel_response = self.client.get(
            reverse(
                "eleves:export_evaluation_accueil_excel",
                args=["evalues"],
            )
        )
        self.assertEqual(excel_response.status_code, 200)
        self.assertIn("spreadsheetml", excel_response["Content-Type"])

        pdf_response = self.client.get(
            reverse(
                "eleves:export_evaluation_accueil_pdf",
                args=["non-evalues"],
            )
        )
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))
