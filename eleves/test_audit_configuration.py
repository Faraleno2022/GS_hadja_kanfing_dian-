from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from .models import Ecole, GrilleTarifaire
from .services_configuration import dupliquer_grille
from .views_configuration import GrilleConfigurationForm


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class ConfigurationGrillesAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('audit-grilles', 'audit@example.com', 'test')
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(nom='École grilles')
        self.source = GrilleTarifaire.objects.create(ecole=self.ecole, niveau='PRIMAIRE_1', annee_scolaire='2027-2028', frais_inscription=100000, tranche_1=300000, date_echeance_tranche_2_defaut=date(2028, 2, 29))
        self.url = reverse('eleves:configurer_ecole', args=[self.ecole.pk])

    def test_bouton_dupliquer_conserve_montants_et_decale_dates(self):
        response = self.client.post(self.url, {'action': 'duplicate_grille', 'source_grille_id': self.source.pk, 'target_annee': '2028-2029'})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        copie = GrilleTarifaire.objects.get(ecole=self.ecole, niveau=self.source.niveau, annee_scolaire='2028-2029')
        self.assertEqual(copie.frais_inscription, self.source.frais_inscription)
        self.assertEqual(copie.tranche_1, self.source.tranche_1)
        self.assertEqual(copie.date_echeance_tranche_2_defaut, date(2029, 2, 28))

    def test_ne_remplace_pas_une_grille_existante(self):
        with self.assertRaises(ValidationError):
            dupliquer_grille(self.ecole, self.source.pk, self.source.annee_scolaire)
        self.source.refresh_from_db()
        self.assertEqual(self.source.frais_inscription, 100000)

    def test_ne_duplique_pas_une_grille_dune_autre_ecole(self):
        autre = Ecole.objects.create(nom='Autre école grilles')
        with self.assertRaises(GrilleTarifaire.DoesNotExist):
            dupliquer_grille(autre, self.source.pk, '2028-2029')
        self.assertEqual(GrilleTarifaire.objects.count(), 1)

    def test_montants_invalides_renvoient_des_erreurs_de_validation(self):
        for valeur in ('abc', '-1', 'NaN', 'Infinity'):
            with self.subTest(valeur=valeur):
                self.source.frais_inscription = valeur
                with self.assertRaises(ValidationError):
                    self.source.full_clean()

    def test_formulaire_montant_invalide_ne_leve_pas_derreur_500(self):
        form = GrilleConfigurationForm({'niveau': 'PRIMAIRE_1', 'annee_scolaire': '2026-2027', 'frais_inscription': 'abc'}, instance=self.source)
        self.assertFalse(form.is_valid())
        self.assertIn('frais_inscription', form.errors)

    def test_bouton_appliquer_dates_fonctionne_sans_echeanciers(self):
        response = self.client.post(self.url, {'action': 'apply_grille_dates', 'grille_id': self.source.pk}, follow=True)
        self.assertContains(response, 'Dates complétées pour 0 échéancier')
