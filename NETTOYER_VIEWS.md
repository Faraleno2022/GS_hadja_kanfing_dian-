# URGENT - Fichier views.py Corrompu

## Problème

Le fichier `notes/views.py` est corrompu avec du code mélangé et des erreurs d'indentation.

## Solution Rapide

**Restaurer depuis une sauvegarde** ou **corriger manuellement**:

1. Ouvrir `notes/views.py`
2. Aller à la ligne 1108
3. **Supprimer toutes les lignes** de 1108 à 1307 (tout le code corrompu)
4. La fonction `bulletin_guineen` commence normalement à la ligne 1308

## OU

Utiliser Git pour restaurer:

```bash
git checkout notes/views.py
```

Puis réappliquer seulement la modification de la fonction `statistiques` (lignes 1018-1068).

## Code Correct pour la Fonction Statistiques

Remplacer la fonction `statistiques` (ligne ~1018) par:

```python
@login_required
def statistiques(request):
    """Statistiques globales de l'école"""
    from eleves.models import Eleve, Classe as ClasseEleve, Ecole
    
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else Ecole.objects.first()
    
    # Statistiques globales de l'école
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
        'recommandations': [],
        'periodes': [
            ('TRIMESTRE_1', 'Trimestre 1'),
            ('TRIMESTRE_2', 'Trimestre 2'),
            ('TRIMESTRE_3', 'Trimestre 3'),
        ]
    }
    
    return render(request, 'notes/statistiques.html', context)
```

## Action Immédiate

1. Restaurer le fichier depuis Git
2. OU supprimer manuellement les lignes 1108-1307
3. Réappliquer la modification de `statistiques`
4. Redémarrer le serveur
