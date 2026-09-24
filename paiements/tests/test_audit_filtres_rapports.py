from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from eleves.models import Classe, Ecole, Eleve
from paiements.models import EcheancierPaiement, Paiement, TypePaiement, ModePaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class FiltresRapportsAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('audit-filtres-rapports')
        self.ecole = Ecole.objects.create(nom='École rapport', etat='VALIDE')
        self.autre = Ecole.objects.create(nom='École extérieure', etat='VALIDE')
        profil = self.user.profil
        profil.role = 'ADMIN'
        profil.ecole = self.ecole
        profil.peut_consulter_rapports = profil.peut_importer_eleves = True
        profil.save()
        self.client.force_login(self.user)
        self.classe = Classe.objects.create(ecole=self.ecole, nom='6e A', niveau='PRIMAIRE_6', annee_scolaire='2026-2027')
        self.externe = Classe.objects.create(ecole=self.autre, nom='6e A', niveau='PRIMAIRE_6', annee_scolaire='2027-2028')
        self.eleve = Eleve.objects.create(classe=self.classe, matricule='FLT-001', prenom='Awa', nom='Test', sexe='F')
        self.type = TypePaiement.objects.create(nom='Inscription + Annuel')
        self.mode = ModePaiement.objects.create(nom='Espèces')
        for annee, montant in [('2025-2026', 900000), ('2026-2027', 100000)]:
            EcheancierPaiement.objects.create(
                eleve=self.eleve, annee_scolaire=annee, frais_inscription_du=0,
                tranche_1_due=montant, tranche_2_due=0, tranche_3_due=0,
                date_echeance_inscription=date(2025, 9, 1), date_echeance_tranche_1=date(2025, 10, 1),
                date_echeance_tranche_2=date(2026, 1, 1), date_echeance_tranche_3=date(2026, 4, 1),
            )

    def test_rapport_exclut_ancien_echeancier(self):
        response = self.client.get(reverse('paiements:rapport_comptable'), {'annee_scolaire': '2026-2027'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_retards'], Decimal('100000'))
        self.assertEqual(response.context['nombre_retards'], 1)

    def test_filtres_invalides_et_classe_exterieure_ne_retournent_pas_toutes_les_donnees(self):
        for params in ({'classe': self.externe.pk}, {'classe': 'abc'}, {'date_debut': 'invalide'}, {'date_debut': '2026-03-01', 'date_fin': '2026-02-01'}, {'statut': 'inconnu'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(reverse('paiements:rapport_comptable'), params).status_code, 400)

    def test_export_preserve_les_filtres_du_lien(self):
        for mois, numero in [(7, 'FLT-JUILLET'), (8, 'FLT-AOUT')]:
            Paiement.objects.create(eleve=self.eleve, type_paiement=self.type, mode_paiement=self.mode, montant=10000, statut='VALIDE', date_paiement=date(2026, mois, 15), annee_scolaire='2026-2027', numero_recu=numero)
        response = self.client.get(reverse('paiements:export_rapport_comptable_excel'), {'classe_id': self.classe.pk, 'du': '2026-08-01', 'au': '2026-08-31'})
        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), data_only=True)
        values = [cell.value for row in workbook['Journal validé'] for cell in row]
        self.assertIn('FLT-AOUT', values)
        self.assertNotIn('FLT-JUILLET', values)

    def test_annee_import_limitee_aux_classes_de_lecole(self):
        response = self.client.get(reverse('eleves:importer_eleves'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['annee_courante'], '2026-2027')
        self.assertEqual(list(response.context['classes']), [self.classe])

    def test_admin_ecole_ne_cree_pas_un_paiement_pour_autre_ecole(self):
        eleve = Eleve.objects.create(classe=self.externe, matricule='FLT-SECRET', prenom='Autre', nom='Élève', sexe='F')
        response = self.client.post(reverse('paiements:ajouter_paiement'), {
            'eleve': eleve.pk, 'type_paiement': self.type.pk, 'mode_paiement': self.mode.pk,
            'montant': 10000, 'date_paiement': '2026-09-01',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Paiement.objects.filter(eleve=eleve).exists())
        self.assertFalse(EcheancierPaiement.objects.filter(eleve=eleve).exists())

    def test_envoi_collectif_refuse_sans_permission(self):
        from unittest.mock import patch
        self.user.profil.role = 'ENSEIGNANT'
        self.user.profil.peut_consulter_rapports = False
        self.user.profil.save()
        with patch('paiements.views.send_retard_notification') as envoyer:
            response = self.client.post(reverse('paiements:envoyer_notifs_retards'))
        self.assertEqual(response.status_code, 403)
        envoyer.assert_not_called()
