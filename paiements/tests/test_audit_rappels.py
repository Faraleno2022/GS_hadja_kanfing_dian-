from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eleves.models import Classe, Ecole, Eleve
from paiements.models import EcheancierPaiement, Relance
from paiements.rappels import gestionnaire_rappels
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from paiements.views import ensure_echeancier_for_eleve


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class RappelsIsolationAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('audit-rappels')
        self.ecole = Ecole.objects.create(nom='École des rappels', etat='VALIDE')
        autre = Ecole.objects.create(nom='Autre école des rappels', etat='VALIDE')
        self.eleves = []
        for ecole in (self.ecole, autre):
            classe = Classe.objects.create(ecole=ecole, nom='1ère année', niveau='PRIMAIRE_1', annee_scolaire='2026-2027')
            eleve = Eleve.objects.create(classe=classe, matricule=f'RAP-{ecole.pk}', prenom='Awa', nom='Diallo', sexe='F')
            ensure_echeancier_for_eleve(eleve)
            self.eleves.append(eleve)
        profil = self.user.profil
        profil.ecole = self.ecole
        profil.role = 'COMPTABLE'
        profil.actif = profil.is_validated = True
        profil.save()
        self.client.force_login(self.user)

    def test_generateur_ne_traite_que_lecole_du_demandeur(self):
        with patch.object(gestionnaire_rappels, 'detecter_eleves_en_retard', return_value=EcheancierPaiement.objects.all()), patch.object(gestionnaire_rappels, 'creer_rappel') as creer:
            stats = gestionnaire_rappels.generer_rappels_automatiques(utilisateur=self.user)
        self.assertEqual(stats['total_eleves_retard'], 1)
        creer.assert_called_once()
        self.assertEqual(creer.call_args.args[0], self.eleves[0])

    def test_statistiques_impayes_comptent_une_fois_le_dernier_solde(self):
        ancien = Relance.objects.create(eleve=self.eleves[0], message='Ancien rappel', solde_estime=30000)
        Relance.objects.filter(pk=ancien.pk).update(date_creation=timezone.now() - timedelta(days=2))
        Relance.objects.create(eleve=self.eleves[0], message='Rappel récent', solde_estime=20000)
        Relance.objects.create(eleve=self.eleves[1], message='Autre école', solde_estime=90000)
        stats = gestionnaire_rappels.obtenir_statistiques_rappels(utilisateur=self.user)
        self.assertEqual(stats['total_rappels'], 2)
        self.assertEqual(stats['eleves_concernes'], 1)
        self.assertEqual(stats['montant_total_impaye'], 20000)
        response = self.client.get(reverse('paiements:gerer_rappels'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['montant_total_impaye'], 20000)

    def test_rappel_autre_ecole_inaccessible_en_lecture_et_ecriture(self):
        relance = Relance.objects.create(eleve=self.eleves[1], message='Autre école')
        for route in ('apercu_message_rappel', 'creer_rappel_individuel'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse('paiements:' + route, args=[self.eleves[1].pk])).status_code, 404)
        response = self.client.post(reverse('paiements:marquer_rappel_envoye', args=[relance.pk]), '{}', content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post(reverse('paiements:supprimer_rappel', args=[relance.pk])).status_code, 404)
        relance.refresh_from_db()
        self.assertEqual(relance.statut, 'ENREGISTREE')

    def test_limites_et_json_invalides_sont_refuses(self):
        relance = Relance.objects.create(eleve=self.eleves[0], message='Rappel')
        for limite in ('abc', '0', '-1', '201'):
            with self.subTest(limite=limite):
                self.assertEqual(self.client.post(reverse('paiements:creer_rappels_automatiques'), {'limite': limite}).status_code, 400)
        for donnees in ('{', '[]', '{"succes": "false"}'):
            with self.subTest(donnees=donnees):
                self.assertEqual(self.client.post(reverse('paiements:marquer_rappel_envoye', args=[relance.pk]), donnees, content_type='application/json').status_code, 400)
        relance.refresh_from_db()
        self.assertEqual(relance.statut, 'ENREGISTREE')

    def test_compte_sans_ecole_ne_voit_aucun_rappel(self):
        Relance.objects.create(eleve=self.eleves[0], message='Rappel')
        self.user.profil.ecole = None
        self.user.profil.save()
        response = self.client.get(reverse('paiements:gerer_rappels'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['total_rappels'], 0)
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
