from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from eleves.models import Classe, Ecole, Eleve
from utilisateurs.models import Profil

from .forms import BienEtablissementForm, ContributionPapierRameForm
from .models_logistique import (
    Article,
    BienEtablissement,
    CategorieArticle,
    ContributionPapierRame,
    MouvementStock,
)


MIDDLEWARE_SANS_LICENCE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != 'ecole_moderne.licence_middleware.LicenceMiddleware'
]


@override_settings(MIDDLEWARE=MIDDLEWARE_SANS_LICENCE)
class LogistiqueSimplifieeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.ecole = Ecole.objects.create(
            nom='École logistique', adresse='Conakry', telephone='+224622000011',
            email='logistique@ecole.local', directeur='Direction', etat='VALIDE',
        )
        self.autre_ecole = Ecole.objects.create(
            nom='Autre école', adresse='Conakry', telephone='+224622000012',
            email='autre@ecole.local', directeur='Direction', etat='VALIDE',
        )
        self.classe = Classe.objects.create(
            ecole=self.ecole, nom='6e A', niveau='PRIMAIRE_6',
            annee_scolaire='2026-2027', capacite_max=40,
        )
        self.autre_classe = Classe.objects.create(
            ecole=self.autre_ecole, nom='6e B', niveau='PRIMAIRE_6',
            annee_scolaire='2026-2027', capacite_max=40,
        )
        self.user = User.objects.create_user('logistique', password='secret')
        self.autre_user = User.objects.create_user('autre_logistique', password='secret')
        Profil.objects.filter(user=self.user).update(
            role='ADMIN', telephone='+224622000013', ecole=self.ecole,
            actif=True, is_validated=True,
        )
        Profil.objects.filter(user=self.autre_user).update(
            role='ADMIN', telephone='+224622000014', ecole=self.autre_ecole,
            actif=True, is_validated=True,
        )
        self.user.refresh_from_db()
        self.autre_user.refresh_from_db()
        self.eleve = Eleve.objects.create(
            matricule='LOG-001', prenom='Aïssatou', nom='Diallo', sexe='F',
            classe=self.classe, statut='ACTIF', cree_par=self.user,
        )
        self.autre_eleve = Eleve.objects.create(
            matricule='AUT-001', prenom='Mamadou', nom='Bah', sexe='M',
            classe=self.autre_classe, statut='ACTIF', cree_par=self.autre_user,
        )
        self.client.force_login(self.user)
        self.categorie_fournitures = CategorieArticle.objects.create(
            nom='Fournitures scolaires',
            code='FOURN-TEST',
            type_categorie='FOURNITURE',
        )

    def creer_fourniture(self, *, code='FOUR-001', nom='Cahier', user=None):
        return Article.objects.create(
            code_article=code,
            nom=nom,
            categorie=self.categorie_fournitures,
            stock_minimum=2,
            stock_maximum=100,
            prix_unitaire=Decimal('5000'),
            prix_vente_unitaire=Decimal('7500'),
            cree_par=user or self.user,
        )

    def test_calcul_des_quantites_et_de_la_valeur_du_bien(self):
        bien = BienEtablissement.objects.create(
            code_bien='BIEN-TEST-001', nom='Tables', type_bien='TABLE',
            localisation='Salle 1', quantite_achetee=25, quantite_utilisee=18,
            quantite_gatee=2, prix_achat_unitaire=Decimal('150000'),
            cree_par=self.user,
        )

        self.assertEqual(bien.quantite_disponible, 5)
        self.assertEqual(bien.valeur_totale_achat, Decimal('3750000'))

    def test_formulaire_refuse_un_usage_superieur_a_la_quantite_achetee(self):
        form = BienEtablissementForm(data={
            'code_bien': '', 'nom': 'Marqueurs', 'type_bien': 'MARQUEUR',
            'localisation': 'Magasin', 'unite_mesure': 'BOITE',
            'quantite_achetee': 10, 'quantite_utilisee': 8, 'quantite_gatee': 3,
            'prix_achat_unitaire': 50000, 'etat': 'BON', 'date_acquisition': '',
            'observations': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('ne peuvent pas dépasser', str(form.non_field_errors()))

    def test_ajout_dun_bien_enregistre_quantites_et_prix(self):
        response = self.client.post(reverse('depenses:creer_bien'), {
            'code_bien': '', 'nom': 'Boîtes de marqueurs',
            'type_bien': 'MARQUEUR', 'localisation': 'Magasin',
            'unite_mesure': 'BOITE', 'quantite_achetee': 12,
            'quantite_utilisee': 7, 'quantite_gatee': 1,
            'prix_achat_unitaire': 50000, 'etat': 'BON',
            'date_acquisition': '2026-08-02', 'observations': '',
        })

        self.assertRedirects(response, reverse('depenses:liste_biens'))
        bien = BienEtablissement.objects.get(nom='Boîtes de marqueurs')
        self.assertEqual(bien.quantite_disponible, 4)
        self.assertEqual(bien.valeur_acquisition, Decimal('600000'))

    def test_formulaire_papier_ne_propose_que_les_eleves_de_lecole(self):
        form = ContributionPapierRameForm(
            user=self.user,
            annee_scolaire='2026-2027',
        )

        self.assertIn(self.eleve, form.fields['eleve'].queryset)
        self.assertNotIn(self.autre_eleve, form.fields['eleve'].queryset)

    def test_contribution_papier_et_paiement_sont_exclusifs(self):
        papier = ContributionPapierRameForm(data={
            'eleve': self.eleve.pk, 'type_contribution': 'PAPIER',
            'nombre_paquets': 3, 'montant_paye': 100000,
            'date_contribution': '2026-08-02', 'observations': '',
        }, user=self.user, annee_scolaire='2026-2027')
        self.assertTrue(papier.is_valid(), papier.errors)
        self.assertEqual(papier.cleaned_data['montant_paye'], Decimal('0'))

        argent = ContributionPapierRameForm(data={
            'eleve': self.eleve.pk, 'type_contribution': 'ARGENT',
            'nombre_paquets': 4, 'montant_paye': 125000,
            'date_contribution': '2026-08-02', 'observations': '',
        }, user=self.user, annee_scolaire='2026-2027')
        self.assertTrue(argent.is_valid(), argent.errors)
        self.assertEqual(argent.cleaned_data['nombre_paquets'], 0)

    def test_creation_et_tableau_de_bord_papier_ram(self):
        response = self.client.post(reverse('depenses:creer_contribution_papier'), {
            'eleve': self.eleve.pk, 'type_contribution': 'ARGENT',
            'nombre_paquets': 0, 'montant_paye': 75000,
            'date_contribution': '2026-08-02', 'observations': 'Payé à la place',
        })

        self.assertRedirects(response, reverse('depenses:liste_contributions_papier'))
        contribution = ContributionPapierRame.objects.get()
        self.assertEqual(contribution.eleve, self.eleve)
        self.assertEqual(contribution.montant_paye, Decimal('75000'))
        dashboard = self.client.get(reverse('depenses:dashboard_logistique'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.context['stats_papier']['total_argent'], Decimal('75000'))
        self.assertContains(dashboard, self.eleve.nom_complet)

    def test_les_donnees_des_autres_ecoles_sont_masquees(self):
        ContributionPapierRame.objects.create(
            eleve=self.autre_eleve, type_contribution='PAPIER', nombre_paquets=2,
            montant_paye=0, cree_par=self.autre_user,
        )

        response = self.client.get(reverse('depenses:liste_contributions_papier'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Mamadou Bah')

    def test_recherche_papier_ram_par_matricule(self):
        ContributionPapierRame.objects.create(
            eleve=self.eleve, type_contribution='PAPIER', nombre_paquets=2,
            montant_paye=0, cree_par=self.user,
        )

        response = self.client.get(
            reverse('depenses:liste_contributions_papier'),
            {'q': 'LOG-001'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['total_enregistrements'], 1)
        self.assertContains(response, 'LOG-001')

    def test_les_nouveaux_ecrans_se_rendent_correctement(self):
        for url_name in ('liste_biens', 'creer_bien', 'creer_contribution_papier'):
            response = self.client.get(reverse(f'depenses:{url_name}'))
            self.assertEqual(response.status_code, 200)

    def test_module_fournitures_est_accessible_et_inventaire_reste_redirige(self):
        for url_name in ('liste_articles', 'liste_mouvements'):
            response = self.client.get(reverse(f'depenses:{url_name}'))
            self.assertEqual(response.status_code, 200)

        for url_name in ('liste_inventaires',):
            response = self.client.get(reverse(f'depenses:{url_name}'))
            self.assertRedirects(response, reverse('depenses:dashboard_logistique'))

    def test_creation_produit_avec_stock_initial(self):
        response = self.client.post(reverse('depenses:creer_article'), {
            'code_article': 'STYLO-001',
            'nom': 'Stylo bleu',
            'categorie': self.categorie_fournitures.pk,
            'description': '',
            'marque': '',
            'reference': '',
            'unite_mesure': 'PIECE',
            'stock_minimum': 5,
            'stock_maximum': 100,
            'prix_unitaire': 2000,
            'prix_vente_unitaire': 3000,
            'stock_initial': 20,
            'etat': 'NEUF',
            'emplacement': 'Magasin',
        })

        self.assertRedirects(response, reverse('depenses:liste_articles'))
        article = Article.objects.get(code_article='STYLO-001')
        self.assertEqual(article.stock_actuel, 20)
        mouvement = article.mouvements.get()
        self.assertEqual(mouvement.type_mouvement, 'ENTREE')
        self.assertEqual(mouvement.quantite, 20)

    def test_vente_met_a_jour_stock_et_tableau_de_bord(self):
        article = self.creer_fourniture()
        MouvementStock.objects.create(
            numero_mouvement='MVT-ENTREE-001',
            article=article,
            type_mouvement='ENTREE',
            motif='ACHAT',
            quantite=10,
            prix_unitaire=article.prix_unitaire,
            cree_par=self.user,
        )

        response = self.client.post(reverse('depenses:creer_vente_fourniture'), {
            'article': article.pk,
            'quantite': 3,
            'prix_vente_unitaire': 7500,
            'acheteur': 'Parent Eleve',
            'document_reference': 'REC-001',
            'observations': '',
        })

        self.assertRedirects(response, reverse('depenses:liste_articles'))
        article.refresh_from_db()
        self.assertEqual(article.stock_actuel, 7)
        vente = article.mouvements.get(motif='VENTE')
        self.assertEqual(vente.montant_total, Decimal('22500'))
        dashboard = self.client.get(reverse('depenses:liste_articles'))
        self.assertEqual(dashboard.context['stats']['quantite_vendue'], 3)
        self.assertEqual(dashboard.context['stats']['quantite_restante'], 7)
        self.assertEqual(dashboard.context['stats']['chiffre_affaires'], Decimal('22500'))
        self.assertEqual(dashboard.context['stats']['solde'], Decimal('7500'))

    def test_vente_refuse_un_stock_insuffisant(self):
        article = self.creer_fourniture()
        MouvementStock.objects.create(
            numero_mouvement='MVT-ENTREE-002',
            article=article,
            type_mouvement='ENTREE',
            motif='ACHAT',
            quantite=2,
            prix_unitaire=article.prix_unitaire,
            cree_par=self.user,
        )

        response = self.client.post(reverse('depenses:creer_vente_fourniture'), {
            'article': article.pk,
            'quantite': 3,
            'prix_vente_unitaire': 7500,
            'acheteur': '',
            'document_reference': '',
            'observations': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Stock insuffisant')
        article.refresh_from_db()
        self.assertEqual(article.stock_actuel, 2)
        self.assertFalse(article.mouvements.filter(motif='VENTE').exists())

    def test_fournitures_des_autres_ecoles_sont_masquees(self):
        self.creer_fourniture(code='ECOLE-001', nom='Cahier visible')
        self.creer_fourniture(
            code='AUTRE-001',
            nom='Produit autre ecole',
            user=self.autre_user,
        )

        response = self.client.get(reverse('depenses:liste_articles'))

        self.assertContains(response, 'Cahier visible')
        self.assertNotContains(response, 'Produit autre ecole')
