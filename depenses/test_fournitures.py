from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from eleves.models import Ecole
from utilisateurs.models import Profil

from .forms_fournitures import VenteFournitureForm
from .models_fournitures import FournitureScolaire, VenteFourniture


class FournituresScolairesTests(TestCase):
    def setUp(self):
        license_patcher = patch(
            'ecole_moderne.licence_middleware._check_license_cached',
            return_value={'valid': True, 'trial': False, 'days_left': 999},
        )
        integrity_patcher = patch(
            'ecole_moderne.licence_middleware._check_integrity_cached',
            return_value={'valid': True, 'reason': ''},
        )
        license_patcher.start()
        integrity_patcher.start()
        self.addCleanup(license_patcher.stop)
        self.addCleanup(integrity_patcher.stop)

        self.ecole = Ecole.objects.create(
            nom='École Fournitures',
            adresse='Conakry',
            telephone='+224620200001',
            directeur='Direction',
            code_prefixe='FOU',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='École Externe',
            adresse='Conakry',
            telephone='+224620200002',
            directeur='Direction B',
            code_prefixe='EXT',
        )
        User = get_user_model()
        self.user = User.objects.create_user('vendeur', password='test-pass')
        Profil.objects.update_or_create(
            user=self.user,
            defaults={
                'role': 'COMPTABLE',
                'telephone': '+224620200003',
                'ecole': self.ecole,
            },
        )
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

        self.produit = FournitureScolaire.objects.create(
            ecole=self.ecole,
            reference='FOU-CAH-001',
            nom='Cahier 200 pages',
            categorie='CAHIER_PAPIER',
            quantite_stock=10,
            stock_minimum=2,
            prix_achat_unitaire=Decimal('1000'),
            prix_vente_unitaire=Decimal('1500'),
            cree_par=self.user,
        )

    def test_ajout_produit_rattache_ecole_et_genere_reference(self):
        response = self.client.post(reverse('depenses:creer_fourniture'), {
            'reference': '',
            'nom': 'Stylo bleu',
            'categorie': 'ECRITURE',
            'unite': 'PIECE',
            'quantite_stock': '50',
            'stock_minimum': '10',
            'prix_achat_unitaire': '2000',
            'prix_vente_unitaire': '3000',
            'description': '',
            'actif': 'on',
        })

        self.assertRedirects(response, reverse('depenses:dashboard_fournitures'))
        produit = FournitureScolaire.objects.get(nom='Stylo bleu')
        self.assertEqual(produit.ecole, self.ecole)
        self.assertTrue(produit.reference.startswith('FOUR-FOU-'))

    def test_vente_met_a_jour_reste_chiffre_affaires_et_solde(self):
        response = self.client.post(reverse('depenses:enregistrer_vente_fourniture'), {
            'produit': self.produit.pk,
            'quantite': '4',
            'prix_vente_unitaire': '',
            'client': 'Parent Diallo',
            'date_vente': '2026-08-03',
            'observations': '',
        })

        self.assertRedirects(response, reverse('depenses:dashboard_fournitures'))
        vente = VenteFourniture.objects.get(produit=self.produit)
        self.assertEqual(vente.montant_total, Decimal('6000'))
        self.assertEqual(vente.marge, Decimal('2000'))

        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_vendue, 4)
        self.assertEqual(self.produit.quantite_restante, 6)
        self.assertEqual(self.produit.solde, Decimal('2000'))

        dashboard = self.client.get(reverse('depenses:dashboard_fournitures'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['resume']['quantite_vendue'], 4)
        self.assertEqual(dashboard.context['resume']['quantite_restante'], 6)
        self.assertEqual(dashboard.context['resume']['chiffre_affaires'], Decimal('6000'))
        self.assertEqual(dashboard.context['resume']['solde'], Decimal('2000'))
        self.assertContains(dashboard, 'Cahier 200 pages')

    def test_vente_superieure_au_stock_est_refusee(self):
        response = self.client.post(reverse('depenses:enregistrer_vente_fourniture'), {
            'produit': self.produit.pk,
            'quantite': '11',
            'prix_vente_unitaire': '1500',
            'client': '',
            'date_vente': '2026-08-03',
            'observations': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock restant insuffisant')
        self.assertFalse(VenteFourniture.objects.exists())

    def test_ecoles_sont_strictement_isolees(self):
        produit_externe = FournitureScolaire.objects.create(
            ecole=self.autre_ecole,
            reference='EXT-SECRET-001',
            nom='Produit confidentiel',
            quantite_stock=20,
            prix_achat_unitaire=100,
            prix_vente_unitaire=200,
        )

        dashboard = self.client.get(reverse('depenses:dashboard_fournitures'))
        self.assertNotContains(dashboard, 'Produit confidentiel')
        self.assertEqual(
            self.client.get(
                reverse('depenses:modifier_fourniture', args=[produit_externe.pk])
            ).status_code,
            404,
        )
        form = VenteFournitureForm(user=self.user)
        self.assertIn(self.produit, form.fields['produit'].queryset)
        self.assertNotIn(produit_externe, form.fields['produit'].queryset)

    def test_stock_ne_peut_pas_descendre_sous_quantite_deja_vendue(self):
        VenteFourniture.objects.create(
            ecole=self.ecole,
            produit=self.produit,
            quantite=4,
            prix_vente_unitaire=1500,
            cree_par=self.user,
        )

        response = self.client.post(
            reverse('depenses:modifier_fourniture', args=[self.produit.pk]),
            {
                'reference': self.produit.reference,
                'nom': self.produit.nom,
                'categorie': self.produit.categorie,
                'unite': self.produit.unite,
                'quantite_stock': '3',
                'stock_minimum': '1',
                'prix_achat_unitaire': '1000',
                'prix_vente_unitaire': '1500',
                'description': '',
                'actif': 'on',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'unités déjà vendues')
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite_stock, 10)
