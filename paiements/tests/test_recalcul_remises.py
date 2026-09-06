from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from administration.audit import mettre_en_corbeille, restaurer_element
from paiements.admin import PaiementAdmin
from paiements.models import Paiement, PaiementRemise, RemiseReduction, TypePaiement
from paiements.recalcul_remises import memoriser_regle_remise
from paiements.services import synchroniser_echeancier_apres_changement_paiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.tests import test_payment_activity


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RecalculRemisesTests(TestCase):
    setUp = test_payment_activity.PaymentActivityTests.setUp

    def scenario(self, base='paiement_echeance'):
        self.echeancier.frais_inscription_du = Decimal('100000')
        self.echeancier.save()
        self.premier = Paiement.objects.create(eleve=self.eleve, type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement, montant=100000, annee_scolaire=self.school_year,
            date_paiement=self.today - timedelta(days=1), statut='VALIDE', numero_recu='REC-PREMIER')
        self.suivant = Paiement.objects.create(eleve=self.eleve, type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement, montant=100000, annee_scolaire=self.school_year,
            date_paiement=self.today, statut='VALIDE', numero_recu='REC-SUIVANT')
        remise = RemiseReduction.objects.create(nom='Remise 50%', type_remise='POURCENTAGE',
            valeur=50, motif='AUTRE', date_debut=self.today, date_fin=self.today)
        self.ligne = PaiementRemise.objects.create(paiement=self.suivant, remise=remise,
            montant_remise=50000, regle_calcul=memoriser_regle_remise(remise, base, ['1']))
        self.recalculer()

    def recalculer(self):
        synchroniser_echeancier_apres_changement_paiement(self.eleve.pk, self.school_year)
        self.echeancier.refresh_from_db()
        self.ligne.refresh_from_db()

    def test_suppression_et_restauration_recalculent_remise_suivante(self):
        self.scenario()
        self.assertEqual(self.ligne.montant_remise, 50000)
        entree = mettre_en_corbeille(self.premier, motif='Correction')
        self.ligne.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 0)
        self.assertEqual(self.echeancier.solde_restant, 400000)
        restaurer_element(entree)
        self.recalculer()
        self.assertEqual(self.ligne.montant_remise, 50000)
        self.assertEqual(self.echeancier.solde_restant, 250000)

    def test_modification_du_premier_paiement_recalcule_suivant(self):
        self.scenario()
        response = self.client.post(reverse('paiements:modifier_paiement', args=[self.premier.pk]), {
            'type_paiement': self.type_paiement.pk, 'mode_paiement': self.mode_paiement.pk,
            'montant': '50000', 'date_paiement': self.premier.date_paiement.isoformat(),
            'motif_modification': 'Correction encaissement',
        })
        self.assertEqual(response.status_code, 302)
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 0)
        self.premier.refresh_from_db()
        self.assertEqual(self.premier.statut, 'EN_ATTENTE')

    def test_admin_modification_recalcule_suivant(self):
        self.scenario()
        self.premier.montant = Decimal('50000')
        request = RequestFactory().post('/admin/paiements/paiement/')
        request.user = self.user
        PaiementAdmin(Paiement, admin.site).save_model(request, self.premier, SimpleNamespace(), True)
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 0)
        self.assertEqual(self.premier.statut, 'EN_ATTENTE')

    def test_remise_sur_tranches_dues_ne_depend_pas_des_versements(self):
        self.scenario(base='tranches_dues')
        self.assertEqual(self.ligne.montant_remise, 200000)
        mettre_en_corbeille(self.premier)
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 200000)

    def test_remise_ancienne_sans_regle_est_preservee(self):
        self.scenario()
        self.ligne.regle_calcul = {}
        self.ligne.save()
        mettre_en_corbeille(self.premier)
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 50000)

    def test_changement_catalogue_ne_change_pas_taux_accorde(self):
        self.scenario()
        self.ligne.remise.valeur = 80
        self.ligne.remise.save()
        self.recalculer()
        self.assertEqual(self.ligne.montant_remise, 50000)

    def test_echec_recalcul_annule_suppression(self):
        self.scenario()
        identifiant = self.premier.pk
        with patch('paiements.recalcul_remises.recalculer_remises_echeancier', side_effect=ValueError('Erreur test')):
            with self.assertRaises(ValueError):
                mettre_en_corbeille(self.premier)
        self.assertTrue(Paiement.objects.filter(pk=identifiant).exists())
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 50000)

    def test_application_conserve_base_tranches_et_taux(self):
        self.scenario()
        self.suivant.statut = 'EN_ATTENTE'
        self.suivant.save()
        self.recalculer()
        response = self.client.post(reverse('paiements:appliquer_remise', args=[self.suivant.pk]), {
            'montant_original': '100000', 'pourcentage_scolarite': '50',
            'tranches': ['1'], 'base_calcul': 'paiement_echeance', 'motif': 'AUTRE',
        })
        self.assertEqual(response.status_code, 302)
        ligne = self.suivant.remises.get()
        self.assertEqual(ligne.regle_calcul['tranches'], [1])
        self.assertEqual(ligne.regle_calcul['base'], 'paiement_echeance')
        self.assertEqual(Decimal(ligne.regle_calcul['valeur']), 50)
        self.suivant.montant = Decimal('200000')
        self.suivant.save()
        synchroniser_echeancier_apres_changement_paiement(self.eleve.pk, self.school_year)
        ligne.refresh_from_db()
        self.assertEqual(ligne.montant_remise, 100000)

    def test_date_corrigee_recalcule_ordre_des_remises(self):
        self.scenario()
        response = self.client.post(reverse('paiements:modifier_paiement', args=[self.premier.pk]), {
            'type_paiement': self.type_paiement.pk, 'mode_paiement': self.mode_paiement.pk,
            'montant': '100000', 'date_paiement': (self.today + timedelta(days=1)).isoformat(),
            'motif_modification': 'Correction date',
        })
        self.assertEqual(response.status_code, 302)
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 0)

    def test_restauration_conserve_regle_de_remise(self):
        self.scenario()
        regle = self.ligne.regle_calcul.copy()
        entree = mettre_en_corbeille(self.suivant)
        restaurer_element(entree)
        self.ligne = PaiementRemise.objects.get(paiement__numero_recu='REC-SUIVANT')
        self.assertEqual(self.ligne.regle_calcul, regle)
        mettre_en_corbeille(self.premier)
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 0)

    def test_admin_suppression_recalcule_remise_suivante(self):
        self.scenario()
        request = RequestFactory().post('/admin/paiements/paiement/')
        request.user = self.user
        model_admin = PaiementAdmin(Paiement, admin.site)
        with patch.object(model_admin, 'message_user'):
            model_admin.delete_queryset(request, Paiement.objects.filter(pk=self.premier.pk))
        self.ligne.refresh_from_db()
        self.assertEqual(self.ligne.montant_remise, 0)

    def test_inscription_reinscription_recalcule_remise_sur_recu(self):
        from eleves.models import GrilleTarifaire
        from paiements.carnet_paiement import construire_donnees_carnet
        self.scenario()
        self.suivant.delete()
        GrilleTarifaire.objects.create(ecole=self.school, niveau=self.classe.niveau,
            annee_scolaire=self.school_year, frais_inscription=100000, frais_reinscription=50000,
            tranche_1=400000, tranche_2=0, tranche_3=0)
        self.premier.montant = Decimal('200000')
        self.premier.type_paiement = TypePaiement.objects.create(nom='Inscription + Tranche 1')
        self.premier.save()
        remise = RemiseReduction.objects.get(nom='Remise 50%')
        self.ligne = PaiementRemise.objects.create(paiement=self.premier, remise=remise,
            montant_remise=50000, regle_calcul=memoriser_regle_remise(remise, 'paiement_echeance', ['1']))
        reinscription = TypePaiement.objects.create(nom='Reinscription + Tranche 1')
        response = self.client.post(reverse('paiements:modifier_paiement', args=[self.premier.pk]), {
            'type_paiement': reinscription.pk, 'mode_paiement': self.mode_paiement.pk,
            'montant': '200000', 'date_paiement': self.premier.date_paiement.isoformat(),
            'motif_modification': 'Correction admission',
        })
        self.assertEqual(response.status_code, 302)
        self.ligne.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.frais_inscription_du, 50000)
        self.assertEqual(self.ligne.montant_remise, 75000)
        self.assertEqual(self.echeancier.solde_restant, 175000)
        data = construire_donnees_carnet(self.premier)
        self.assertEqual(data['total_remises'], 75000)
        self.assertEqual(data['reste'], 175000)
