# Nouvelle vue statistiques à remplacer dans notes/views.py

@login_required
def statistiques(request):
    """Statistiques globales de l'école"""
    from eleves.models import Eleve, Classe as ClasseEleve, Ecole
    from django.db.models import Avg, Count, Q, Sum
    from decimal import Decimal
    import json
    
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else Ecole.objects.first()
    
    # Statistiques globales de l'école
    total_eleves = Eleve.objects.filter(statut='ACTIF').count()
    total_classes = ClasseEleve.objects.filter(actif=True).count()
    
    # Période sélectionnée
    periode = request.GET.get('periode', 'TRIMESTRE_1')
    
    # Calculer les moyennes de tous les élèves
    eleves_evalues = []
    eleves_non_admis = []  # < 10/20
    eleves_a_suivre = []  # Entre 10 et 12/20
    eleves_excellents = []  # >= 16/20
    eleves_precaution = []  # Entre 8 et 10/20
    total_echecs = 0
    
    # Parcourir tous les élèves actifs
    tous_eleves = Eleve.objects.filter(statut='ACTIF')
    
    for eleve in tous_eleves:
        try:
            # Trouver la ClasseNote correspondante
            classe_note = ClasseNote.objects.filter(
                nom__icontains=eleve.classe.nom.split()[0]
            ).first()
            
            if not classe_note:
                continue
            
            # Récupérer les matières
            matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
            
            if not matieres.exists():
                continue
            
            # Calculer la moyenne
            total_points = Decimal('0')
            total_coefficients = Decimal('0')
            
            for matiere in matieres:
                # Notes mensuelles
                notes_mensuelles = NoteMensuelle.objects.filter(
                    eleve=eleve,
                    matiere=matiere,
                    absent=False
                )
                
                # Notes de composition
                notes_composition = CompositionNote.objects.filter(
                    eleve=eleve,
                    matiere=matiere,
                    periode=periode,
                    absent=False
                )
                
                if notes_mensuelles.exists() or notes_composition.exists():
                    moy_cours = Decimal('0')
                    if notes_mensuelles.exists():
                        moy_cours = sum(n.note for n in notes_mensuelles) / len(notes_mensuelles)
                    
                    note_compo = Decimal('0')
                    if notes_composition.exists():
                        note_compo = notes_composition.first().note
                    
                    # Moyenne matière
                    if moy_cours > 0 or note_compo > 0:
                        moy_matiere = (moy_cours + note_compo) / 2
                        total_points += moy_matiere * matiere.coefficient
                        total_coefficients += matiere.coefficient
            
            # Si l'élève a des notes
            if total_coefficients > 0:
                moyenne_generale = total_points / total_coefficients
                
                eleve_data = {
                    'eleve': eleve,
                    'classe': eleve.classe.nom,
                    'moyenne': float(moyenne_generale)
                }
                
                eleves_evalues.append(eleve_data)
                
                # Catégorisation
                if moyenne_generale < 10:
                    eleves_non_admis.append(eleve_data)
                    total_echecs += 1
                elif moyenne_generale < 12:
                    eleves_a_suivre.append(eleve_data)
                elif moyenne_generale < 10 and moyenne_generale >= 8:
                    eleves_precaution.append(eleve_data)
                elif moyenne_generale >= 16:
                    eleves_excellents.append(eleve_data)
        
        except Exception as e:
            continue
    
    # Statistiques calculées
    nb_evalues = len(eleves_evalues)
    nb_non_admis = len(eleves_non_admis)
    nb_a_suivre = len(eleves_a_suivre)
    nb_excellents = len(eleves_excellents)
    nb_precaution = len(eleves_precaution)
    
    taux_reussite = 0
    if nb_evalues > 0:
        taux_reussite = round(((nb_evalues - nb_non_admis) / nb_evalues) * 100, 1)
    
    taux_echec = 0
    if nb_evalues > 0:
        taux_echec = round((nb_non_admis / nb_evalues) * 100, 1)
    
    # Stratégies de boost
    strategies = []
    
    if nb_non_admis > 0:
        strategies.append({
            'titre': 'Soutien Scolaire Intensif',
            'description': f'{nb_non_admis} élèves en échec nécessitent un soutien immédiat',
            'actions': [
                'Cours de rattrapage quotidiens',
                'Tutorat individuel',
                'Suivi personnalisé des parents',
                'Exercices supplémentaires'
            ],
            'priorite': 'URGENT',
            'icone': 'fa-exclamation-triangle',
            'couleur': 'danger'
        })
    
    if nb_precaution > 0:
        strategies.append({
            'titre': 'Précautions à Prendre',
            'description': f'{nb_precaution} élèves entre 8 et 10/20 risquent l\'échec',
            'actions': [
                'Surveillance accrue',
                'Devoirs supplémentaires',
                'Rencontre avec les parents',
                'Évaluation des difficultés'
            ],
            'priorite': 'IMPORTANT',
            'icone': 'fa-exclamation-circle',
            'couleur': 'warning'
        })
    
    if nb_a_suivre > 0:
        strategies.append({
            'titre': 'Élèves à Suivre',
            'description': f'{nb_a_suivre} élèves entre 10 et 12/20 peuvent progresser',
            'actions': [
                'Encouragement régulier',
                'Exercices ciblés',
                'Suivi hebdomadaire',
                'Valorisation des progrès'
            ],
            'priorite': 'MOYEN',
            'icone': 'fa-eye',
            'couleur': 'info'
        })
    
    if nb_excellents > 0:
        strategies.append({
            'titre': 'Valorisation des Excellents',
            'description': f'{nb_excellents} élèves excellents (≥16/20) à encourager',
            'actions': [
                'Félicitations publiques',
                'Défis supplémentaires',
                'Rôle de tuteur',
                'Récompenses'
            ],
            'priorite': 'BONUS',
            'icone': 'fa-star',
            'couleur': 'success'
        })
    
    # Recommandations générales
    recommandations = []
    
    if taux_echec > 30:
        recommandations.append({
            'type': 'CRITIQUE',
            'message': f'Taux d\'échec élevé ({taux_echec}%). Action urgente requise!',
            'couleur': 'danger'
        })
    elif taux_echec > 20:
        recommandations.append({
            'type': 'ATTENTION',
            'message': f'Taux d\'échec préoccupant ({taux_echec}%). Renforcer le soutien.',
            'couleur': 'warning'
        })
    
    if taux_reussite >= 80:
        recommandations.append({
            'type': 'EXCELLENT',
            'message': f'Excellent taux de réussite ({taux_reussite}%). Continuez!',
            'couleur': 'success'
        })
    
    if nb_evalues < total_eleves * 0.5:
        recommandations.append({
            'type': 'INFO',
            'message': f'Seulement {nb_evalues}/{total_eleves} élèves évalués. Intensifier les évaluations.',
            'couleur': 'info'
        })
    
    context = {
        'titre_page': 'Statistiques de l\'École',
        'ecole': ecole,
        'periode': periode,
        
        # Statistiques globales
        'total_eleves': total_eleves,
        'total_classes': total_classes,
        'nb_evalues': nb_evalues,
        'nb_non_evalues': total_eleves - nb_evalues,
        
        # Résultats
        'nb_non_admis': nb_non_admis,
        'nb_a_suivre': nb_a_suivre,
        'nb_excellents': nb_excellents,
        'nb_precaution': nb_precaution,
        'total_echecs': total_echecs,
        
        # Taux
        'taux_reussite': taux_reussite,
        'taux_echec': taux_echec,
        
        # Listes
        'eleves_non_admis': eleves_non_admis[:20],  # Top 20
        'eleves_a_suivre': eleves_a_suivre[:20],
        'eleves_excellents': eleves_excellents[:20],
        
        # Stratégies et recommandations
        'strategies': strategies,
        'recommandations': recommandations,
        
        # Périodes
        'periodes': [
            ('TRIMESTRE_1', 'Trimestre 1'),
            ('TRIMESTRE_2', 'Trimestre 2'),
            ('TRIMESTRE_3', 'Trimestre 3'),
            ('SEMESTRE_1', 'Semestre 1'),
            ('SEMESTRE_2', 'Semestre 2'),
        ]
    }
    
    return render(request, 'notes/statistiques.html', context)
