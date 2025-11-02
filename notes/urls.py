from django.urls import path
from . import views
from .bulletin_intelligent import (
    bulletin_intelligent_view,
    bulletin_intelligent_pdf,
    bulletin_intelligent_excel
)

app_name = 'notes'

urlpatterns = [
    path('', views.tableau_bord, name='tableau_bord'),
    path('classes/', views.gerer_classes, name='gerer_classes'),
    path('classes/modifier/<int:classe_id>/', views.modifier_classe, name='modifier_classe'),
    path('classes/supprimer/<int:classe_id>/', views.supprimer_classe, name='supprimer_classe'),
    path('matieres/', views.gerer_matieres, name='gerer_matieres'),
    path('matieres/modifier/<int:matiere_id>/', views.modifier_matiere, name='modifier_matiere'),
    path('matieres/supprimer/<int:matiere_id>/', views.supprimer_matiere, name='supprimer_matiere'),
    path('matieres/charger-defaut/<int:classe_id>/', views.charger_matieres_defaut, name='charger_matieres_defaut'),
    path('evaluations/', views.gerer_evaluations, name='gerer_evaluations'),
    path('evaluations/creer/', views.creer_evaluation, name='creer_evaluation'),
    path('eleves/', views.gerer_eleves, name='gerer_eleves'),
    path('saisir/', views.saisir_notes, name='saisir_notes'),
    path('consulter/', views.consulter_notes, name='consulter_notes'),
    path('bulletins/', views.bulletin_dynamique, name='generer_bulletins'),
    path('bulletin-guineen/', views.bulletin_guineen, name='bulletin_guineen'),
    path('bulletin-dynamique/', views.bulletin_dynamique, name='bulletin_dynamique'),
    path('saisie-notes-guineen/', views.saisie_notes_simple, name='saisie_notes_guineen'),
    path('sauvegarder-notes-guineen/', views.sauvegarder_notes_guineen, name='sauvegarder_notes_guineen'),
    path('sauvegarder-appreciations-maternelle/', views.sauvegarder_appreciations_maternelle, name='sauvegarder_appreciations_maternelle'),
    path('statistiques/', views.statistiques, name='statistiques'),
    path('liste-saisie-pdf/', views.liste_saisie_pdf, name='liste_saisie_pdf'),
    path('sauvegarder-notes/', views.sauvegarder_notes, name='sauvegarder_notes'),
    
    # Bulletin Intelligent avec calculs automatiques et exports
    path('bulletin-intelligent/<int:eleve_id>/<int:classe_note_id>/<str:periode>/', 
         bulletin_intelligent_view, name='bulletin_intelligent'),
    path('bulletin-intelligent/<int:eleve_id>/<int:classe_note_id>/<str:periode>/pdf/', 
         bulletin_intelligent_pdf, name='bulletin_intelligent_pdf'),
    path('bulletin-intelligent/<int:eleve_id>/<int:classe_note_id>/<str:periode>/excel/', 
         bulletin_intelligent_excel, name='bulletin_intelligent_excel'),
]
