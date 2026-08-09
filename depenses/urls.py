from django.urls import path
from . import views
from . import views_logistique
from . import views_bibliotheque
from . import views_fournitures
from . import views_recouvrement

app_name = 'depenses'

urlpatterns = [
    # Hub Recouvrement: tableau de bord général + accès aux sous-modules
    path('', views_recouvrement.hub_recouvrement, name='tableau_bord'),

    # Tableau de bord des dépenses générales
    path('depenses/', views.tableau_bord, name='dashboard_depenses'),

    # Gestion des dépenses
    path('liste/', views.liste_depenses, name='liste_depenses'),
    path('ajouter/', views.ajouter_depense, name='ajouter_depense'),
    path('<int:depense_id>/', views.detail_depense, name='detail_depense'),
    path('<int:depense_id>/modifier/', views.modifier_depense, name='modifier_depense'),
    path('<int:depense_id>/supprimer/', views.supprimer_depense, name='supprimer_depense'),
    path('<int:depense_id>/valider/', views.valider_depense, name='valider_depense'),
    path('<int:depense_id>/marquer-payee/', views.marquer_payee, name='marquer_payee'),
    
    # Gestion des catégories
    path('categories/', views.gestion_categories, name='gestion_categories'),
    path('categories/<int:categorie_id>/modifier/', views.modifier_categorie, name='modifier_categorie'),
    path('categories/<int:categorie_id>/supprimer/', views.supprimer_categorie, name='supprimer_categorie'),
    
    # ===== RECOUVREMENT: CUISINE / DOCUMENTS / VERSEMENTS =====
    path('recouvrement/<slug:module>/', views_recouvrement.dashboard_module, name='module_recouvrement'),
    path('recouvrement/<slug:module>/nouveau/', views_recouvrement.creer_ligne_module, name='module_recouvrement_nouveau'),
    path('recouvrement/<slug:module>/<int:pk>/modifier/', views_recouvrement.modifier_ligne_module, name='module_recouvrement_modifier'),
    path('recouvrement/<slug:module>/<int:pk>/supprimer/', views_recouvrement.supprimer_ligne_module, name='module_recouvrement_supprimer'),
    path('recouvrement/<slug:module>/export/excel/', views_recouvrement.export_module_excel, name='module_recouvrement_export_excel'),
    path('recouvrement/<slug:module>/export/pdf/', views_recouvrement.export_module_pdf, name='module_recouvrement_export_pdf'),

    # ===== RECOUVREMENT: INFORMATIQUE =====
    path('informatique/', views_recouvrement.dashboard_informatique, name='dashboard_informatique'),
    path('informatique/nouveau/', views_recouvrement.creer_abonnement_informatique, name='creer_abonnement_informatique'),
    path('informatique/<int:pk>/modifier/', views_recouvrement.modifier_abonnement_informatique, name='modifier_abonnement_informatique'),
    path('informatique/<int:pk>/supprimer/', views_recouvrement.supprimer_abonnement_informatique, name='supprimer_abonnement_informatique'),
    path('informatique/<int:pk>/carte/', views_recouvrement.carte_abonnement_informatique, name='carte_abonnement_informatique'),
    path('informatique/export/excel/', views_recouvrement.export_informatique_excel, name='export_informatique_excel'),
    path('informatique/export/pdf/', views_recouvrement.export_informatique_pdf, name='export_informatique_pdf'),
    path('informatique/api/eleve/<int:eleve_id>/', views_recouvrement.api_eleve_informatique, name='api_eleve_informatique'),

    # ===== RECOUVREMENT: SALAIRES ENSEIGNANTS =====
    path('salaires/', views_recouvrement.dashboard_salaires, name='dashboard_salaires'),
    path('salaires/export/excel/', views_recouvrement.export_salaires_excel, name='export_salaires_excel'),

    # ===== LOGISTIQUE =====
    path('logistique/', views_logistique.dashboard_logistique, name='dashboard_logistique'),
    path('logistique/biens/', views_logistique.liste_biens, name='liste_biens'),
    path('logistique/biens/nouveau/', views_logistique.creer_bien, name='creer_bien'),
    path('logistique/biens/<int:bien_id>/modifier/', views_logistique.modifier_bien, name='modifier_bien'),
    path('logistique/rames/', views_logistique.liste_contributions_rames, name='liste_contributions_rames'),
    path('logistique/rames/nouveau/', views_logistique.ajouter_contribution_rame, name='ajouter_contribution_rame'),
    path('logistique/rames/<int:contribution_id>/modifier/', views_logistique.modifier_contribution_rame, name='modifier_contribution_rame'),

    # ===== FOURNITURES SCOLAIRES =====
    path('fournitures/', views_fournitures.dashboard_fournitures, name='dashboard_fournitures'),
    path('fournitures/produits/nouveau/', views_fournitures.creer_fourniture, name='creer_fourniture'),
    path('fournitures/produits/<int:produit_id>/modifier/', views_fournitures.modifier_fourniture, name='modifier_fourniture'),
    path('fournitures/ventes/', views_fournitures.liste_ventes_fournitures, name='liste_ventes_fournitures'),
    path('fournitures/ventes/nouvelle/', views_fournitures.enregistrer_vente_fourniture, name='enregistrer_vente_fourniture'),
    
    # ===== BIBLIOTHÈQUE =====
    path('bibliotheque/', views_bibliotheque.dashboard_bibliotheque, name='dashboard_bibliotheque'),
    path('bibliotheque/catalogue/', views_bibliotheque.catalogue_livres, name='catalogue_livres'),
    path('bibliotheque/catalogue/nouveau/', views_bibliotheque.creer_livre, name='creer_livre'),
    path('bibliotheque/catalogue/<int:livre_id>/modifier/', views_bibliotheque.modifier_livre, name='modifier_livre'),
    path('bibliotheque/catalogue/<int:livre_id>/supprimer/', views_bibliotheque.supprimer_livre, name='supprimer_livre'),
    path('bibliotheque/categories/', views_bibliotheque.gestion_categories_livres, name='gestion_categories_livres'),
    path('bibliotheque/categories/<int:categorie_id>/modifier/', views_bibliotheque.modifier_categorie_livre, name='modifier_categorie_livre'),
    path('bibliotheque/categories/<int:categorie_id>/supprimer/', views_bibliotheque.supprimer_categorie_livre, name='supprimer_categorie_livre'),
    path('bibliotheque/emprunts/', views_bibliotheque.liste_emprunts, name='liste_emprunts'),
    path('bibliotheque/emprunts/nouveau/', views_bibliotheque.creer_emprunt, name='creer_emprunt'),
    path('bibliotheque/emprunts/<int:emprunt_id>/retour/', views_bibliotheque.retourner_livre, name='retourner_livre'),
    path('bibliotheque/reservations/', views_bibliotheque.liste_reservations, name='liste_reservations'),
    path('bibliotheque/statistiques/', views_bibliotheque.statistiques_bibliotheque, name='statistiques_bibliotheque'),
]
