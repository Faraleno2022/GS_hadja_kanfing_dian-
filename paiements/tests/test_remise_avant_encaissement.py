"""Un tarif saisi avant remise devient un net à encaisser une seule fois."""
from decimal import Decimal
from io import BytesIO

from django.test import TestCase, override_settings
from django.urls import reverse

from paiements import tests_modification_paiement as fixtures
from paiements.models import Paiement, RemiseReduction
from paiements.recalcul_remises import montant_brut_pour_remise, montant_affiche_sur_recu
from paiements.services import synchroniser_echeancier_apres_changement_paiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import _valider_paiement_impl


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RemiseAvantEncaissementTests(TestCase):
    def setUp(self):
        fixtures.ApplicationRemisePaiementTest.setUp(self)
        # Répartition de test : les frais réels du paiement 98 ne sont pas connus.
        self.echeancier.frais_inscription_du = 210000
        self.echeancier.tranche_1_due = 600000
        self.echeancier.tranche_2_due = 600000
        self.echeancier.tranche_3_due = 600000
        self.echeancier.save()
        self.paiement.montant = 2010000
        self.paiement.save()
        self.url = reverse('paiements:appliquer_remise', args=[self.paiement.pk])

    def appliquer(self, pct='5', **extra):
        data = {
            'montant_original': '2010000', 'pourcentage_scolarite': pct,
            'tranches': ['1', '2', '3'], 'base_calcul': 'paiement_echeance',
            'motif': 'AUTRE', 'deduire_du_montant': 'on',
        }
        data.update(extra)
        response = self.client.post(self.url, data)
        self.paiement.refresh_from_db()
        return response

    def assert_net(self, net=1920000, remise=90000):
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, net)
        self.assertEqual(sum(l.montant_remise for l in self.paiement.remises.all()), remise)

    def test_tarif_complet_sans_option_reste_refuse_comme_encaissement(self):
        response = self.appliquer(deduire_du_montant='')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.paiement.montant, 2010000)
        self.assertFalse(self.paiement.remises.exists())
        self.assertIn('0 GNF', str(response.context['form'].errors))

    def test_cinq_pourcent_des_tranches_exclut_inscription(self):
        for base in ('paiement_echeance', 'tranches_dues'):
            with self.subTest(base=base):
                response = self.appliquer(base_calcul=base)
                self.assertEqual(response.status_code, 302)
                self.assert_net()
                self.assertEqual(montant_brut_pour_remise(self.paiement), 2010000)
                self.assertEqual(self.paiement.remises.get().regle_calcul['tranches'], [1, 2, 3])
                self.echeancier.refresh_from_db()
                self.assertEqual(self.echeancier.frais_inscription_du, 210000)

    def test_tranche_selectionnee_seule_est_remisee(self):
        self.appliquer(tranches=['1'])
        self.assert_net(1980000, 30000)

    def test_reappliquer_ne_deduit_pas_deux_fois(self):
        for _ in range(3):
            self.appliquer()
            self.assert_net()
        self.assertEqual(self.paiement.remises.count(), 1)

    def test_changer_taux_repart_du_tarif_initial(self):
        self.appliquer()
        self.appliquer('10')
        self.assert_net(1830000, 180000)
        self.appliquer('5')
        self.assert_net()

    def test_montant_original_poste_ne_peut_pas_modifier_le_tarif(self):
        self.appliquer(montant_original='9000000')
        self.assert_net()

    def test_formulaire_reouvert_presente_tarif_initial_et_option(self):
        self.appliquer()
        response = self.client.get(self.url)
        self.assertContains(response, 'data-montant-brut="2010000"')
        self.assertEqual(response.context['montant_avant_remise'], 2010000)
        self.assertTrue(response.context['form']['deduire_du_montant'].value())
        self.assertEqual(response.context['tranches_info'][2]['sur_ce_paiement_brut'], 600000)

    def test_validation_cartes_et_carnet_utilisent_net(self):
        from paiements.carnet_paiement import construire_donnees_carnet
        self.appliquer()
        _valider_paiement_impl(self.paiement, self.user)
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.total_paye, 1920000)
        self.assertEqual(self.echeancier.total_remises_valides, 90000)
        self.assertEqual(self.echeancier.solde_restant, 0)
        carnet = construire_donnees_carnet(self.paiement)
        self.assertEqual(carnet['total_encaisse'], 1920000)
        self.assertEqual(carnet['reste'], 0)

    def test_recus_prive_et_public_ne_rededuisent_pas_remise(self):
        from pypdf import PdfReader
        from paiements.recu_public import generer_token_recu
        self.appliquer()
        _valider_paiement_impl(self.paiement, self.user)
        self.assertEqual(montant_affiche_sur_recu(self.paiement), 1920000)
        for name, params in (
            ('paiements:generer_recu_pdf', {}),
            ('paiements:recu_public_pdf', {'token': generer_token_recu(self.paiement.pk)}),
        ):
            with self.subTest(recu=name):
                response = self.client.get(reverse(name, args=[self.paiement.pk]), params)
                self.assertEqual(response.status_code, 200)
                texte = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(response.content)).pages)
                self.assertIn('Montant payé : 1 920 000 GNF', texte)
                self.assertNotIn('Montant payé : 1 830 000 GNF', texte)
                self.assertIn('Remise de : 90 000 GNF', texte)

    def test_cumul_ne_peut_pas_remiser_inscription(self):
        self.appliquer()
        lignes_avant = list(self.paiement.remises.values())
        remises = [RemiseReduction.objects.create(
            nom=f'Remise fixe {n}', type_remise='MONTANT_FIXE', valeur=950000,
            motif='AUTRE', date_debut=self.paiement.date_paiement,
            date_fin=self.paiement.date_paiement,
        ) for n in range(2)]
        response = self.appliquer('', remises=[r.pk for r in remises])
        self.assertEqual(response.status_code, 302)
        self.assert_net()
        self.assertEqual(list(self.paiement.remises.values()), lignes_avant)

    def test_depassement_avec_autre_versement_annule_aussi_changement_montant(self):
        Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_p, mode_paiement=self.mode_p,
            montant=10000, date_paiement=self.paiement.date_paiement,
            annee_scolaire=self.paiement.annee_scolaire, statut='EN_ATTENTE',
        )
        self.appliquer()
        self.assertEqual(self.paiement.montant, 2010000)
        self.assertFalse(self.paiement.remises.exists())

    def test_annulation_remise_validee_conserve_encaissement_et_reouvre_solde(self):
        self.appliquer()
        _valider_paiement_impl(self.paiement, self.user)
        response = self.client.post(reverse('paiements:annuler_remise_paiement', args=[self.paiement.pk]))
        self.assertEqual(response.status_code, 302)
        self.assert_net(1920000, 0)
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.solde_restant, 90000)

    def test_suppression_restauration_preserve_net_et_base_de_remise(self):
        from administration.audit import mettre_en_corbeille, restaurer_element
        self.appliquer()
        _valider_paiement_impl(self.paiement, self.user)
        entree = mettre_en_corbeille(self.paiement)
        restored, _ = restaurer_element(entree)
        self.paiement = restored
        self.assert_net()
        self.assertEqual(montant_brut_pour_remise(restored), 2010000)

    def test_recalcul_tarif_ne_rededuit_pas_remise_du_cash(self):
        self.appliquer()
        _valider_paiement_impl(self.paiement, self.user)
        self.echeancier.frais_inscription_du = 310000
        self.echeancier.save()
        for _ in range(2):
            synchroniser_echeancier_apres_changement_paiement(self.eleve.pk, self.paiement.annee_scolaire)
            # La base initiale donne 1 700 000 de scolarité ; le cash reste fixe.
            self.assert_net(1920000, 85000)

    def test_net_nul_affiche_refus_sans_erreur_500(self):
        self.echeancier.frais_inscription_du = 0
        self.echeancier.save()
        self.paiement.montant = 1800000
        self.paiement.save()
        response = self.appliquer('100')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.paiement.montant, 1800000)
        self.assertFalse(self.paiement.remises.exists())

    def test_arrondi_demi_franc_est_coherent_apres_recalcul(self):
        self.echeancier.tranche_3_due = 600010
        self.echeancier.save()
        self.paiement.montant = 2010010
        self.paiement.save()
        self.appliquer()
        self.assert_net(1920009, 90001)

    def test_retour_mode_encaisse_ne_change_pas_cash_ni_rededuit_sur_recu(self):
        self.appliquer()
        self.appliquer(deduire_du_montant='', base_calcul='tranches_dues')
        self.assert_net()
        self.assertEqual(montant_affiche_sur_recu(self.paiement), 1920000)

    def test_paiement_valide_ne_peut_pas_etre_reduit(self):
        self.appliquer()
        _valider_paiement_impl(self.paiement, self.user)
        self.appliquer('10')
        self.assert_net()
        self.assertEqual(self.paiement.statut, 'VALIDE')

    def test_synchronisation_conserve_net_et_tarif_initial(self):
        from synchronisation.engine import serialize_instance
        self.appliquer()
        self.assertEqual(serialize_instance(self.paiement)['montant'], '1920000')
        payload = serialize_instance(self.paiement.remises.get())
        self.assertEqual(Decimal(payload['regle_calcul']['montant_avant_remise']), 2010000)
        self.assertTrue(payload['regle_calcul']['montant_net_enregistre'])
