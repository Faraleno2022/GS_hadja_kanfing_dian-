from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from eleves.models import Classe, Ecole, Eleve, Responsable
from utilisateurs.models import Profil

from .models_recouvrement import (
    AbonnementInformatique, DepenseCuisine, DepenseDocument, Versement,
)


class RecouvrementTestsBase(TestCase):
    def setUp(self):
        for cible, valeur in (
            ('ecole_moderne.licence_middleware._check_license_cached',
             {'valid': True, 'trial': False, 'days_left': 999}),
            ('ecole_moderne.licence_middleware._check_integrity_cached',
             {'valid': True, 'reason': ''}),
        ):
            patcher = patch(cible, return_value=valeur)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.ecole = Ecole.objects.create(
            nom='École Recouvrement',
            adresse='Conakry',
            telephone='+224620300001',
            directeur='Direction',
            code_prefixe='REC',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='École Voisine',
            adresse='Conakry',
            telephone='+224620300002',
            directeur='Direction B',
            code_prefixe='VOI',
        )

        User = get_user_model()
        self.user = User.objects.create_user('gestionnaire', password='test-pass')
        Profil.objects.update_or_create(
            user=self.user,
            defaults={'role': 'ADMIN', 'telephone': '+224620300003', 'ecole': self.ecole},
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_login(self.user)


class ModulesSimplesTests(RecouvrementTestsBase):
    """Cuisine, documents et versements: saisie, cloisonnement et exports."""

    def test_creation_depense_cuisine_rattachee_a_lecole(self):
        response = self.client.post(
            reverse('depenses:module_recouvrement_nouveau', kwargs={'module': 'cuisine'}),
            {
                'date': timezone.localdate().isoformat(),
                'designation': 'Achat de riz',
                'montant': '450000',
                'observation': 'Sac de 50 kg',
            },
        )
        self.assertEqual(response.status_code, 302)
        depense = DepenseCuisine.objects.get()
        self.assertEqual(depense.ecole, self.ecole)
        self.assertEqual(depense.cree_par, self.user)
        self.assertEqual(depense.montant, Decimal('450000'))
        self.assertEqual(depense.libelle, 'Achat de riz')

    def test_montant_nul_refuse(self):
        response = self.client.post(
            reverse('depenses:module_recouvrement_nouveau', kwargs={'module': 'documents'}),
            {
                'date': timezone.localdate().isoformat(),
                'designation': 'Impression bulletins',
                'montant': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DepenseDocument.objects.exists())
        self.assertContains(response, 'Le montant doit être supérieur à zéro.')

    def test_date_future_refusee(self):
        response = self.client.post(
            reverse('depenses:module_recouvrement_nouveau', kwargs={'module': 'versements'}),
            {
                'date': (timezone.localdate() + timedelta(days=3)).isoformat(),
                'lieu_versement': 'Ecobank Matam',
                'montant': '1000000',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Versement.objects.exists())

    def test_tableau_de_bord_ne_montre_que_son_ecole(self):
        DepenseCuisine.objects.create(
            ecole=self.ecole, date=timezone.localdate(),
            designation='Gaz', montant=Decimal('200000'),
        )
        DepenseCuisine.objects.create(
            ecole=self.autre_ecole, date=timezone.localdate(),
            designation='Charbon école voisine', montant=Decimal('900000'),
        )
        response = self.client.get(
            reverse('depenses:module_recouvrement', kwargs={'module': 'cuisine'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gaz')
        self.assertNotContains(response, 'Charbon école voisine')
        self.assertEqual(response.context['total_filtre'], Decimal('200000'))

    def test_filtre_par_periode(self):
        DepenseCuisine.objects.create(
            ecole=self.ecole, date=date(2026, 1, 15),
            designation='Ancien achat', montant=Decimal('100000'),
        )
        DepenseCuisine.objects.create(
            ecole=self.ecole, date=timezone.localdate(),
            designation='Achat récent', montant=Decimal('300000'),
        )
        response = self.client.get(
            reverse('depenses:module_recouvrement', kwargs={'module': 'cuisine'}),
            {'du': timezone.localdate().isoformat()},
        )
        self.assertEqual(response.context['total_filtre'], Decimal('300000'))
        self.assertEqual(response.context['nombre'], 1)

    def test_module_inconnu_renvoie_404(self):
        response = self.client.get(
            reverse('depenses:module_recouvrement', kwargs={'module': 'inexistant'})
        )
        self.assertEqual(response.status_code, 404)

    def test_exports_excel_et_pdf(self):
        Versement.objects.create(
            ecole=self.ecole, date=timezone.localdate(),
            lieu_versement='Ecobank Matam', montant=Decimal('2500000'),
        )
        excel = self.client.get(
            reverse('depenses:module_recouvrement_export_excel', kwargs={'module': 'versements'})
        )
        self.assertEqual(excel.status_code, 200)
        self.assertIn('spreadsheetml', excel['Content-Type'])
        self.assertTrue(excel.content[:2] == b'PK')

        pdf = self.client.get(
            reverse('depenses:module_recouvrement_export_pdf', kwargs={'module': 'versements'})
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_suppression(self):
        depense = DepenseDocument.objects.create(
            ecole=self.ecole, date=timezone.localdate(),
            designation='Certificats', montant=Decimal('75000'),
        )
        confirmation = self.client.get(
            reverse('depenses:module_recouvrement_supprimer',
                    kwargs={'module': 'documents', 'pk': depense.pk})
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, 'Certificats')

        response = self.client.post(
            reverse('depenses:module_recouvrement_supprimer',
                    kwargs={'module': 'documents', 'pk': depense.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DepenseDocument.objects.exists())


class AbonnementInformatiqueTests(RecouvrementTestsBase):
    """Abonnements informatique: saisie, alertes, carte et exports."""

    def setUp(self):
        super().setUp()
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='7ème année', niveau='COLLEGE_7',
            annee_scolaire='2025-2026', capacite_max=40,
        )
        self.responsable = Responsable.objects.create(
            prenom='Mamadou', nom='Diallo', relation='PERE',
            telephone='+224620300004', adresse='Conakry',
        )
        self.eleve = Eleve.objects.create(
            matricule='REC-001', prenom='Aissatou', nom='Camara', sexe='F',
            date_naissance=date(2012, 3, 12), lieu_naissance='Conakry',
            classe=self.classe, date_inscription=timezone.localdate(),
            statut='ACTIF', responsable_principal=self.responsable,
        )

    def _creer(self, **kwargs):
        params = {
            'eleve': self.eleve,
            'date': timezone.localdate(),
            'montant': Decimal('150000'),
            'date_debut': timezone.localdate(),
            'date_fin': timezone.localdate() + timedelta(days=30),
        }
        params.update(kwargs)
        return AbonnementInformatique.objects.create(**params)

    def test_creation_abonnement(self):
        response = self.client.post(reverse('depenses:creer_abonnement_informatique'), {
            'eleve': self.eleve.pk,
            'date': timezone.localdate().isoformat(),
            'montant': '150000',
            'date_debut': timezone.localdate().isoformat(),
            'date_fin': (timezone.localdate() + timedelta(days=30)).isoformat(),
            'alerte_avant_jours': '7',
            'statut': 'ACTIF',
        })
        self.assertEqual(response.status_code, 302)
        abonnement = AbonnementInformatique.objects.get()
        self.assertEqual(abonnement.eleve, self.eleve)
        self.assertEqual(abonnement.cree_par, self.user)

    def test_fin_avant_debut_refusee(self):
        response = self.client.post(reverse('depenses:creer_abonnement_informatique'), {
            'eleve': self.eleve.pk,
            'date': timezone.localdate().isoformat(),
            'montant': '150000',
            'date_debut': timezone.localdate().isoformat(),
            'date_fin': (timezone.localdate() - timedelta(days=1)).isoformat(),
            'alerte_avant_jours': '7',
            'statut': 'ACTIF',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AbonnementInformatique.objects.exists())
        self.assertContains(response, "La fin doit être postérieure au début")

    def test_statut_effectif_et_alertes(self):
        expire = self._creer(date_fin=timezone.localdate() - timedelta(days=2))
        bientot = self._creer(date_fin=timezone.localdate() + timedelta(days=2))

        self.assertEqual(expire.statut_effectif, 'EXPIRE')
        self.assertEqual(expire.libelle_statut, 'Expiré')
        self.assertTrue(bientot.est_proche_expiration)
        self.assertFalse(bientot.est_expire)

        response = self.client.get(reverse('depenses:dashboard_informatique'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['nb_expires'], 1)
        self.assertEqual(response.context['nb_bientot'], 1)

    def test_recherche_par_matricule(self):
        self._creer()
        response = self.client.get(
            reverse('depenses:dashboard_informatique'), {'q': 'REC-001'}
        )
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

        response = self.client.get(
            reverse('depenses:dashboard_informatique'), {'q': 'INTROUVABLE'}
        )
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_pages_de_saisie_et_de_suppression(self):
        abonnement = self._creer()
        for url in (
            reverse('depenses:creer_abonnement_informatique'),
            reverse('depenses:modifier_abonnement_informatique', kwargs={'pk': abonnement.pk}),
            reverse('depenses:supprimer_abonnement_informatique', kwargs={'pk': abonnement.pk}),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'REC-001')

    def test_carte_abonnement_pdf(self):
        abonnement = self._creer()
        response = self.client.get(
            reverse('depenses:carte_abonnement_informatique', kwargs={'pk': abonnement.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_exports_informatique(self):
        self._creer()
        excel = self.client.get(reverse('depenses:export_informatique_excel'))
        self.assertEqual(excel.status_code, 200)
        self.assertTrue(excel.content[:2] == b'PK')

        pdf = self.client.get(reverse('depenses:export_informatique_pdf'))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_api_eleve(self):
        self._creer()
        response = self.client.get(
            reverse('depenses:api_eleve_informatique', kwargs={'eleve_id': self.eleve.pk})
        )
        self.assertEqual(response.status_code, 200)
        donnees = response.json()
        self.assertEqual(donnees['matricule'], 'REC-001')
        self.assertEqual(donnees['classe'], self.classe.nom)
        self.assertIsNotNone(donnees['dernier_abonnement'])


class HubRecouvrementTests(RecouvrementTestsBase):
    def test_hub_affiche_les_cartes_et_les_totaux(self):
        DepenseCuisine.objects.create(
            ecole=self.ecole, date=timezone.localdate(),
            designation='Gaz', montant=Decimal('200000'),
        )
        Versement.objects.create(
            ecole=self.ecole, date=timezone.localdate(),
            lieu_versement='Ecobank', montant=Decimal('1000000'),
        )
        response = self.client.get(reverse('depenses:tableau_bord'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recouvrement')
        self.assertContains(response, 'Dépenses de la cuisine')
        self.assertContains(response, 'Informatique')
        self.assertEqual(response.context['sorties_mois'], Decimal('200000'))
        self.assertEqual(response.context['versements_mois'], Decimal('1000000'))
        self.assertEqual(len(response.context['cartes']), 10)
