from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext

from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from eleves.models import Classe, Eleve
from . import tests as fixtures
from .models import AbonnementBus, GrilleTarifaireBus


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class SuiviBusClasseTests(TestCase):
    def setUp(self):
        fixtures.GrilleEtPaiementBusTests.setUp(self)
        self.sans_bus = Eleve.objects.create(
            matricule='BUS-A-002', prenom='Sans', nom='Abonnement', sexe='F', classe=self.classe,
        )
        self.today = date(2026, 9, 13)
        self.clock = patch('django.utils.timezone.localdate', return_value=self.today)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def versement(self, **kwargs):
        data = dict(eleve=self.eleve, grille=self.grille, montant=50000,
                    periodicite='T1', date_debut=self.today,
                    date_expiration=date(2027, 4, 15), mode_paiement=self.mode)
        data.update(kwargs)
        return AbonnementBus.objects.create(**data)

    def dashboard(self, **kwargs):
        return self.client.get(reverse('bus:index'), {'classe_id': self.classe.pk, **kwargs})

    def ligne(self, response, eleve=None):
        self.assertEqual(response.status_code, 200)
        return next(row for row in response.context['lignes_bus']
                    if row['eleve'].pk == (eleve or self.eleve).pk)

    def test_deux_versements_un_seul_du_et_tous_les_recus(self):
        a = self.versement()
        b = self.versement(periodicite='ANNUEL', montant=100000)
        response = self.dashboard()
        row = self.ligne(response)
        self.assertEqual(row['nombre_paiements'], 2)
        self.assertEqual(row['montant_paye'], 150000)
        self.assertEqual(row['reste'], 250000)
        self.assertEqual(row['reste'], self.grille.situation_paiements(self.eleve)['ANNUEL']['reste'])
        for paiement in (a, b):
            self.assertContains(response, reverse('bus:recu_pdf', args=[paiement.pk]))
        self.assertContains(response, '?abonnement=' + str(b.pk))
        sans = self.ligne(response, self.sans_bus)
        self.assertEqual(sans['statut'], 'Sans abonnement')
        self.assertEqual(sans['nombre_paiements'], 0)
        self.assertIsNone(sans['reste'])

    def test_modification_suppression_et_tarif_recalculent_le_solde(self):
        a = self.versement()
        b = self.versement()
        self.assertEqual(self.ligne(self.dashboard())['reste'], 300000)
        a.montant = 70000
        a.save()
        self.assertEqual(self.ligne(self.dashboard())['reste'], 280000)
        b.delete()
        self.assertEqual(self.ligne(self.dashboard())['reste'], 330000)
        self.grille.tranche_1 = 160000
        self.grille.save()
        self.assertEqual(self.ligne(self.dashboard())['reste'], 340000)

    def test_ancien_paiement_exclu_et_transfert_classe_conserve_versements(self):
        self.versement()
        ancien = GrilleTarifaireBus.objects.create(
            ecole=self.ecole, zone='Ratoma', annee_scolaire='2025-2026',
            tranche_1=100000, tranche_2=100000, tranche_3=100000,
        )
        self.versement(grille=ancien, montant=200000)
        self.assertEqual(self.ligne(self.dashboard())['nombre_paiements'], 1)
        nouvelle = Classe.objects.create(
            ecole=self.ecole, nom='1ère année B', niveau=self.classe.niveau,
            annee_scolaire=self.classe.annee_scolaire,
        )
        self.eleve.classe = nouvelle
        self.eleve.save()
        response = self.dashboard(classe_id=nouvelle.pk)
        self.assertEqual(self.ligne(response)['reste'], 350000)
        self.assertFalse(any(row['eleve'].pk == self.eleve.pk for row in self.dashboard().context['lignes_bus']))

    def test_choix_eleve_et_isolation_ecole(self):
        response = self.dashboard(eleve_id=self.eleve.pk)
        self.assertEqual(len(response.context['lignes_bus']), 1)
        self.assertNotIn(self.autre_classe, response.context['classes_bus'])
        for params in (
            {'classe_id': self.autre_classe.pk},
            {'eleve_id': self.autre_eleve.pk},
            {'classe_id': 'invalide'}, {'eleve_id': 'invalide'},
        ):
            self.assertEqual(self.dashboard(**params).status_code, 404)

    def test_statut_reel_et_carte_seulement_si_valide(self):
        a = self.versement()
        for statut, debut, fin, attendu in (
            ('ACTIF', self.today, self.today, 'Actif'),
            ('ACTIF', self.today, self.today - timedelta(days=1), 'Expiré'),
            ('EXPIRE', self.today, self.today + timedelta(days=20), 'Expiré'),
            ('SUSPENDU', self.today, self.today + timedelta(days=20), 'Suspendu'),
            ('ACTIF', self.today + timedelta(days=2), self.today + timedelta(days=20), 'À venir'),
        ):
            with self.subTest(attendu=attendu):
                a.statut, a.date_debut, a.date_expiration = statut, debut, fin
                a.save()
                row = self.ligne(self.dashboard())
                self.assertEqual(row['statut'], attendu)
                self.assertEqual(bool(row['carte_abonnement']), attendu == 'Actif')
                self.assertEqual(row['reste'], 350000)

    def test_legacy_sans_grille_n_invente_pas_un_solde(self):
        self.versement(grille=None)
        row = self.ligne(self.dashboard())
        self.assertIsNone(row['reste'])
        self.assertEqual(row['montant_paye'], 50000)

    def test_plusieurs_grilles_ne_multiplient_pas_le_tarif(self):
        self.versement()
        self.versement()
        grille = GrilleTarifaireBus.objects.create(
            ecole=self.ecole, zone='Autre circuit', annee_scolaire='2026-2027',
            tranche_1=20000, tranche_2=20000, tranche_3=20000,
        )
        self.versement(grille=grille, montant=20000)
        row = self.ligne(self.dashboard())
        self.assertEqual(row['reste'], 340000)
        self.assertEqual(len(row['situations']), 2)

    def test_carte_du_recu_selectionne_et_acces_inter_ecoles(self):
        a = self.versement()
        response = self.client.get(reverse('eleves:ticket_bus_pdf', args=[self.eleve.pk]), {'abonnement': a.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))
        autre = self.versement(eleve=self.autre_eleve, grille=self.autre_grille)
        response = self.client.get(reverse('eleves:ticket_bus_pdf', args=[self.eleve.pk]), {'abonnement': autre.pk})
        self.assertEqual(response.status_code, 404)
        a.statut = 'SUSPENDU'
        a.save()
        response = self.client.get(reverse('eleves:ticket_bus_pdf', args=[self.eleve.pk]), {'abonnement': a.pk})
        self.assertEqual(response.status_code, 404)

    def test_pagination_et_pas_de_requete_par_eleve(self):
        self.versement()
        with CaptureQueriesContext(connection) as one:
            self.dashboard()
        for n in range(28):
            eleve = Eleve.objects.create(
                matricule=f'BUS-P-{n}', prenom=f'Prénom {n}', nom='Pagination',
                sexe='M', classe=self.classe,
            )
            self.versement(eleve=eleve)
        with CaptureQueriesContext(connection) as many:
            response = self.dashboard()
        self.assertLessEqual(len(many), len(one) + 2)
        self.assertEqual(response.context['page_bus'].paginator.count, 30)
        self.assertEqual(len(response.context['lignes_bus']), 25)
        self.assertContains(response, 'page_bus=2')
        self.assertEqual(len(self.dashboard(page_bus=2).context['lignes_bus']), 5)
