from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Classe, Ecole, Eleve


class NouvelElevePaiementWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin_workflow",
            email="workflow@test.local",
            password="secret",
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom="École parcours",
            adresse="Conakry",
            telephone="+224622000001",
            email="workflow@ecole.local",
            directeur="Direction",
            etat="VALIDE",
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom="1ère année A",
            niveau="PRIMAIRE_1",
            annee_scolaire="2026-2027",
            capacite_max=40,
        )

    def test_ajout_eleve_redirige_vers_son_paiement(self):
        middleware_sans_licence = [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]
        with self.settings(MIDDLEWARE=middleware_sans_licence):
            response = self.client.post(
                reverse("eleves:ajouter_eleve"),
                {
                    "prenom": "MARIAMA",
                    "nom": "DIALLO",
                    "sexe": "F",
                    "classe": self.classe.pk,
                    "statut": "ACTIF",
                },
            )

        self.assertEqual(response.status_code, 302)
        eleve = Eleve.objects.get(prenom="MARIAMA", nom="DIALLO")
        self.assertEqual(
            response.url,
            reverse("paiements:ajouter_paiement_eleve", kwargs={"eleve_id": eleve.pk}),
        )
        self.assertEqual(
            self.client.session.get("nouvel_eleve_paiement_id"),
            eleve.pk,
        )
