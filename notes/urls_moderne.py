"""
URLs modernes pour le module de gestion des notes
Interface simplifiée et intuitive
"""

from django.urls import path
from . import views_moderne

app_name = 'notes_moderne'

urlpatterns = [
    # Dashboard principal
    path('', views_moderne.dashboard_moderne, name='dashboard'),
    
    # Saisie des notes
    path('saisie/<int:evaluation_id>/', views_moderne.saisie_notes_moderne, name='saisie_notes'),
    
    # Classements
    path('classement/<int:classe_id>/', views_moderne.classement_moderne, name='classement'),
    path('classement/<int:classe_id>/<str:trimestre>/', views_moderne.classement_moderne, name='classement_trimestre'),
    
    # Gestion des matières
    path('matieres/', views_moderne.gestion_matieres_moderne, name='gestion_matieres'),
    path('matieres/<int:classe_id>/', views_moderne.gestion_matieres_moderne, name='matieres_classe'),
    
    # API AJAX
    path('api/stats/', views_moderne.ajax_stats_notes, name='ajax_stats'),
]
