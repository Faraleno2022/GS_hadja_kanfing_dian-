from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from administration.models import ElementCorbeille
from eleves.models import Classe, Ecole, Eleve, GrilleTarifaire
from paiements.models import ModePaiement, Paiement, Relance, TypePaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import ensure_echeancier_for_eleve


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class IntegritePaiementsAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('audit-integrite')
        self.ecole = Ecole.objects.create(nom='École intégrité', etat='VALIDE')
        profil = self.user.profil
        profil.ecole = self.ecole
        profil.role = 'ADMIN'
        profil.actif = profil.is_validated = True
        profil.save()
        self.client.force_login(self.user)
        self.classe = Classe.objects.create(ecole=self.ecole, nom='Petite section A', niveau='PETITE_SECTION', annee_scolaire='2026-2027')
        self.eleve = Eleve.objects.create(classe=self.classe, matricule='INT-001', prenom='Awa', nom='Diallo', sexe='F')
        GrilleTarifaire.objects.create(ecole=self.ecole, niveau=self.classe.niveau, annee_scolaire=self.classe.annee_scolaire, frais_inscription=100000, tranche_1=300000, tranche_2=300000, tranche_3=300000)
        self.type = TypePaiement.objects.create(nom='Inscription + Annuel')
        self.mode = ModePaiement.objects.create(nom='Espèces')
        self.echeancier = ensure_echeancier_for_eleve(self.eleve)
        self.paiement = Paiement.objects.create(eleve=self.eleve, type_paiement=self.type, mode_paiement=self.mode, montant=100000, date_paiement=date(2026, 9, 6), annee_scolaire='2026-2027')

    def corriger(self, montant):
        return self.client.post(reverse('paiements:modifier_paiement', args=[self.paiement.pk]), {
            'type_paiement': self.type.pk, 'mode_paiement': self.mode.pk,
            'date_paiement': '2026-09-06', 'montant': montant,
            'motif_modification': 'Corriger une erreur de saisie',
        })

    def test_echec_recalcul_annule_modification_et_journal(self):
        avant = ElementCorbeille.objects.count()
        with patch('paiements.services.synchroniser_echeancier_apres_changement_paiement', side_effect=RuntimeError('Recalcul interrompu')):
            response = self.corriger('200000')
        self.assertContains(response, "Aucun montant n&#x27;a été modifié")
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('100000'))
        self.assertEqual(ElementCorbeille.objects.count(), avant)
        self.assertEqual(response.context['form'].data['montant'], '200000')

    def test_modification_excessive_refusee_sans_changer_le_solde(self):
        avant = self.echeancier.solde_restant
        response = self.corriger('1000001')
        self.assertContains(response, 'dépasse le solde restant dû')
        self.paiement.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('100000'))
        self.assertEqual(self.echeancier.solde_restant, avant)

    def test_validation_excessive_explique_le_refus_sans_envoyer_de_recu(self):
        Paiement.objects.filter(pk=self.paiement.pk).update(montant=1000001)
        with patch('paiements.views.send_payment_receipt') as envoyer:
            response = self.client.post(reverse('paiements:valider_paiement', args=[self.paiement.pk]), follow=True)
        self.assertContains(response, 'dépasse le solde restant dû')
        envoyer.assert_not_called()
        self.paiement.refresh_from_db()
        self.assertEqual(self.paiement.statut, 'EN_ATTENTE')

    def test_statistiques_rappels_isolees_et_semaines_sans_trou(self):
        autre_ecole = Ecole.objects.create(nom='Autre école rappels')
        autre_classe = Classe.objects.create(ecole=autre_ecole, nom='Petite section A', niveau='PETITE_SECTION', annee_scolaire='2026-2027')
        autre_eleve = Eleve.objects.create(classe=autre_classe, matricule='AUTRE-INT', prenom='Secret', nom='Autre', sexe='F')
        maintenant = timezone.now()
        for age in (0, 6.5, 7, 13.9):
            relance = Relance.objects.create(eleve=self.eleve, message='Rappel', statut='ENVOYEE')
            Relance.objects.filter(pk=relance.pk).update(date_creation=maintenant - timedelta(days=age))
        Relance.objects.create(eleve=autre_eleve, message='Rappel autre école')
        with patch('paiements.views_rappels.timezone.now', return_value=maintenant):
            response = self.client.get(reverse('paiements:statistiques_rappels'), {'periode': 14})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['total_rappels'], 4)
        self.assertEqual(response.context['stats']['eleves_concernes'], 1)
        self.assertEqual(sum(row['nb_rappels'] for row in response.context['rappels_par_semaine']), 4)
        self.assertEqual([row['eleve_id'] for row in response.context['top_eleves']], [self.eleve.pk])

    def test_periode_invalide_refusee(self):
        for periode in ('abc', '0', '-1', '367'):
            with self.subTest(periode=periode):
                self.assertEqual(self.client.get(reverse('paiements:statistiques_rappels'), {'periode': periode}).status_code, 400)
