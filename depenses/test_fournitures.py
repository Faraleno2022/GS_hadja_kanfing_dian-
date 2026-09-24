from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Ecole
from paiements.tests.support import MIDDLEWARE_SANS_LICENCE
from utilisateurs.models import Profil
from depenses.forms import VenteFournitureForm
from depenses.models_logistique import Article, CategorieArticle, MouvementStock


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class FournituresScolairesTests(TestCase):
    def setUp(self):
        self.ecole = Ecole.objects.create(nom='École Fournitures', adresse='Conakry', telephone='+224620200001', directeur='Direction')
        self.autre_ecole = Ecole.objects.create(nom='École Externe', adresse='Conakry', telephone='+224620200002', directeur='Direction')
        self.user = get_user_model().objects.create_user('vendeur', password='test-pass')
        self.autre_user = get_user_model().objects.create_user('vendeur-externe', password='test-pass')
        for user, ecole in ((self.user, self.ecole), (self.autre_user, self.autre_ecole)):
            Profil.objects.filter(user=user).update(role='COMPTABLE', ecole=ecole)
            user.refresh_from_db()
        self.client.force_login(self.user)
        self.categorie = CategorieArticle.objects.create(nom='Fournitures', code='FOU-TEST', type_categorie='FOURNITURE')
        self.produit = Article.objects.create(
            code_article='FOU-CAH-001', nom='Cahier 200 pages', categorie=self.categorie,
            prix_unitaire=1000, prix_vente_unitaire=1500, cree_par=self.user,
        )
        MouvementStock.objects.create(
            numero_mouvement='ENTREE-FOU-001', article=self.produit, type_mouvement='ENTREE',
            motif='ACHAT', quantite=10, prix_unitaire=1000, cree_par=self.user,
        )

    def _article_data(self, **changes):
        data = {
            'code_article': '', 'nom': 'Stylo bleu', 'categorie': self.categorie.pk,
            'unite_mesure': 'PIECE', 'stock_initial': 50, 'stock_minimum': 2,
            'stock_maximum': 100, 'prix_unitaire': 2000, 'prix_vente_unitaire': 3000,
            'etat': 'NEUF', 'emplacement': 'Magasin',
        }
        data.update(changes)
        return data

    def _vente(self, quantite, article=None):
        return self.client.post(reverse('depenses:creer_vente_fourniture'), {
            'article': (article or self.produit).pk, 'quantite': quantite,
            'prix_vente_unitaire': '', 'acheteur': 'Parent Diallo',
        })

    def test_ajout_produit_rattache_ecole_et_genere_reference(self):
        response = self.client.post(reverse('depenses:creer_article'), self._article_data())
        self.assertRedirects(response, reverse('depenses:liste_articles'))
        produit = Article.objects.get(nom='Stylo bleu')
        self.assertEqual(produit.cree_par.profil.ecole_id, self.ecole.pk)
        self.assertTrue(produit.code_article)
        self.assertEqual(produit.stock_actuel, 50)
        self.assertEqual(produit.mouvements.get().montant_total, Decimal('100000'))

    def test_vente_met_a_jour_reste_chiffre_affaires_et_solde(self):
        self.assertRedirects(self._vente(4), reverse('depenses:liste_articles'))
        vente = self.produit.mouvements.get(motif='VENTE')
        self.assertEqual(vente.montant_total, Decimal('6000'))
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.stock_actuel, 6)
        dashboard = self.client.get(reverse('depenses:liste_articles'))
        self.assertEqual(dashboard.status_code, 200)
        for key, value in {'quantite_vendue': 4, 'quantite_restante': 6, 'chiffre_affaires': Decimal('6000'), 'solde': Decimal('2000')}.items():
            self.assertEqual(dashboard.context['stats'][key], value)
        self.assertContains(dashboard, self.produit.nom)

    def test_vente_superieure_au_stock_est_refusee(self):
        response = self._vente(11)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock insuffisant')
        self.assertFalse(self.produit.mouvements.filter(motif='VENTE').exists())
        self.assertEqual(self.produit.stock_actuel, 10)

    def test_ecoles_sont_strictement_isolees(self):
        produit = Article.objects.create(code_article='EXT-SECRET', nom='Produit confidentiel', categorie=self.categorie, prix_unitaire=100, prix_vente_unitaire=200, cree_par=self.autre_user)
        self.assertNotContains(self.client.get(reverse('depenses:liste_articles')), produit.nom)
        self.assertEqual(self.client.get(reverse('depenses:modifier_article', args=[produit.pk])).status_code, 404)
        form = VenteFournitureForm(user=self.user)
        self.assertIn(self.produit, form.fields['article'].queryset)
        self.assertNotIn(produit, form.fields['article'].queryset)
        self.assertEqual(self._vente(1, produit).status_code, 200)
        self.assertFalse(produit.mouvements.filter(motif='VENTE').exists())

    def test_modifier_produit_ne_remplace_pas_le_journal_de_stock(self):
        self.assertRedirects(self._vente(4), reverse('depenses:liste_articles'))
        response = self.client.post(reverse('depenses:modifier_article', args=[self.produit.pk]), self._article_data(
            code_article=self.produit.code_article, nom=self.produit.nom, stock_initial=3,
            prix_unitaire=1000, prix_vente_unitaire=1500,
        ))
        self.assertRedirects(response, reverse('depenses:liste_articles'))
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.stock_actuel, 6)
        self.assertEqual(self.produit.mouvements.count(), 2)
