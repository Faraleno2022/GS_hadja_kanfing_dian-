from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.models import ModePaiement

from .forms import AbonnementBusForm, AbonnementCantineForm
from .models import AbonnementBus, GrilleTarifaireBus


class SubscriptionExternalReferenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-reference-abonnement",
            email="reference@example.com",
            password="test-password",
        )
        self.school = Ecole.objects.create(
            nom="École références",
            adresse="Conakry",
            telephone="620000921",
            directeur="Direction",
        )
        self.classe = Classe.objects.create(
            ecole=self.school,
            nom="3ème références",
            niveau="PRIMAIRE_3",
            annee_scolaire="2026-2027",
        )
        parent = Responsable.objects.create(
            nom="Parent",
            prenom="Référence",
            relation="PERE",
            telephone="620000922",
            adresse="Conakry",
        )
        self.student = Eleve.objects.create(
            matricule="REF-001",
            prenom="Élève",
            nom="Référence",
            sexe="F",
            date_naissance=date(2017, 1, 1),
            classe=self.classe,
            date_inscription=date(2026, 8, 1),
            responsable_principal=parent,
        )
        self.mode = ModePaiement.objects.create(nom="Mobile money références")
        self.grille = GrilleTarifaireBus.objects.create(
            ecole=self.school,
            zone="Zone test",
            annee_scolaire="2026-2027",
            tranche_1=50000,
            tranche_2=50000,
            tranche_3=50000,
        )

    def test_formulaire_bus_conserve_reference_externe(self):
        form = AbonnementBusForm(
            data={
                "eleve": self.student.pk,
                "grille": self.grille.pk,
                "periodicite": AbonnementBus.Periodicite.TRANCHE_1,
                "montant": 50000,
                "date_debut": "2026-08-30",
                "mode_paiement": self.mode.pk,
                "reference_externe": "OM-RECU-12345",
                "observations": "",
            },
            ecole=self.school,
        )
        self.assertTrue(form.is_valid(), form.errors)
        subscription = form.save(commit=False)
        subscription.date_expiration = date(2027, 6, 30)
        subscription.save()
        self.assertEqual(subscription.reference_externe, "OM-RECU-12345")

    def test_formulaire_cantine_expose_reference_externe(self):
        form = AbonnementCantineForm()
        self.assertIn("reference_externe", form.fields)

