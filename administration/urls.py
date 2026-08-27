from django.urls import path
from . import views
from bus import views as bus_views

app_name = 'administration'

urlpatterns = [
    # Tableau de bord principal
    path('', views.dashboard, name='dashboard'),

    # Grilles tarifaires du transport scolaire (séparées par école)
    path('grilles-bus/', bus_views.grilles_bus, name='grilles_bus'),
    path('grilles-bus/nouvelle/', bus_views.grille_bus_form, name='grille_bus_nouvelle'),
    path('grilles-bus/<int:grille_id>/modifier/', bus_views.grille_bus_form, name='grille_bus_modifier'),
    path('grilles-bus/<int:grille_id>/basculer/', bus_views.basculer_grille_bus, name='grille_bus_basculer'),
    
    # Gestion des utilisateurs
    path('users/', views.users_management, name='users_management'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    
    # Statistiques et monitoring
    path('stats/', views.system_stats, name='system_stats'),
    path('logs/', views.system_logs, name='system_logs'),
    
    # Actions système
    path('maintenance/toggle/', views.toggle_maintenance, name='toggle_maintenance'),
    path('logs/clear/', views.clear_old_logs, name='clear_old_logs'),
    path('ecoles/<int:ecole_id>/valider/', views.valider_ecole, name='valider_ecole'),
    path('ecoles/<int:ecole_id>/rejeter/', views.rejeter_ecole, name='rejeter_ecole'),
    path('users/<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:user_id>/toggle-staff/', views.user_toggle_staff, name='user_toggle_staff'),
    path('users/<int:user_id>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('users/<int:user_id>/activate-and-validate/', views.user_activate_and_validate, name='user_activate_and_validate'),
    
    # Corbeille et restauration
    path('corbeille/', views.corbeille_list, name='corbeille_list'),
    path('corbeille/restaurer/<int:log_id>/', views.restaurer_element, name='restaurer_element'),

    # Corbeille des élèves supprimés
    path('corbeille/eleves/', views.corbeille_eleves, name='corbeille_eleves'),
    path('corbeille/eleves/<int:corbeille_id>/restaurer/', views.restaurer_eleve_corbeille, name='restaurer_eleve_corbeille'),
    path('corbeille/eleves/<int:corbeille_id>/purger/', views.purger_eleve_corbeille, name='purger_eleve_corbeille'),

    # Corbeille des paiements, échéanciers, abonnements...
    path('corbeille/elements/', views.corbeille_elements, name='corbeille_elements'),
    path('corbeille/elements/<int:corbeille_id>/restaurer/', views.restaurer_element_corbeille, name='restaurer_element_corbeille'),
    path('corbeille/elements/<int:corbeille_id>/purger/', views.purger_element_corbeille, name='purger_element_corbeille'),

    # Corbeille mémoire des modifications
    path('journal-modifications/', views.journal_modifications, name='journal_modifications'),
]
