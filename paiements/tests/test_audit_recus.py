from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from eleves.models import Classe, Ecole, Eleve
from paiements.models import ModePaiement, Paiement, TypePaiement
from synchronisation.mixins import SyncTrackedModel


class NumerotationRecusAuditTests(TestCase):
    def setUp(self):
        ecole = Ecole.objects.create(nom='École reçus')
        classe = Classe.objects.create(ecole=ecole, nom='1ère année', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
        self.eleve = Eleve.objects.create(classe=classe, matricule='REC-AUDIT', nom='Diallo', prenom='Aminata', sexe='F')
        self.type = TypePaiement.objects.create(nom='Tranche 1')
        self.mode = ModePaiement.objects.create(nom='Espèces')
        self.prefixe = f'REC{timezone.now().year}'

    def creer(self, **kwargs):
        return Paiement.objects.create(eleve=self.eleve, type_paiement=self.type, mode_paiement=self.mode,
                                       date_paiement=date(2026, 9, 1), montant=1000, **kwargs)

    def test_numerotation_continue_apres_9999(self):
        self.creer(numero_recu=f'{self.prefixe}9999')
        self.assertEqual(self.creer().numero_recu, f'{self.prefixe}10000')
        self.assertEqual(self.creer().numero_recu, f'{self.prefixe}10001')

    def test_numero_non_numerique_nempeche_pas_la_generation(self):
        self.creer(numero_recu=f'{self.prefixe}EXTERNE')
        self.assertEqual(self.creer().numero_recu, f'{self.prefixe}0001')

    def test_erreur_integrite_etrangere_nest_pas_masquee_par_une_boucle(self):
        with patch.object(SyncTrackedModel, 'save', side_effect=IntegrityError('contrainte étrangère')) as save:
            with self.assertRaises(IntegrityError):
                self.creer()
        self.assertEqual(save.call_count, 1)
        self.assertEqual(Paiement.objects.count(), 0)

    def test_montant_invalide_nempoisonne_pas_la_transaction(self):
        for montant in ('NaN', 'Infinity', '-1', '0'):
            with self.subTest(montant=montant), self.assertRaises(ValidationError):
                Paiement.objects.create(eleve=self.eleve, type_paiement=self.type, mode_paiement=self.mode, montant=Decimal(montant))
        self.assertEqual(self.creer().montant, Decimal('1000'))
