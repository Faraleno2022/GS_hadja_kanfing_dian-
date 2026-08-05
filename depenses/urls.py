from django.urls import path
from . import views
from . import views_logistique
from . import views_bibliotheque
from . import views_recouvrement

app_name = 'depenses'

urlpatterns = [
    # Tableau de bord général du menu Recouvrement (vue d'ensemble en cartes)
    path('', views_recouvrement.tableau_bord_general, name='tableau_bord'),

    # ===== RECOUVREMENT : Dépenses courantes (ancien tableau de bord) =====
    path('courantes/', views.dashboard_courantes, name='dashboard_courantes'),

    # ===== RECOUVREMENT : Cuisine / Document / Versement (modules génériques) =====
    path('recouvrement/<str:cle>/', views_recouvrement.liste_module_simple, name='liste_module_simple'),
    path('recouvrement/<str:cle>/tableau-de-bord/', views_recouvrement.dashboard_module_simple, name='dashboard_module_simple'),
    path('recouvrement/<str:cle>/ajouter/', views_recouvrement.ajouter_module_simple, name='ajouter_module_simple'),
    path('recouvrement/<str:cle>/<int:pk>/modifier/', views_recouvrement.modifier_module_simple, name='modifier_module_simple'),
    path('recouvrement/<str:cle>/<int:pk>/supprimer/', views_recouvrement.supprimer_module_simple, name='supprimer_module_simple'),
    path('recouvrement/<str:cle>/export/excel/', views_recouvrement.export_module_simple_excel, name='export_module_simple_excel'),
    path('recouvrement/<str:cle>/export/pdf/', views_recouvrement.export_module_simple_pdf, name='export_module_simple_pdf'),

    # ===== RECOUVREMENT : Informatique (abonnements élèves) =====
    path('informatique/', views_recouvrement.liste_abonnements_informatique, name='liste_abonnements_informatique'),
    path('informatique/tableau-de-bord/', views_recouvrement.dashboard_informatique, name='dashboard_informatique'),
    path('informatique/recherche-eleve/', views_recouvrement.recherche_eleve_informatique, name='recherche_eleve_informatique'),
    path('informatique/ajouter/', views_recouvrement.ajouter_abonnement_informatique, name='ajouter_abonnement_informatique'),
    path('informatique/<int:pk>/modifier/', views_recouvrement.modifier_abonnement_informatique, name='modifier_abonnement_informatique'),
    path('informatique/<int:pk>/supprimer/', views_recouvrement.supprimer_abonnement_informatique, name='supprimer_abonnement_informatique'),
    path('informatique/<int:pk>/carte/pdf/', views_recouvrement.carte_abonnement_informatique_pdf, name='carte_abonnement_informatique_pdf'),
    path('informatique/export/excel/', views_recouvrement.export_informatique_excel, name='export_informatique_excel'),
    path('informatique/export/pdf/', views_recouvrement.export_informatique_pdf, name='export_informatique_pdf'),

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
    
    # ===== LOGISTIQUE =====
    path('logistique/', views_logistique.dashboard_logistique, name='dashboard_logistique'),
    path('logistique/biens/', views_logistique.liste_biens, name='liste_biens'),
    path('logistique/biens/nouveau/', views_logistique.creer_bien, name='creer_bien'),
    path('logistique/biens/<int:bien_id>/modifier/', views_logistique.modifier_bien, name='modifier_bien'),
    path('logistique/papier-ram/', views_logistique.liste_contributions_papier, name='liste_contributions_papier'),
    path('logistique/papier-ram/nouveau/', views_logistique.creer_contribution_papier, name='creer_contribution_papier'),
    path('logistique/papier-ram/<int:contribution_id>/modifier/', views_logistique.modifier_contribution_papier, name='modifier_contribution_papier'),

    # Gestion et vente des fournitures scolaires
    path('fournitures/', views_logistique.liste_articles, name='liste_articles'),
    path('fournitures/produits/nouveau/', views_logistique.creer_article, name='creer_article'),
    path('fournitures/produits/<int:article_id>/', views_logistique.detail_article, name='detail_article'),
    path('fournitures/produits/<int:article_id>/modifier/', views_logistique.modifier_article, name='modifier_article'),
    path('fournitures/produits/<int:article_id>/archiver/', views_logistique.supprimer_article, name='supprimer_article'),
    path('fournitures/ventes/nouvelle/', views_logistique.creer_vente_fourniture, name='creer_vente_fourniture'),
    path('fournitures/mouvements/', views_logistique.liste_mouvements, name='liste_mouvements'),
    path('fournitures/mouvements/nouveau/', views_logistique.creer_mouvement, name='creer_mouvement'),
    path('fournitures/export/excel/', views_logistique.export_stock_excel, name='export_stock_excel'),

    # Compatibilité : les anciens favoris sont redirigés vers le module simplifié.
    path('logistique/articles/', views_logistique.liste_articles, name='liste_articles_legacy'),
    path('logistique/articles/nouveau/', views_logistique.creer_article, name='creer_article_legacy'),
    path('logistique/articles/<int:article_id>/', views_logistique.detail_article, name='detail_article_legacy'),
    path('logistique/articles/<int:article_id>/modifier/', views_logistique.modifier_article, name='modifier_article_legacy'),
    path('logistique/articles/<int:article_id>/supprimer/', views_logistique.supprimer_article, name='supprimer_article_legacy'),
    path('logistique/categories/', views_logistique.ancienne_logistique_redirection, name='gestion_categories_articles'),
    path('logistique/categories/<int:categorie_id>/modifier/', views_logistique.ancienne_logistique_redirection, name='modifier_categorie_article'),
    path('logistique/mouvements/', views_logistique.liste_mouvements, name='liste_mouvements_legacy'),
    path('logistique/mouvements/nouveau/', views_logistique.creer_mouvement, name='creer_mouvement_legacy'),
    path('logistique/inventaires/', views_logistique.ancienne_logistique_redirection, name='liste_inventaires'),
    path('logistique/inventaires/nouveau/', views_logistique.ancienne_logistique_redirection, name='creer_inventaire'),
    path('logistique/inventaires/<int:inventaire_id>/', views_logistique.ancienne_logistique_redirection, name='detail_inventaire'),
    path('logistique/inventaires/<int:inventaire_id>/valider/', views_logistique.ancienne_logistique_redirection, name='valider_inventaire'),
    path('logistique/export/excel/', views_logistique.export_stock_excel, name='export_stock_excel_legacy'),
    
    # ===== BIBLIOTHÈQUE =====
    path('bibliotheque/', views_bibliotheque.dashboard_bibliotheque, name='dashboard_bibliotheque'),
    path('bibliotheque/catalogue/', views_bibliotheque.catalogue_livres, name='catalogue_livres'),
    path('bibliotheque/livres/ajouter/', views_bibliotheque.ajouter_livre, name='ajouter_livre'),
    path('bibliotheque/livres/<int:livre_id>/modifier/', views_bibliotheque.modifier_livre, name='modifier_livre'),
    path('bibliotheque/livres/<int:livre_id>/supprimer/', views_bibliotheque.supprimer_livre, name='supprimer_livre'),
    path('bibliotheque/categories/', views_bibliotheque.gestion_categories_livres, name='gestion_categories_livres'),
    path('bibliotheque/categories/<int:categorie_id>/modifier/', views_bibliotheque.modifier_categorie_livre, name='modifier_categorie_livre'),
    path('bibliotheque/categories/<int:categorie_id>/supprimer/', views_bibliotheque.supprimer_categorie_livre, name='supprimer_categorie_livre'),
    path('bibliotheque/emprunts/', views_bibliotheque.liste_emprunts, name='liste_emprunts'),
    path('bibliotheque/emprunts/nouveau/', views_bibliotheque.creer_emprunt, name='creer_emprunt'),
    path('bibliotheque/emprunts/<int:emprunt_id>/retour/', views_bibliotheque.retourner_livre, name='retourner_livre'),
    path('bibliotheque/reservations/', views_bibliotheque.liste_reservations, name='liste_reservations'),
    path('bibliotheque/reservations/nouvelle/', views_bibliotheque.creer_reservation, name='creer_reservation'),
    path('bibliotheque/reservations/<int:reservation_id>/annuler/', views_bibliotheque.annuler_reservation, name='annuler_reservation'),
    path('bibliotheque/reservations/<int:reservation_id>/emprunter/', views_bibliotheque.emprunter_reservation, name='emprunter_reservation'),
    path('bibliotheque/statistiques/', views_bibliotheque.statistiques_bibliotheque, name='statistiques_bibliotheque'),
]
