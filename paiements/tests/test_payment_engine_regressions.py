from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from administration.corbeille import restaurer
from administration.models import ElementCorbeille
from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.admin import EcheancierPaiementAdmin, PaiementAdmin
from paiements.allocation import INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3
from paiements.models import (
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    RemiseReduction,
    TypePaiement,
)
from paiements.payment_engine import (
    preparer_ventilation_remises,
    recalculer_echeancier,
    situation_echeancier,
)
from paiements.tests.support import TEST_MIDDLEWARE


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PaymentEngineRegressionTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='Ecole moteur', adresse='Conakry', telephone='+224620000001',
            directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='8e', niveau='COLLEGE_8',
            annee_scolaire='2025-2026',
        )
        responsable = Responsable.objects.create(
            prenom='Parent', nom='Moteur', relation='PERE',
            telephone='+224620000002', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='MOT-001', prenom='Aïssatou', nom='Test', sexe='F',
            date_naissance=date(2012, 1, 1), lieu_naissance='Conakry',
            classe=self.classe, date_inscription=date(2025, 9, 1),
            responsable_principal=responsable,
        )
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2025-2026',
            frais_inscription_du=Decimal('30000'),
            tranche_1_due=Decimal('400000'),
            tranche_2_due=Decimal('300000'),
            tranche_3_due=Decimal('200000'),
            date_echeance_inscription=date(2025, 9, 15),
            date_echeance_tranche_1=date(2025, 12, 15),
            date_echeance_tranche_2=date(2026, 3, 15),
            date_echeance_tranche_3=date(2026, 6, 15),
        )
        self.type_t1 = TypePaiement.objects.create(nom='Tranche 1')
        self.type_t3 = TypePaiement.objects.create(nom='Tranche 3')
        self.mode = ModePaiement.objects.create(nom='Espèces')

    def _remise(self, nom, valeur):
        return RemiseReduction.objects.create(
            nom=nom, type_remise='POURCENTAGE', valeur=valeur,
            motif='SOCIALE', date_debut=date(2025, 9, 1),
            date_fin=date(2026, 8, 31), actif=True,
        )

    def test_une_remise_t3_ne_couvre_jamais_inscription(self):
        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_t3,
            mode_paiement=self.mode, montant=Decimal('0'),
            date_paiement=date(2025, 10, 1), statut='VALIDE',
        )
        remise = RemiseReduction.objects.create(
            nom='T3 offerte', type_remise='MONTANT_FIXE', valeur=200000,
            motif='SOCIALE', date_debut=date(2025, 9, 1),
            date_fin=date(2026, 8, 31), actif=True,
        )
        PaiementRemise.objects.create(
            paiement=paiement, remise=remise, montant_remise=200000,
            montant_base=200000, applique_tranche_3=True,
            montant_tranche_3=200000, motif='GESTE_COMMERCIAL',
        )

        situation = situation_echeancier(
            self.echeancier, date_reference=date(2025, 10, 1)
        )

        self.assertEqual(situation['retard_total'], Decimal('30000'))
        self.assertEqual(situation['solde_restant'], Decimal('730000'))

    def test_un_paiement_dune_ancienne_annee_nest_pas_rejoue(self):
        Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_t1,
            mode_paiement=self.mode, montant=Decimal('400000'),
            date_paiement=date(2025, 7, 1), annee_scolaire='2024-2025',
            statut='VALIDE',
        )

        recalculer_echeancier(self.echeancier)
        self.echeancier.refresh_from_db()

        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('0'))
        self.assertEqual(self.echeancier.statut, 'EN_RETARD')

    def test_date_echeance_du_jour_nest_pas_encore_en_retard(self):
        self.echeancier.date_echeance_inscription = date(2025, 10, 1)
        self.echeancier.save(update_fields=['date_echeance_inscription'])

        situation = situation_echeancier(
            self.echeancier, date_reference=date(2025, 10, 1)
        )

        self.assertEqual(situation['retards']['inscription'], Decimal('0'))

    def test_cumul_de_remises_est_plafonne_a_cent_pour_cent(self):
        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_t1,
            mode_paiement=self.mode, montant=Decimal('100000'),
            date_paiement=date(2025, 10, 1), statut='EN_ATTENTE',
        )
        details = preparer_ventilation_remises(
            paiement,
            [self._remise('60 A', 60), self._remise('60 B', 60)],
            [1],
            'TRANCHE',
        )

        self.assertEqual(
            sum((item['montant_remise'] for item in details), Decimal('0')),
            Decimal('400000'),
        )
        self.assertEqual(details[0]['montant_remise'], Decimal('240000'))
        self.assertEqual(details[1]['montant_remise'], Decimal('160000'))

    def test_remise_t1_ne_s_affiche_pas_comme_paiement_t2(self):
        """Le cash brut reste sur T1 dans les reçus/exports par tranche."""
        type_combine = TypePaiement.objects.create(
            nom='Inscription + Tranche 1'
        )
        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=type_combine,
            mode_paiement=self.mode, montant=Decimal('430000'),
            date_paiement=date(2025, 10, 1), statut='VALIDE',
            annee_scolaire='2025-2026',
        )
        remise = self._remise('Remise T1 5 %', 5)
        PaiementRemise.objects.create(
            paiement=paiement, remise=remise,
            montant_remise=Decimal('20000'), montant_base=Decimal('400000'),
            applique_tranche_1=True, montant_tranche_1=Decimal('20000'),
            motif='GESTE_COMMERCIAL', deduite_du_paiement=False,
        )

        situation = situation_echeancier(
            self.echeancier, date_reference=date(2025, 10, 1)
        )

        # La ventilation comptable nette explique toujours le solde.
        self.assertEqual(
            situation['allocations'][paiement.id][TRANCHE_2],
            Decimal('20000'),
        )
        # Sur les documents, la remise reste dans sa colonne/rubrique et le
        # paiement brut ne semble jamais avoir commencé la tranche suivante.
        affichee = situation['allocations_affichees'][paiement.id]
        self.assertEqual(affichee[INSCRIPTION], Decimal('30000'))
        self.assertEqual(affichee[TRANCHE_1], Decimal('400000'))
        self.assertEqual(affichee[TRANCHE_2], Decimal('0'))
        self.assertEqual(affichee[TRANCHE_3], Decimal('0'))

        # Les exports PDF et Excel partagent cette même source de données.
        from paiements.views_tranches import _donnees_tranches_eleve

        ligne_export = _donnees_tranches_eleve(self.eleve, '2025-2026')
        self.assertEqual(ligne_export['inscription'], Decimal('30000'))
        self.assertEqual(ligne_export['tranche_1'], Decimal('400000'))
        self.assertEqual(ligne_export['tranche_2'], Decimal('0'))
        self.assertEqual(ligne_export['tranche_3'], Decimal('0'))
        self.assertEqual(ligne_export['remise'], Decimal('20000'))

    def test_annulation_remise_validee_est_bloquee(self):
        user = get_user_model().objects.create_superuser(
            username='admin-remise', email='a@example.com', password='pass1234'
        )
        self.client.force_login(user)
        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_t1,
            mode_paiement=self.mode, montant=Decimal('100000'),
            date_paiement=date(2025, 10, 1), statut='VALIDE',
        )
        lien = PaiementRemise.objects.create(
            paiement=paiement, remise=self._remise('10', 10),
            montant_remise=40000, montant_base=400000,
            applique_tranche_1=True, montant_tranche_1=40000,
            motif='GESTE_COMMERCIAL',
        )

        response = self.client.post(reverse(
            'paiements:annuler_remise_paiement_unique',
            kwargs={'paiement_id': paiement.pk, 'remise_id': lien.pk},
        ))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(PaiementRemise.objects.filter(pk=lien.pk).exists())

    def test_suppression_admin_paiement_va_dans_corbeille_et_recalcule(self):
        user = get_user_model().objects.create_superuser(
            username='admin-corbeille', email='c@example.com', password='pass1234'
        )
        paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_t1,
            mode_paiement=self.mode, montant=Decimal('400000'),
            date_paiement=date(2025, 10, 1), statut='VALIDE',
        )
        remise = RemiseReduction.objects.create(
            nom='Remise corbeille', type_remise='MONTANT_FIXE', valeur=40000,
            motif='SOCIALE', date_debut=date(2025, 9, 1),
            date_fin=date(2026, 8, 31), actif=True,
        )
        lien = PaiementRemise.objects.create(
            paiement=paiement, remise=remise, montant_remise=40000,
            montant_base=400000, applique_tranche_1=True,
            montant_tranche_1=40000, motif='GESTE_COMMERCIAL',
        )
        recalculer_echeancier(self.echeancier)
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('360000'))
        self.assertEqual(self.echeancier.tranche_2_payee, Decimal('40000'))

        request = RequestFactory().post('/admin/paiements/paiement/delete/')
        request.user = user
        model_admin = PaiementAdmin(Paiement, admin.site)
        model_admin.message_user = lambda *args, **kwargs: None
        paiement_pk = paiement.pk
        lien_pk = lien.pk
        model_admin.delete_model(request, paiement)

        self.assertFalse(Paiement.objects.filter(pk=paiement_pk).exists())
        element = ElementCorbeille.objects.get(
            model_label='paiements.Paiement', type_operation='SUPPRESSION'
        )
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('0'))

        restaure, ignores = restaurer(element, user=user)
        self.assertEqual(ignores, [])
        self.assertTrue(Paiement.objects.filter(pk=restaure.pk).exists())
        self.assertTrue(PaiementRemise.objects.filter(pk=lien_pk).exists())
        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.tranche_1_payee, Decimal('360000'))
        self.assertEqual(self.echeancier.tranche_2_payee, Decimal('40000'))

    def test_suppression_admin_echeancier_va_dans_corbeille(self):
        user = get_user_model().objects.create_superuser(
            username='admin-ech', email='e@example.com', password='pass1234'
        )
        request = RequestFactory().post('/admin/paiements/echeancier/delete/')
        request.user = user
        model_admin = EcheancierPaiementAdmin(EcheancierPaiement, admin.site)
        model_admin.message_user = lambda *args, **kwargs: None
        pk = self.echeancier.pk

        model_admin.delete_model(request, self.echeancier)

        self.assertFalse(EcheancierPaiement.objects.filter(pk=pk).exists())
        self.assertTrue(ElementCorbeille.objects.filter(
            model_label='paiements.EcheancierPaiement', objet_id=pk,
        ).exists())
