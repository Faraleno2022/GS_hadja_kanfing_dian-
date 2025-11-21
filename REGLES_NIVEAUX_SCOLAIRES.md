# 📚 Règles de calcul par niveau scolaire - Système Guinéen

## 🎯 Règles spécifiques par niveau

### 1. 🍼 MATERNELLE / GARDERIE

**Règle principale: PAS DE NOTES**

- ❌ **Pas de notes numériques**
- ✅ **Uniquement des appréciations qualitatives**
- ✅ **Suivi pédagogique qualitatif**
- ✅ **Évaluation par compétences**

**Classes concernées:**
- Garderie
- Crèche
- Petite Section
- Moyenne Section
- Grande Section
- Maternelle

**Bulletin:**
```
Moyenne générale: N/A
Mention: Suivi continu
Appréciation: Suivi pédagogique qualitatif - Pas de notes numériques

Matières:
- Éveil: Très bien acquis
- Motricité: En cours d'acquisition
- Langage: Acquis
```

### 2. 🎒 PRIMAIRE (1ère à 6ème année)

**Règle principale: PAS DE COEFFICIENTS**

- ✅ **Notes de 0 à 20**
- ❌ **Pas de coefficients (tous égaux à 1)**
- ✅ **Moyenne simple (non pondérée)**

**Classes concernées:**
- 1ère année (CP1)
- 2ème année (CP2)
- 3ème année (CE1)
- 4ème année (CE2)
- 5ème année (CM1)
- 6ème année (CM2)

**Calcul de la moyenne:**
```python
# PRIMAIRE: Moyenne simple
Moyenne = Somme(notes) / Nombre de matières

Exemple:
Français: 14/20
Maths: 16/20
Sciences: 12/20
Histoire: 15/20

Moyenne = (14 + 16 + 12 + 15) / 4 = 14.25/20
```

### 3. 📖 COLLÈGE (7ème à 10ème année)

**Règle principale: COEFFICIENTS APPLIQUÉS**

- ✅ **Notes de 0 à 20**
- ✅ **Coefficients par matière**
- ✅ **Moyenne pondérée**
- ✅ **Système: 40% continu + 60% composition**

**Classes concernées:**
- 7ème année
- 8ème année
- 9ème année
- 10ème année

**Calcul de la moyenne:**
```python
# COLLÈGE: Moyenne pondérée
Moyenne = Somme(note × coefficient) / Somme(coefficients)

Exemple:
Français (coef 3): 14/20 → 42 points
Maths (coef 4): 16/20 → 64 points
Sciences (coef 2): 12/20 → 24 points

Total points = 130
Total coefficients = 9
Moyenne = 130 / 9 = 14.44/20
```

### 4. 🎓 LYCÉE (11ème à Terminale)

**Règle principale: COEFFICIENTS ÉLEVÉS**

- ✅ **Notes de 0 à 20**
- ✅ **Coefficients par matière (plus élevés)**
- ✅ **Moyenne pondérée**
- ✅ **Système: 40% continu + 60% composition**
- ✅ **Spécialisation par série (Scientifique, Littéraire, etc.)**

**Classes concernées:**
- 11ème année
- 12ème année (Série Scientifique/Littéraire)
- Terminale

**Exemple série scientifique:**
```python
Mathématiques (coef 5): 15/20 → 75 points
Physique (coef 4): 14/20 → 56 points
Français (coef 2): 12/20 → 24 points

Total points = 155
Total coefficients = 11
Moyenne = 155 / 11 = 14.09/20
```

## 📊 Tableau récapitulatif

| Niveau | Notes | Coefficients | Type de moyenne | Bulletin |
|--------|-------|--------------|-----------------|----------|
| **Maternelle** | ❌ Non | ❌ N/A | Appréciations | Qualitatif |
| **Primaire** | ✅ Oui | ❌ Non (=1) | Simple | Quantitatif |
| **Collège** | ✅ Oui | ✅ Oui | Pondérée | Quantitatif |
| **Lycée** | ✅ Oui | ✅ Oui | Pondérée | Quantitatif |

