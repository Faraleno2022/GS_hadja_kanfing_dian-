# Remplacement Rapide - Vue Statistiques

## Instructions

Dans `notes/views.py`, **supprimer complètement** la fonction `statistiques` (lignes ~1018 à ~1222)

Et la **remplacer** par ce code simple:

```python
@login_required
def statistiques(request):
    """Statistiques globales de l'école"""
    from eleves.models import Eleve, Classe as ClasseEleve, Ecole
    
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else Ecole.objects.first()
    
    # Statistiques globales
    total_eleves = Eleve.objects.filter(statut='ACTIF').count()
    total_classes = ClasseEleve.objects.all().count()
    
    # Période sélectionnée
    periode = request.GET.get('periode', 'TRIMESTRE_1')
    
    # Pour l'instant, affichage simple
    context = {
        'titre_page': 'Statistiques de l\'École',
        'ecole': ecole,
        'periode': periode,
        'total_eleves': total_eleves,
        'total_classes': total_classes,
        'nb_evalues': 0,
        'nb_non_evalues': total_eleves,
        'nb_non_admis': 0,
        'nb_a_suivre': 0,
        'nb_excellents': 0,
        'nb_precaution': 0,
        'total_echecs': 0,
        'taux_reussite': 0,
        'taux_echec': 0,
        'eleves_non_admis': [],
        'eleves_a_suivre': [],
        'eleves_excellents': [],
        'strategies': [],
        'recommandations': [{
            'type': 'INFO',
            'message': 'Page de statistiques en cours de développement',
            'couleur': 'info'
        }],
        'periodes': [
            ('TRIMESTRE_1', 'Trimestre 1'),
            ('TRIMESTRE_2', 'Trimestre 2'),
            ('TRIMESTRE_3', 'Trimestre 3'),
            ('SEMESTRE_1', 'Semestre 1'),
            ('SEMESTRE_2', 'Semestre 2'),
        ]
    }
    
    return render(request, 'notes/statistiques.html', context)
```

Cette version simple affichera la page sans erreur. Vous pourrez ensuite ajouter progressivement les calculs.
