from django.urls import path
from . import views

app_name = 'abonnements'

urlpatterns = [
    # Tableau de bord
    path('', views.tableau_bord_abonnements, name='tableau_bord'),
    
    # Bus
    path('bus/', views.liste_abonnements_bus, name='liste_bus'),
    path('bus/nouveau/', views.creer_abonnement_bus, name='creer_bus'),
    
    # Cantine
    path('cantine/', views.liste_abonnements_cantine, name='liste_cantine'),
    path('cantine/nouveau/', views.creer_abonnement_cantine, name='creer_cantine'),
    path('cantine/presences/', views.gerer_presences_cantine, name='presences_cantine'),
    path('cantine/presences/enregistrer/', views.enregistrer_presence_cantine, name='enregistrer_presence'),
]
