"""Le refus reste sur le formulaire et permet de corriger un tarif avant remise."""
import re
from io import BytesIO

from django.test import TestCase, override_settings
from django.urls import reverse

from paiements import tests_modification_paiement as fixtures
from paiements.models import Paiement, PaiementRemise, RemiseReduction
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import _valider_paiement_impl


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RefusRemiseFormulaireTests(TestCase):
    def setUp(self):
        fixtures.ApplicationRemisePaiementTest.setUp(self)
        # Montants du reçu REC20260072 : inscription 30 000 et 3 x 660 000.
        self.echeancier.frais_inscription_du = 30000
        for num in (1, 2, 3):
            setattr(self.echeancier, f'tranche_{num}_due', 660000)
        self.echeancier.save()
        self.paiement.montant = 2010000
        self.paiement.save()
        self.url = reverse('paiements:appliquer_remise', args=[self.paiement.pk])
        self.data = {
            'montant_original': '2010000', 'pourcentage_scolarite': '5',
            'tranches': ['1', '2', '3'], 'base_calcul': 'paiement_echeance',
            'motif': 'AUTRE',
        }

    def autre_paiement(self, montant=2010000):
        return Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=montant, date_paiement=self.paiement.date_paiement,
            annee_scolaire=self.paiement.annee_scolaire, statut='EN_ATTENTE',
        )

    def remise_catalogue(self, nom, montant):
        return RemiseReduction.objects.create(
            nom=nom, type_remise='MONTANT_FIXE', valeur=montant, motif='AUTRE',
            date_debut=self.paiement.date_paiement, date_fin=self.paiement.date_paiement,
        )

    def test_refus_conserve_choix_et_permet_correction_du_tarif(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'paiements/appliquer_remise.html')
        form = response.context['form']
        self.assertIn('deduire_du_montant', form.errors)
        self.assertEqual(form['pourcentage_scolarite'].value(), '5')
        self.assertEqual(form['tranches'].value(), ['1', '2', '3'])
        self.assertEqual(form['motif'].value(), 'AUTRE')
        self.assertEqual(form['base_calcul'].value(), 'paiement_echeance')
        self.assertFalse(form['deduire_du_montant'].value())
        self.assertContains(response, 'href="#id_deduire_du_montant"')
        self.assertContains(response, 'Remise refusée', count=1)
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, 2010000)
        self.assertFalse(self.paiement.remises.exists())

        self.data['deduire_du_montant'] = 'on'
        for base in ('paiement_echeance', 'tranches_dues'):
            self.data['base_calcul'] = base
            response = self.client.post(self.url, self.data)
            self.assertRedirects(response, reverse('paiements:detail_paiement', args=[self.paiement.pk]))
            self.paiement.refresh_from_db()
            self.assertEqual(self.paiement.montant, 1911000)
            self.assertEqual(self.paiement.remises.get().montant_remise, 99000)

        _valider_paiement_impl(self.paiement, self.user)
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.total_paye, 1911000)
        self.assertEqual(self.echeancier.total_remises_valides, 99000)
        self.assertEqual(self.echeancier.frais_inscription_du, 30000)
        self.assertEqual(self.echeancier.solde_restant, 0)

    def test_option_cochee_identifie_autre_paiement_et_preserve_montant(self):
        autre = self.autre_paiement()
        response = self.client.post(self.url, dict(self.data, deduire_du_montant='on'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form']['deduire_du_montant'].value())
        erreurs = ' '.join(response.context['form'].non_field_errors())
        self.assertIn("L'option tarif avant remise est déjà prise en compte", erreurs)
        self.assertIn('Autres paiements de cet élève (validés ou en attente) : 2 010 000 GNF', erreurs)
        self.assertNotIn('cochez', erreurs)
        self.assertContains(response, 'Remise refusée', count=1)
        self.assertEqual(response.context['paiement'].montant, 2010000)
        self.paiement.refresh_from_db()
        autre.refresh_from_db()
        self.assertEqual(self.paiement.montant, 2010000)
        self.assertEqual(autre.montant, 2010000)
        self.assertFalse(self.paiement.remises.exists())
        self.assertFalse(RemiseReduction.objects.filter(nom='Remise scolarité 5%').exists())

    def test_refus_reaffiche_montant_et_remise_restaures(self):
        self.client.post(self.url, dict(self.data, deduire_du_montant='on'))
        lignes_avant = list(self.paiement.remises.values())
        self.autre_paiement()
        response = self.client.post(self.url, dict(
            self.data, deduire_du_montant='on', pourcentage_scolarite='10',
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paiement'].montant, 1911000)
        self.assertEqual(list(self.paiement.remises.values()), lignes_avant)
        self.assertEqual(response.context['remises_existantes'][0].montant_remise, 99000)
        self.assertEqual(response.context['form']['pourcentage_scolarite'].value(), '10')
        self.assertTrue(response.context['form']['deduire_du_montant'].value())

    def test_catalogue_conserve_selection_postee_apres_refus(self):
        ancienne = self.remise_catalogue('Ancienne remise', 5000)
        nouvelle = self.remise_catalogue('Remise demandée', 150000)
        ligne = PaiementRemise.objects.create(
            paiement=self.paiement, remise=ancienne, montant_remise=5000,
        )
        for selections, pct in (([str(nouvelle.pk)], ''), ([], '5')):
            with self.subTest(selections=selections):
                response = self.client.post(self.url, dict(
                    self.data, remises=selections, pourcentage_scolarite=pct,
                ))
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                for remise, checked in ((ancienne, False), (nouvelle, bool(selections))):
                    tag = re.search(rf'<input\b[^>]*id="remise_{remise.pk}"[^>]*>', html).group()
                    self.assertEqual('checked' in tag, checked)
                ligne.refresh_from_db()
                self.assertEqual(ligne.montant_remise, 5000)
                self.assertEqual(self.paiement.remises.count(), 1)

    def test_recus_affichent_net_exact_sans_double_deduction(self):
        from pypdf import PdfReader
        from paiements.recu_public import generer_token_recu

        self.client.post(self.url, dict(self.data, deduire_du_montant='on'))
        self.paiement.refresh_from_db()
        _valider_paiement_impl(self.paiement, self.user)
        for name, params in (
            ('paiements:generer_recu_pdf', {}),
            ('paiements:recu_public_pdf', {'token': generer_token_recu(self.paiement.pk)}),
        ):
            with self.subTest(recu=name):
                response = self.client.get(reverse(name, args=[self.paiement.pk]), params)
                self.assertEqual(response.status_code, 200)
                texte = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(response.content)).pages)
                self.assertIn('Montant payé : 1 911 000 GNF', texte)
                self.assertIn('Remise de : 99 000 GNF', texte)
                self.assertNotIn('Montant payé : 1 812 000 GNF', texte)
