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

    def test_ajout_eleve_affiche_le_choix_paiement_ou_nouvel_eleve(self):
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
            f"{reverse('eleves:ajouter_eleve')}?eleve_ajoute={eleve.pk}&classe_id={self.classe.pk}",
        )
        self.assertNotIn("nouvel_eleve_paiement_id", self.client.session)

        with self.settings(MIDDLEWARE=middleware_sans_licence):
            choix = self.client.get(response.url)
        self.assertEqual(choix.status_code, 200)
        self.assertContains(choix, "Ajouter un paiement")
        self.assertContains(choix, "Continuer l'ajout des élèves")
        self.assertContains(choix, eleve.matricule)
        self.assertContains(
            choix,
            f"{reverse('paiements:ajouter_paiement_eleve', kwargs={'eleve_id': eleve.pk})}?origine=ajout_eleve",
        )

        with self.settings(MIDDLEWARE=middleware_sans_licence):
            paiement = self.client.get(
                reverse(
                    "paiements:ajouter_paiement_eleve",
                    kwargs={"eleve_id": eleve.pk},
                ),
                {"origine": "ajout_eleve"},
            )
        self.assertEqual(paiement.status_code, 200)
        self.assertEqual(
            self.client.session.get("nouvel_eleve_paiement_id"),
            eleve.pk,
        )

    def test_continuer_ajout_quitte_le_parcours_de_paiement(self):
        session = self.client.session
        session["nouvel_eleve_paiement_id"] = 123
        session.save()

        middleware_sans_licence = [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]
        with self.settings(MIDDLEWARE=middleware_sans_licence):
            response = self.client.get(
                reverse("eleves:ajouter_eleve"),
                {"classe_id": self.classe.pk, "continuer": "1"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("nouvel_eleve_paiement_id", self.client.session)
        self.assertEqual(response.context["form"].fields["classe"].initial, self.classe.pk)
