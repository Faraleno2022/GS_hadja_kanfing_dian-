from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from administration.models import CorbeilleElement, ElementCorbeille
from eleves.models import Classe, Ecole, Eleve, Responsable
from paiements.dashboard_metrics import build_payment_dashboard_metrics
from paiements.models import EcheancierPaiement, ModePaiement, Paiement, TypePaiement
from paiements.payment_engine import recalculer_echeancier
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(
    MIDDLEWARE=MIDDLEWARE_SANS_LICENCE,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class PaymentMutationWorkflowTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            'audit_caisse', 'audit-caisse@example.com', 'secret'
        )
        self.client.force_login(self.user)
        self.ecole = Ecole.objects.create(
            nom='École audit caisse', adresse='Conakry',
            telephone='+224622880001', directeur='Direction',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='Classe audit', niveau='PRIMAIRE_2',
            annee_scolaire='2026-2027',
        )
        responsable = Responsable.objects.create(
            prenom='Mamadou', nom='Camara', relation='PERE',
            telephone='+224622880002', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='AUD-CAISSE-001', prenom='Aminata', nom='Diallo',
            sexe='F', date_naissance=date(2017, 1, 5),
            lieu_naissance='Conakry', classe=self.classe,
            date_inscription=date(2026, 8, 1),
            responsable_principal=responsable,
        )
        self.type_paiement = TypePaiement.objects.create(nom='Scolarité audit')
        self.mode_paiement = ModePaiement.objects.create(nom='Espèces audit')
        self.echeancier = EcheancierPaiement.objects.create(
            eleve=self.eleve, annee_scolaire='2026-2027',
            frais_inscription_du=Decimal('50000'),
            tranche_1_due=Decimal('200000'),
            tranche_2_due=Decimal('200000'),
            tranche_3_due=Decimal('200000'),
            date_echeance_inscription=date(2026, 8, 1),
            date_echeance_tranche_1=date(2026, 9, 1),
            date_echeance_tranche_2=date(2027, 1, 1),
            date_echeance_tranche_3=date(2027, 3, 1),
        )
        self.paiement = Paiement.objects.create(
            eleve=self.eleve, type_paiement=self.type_paiement,
            mode_paiement=self.mode_paiement, montant=Decimal('100000'),
            date_paiement=date(2026, 8, 20), annee_scolaire='2026-2027',
            statut='VALIDE', cree_par=self.user, valide_par=self.user,
        )
        recalculer_echeancier(self.echeancier)

    def _modifier_montant(self):
        return self.client.post(
            reverse('paiements:modifier_paiement', args=[self.paiement.pk]),
            {
                'type_paiement': self.type_paiement.pk,
                'mode_paiement': self.mode_paiement.pk,
                'montant': '150 000 GNF',
                'date_paiement': '2026-08-20',
                'reference_externe': '',
                'observations': '',
                'motif_modification': 'Correction du montant du reçu',
            },
        )

    def test_modification_recalcule_et_alimente_cartes_et_historique(self):
        response = self._modifier_montant()
        self.assertEqual(response.status_code, 302)

        self.paiement.refresh_from_db()
        self.echeancier.refresh_from_db()
        self.assertEqual(self.paiement.montant, Decimal('150000'))
        self.assertEqual(self.echeancier.total_paye, Decimal('150000'))

        audit = ElementCorbeille.objects.get(
            model_label='paiements.Paiement',
            type_operation=ElementCorbeille.MODIFICATION,
            objet_id=self.paiement.pk,
        )
        self.assertEqual(audit.motif, 'Correction du montant du reçu')

        metrics = build_payment_dashboard_metrics(
            self.user, today=timezone.localdate()
        )
        modifications = metrics['mutations'][0]['values']
        self.assertEqual(modifications['today']['amount'], 150000)
        self.assertEqual(modifications['today']['count'], 1)

        history = self.client.get(
            reverse('paiements:historique_mutations_paiements'),
            {'periode': 'today'},
        )
        self.assertContains(history, 'Correction du montant du reçu')
        self.assertContains(history, '150')

    def test_suppression_recalcule_et_alimente_cartes_et_historique(self):
        paiement_id = self.paiement.pk
        response = self.client.post(
            reverse('paiements:supprimer_paiement', args=[paiement_id]),
            {'motif': 'Paiement enregistré deux fois'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Paiement.objects.filter(pk=paiement_id).exists())

        self.echeancier.refresh_from_db()
        self.assertEqual(self.echeancier.total_paye, Decimal('0'))
        deletion = CorbeilleElement.objects.get(
            app_label='paiements', model_name='Paiement',
            objet_id_origine=paiement_id,
        )
        self.assertEqual(deletion.motif, 'Paiement enregistré deux fois')

        metrics = build_payment_dashboard_metrics(
            self.user, today=timezone.localdate()
        )
        deletions = metrics['mutations'][1]['values']
        self.assertEqual(deletions['today']['amount'], 100000)
        self.assertEqual(deletions['today']['count'], 1)

        history = self.client.get(
            reverse('paiements:historique_mutations_paiements'),
            {'periode': 'today'},
        )
        self.assertContains(history, 'Paiement enregistré deux fois')
        self.assertContains(history, self.paiement.numero_recu)
