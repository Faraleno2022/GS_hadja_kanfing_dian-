from urllib.parse import parse_qs

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from administration.audit import mettre_en_corbeille, restaurer_element
from eleves.models import Ecole, Eleve
from paiements.models import Paiement
from paiements.tests import test_revision as fixtures
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import _valider_paiement_impl
from utilisateurs.models import Profil


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RevisionCardTests(TestCase):
    setUp = fixtures.RevisionTests.setUp
    creer_echeancier = fixtures.RevisionTests.creer_echeancier
    paiement = fixtures.RevisionTests.paiement
    donnees = fixtures.RevisionTests.donnees
    solde = fixtures.RevisionTests.solde

    def resume(self, **params):
        response = self.client.get(reverse('paiements:ajax_statistiques_paiements'), params)
        self.assertEqual(response.status_code, 200)
        return response.json()['resume_revision']

    def test_total_compte_une_revision_par_eleve_pas_les_versements(self):
        self.paiement()
        self.paiement(revision=False, montant=50000)
        autre = Eleve.objects.create(matricule='REV-CARTE-2', prenom='Moussa', nom='Camara', sexe='M', classe=self.classe)
        paiement = Paiement.objects.create(
            eleve=autre, type_paiement=self.type, mode_paiement=self.mode,
            montant=50000, date_paiement='2026-09-08', annee_scolaire='2026-2027',
            statut='VALIDE', frais_revision_inclus=True,
        )
        resume = self.resume()
        self.assertEqual((resume['nombre'], resume['montant'], resume['tarif']), (2, 40000, 20000))
        self.assertEqual(self.solde(), 130000)
        paiement.statut = 'ANNULE'
        paiement.save(update_fields=['statut'])
        self.assertEqual(self.resume()['montant'], 20000)

    def test_validation_suppression_restauration_actualisent_carte(self):
        paiement = self.paiement(valide=False)
        self.assertEqual(self.resume()['montant'], 0)
        paiement = _valider_paiement_impl(paiement, self.user)
        self.assertEqual(self.resume()['montant'], 20000)
        element = mettre_en_corbeille(paiement)
        self.assertEqual(self.resume()['montant'], 0)
        restaurer_element(element)
        self.assertEqual(self.resume()['montant'], 20000)
        self.assertEqual(self.solde(), 180000)

    def test_retrait_option_recalcule_carte_et_conserve_versement(self):
        paiement = self.paiement()
        response = self.client.post(reverse('paiements:modifier_paiement', args=[paiement.pk]),
                                    self.donnees(paiement, frais_revision_inclus=''))
        self.assertEqual(response.status_code, 302)
        resume = self.resume()
        self.assertEqual((resume['nombre'], resume['montant']), (0, 0))
        paiement.refresh_from_db()
        self.assertEqual(paiement.montant, 100000)
        self.assertEqual(self.solde(), 200000)

    def test_meme_perimetre_pour_carte_liste_et_actualisation(self):
        self.paiement()
        self.creer_echeancier('2027-2028')
        self.paiement(annee='2027-2028')
        params = {'annee_scolaire': '2026-2027', 'classe': str(self.classe.pk), 'q': 'Aminata'}
        resume = self.resume(**params)
        self.assertEqual((resume['nombre'], resume['montant'], resume['annee']), (1, 20000, '2026-2027'))
        self.assertEqual(parse_qs(resume['filtres']), {key: [value] for key, value in params.items()})
        before = list(Paiement.objects.values())
        for name in ('tableau_bord', 'liste_revisions'):
            response = self.client.get(reverse('paiements:' + name), params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['resume_revision'], resume)
            self.assertContains(response, 'data-revision-card')
            self.assertContains(response, 'Montant total des frais de révision')
        self.assertEqual(list(Paiement.objects.values()), before)
        self.assertEqual(self.resume(annee_scolaire='2025-2026')['montant'], 0)
        self.assertEqual(self.resume(q='Introuvable')['montant'], 0)
        self.assertEqual(self.resume(classe='999999')['montant'], 0)

    def test_carte_ne_divulgue_pas_autre_ecole(self):
        self.paiement()
        user = get_user_model().objects.create_user('carte-autre-ecole', password='test')
        autre = Ecole.objects.create(nom='Autre école carte', adresse='Conakry', telephone='620000012', directeur='Direction')
        Profil.objects.update_or_create(user=user, defaults={'ecole': autre, 'role': 'COMPTABLE'})
        self.client.force_login(user)
        self.assertEqual(self.resume()['montant'], 0)
        response = self.client.get(reverse('paiements:tableau_bord'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['resume_revision']['nombre'], 0)
