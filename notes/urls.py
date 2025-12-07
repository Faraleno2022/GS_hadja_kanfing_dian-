from django.urls import path
from . import views
from .bulletin_intelligent import (
    bulletin_intelligent_view,
    bulletin_intelligent_pdf,
    bulletin_intelligent_excel,
    bulletins_classe_pdf
)
from .views_import import (
    importer_notes,
    telecharger_template_import,
    get_matieres_classe,
    get_evaluations_matiere
)
from .whatsapp_bulletin import envoyer_bulletin_whatsapp, apercu_message_whatsapp
from .export_resultats import exporter_resultats_pdf, exporter_resultats_excel
from .export_notes_complet import exporter_notes_complet_pdf, exporter_notes_complet_excel
from .bulletin_public import bulletin_public_pdf
from .export_statistiques_pdf import exporter_statistiques_pdf, exporter_conseils_pdf

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
    path('supprimer-notes/', views.supprimer_notes, name='supprimer_notes'),
    path('imprimer-tableau-notes-pdf/', views.imprimer_tableau_notes_pdf, name='imprimer_tableau_notes_pdf'),
    path('imprimer-tableau-notes-html/', views.imprimer_tableau_notes_html, name='imprimer_tableau_notes_html'),
    
    # Bulletin Intelligent avec calculs automatiques et exports
    path('bulletin-intelligent/<int:eleve_id>/<int:classe_note_id>/<str:periode>/', 
         bulletin_intelligent_view, name='bulletin_intelligent'),
    path('bulletin-intelligent/<int:eleve_id>/<int:classe_note_id>/<str:periode>/pdf/', 
         bulletin_intelligent_pdf, name='bulletin_intelligent_pdf'),
    path('bulletin-intelligent/<int:eleve_id>/<int:classe_note_id>/<str:periode>/excel/', 
         bulletin_intelligent_excel, name='bulletin_intelligent_excel'),
    
    # PDF de tous les bulletins d'une classe
    path('bulletins-classe-pdf/<int:classe_note_id>/<str:periode>/', 
         bulletins_classe_pdf, name='bulletins_classe_pdf'),
    
    # Importation de notes
    path('importer/', importer_notes, name='importer_notes'),
    path('template-import/', telecharger_template_import, name='telecharger_template_import'),
    
    # API AJAX pour l'importation
    path('api/matieres-classe/', get_matieres_classe, name='api_matieres_classe'),
    path('api/evaluations-matiere/', get_evaluations_matiere, name='api_evaluations_matiere'),
    
    # WhatsApp Bulletin
    path('bulletin/whatsapp/envoyer/', envoyer_bulletin_whatsapp, name='envoyer_bulletin_whatsapp'),
    path('bulletin/whatsapp/apercu/', apercu_message_whatsapp, name='apercu_message_whatsapp'),
    
    # Bulletin public (téléchargement sans authentification via token)
    path('bulletin-public/<int:eleve_id>/<int:classe_note_id>/<str:periode>/', 
         bulletin_public_pdf, name='bulletin_public_pdf'),
    
    # Export des résultats par classe
    path('exporter-resultats-pdf/', exporter_resultats_pdf, name='exporter_resultats_pdf'),
    path('exporter-resultats-excel/', exporter_resultats_excel, name='exporter_resultats_excel'),
    
    # Export complet des notes par matière
    path('exporter-notes-complet-pdf/', exporter_notes_complet_pdf, name='exporter_notes_complet_pdf'),
    path('exporter-notes-complet-excel/', exporter_notes_complet_excel, name='exporter_notes_complet_excel'),
    
    # Export des statistiques en PDF avec graphiques et recommandations
    path('exporter-statistiques-pdf/', exporter_statistiques_pdf, name='exporter_statistiques_pdf'),
    
    # Export des conseils et prises de décision en PDF
    path('exporter-conseils-pdf/', exporter_conseils_pdf, name='exporter_conseils_pdf'),
]
