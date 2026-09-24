from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve
from paiements.models import ModePaiement, Paiement, PaiementRemise, RemiseReduction, TypePaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RapportRemisesAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('rapport-audit', password='test')
        self.client.force_login(self.user)
        ecole = Ecole.objects.create(nom='École audit remises')
        classe = Classe.objects.create(ecole=ecole, nom='1ère année', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
        eleve = Eleve.objects.create(classe=classe, matricule='R-001', nom='Bah', prenom='Aminata', sexe='F')
        mode = ModePaiement.objects.create(nom='Espèces')
        type_paiement = TypePaiement.objects.create(nom='Tranche 1')
        self.paiements = [Paiement.objects.create(eleve=eleve, type_paiement=type_paiement, mode_paiement=mode,
                                                 montant=20000, statut='VALIDE', date_paiement=date(2026, 9, 1)) for _ in range(2)]
        remise = RemiseReduction.objects.create(nom='Sociale', type_remise='MONTANT_FIXE', valeur=3000,
                                               motif='SOCIALE', date_debut=date(2026, 7, 1), date_fin=date(2027, 6, 30))
        autre_remise = RemiseReduction.objects.create(nom='Fratrie', type_remise='MONTANT_FIXE', valeur=3000,
                                                      motif='FRATRIE', date_debut=date(2026, 7, 1), date_fin=date(2027, 6, 30))
        for paiement, regle, montant in ((self.paiements[0], remise, 3000), (self.paiements[0], autre_remise, 3000), (self.paiements[1], remise, 2000)):
            PaiementRemise.objects.create(paiement=paiement, remise=regle, montant_remise=montant)

    def test_encaissements_comptes_une_fois_par_recu(self):
        response = self.client.get(reverse('rapports:rapport_remises'), {'date_debut': '2026-07-01', 'date_fin': '2026-09-11'})
        self.assertEqual(response.status_code, 200)
        stats = response.context['stats_remises']
        self.assertEqual(stats['total_remises'], 8000)
        self.assertEqual(stats['total_montants_finals'], 40000)
        self.assertEqual(stats['total_couvert'], 48000)
        self.assertEqual(stats['nombre_paiements_avec_remise'], 2)

    def test_periode_invalide_est_refusee_sans_erreur_500(self):
        for filtres in ({'date_debut': 'invalide'}, {'date_debut': '2026-10-01', 'date_fin': '2026-09-01'}):
            with self.subTest(filtres=filtres):
                response = self.client.get(reverse('rapports:rapport_remises'), filtres)
                self.assertEqual(response.status_code, 400)
