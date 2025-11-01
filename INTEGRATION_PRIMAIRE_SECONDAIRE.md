# Intégration Primaire et Secondaire - Système Guinéen

## Vue d'ensemble

Le système de notes guinéen a été étendu pour supporter à la fois le **primaire** et le **secondaire** avec leurs spécificités respectives.

## Différences entre Primaire et Secondaire

### 🎒 PRIMAIRE
- **Système**: Trimestriel uniquement (3 trimestres)
- **Notes**: Notes mensuelles uniquement
- **Calcul**: Moyenne des notes mensuelles par trimestre
- **Pas de compositions** mensuelles
- **Formule**:
  ```
  Trimestre 1 = (Oct + Nov + Déc) ÷ 3
  Trimestre 2 = (Jan + Fév + Mars) ÷ 3
  Trimestre 3 = (Avr + Mai + Juin) ÷ 3
  Moyenne Annuelle = (T1 + T2 + T3) ÷ 3
  ```

### 🎓 SECONDAIRE
- **Système**: Semestriel OU Trimestriel (au choix)
- **Notes**: Notes mensuelles + Compositions
- **Calcul**: Moyenne des notes de cours + Composition

#### Semestriel:
```
Note de Cours S1 = (Oct + Nov + Déc + Jan) ÷ 4
Note Semestre 1 = (Note de Cours S1 + Composition S1) ÷ 2

Note de Cours S2 = (Fév + Mars + Avr + Mai) ÷ 4
Note Semestre 2 = (Note de Cours S2 + Composition S2) ÷ 2

Moyenne Annuelle = (S1 + S2) ÷ 2
```

#### Trimestriel:
```
Note de Cours T1 = (Oct + Nov + Déc) ÷ 3
Note Trimestre 1 = (Note de Cours T1 + Composition T1) ÷ 2

Note de Cours T2 = (Jan + Fév + Mars) ÷ 3
Note Trimestre 2 = (Note de Cours T2 + Composition T2) ÷ 2

Note de Cours T3 = (Avr + Mai + Juin) ÷ 3
Note Trimestre 3 = (Note de Cours T3 + Composition T3) ÷ 2

Moyenne Annuelle = (T1 + T2 + T3) ÷ 3
```

## Modifications Apportées

### 1. Modèle `ClasseNote`
Ajout du champ `niveau_enseignement`:
```python
niveau_enseignement = models.CharField(
    max_length=20,
    choices=[
        ('PRIMAIRE', 'Primaire'),
        ('SECONDAIRE', 'Secondaire'),
    ],
    default='SECONDAIRE',
    verbose_name="Niveau d'enseignement"
)
```

### 2. Vues Django

#### `bulletin_guineen()`
- Détecte automatiquement le niveau d'enseignement
- Force le système trimestriel pour le primaire
- Gère les compositions uniquement pour le secondaire
- Supporte le trimestre 3 pour le secondaire trimestriel

#### `saisie_notes_guineen()`
- Adapte l'interface selon le niveau
- Masque les compositions pour le primaire
- Affiche le trimestre 3 pour le secondaire trimestriel

#### `sauvegarder_notes_guineen()`
- Sauvegarde les compositions uniquement pour le secondaire
- Gère le trimestre 3 en mode trimestriel

### 3. Templates

Les templates s'adaptent automatiquement selon:
- `{{ niveau_enseignement }}`: PRIMAIRE ou SECONDAIRE
- `{{ system_type }}`: semestre ou trimestre

## Utilisation

### Configuration d'une Classe

1. **Via l'Admin Django**:
   - Allez dans **Notes > Classes (Notes)**
   - Créez ou modifiez une classe
   - Sélectionnez le **Niveau d'enseignement**:
     - PRIMAIRE: Pour les classes du primaire
     - SECONDAIRE: Pour collège et lycée

2. **Comportement Automatique**:
   - **Primaire**: Le système force automatiquement le mode trimestriel
   - **Secondaire**: L'utilisateur peut choisir entre semestriel et trimestriel

### Saisie des Notes

#### Pour le Primaire:
1. Sélectionner une classe primaire
2. Choisir un élève
3. Saisir les notes mensuelles (Oct-Juin)
4. **Pas de compositions à saisir**
5. Sauvegarder

#### Pour le Secondaire:
1. Sélectionner une classe secondaire
2. Choisir le système (Semestriel/Trimestriel)
3. Choisir un élève
4. Saisir les notes mensuelles
5. Saisir les compositions (2 ou 3 selon le système)
6. Sauvegarder

### Génération du Bulletin

Le bulletin s'adapte automatiquement:
- **Primaire**: Affiche 3 trimestres avec moyennes mensuelles
- **Secondaire Semestriel**: Affiche 2 semestres avec notes de cours et compositions
- **Secondaire Trimestriel**: Affiche 3 trimestres avec notes de cours et compositions

## Migration des Données Existantes

Pour les classes déjà créées:
```python
# Par défaut, toutes les classes sont en SECONDAIRE
# Pour changer une classe en PRIMAIRE:
from notes.models import ClasseNote

classe = ClasseNote.objects.get(nom="CP1")
classe.niveau_enseignement = 'PRIMAIRE'
classe.save()
```

## Fichiers Modifiés

```
notes/
├── models.py                     # Ajout niveau_enseignement
├── views.py                      # Adaptation des 3 vues
└── migrations/
    └── 0004_classenote_niveau_enseignement.py

templates/notes/
├── saisie_notes_guineen.html     # À mettre à jour
└── bulletin_guineen.html         # À mettre à jour
```

## Prochaines Étapes

1. ✅ Modèles mis à jour
2. ✅ Vues adaptées
3. ✅ Migrations créées et appliquées
4. ⏳ Templates à mettre à jour (en cours)
5. ⏳ Tests et validation

## Notes Importantes

- **Primaire**: Toujours trimestriel, pas de compositions
- **Secondaire**: Choix entre semestriel et trimestriel, avec compositions
- **Trimestre 3**: Uniquement pour le secondaire en mode trimestriel
- **Rétrocompatibilité**: Les classes existantes restent en SECONDAIRE par défaut

---

**Version:** 2.0  
**Date:** Octobre 2024  
**Système:** Gestion Scolaire - Notes Guinéennes (Primaire + Secondaire)