## 🔧 Implémentation dans le code

### Fonction de détection du niveau

```python
def detecter_niveau_scolaire(classe_nom):
    """Détecte automatiquement le niveau"""
    nom_upper = str(classe_nom).upper()
    
    if any(x in nom_upper for x in ['MATERNELLE', 'GARDERIE']):
        return 'MATERNELLE'
    elif any(x in nom_upper for x in ['1ÈRE ANNÉE', '2ÈME ANNÉE']):
        return 'PRIMAIRE'
    elif any(x in nom_upper for x in ['7ÈME', '8ÈME', '9ÈME', '10ÈME']):
        return 'COLLEGE'
    elif any(x in nom_upper for x in ['11ÈME', '12ÈME', 'TERMINALE']):
        return 'LYCEE'
```

### Application des règles dans le calcul

```python
def calculer_moyenne_generale_eleve(eleve, matieres, periode, system_type):
    niveau = detecter_niveau_scolaire(classe.nom)
    
    # MATERNELLE: Pas de notes
    if niveau == 'MATERNELLE':
        return {
            'moyenne_generale': None,
            'appreciations_only': True,
            'appreciation': 'Suivi pédagogique qualitatif'
        }
    
    # PRIMAIRE: Pas de coefficients
    if niveau == 'PRIMAIRE':
        coefficient = Decimal('1')  # Toujours 1
    else:
        coefficient = matiere.coefficient  # Utiliser le coefficient défini
```

## ✅ Avantages de cette approche

1. **Automatique**: Détection du niveau basée sur le nom de classe
2. **Conforme**: Respect des pratiques pédagogiques guinéennes
3. **Flexible**: Facile d'ajouter de nouveaux niveaux
4. **Cohérent**: Même règle appliquée partout

## 📋 Exemples de bulletins

### Bulletin Maternelle
```
École: Les Petits Génies
Classe: Petite Section
Élève: CAMARA Aminata

ÉVALUATION QUALITATIVE
----------------------
Langage: Très bien - Participe activement
Éveil mathématique: Bien - Progresse régulièrement
Motricité: Très bien - Excellente coordination
Arts plastiques: Excellent - Très créative

Appréciation générale: Aminata est une élève épanouie qui 
progresse bien dans tous les domaines.
```

### Bulletin Primaire
```
École: École Primaire Centrale
Classe: 3ème année (CE1)
Élève: DIALLO Mohamed

NOTES (toutes matières coefficient 1)
--------------------------------------
Français: 15/20
Mathématiques: 17/20
Sciences: 14/20
Histoire-Géo: 13/20
Éducation civique: 16/20

Moyenne générale: 15.00/20 (moyenne simple)
Rang: 3ème/25
Mention: Bien
```

### Bulletin Collège/Lycée
```
Lycée: Lycée d'Excellence
Classe: 12ème Série Scientifique
Élève: BAH Fatoumata

NOTES (avec coefficients)
-------------------------
Mathématiques (5): 16/20 → 80 points
Physique (4): 15/20 → 60 points
Chimie (3): 17/20 → 51 points
SVT (2): 14/20 → 28 points
Français (2): 13/20 → 26 points

Total: 245 points / 16 coef = 15.31/20
Rang: 2ème/30
Mention: Bien
```

## 🚀 Mise en œuvre

Le module `calculs_moyennes.py` applique automatiquement ces règles:

1. **Détection** du niveau scolaire
2. **Application** des règles spécifiques
3. **Calcul** adapté au niveau
4. **Génération** du bulletin approprié

---

**Date de mise en œuvre:** 21 novembre 2025  
**Statut:** ✅ Implémenté dans le module centralisé  
**Impact:** Tous les bulletins et classements
