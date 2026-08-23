from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from paiements.tests.support import TEST_MIDDLEWARE

from eleves.models import Ecole, Classe, Responsable, Eleve
from paiements.models import (
    ModePaiement,
    TypePaiement,
    Paiement,
    EcheancierPaiement,
    RemiseReduction,
    PaiementRemise,
)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class ValiderEcheancierRedirectTests(TestCase):
    def setUp(self):
        # Auth user (superuser bypasses granular permission checks)
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass1234"
        )
        # force_login : django-axes exige un objet request dans authenticate(),
        # que le client de test ne fournit pas via login().
        self.client.force_login(self.user)

        # Minimal school data
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
            adresse="Addr"
        )
        self.eleve = Eleve.objects.create(
            matricule="TEMP-001",
            prenom="Alice",
            nom="Test",
            sexe="F",
            date_naissance=timezone.now().date().replace(year=timezone.now().year - 10),
            lieu_naissance="Ville",
            classe=self.classe,
            date_inscription=timezone.now().date(),
            statut="ACTIF",
            responsable_principal=self.responsable,
        )
        self.mode = ModePaiement.objects.create(nom="Espèces")
        self.type = TypePaiement.objects.create(nom="Scolarité")
        today = timezone.localdate()
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve,
            annee_scolaire=self.classe.annee_scolaire,
            frais_inscription_du=0,
            tranche_1_due=500000,
            tranche_2_due=500000,
            tranche_3_due=500000,
            date_echeance_inscription=today,
            date_echeance_tranche_1=today + timedelta(days=30),
            date_echeance_tranche_2=today + timedelta(days=60),
            date_echeance_tranche_3=today + timedelta(days=90),
        )

    def _create_pending_payment(self):
        return Paiement.objects.create(
            eleve=self.eleve,
            type_paiement=self.type,
            mode_paiement=self.mode,
            montant=100000,
            date_paiement=timezone.now().date(),
            statut="EN_ATTENTE",
            numero_recu="",  # let model auto-generate
        )

    def test_redirects_to_detail_when_no_remise(self):
        paiement = self._create_pending_payment()
        url = reverse("paiements:valider_echeancier", kwargs={"eleve_id": self.eleve.id})
        resp = self.client.post(url, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            reverse("paiements:detail_paiement", kwargs={"paiement_id": paiement.id}),
            resp.url,
        )

    def test_redirects_back_to_echeancier_when_remise_exists(self):
        paiement = self._create_pending_payment()
        # Apply a remise to the payment
        today = timezone.now().date()
        remise = RemiseReduction.objects.create(
            nom="Remise fratrie",
            type_remise="POURCENTAGE",
            valeur=10,
            motif="FRATRIE",
            date_debut=today.replace(day=1),
            date_fin=today.replace(day=28 if today.month == 2 else 30),
            actif=True,
        )
        PaiementRemise.objects.create(paiement=paiement, remise=remise, montant_remise=5000)

        url = reverse("paiements:valider_echeancier", kwargs={"eleve_id": self.eleve.id})
        resp = self.client.post(url, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(
            reverse("paiements:echeancier_eleve", kwargs={"eleve_id": self.eleve.id}),
            resp.url,
        )

    def test_detail_liste_tous_les_paiements_du_meme_eleve_uniquement(self):
        paiement_consulte = self._create_pending_payment()
        autre_paiement = self._create_pending_payment()
        autre_eleve = Eleve.objects.create(
            matricule="TEMP-002",
            prenom="Bob",
            nom="Test",
            sexe="M",
            date_naissance=self.eleve.date_naissance,
            lieu_naissance="Ville",
            classe=self.classe,
            date_inscription=timezone.localdate(),
            statut="ACTIF",
            responsable_principal=self.responsable,
        )
        paiement_autre_eleve = Paiement.objects.create(
            eleve=autre_eleve,
            type_paiement=self.type,
            mode_paiement=self.mode,
            montant=75000,
            date_paiement=timezone.localdate(),
            statut="EN_ATTENTE",
            numero_recu="",
        )
        middleware_sans_licence = [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]

        with self.settings(MIDDLEWARE=middleware_sans_licence):
            response = self.client.get(
                reverse(
                    "paiements:detail_paiement",
                    kwargs={"paiement_id": paiement_consulte.pk},
                )
            )

        self.assertEqual(response.status_code, 200)
        paiements_affiches = list(response.context["paiements_eleve"])
        self.assertCountEqual(
            [paiement.pk for paiement in paiements_affiches],
            [paiement_consulte.pk, autre_paiement.pk],
        )
        self.assertContains(response, paiement_consulte.numero_recu)
        self.assertContains(response, autre_paiement.numero_recu)
        self.assertNotContains(response, paiement_autre_eleve.numero_recu)

    @patch("paiements.views.send_payment_receipt")
    def test_validation_du_paiement_du_nouvel_eleve_retourne_au_formulaire_eleve(self, _send_receipt):
        paiement = self._create_pending_payment()
        session = self.client.session
        session["nouvel_eleve_paiement_id"] = self.eleve.pk
        session.save()
        middleware_sans_licence = [
            middleware
            for middleware in settings.MIDDLEWARE
            if middleware != "ecole_moderne.licence_middleware.LicenceMiddleware"
        ]

        with self.settings(MIDDLEWARE=middleware_sans_licence):
            response = self.client.post(
                reverse("paiements:valider_paiement", kwargs={"paiement_id": paiement.pk}),
                follow=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("eleves:ajouter_eleve"))
        self.assertNotIn("nouvel_eleve_paiement_id", self.client.session)
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, "VALIDE")
