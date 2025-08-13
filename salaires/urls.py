from django.urls import path
from . import views

app_name = 'salaires'

urlpatterns = [
    # Tableau de bord
    path('', views.tableau_bord, name='tableau_bord'),
    
    # Gestion des enseignants
    path('enseignants/', views.liste_enseignants, name='liste_enseignants'),
    path('enseignants/export/csv/', views.export_enseignants_csv, name='export_enseignants_csv'),
    path('enseignants/export/pdf/', views.export_enseignants_pdf, name='export_enseignants_pdf'),
    path('enseignants/ajouter/', views.ajouter_enseignant, name='ajouter_enseignant'),
    path('enseignants/<int:enseignant_id>/', views.detail_enseignant, name='detail_enseignant'),
    path('enseignants/<int:enseignant_id>/modifier/', views.modifier_enseignant, name='modifier_enseignant'),
    path('enseignants/<int:enseignant_id>/supprimer/', views.supprimer_enseignant, name='supprimer_enseignant'),
    # Affectations de classes
    path('enseignants/<int:enseignant_id>/affectations/ajouter/', views.ajouter_affectation, name='ajouter_affectation'),
    path('enseignants/affectations/<int:affectation_id>/clore/', views.clore_affectation, name='clore_affectation'),
    path('enseignants/affectations/<int:affectation_id>/supprimer/', views.supprimer_affectation, name='supprimer_affectation'),
    
    # États de salaire
    path('etats/', views.etats_salaire, name='etats_salaire'),
    path('etats/export/csv/', views.export_etats_salaire_csv, name='export_etats_salaire_csv'),
    path('etats/export/pdf/', views.export_etats_salaire_pdf, name='export_etats_salaire_pdf'),
    path('calculer/<int:periode_id>/', views.calculer_salaires, name='calculer_salaires'),
    path('valider/<int:etat_id>/', views.valider_etat_salaire, name='valider_etat_salaire'),
    path('marquer-paye/<int:etat_id>/', views.marquer_paye, name='marquer_paye'),
    
    # Gestion des périodes
    path('periodes/', views.gestion_periodes, name='gestion_periodes'),
    path('periodes/creer/', views.creer_periode, name='creer_periode'),
    path('periodes/cloturer/<int:periode_id>/', views.cloturer_periode, name='cloturer_periode'),

    # Rapport paiements (totaux par mois/année)
    path('rapport/paiements/', views.rapport_paiements, name='rapport_paiements'),
    path('rapport/paiements/export/pdf/', views.export_rapport_paiements_pdf, name='export_rapport_paiements_pdf'),

    # Actions sur les enseignants
    path('enseignants/changer-statut/<int:enseignant_id>/', views.changer_statut_enseignant, name='changer_statut_enseignant'),
]
