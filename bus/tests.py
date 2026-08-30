from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve
from paiements.models import ModePaiement
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from utilisateurs.models import Profil

from .forms import AbonnementBusForm
from .models import AbonnementBus, GrilleTarifaireBus


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class GrilleEtPaiementBusTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(
            nom='École Bus A',
            adresse='Conakry',
            telephone='+224620000101',
            directeur='Direction A',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='École Bus B',
            adresse='Conakry',
            telephone='+224620000102',
            directeur='Direction B',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole,
            nom='1ère année',
            niveau='PRIMAIRE_1',
            annee_scolaire='2026-2027',
        )
        self.autre_classe = Classe.objects.create(
            ecole=self.autre_ecole,
            nom='2ème année',
            niveau='PRIMAIRE_2',
            annee_scolaire='2026-2027',
        )
        self.eleve = Eleve.objects.create(
            matricule='BUS-A-001',
            prenom='Fara',
            nom='Leno',
            sexe='M',
            classe=self.classe,
        )
        self.autre_eleve = Eleve.objects.create(
            matricule='BUS-B-001',
            prenom='Mory',
            nom='Camara',
            sexe='M',
            classe=self.autre_classe,
        )
        self.mode = ModePaiement.objects.create(nom='Espèces Bus')
        self.grille = GrilleTarifaireBus.objects.create(
            ecole=self.ecole,
            zone='Ratoma',
            annee_scolaire='2026-2027',
            tranche_1=150000,
            tranche_2=125000,
            tranche_3=125000,
            date_echeance_tranche_1=date(2026, 10, 15),
            date_echeance_tranche_2=date(2027, 1, 15),
            date_echeance_tranche_3=date(2027, 4, 15),
        )
        self.autre_grille = GrilleTarifaireBus.objects.create(
            ecole=self.autre_ecole,
            zone='Matoto',
            annee_scolaire='2026-2027',
            tranche_1=100000,
            tranche_2=100000,
            tranche_3=100000,
        )
        User = get_user_model()
        self.user = User.objects.create_user(username='admin_bus_a', password='secret123')
        Profil.objects.update_or_create(
            user=self.user,
            defaults={
                'role': 'ADMIN',
                'telephone': '+224620000111',
                'ecole': self.ecole,
                'is_validated': True,
                'allowed_menus': ['bus'],
            },
        )
        self.client.force_login(self.user)

    def donnees_paiement(self, **overrides):
        donnees = {
            'eleve': self.eleve.pk,
            'grille': self.grille.pk,
            'periodicite': 'T2',
            'montant': 80000,
            'date_debut': '2026-11-20',
            'mode_paiement': self.mode.pk,
            'observations': '',
        }
        donnees.update(overrides)
        return donnees

    def test_admin_ecole_cree_sa_propre_grille(self):
        response = self.client.post(reverse('bus:grille_nouvelle'), {
            'ecole': self.ecole.pk,
            'zone': 'Sonfonia',
            'annee_scolaire': '2026-2027',
            'tranche_1': 120000,
            'tranche_2': 110000,
            'tranche_3': 100000,
            'actif': 'on',
        })
        self.assertRedirects(response, reverse('administration:grilles_bus'))
        self.assertTrue(
            GrilleTarifaireBus.objects.filter(ecole=self.ecole, zone='Sonfonia').exists()
        )

    def test_grilles_et_api_sont_isolees_par_ecole(self):
        liste = self.client.get(reverse('administration:grilles_bus'))
        self.assertContains(liste, 'Ratoma')
        self.assertNotContains(liste, 'Matoto')

        response = self.client.get(reverse('bus:tarif_bus_json'), {
            'eleve_id': self.eleve.pk,
            'grille_id': self.autre_grille.pk,
            'periodicite': 'T1',
        })
        self.assertEqual(response.status_code, 404)

    def test_paiement_bus_enregistre_grille_mode_et_recu(self):
        response = self.client.post(reverse('bus:nouveau'), self.donnees_paiement())
        self.assertRedirects(response, reverse('bus:liste'))

        paiement = AbonnementBus.objects.get(eleve=self.eleve)
        self.assertEqual(paiement.grille, self.grille)
        self.assertEqual(paiement.mode_paiement, self.mode)
        self.assertEqual(paiement.periodicite, 'T2')
        self.assertEqual(paiement.montant, 80000)
        self.assertEqual(paiement.zone, 'Ratoma')
        self.assertEqual(paiement.annee_scolaire, '2026-2027')
        self.assertTrue(paiement.numero_recu.startswith('BUS'))

        suggestion = self.client.get(reverse('bus:tarif_bus_json'), {
            'eleve_id': self.eleve.pk,
            'grille_id': self.grille.pk,
            'periodicite': 'T2',
        })
        self.assertEqual(suggestion.status_code, 200)
        self.assertEqual(suggestion.json()['du'], 125000)
        self.assertEqual(suggestion.json()['paye'], 80000)
        self.assertEqual(suggestion.json()['reste'], 45000)

    def test_formulaire_refuse_le_depassement_de_la_tranche(self):
        AbonnementBus.objects.create(
            eleve=self.eleve,
            grille=self.grille,
            periodicite='T1',
            montant=140000,
            date_debut=date(2026, 9, 1),
            date_expiration=date(2027, 4, 15),
            mode_paiement=self.mode,
        )
        form = AbonnementBusForm(
            data=self.donnees_paiement(periodicite='T1', montant=20000),
            ecole=self.ecole,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('montant', form.errors)

    def test_formulaire_refuse_eleve_et_grille_de_deux_ecoles(self):
        form = AbonnementBusForm(
            data=self.donnees_paiement(eleve=self.autre_eleve.pk),
            ecole=self.ecole,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('eleve', form.errors)

    def test_recu_pdf_affiche_la_grille_et_la_situation_des_tranches(self):
        from io import BytesIO
        from pypdf import PdfReader

        paiement = AbonnementBus.objects.create(
            eleve=self.eleve,
            grille=self.grille,
            periodicite='T2',
            montant=80000,
            date_debut=date(2026, 11, 20),
            date_expiration=date(2027, 4, 15),
            mode_paiement=self.mode,
            zone=self.grille.zone,
        )
        response = self.client.get(reverse('bus:recu_pdf', args=[paiement.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        texte = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('SITUATION DES TRANCHES', texte)
        self.assertIn('Ratoma - 2026-2027', texte)
        self.assertIn('80 000', texte)

        from .abonnement_public import generer_token_abonnement

        public_response = self.client.get(
            reverse('bus:recu_public_pdf', args=[paiement.pk]),
            {'token': generer_token_abonnement(paiement.pk)},
        )
        self.assertEqual(public_response.status_code, 200)
        texte_public = '\n'.join(
            page.extract_text() or ''
            for page in PdfReader(BytesIO(public_response.content)).pages
        )
        self.assertIn("SITUATION DES TRANCHES DE L'ANNÉE", texte_public)
        self.assertIn(paiement.numero_recu, texte_public)
