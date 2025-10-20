from django.urls import path, include
from . import views
from . import views_moderne
from . import bulletin_ameliore

app_name = 'notes'

urlpatterns = [
    # Dashboard principal - nouvelle interface moderne
    path('', views_moderne.dashboard_moderne, name='dashboard'),
    
    # Ancien dashboard pour compatibilité
    path('ancien/', views.tableau_bord, name='tableau_bord'),
    # Classes
    path('classes/<str:niveau>/nouvelle/', views.creer_classe, name='creer_classe'),
    path('classes/<int:classe_id>/supprimer/', views.supprimer_classe, name='supprimer_classe'),
    path('classes/<int:classe_id>/matieres/', views.matieres_classe, name='matieres_classe'),
    # Matières
    path('classes/<int:classe_id>/matieres/nouvelle/', views.creer_matiere, name='creer_matiere'),
    path('matieres/<int:pk>/supprimer/', views.supprimer_matiere, name='supprimer_matiere'),
    # Évaluations & Saisie notes
    path('classes/<int:classe_id>/matieres/<int:matiere_id>/evaluations/nouvelle/', views.creer_evaluation, name='creer_evaluation'),
    path('classes/<int:classe_id>/matieres/<int:matiere_id>/evaluations/', views.evaluations_matiere, name='evaluations_matiere'),
    # Saisie des notes - nouvelles interfaces modernes
    path('evaluations/<int:evaluation_id>/saisie-moderne/', views_moderne.saisie_notes_moderne, name='saisie_notes_moderne'),
    
    # Interface simplifiée et intuitive (RECOMMANDÉE)
    path('evaluations/<int:evaluation_id>/saisie-simple/', views.saisie_notes_simple, name='saisie_notes_simple'),
    
    # Anciennes interfaces pour compatibilité
    path('evaluations/<int:evaluation_id>/saisie/', views.saisie_notes, name='saisie_notes'),
    path('evaluations/<int:evaluation_id>/saisie-individuelle/', views.saisie_notes_individuelle, name='saisie_notes_individuelle'),
    path('evaluations/<int:evaluation_id>/', views.evaluation_detail, name='evaluation_detail'),
    # AJAX endpoints pour saisie individuelle
    path('ajax/sauvegarder-note/', views.ajax_sauvegarder_note, name='ajax_sauvegarder_note'),
    path('ajax/sauvegarder-notes-masse/', views.ajax_sauvegarder_notes_masse, name='ajax_sauvegarder_notes_masse'),
    path('ajax/supprimer-note/', views.ajax_supprimer_note, name='ajax_supprimer_note'),
    # Bulletin PDF
    path('classes/<int:classe_id>/eleves/<int:eleve_id>/bulletin/<str:trimestre>/', views.bulletin_pdf, name='bulletin_pdf'),
    path('classes/<int:classe_id>/bulletins/<str:trimestre>/', views.bulletins_classe_pdf, name='bulletins_classe_pdf'),
    # Bulletins semestriels (Collège/Lycée)
    path('classes/<int:classe_id>/eleves/<int:eleve_id>/bulletin-semestriel/<int:semestre>/', views.bulletin_semestre_pdf, name='bulletin_semestre_pdf'),
    path('classes/<int:classe_id>/bulletins-semestriels/<int:semestre>/', views.bulletins_semestre_classe_pdf, name='bulletins_semestre_classe_pdf'),
    # Bulletin semestriel amélioré avec statistiques et recommandations
    path('classes/<int:classe_id>/eleves/<int:eleve_id>/bulletin-semestriel-ameliore/<int:semestre>/', bulletin_ameliore.bulletin_semestre_ameliore_pdf, name='bulletin_semestre_ameliore_pdf'),
    # Bulletins mensuels (Collège/Lycée)
    path('classes/<int:classe_id>/eleves/<int:eleve_id>/bulletin-mensuel/<int:mois>/', views.bulletin_mensuel_pdf, name='bulletin_mensuel_pdf'),
    path('classes/<int:classe_id>/bulletins-mensuels/<int:mois>/', views.bulletins_mensuels_classe_pdf, name='bulletins_mensuels_classe_pdf'),
    # Export Excel des notes d'une matière
    path('classes/<int:classe_id>/matieres/<int:matiere_id>/export/<str:trimestre>/', views.export_notes_excel, name='export_notes_excel'),
    # Bulletins annuels
    path('classes/<int:classe_id>/eleves/<int:eleve_id>/bulletin-annuel/', views.bulletin_annuel_pdf, name='bulletin_annuel_pdf'),
    path('classes/<int:classe_id>/bulletins-annuels/', views.bulletins_annuels_classe_pdf, name='bulletins_annuels_classe_pdf'),
    # Classements - nouvelles interfaces modernes
    path('classes/<int:classe_id>/classement-moderne/', views_moderne.classement_moderne, name='classement_moderne'),
    path('classes/<int:classe_id>/classement-moderne/<str:trimestre>/', views_moderne.classement_moderne, name='classement_moderne_trimestre'),
    
    # Gestion des matières moderne
    path('matieres-moderne/', views_moderne.gestion_matieres_moderne, name='gestion_matieres_moderne'),
    path('matieres-moderne/<int:classe_id>/', views_moderne.gestion_matieres_moderne, name='matieres_classe_moderne'),
    
    # API AJAX modernes
    path('api/stats-notes/', views_moderne.ajax_stats_notes, name='ajax_stats_notes'),
    
    # Détails des notes par élève
    path('eleves/<int:eleve_id>/notes/', views_moderne.details_notes_eleve, name='details_notes_eleve'),
    
    # API pour fenêtre modale liste élèves avec notes
    path('api/eleves-notes-modal/', views_moderne.liste_eleves_notes_modal, name='liste_eleves_notes_modal'),
    
    # Classements - anciennes interfaces pour compatibilité
    path('classes/<int:classe_id>/classement/', views.classement_classe, name='classement_classe'),
    path('classes/<int:classe_id>/classement/<str:trimestre>/', views.classement_classe, name='classement_classe'),
    path('classes/<int:classe_id>/classement/<str:trimestre>/pdf/', views.classement_classe_pdf, name='classement_classe_pdf'),
    path('classes/<int:classe_id>/classement/<str:trimestre>/excel/', views.classement_classe_excel, name='classement_classe_excel'),
    # Exports liste des admis (semestriel)
    path('classes/<int:classe_id>/admis/semestre/<int:semestre>/pdf/', views.export_admis_semestre_pdf, name='export_admis_semestre_pdf'),
    path('classes/<int:classe_id>/admis/semestre/<int:semestre>/excel/', views.export_admis_semestre_excel, name='export_admis_semestre_excel'),
    # Cartes scolaires
    path('classes/<int:classe_id>/cartes-scolaires/', views.cartes_scolaires_classe, name='cartes_scolaires_classe'),
    path('classes/<int:classe_id>/cartes-scolaires/pdf/', views.cartes_scolaires_pdf, name='cartes_scolaires_pdf'),
    # Carte individuelle par matricule
    path('carte-eleve/<path:matricule>/', views.carte_eleve_pdf, name='carte_eleve_pdf'),
]
