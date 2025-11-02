# Matières par Défaut - Module Notes

## ✅ Fonctionnalité Améliorée - Version 2.0!

Un système de chargement automatique des matières par défaut a été créé selon les niveaux scolaires avec détection automatique des séries pour le lycée.

## 📚 Matières définies par niveau

### 🏫 COLLÈGE (7ème, 8ème, 9ème, 10ème)
| Matière | Code | Coefficient |
|---------|------|-------------|
| Mathématique | MATHS | 2.0 |
| Physique | PHYS | 1.0 |
| Chimie | CHI | 1.0 |
| Biologie | BIO | 1.0 |
| Français | FR | 2.0 |
| Anglais | ANG | 1.0 |
| Histoire | HIS | 1.0 |
| Géographie | GEO | 1.0 |
| Education Civique et Morale | ECM | 1.0 |
| Education Physique et Sportive | EPS | 1.0 |
| Dictée et Questions | DICQ | 2.0 |
| Rédaction | RED | 1.0 |

**Total: 12 matières**

### 📖 PRIMAIRE (CP, CE1, CE2, CM1, CM2, 6ème)
| Matière | Code | Coefficient |
|---------|------|-------------|
| Calcul écrit | CALC | 1.0 |
| Dictée et Questions | DICQ | 1.0 |
| Géographie | GEO | 1.0 |
| Histoire | HIS | 1.0 |
| E.C.M | ECM | 1.0 |
| Rédaction | RED | 1.0 |
| Sciences d'observation | SCI | 1.0 |
| Lecture | LECT | 1.0 |
| Langage | LANG | 1.0 |
| Écriture | ECR | 1.0 |
| Récitation/Chant | REC | 1.0 |
| Dessin | DESS | 1.0 |
| EPS | EPS | 1.0 |

**Total: 13 matières**

### 👶 MATERNELLE (Petite, Moyenne, Grande Section)
| Matière | Code | Coefficient |
|---------|------|-------------|
| Langage | LANG | 1.0 |
| Écriture | ECR | 1.0 |
| Calcul | CALC | 1.0 |
| Dessin | DESS | 1.0 |
| Récitation/Chant | REC | 1.0 |
| Jeux éducatifs | JEUX | 1.0 |
| Psychomotricité | PSYCH | 1.0 |

**Total: 7 matières**

### 🎓 LYCÉE - Série Sciences Mathématiques (11ème SM, 12ème SM)
| Matière | Code | Coefficient |
|---------|------|-------------|
| Mathématique | MATHS | 4.0 |
| Physique | PHYS | 3.0 |
| Chimie | CHI | 3.0 |
| Anglais | ANG | 2.0 |
| Économie | ECO | 2.0 |
| Philosophie | PHILO | 2.0 |
| Biologie | BIO | 1.0 |
| Français | FR | 2.0 |
| Géologie | GEOL | 1.0 |

**Total: 9 matières**

### 🔬 LYCÉE - Série Sciences Expérimentales (11ème SE, 12ème SE)
| Matière | Code | Coefficient |
|---------|------|-------------|
| Biologie | BIO | 3.0 |
| Physique | PHYS | 3.0 |
| Chimie | CHI | 3.0 |
| Anglais | ANG | 2.0 |
| Économie | ECO | 2.0 |
| Philosophie | PHILO | 2.0 |
| Mathématique | MATHS | 2.0 |
| Français | FR | 2.0 |
| Géologie | GEOL | 1.0 |

**Total: 9 matières**

### 📚 LYCÉE - Série Sciences Sociales/Lettres (11ème SL, 12ème SL)
| Matière | Code | Coefficient |
|---------|------|-------------|
| Français | FR | 4.0 |
| Philosophie | PHILO | 3.0 |
| Anglais | ANG | 3.0 |
| Mathématique | MATHS | 2.0 |
| Géographie | GEO | 2.0 |
| Histoire | HIS | 2.0 |
| Économie | ECO | 2.0 |

**Total: 7 matières**

## 🎯 Utilisation

### Dans l'interface web

1. Accédez à **Gérer les Matières** (`/notes/matieres/`)
2. Sélectionnez une classe
3. Cliquez sur le bouton **"Charger matières par défaut"** (vert avec icône magique ✨)
4. Confirmez l'action
5. Les matières correspondant au niveau de la classe seront automatiquement ajoutées

### Fonctionnement intelligent

- ✅ **Détection automatique** du niveau de la classe
- ✅ **Détection automatique** de la série pour le lycée (SM, SE, SL)
- ✅ **Vérification des doublons** - Ne crée pas de matières déjà existantes
- ✅ **Messages informatifs** :
  - Nombre de matières ajoutées
  - Nombre de matières déjà existantes
  - Erreurs éventuelles
- ✅ **Confirmation** avant chargement
- ✅ **Redirection** automatique vers la classe

## 📁 Fichiers créés

### `notes/matieres_defaut.py` ⭐ NOUVEAU
Fichier contenant:
- `MATIERES_COLLEGE` : 12 matières pour le collège
- `MATIERES_PRIMAIRE` : 13 matières pour le primaire
- `MATIERES_MATERNELLE` : 7 matières pour la maternelle
- `MATIERES_LYCEE_SM` : 9 matières pour Sciences Mathématiques
- `MATIERES_LYCEE_SE` : 9 matières pour Sciences Expérimentales
- `MATIERES_LYCEE_SL` : 7 matières pour Sciences Sociales/Lettres
- Fonction `get_matieres_par_defaut(niveau, serie, nom_classe)` avec détection automatique
- Fonction `charger_matieres_pour_classe(classe, user)` pour le chargement
- Fonction `detecter_niveau_depuis_nom(nom_classe)` pour la détection automatique

### Vue ajoutée
- `charger_matieres_defaut(request, classe_id)` dans `notes/views.py`

### URL ajoutée
- `/notes/matieres/charger-defaut/<classe_id>/`

### Bouton dans le template
- Bouton vert "Charger matières par défaut" dans `gerer_matieres.html`

## 🔧 Code technique

### Structure des données
```python
MATIERES_PAR_NIVEAU = {
    'COLLEGE_7': [
        {'nom': 'MATHEMATIQUE', 'code': 'MATH', 'coefficient': 2.0},
        {'nom': 'DICTEE ET OUEST', 'code': 'DICT', 'coefficient': 2.0},
        # ...
    ],
    # ...
}
```

### Fonction d'obtention
```python
def obtenir_matieres_par_niveau(niveau):
    """Retourne la liste des matières par défaut pour un niveau"""
    return MATIERES_PAR_NIVEAU.get(niveau, [])
```

### Vue de chargement
```python
@login_required
def charger_matieres_defaut(request, classe_id):
    """Charger les matières par défaut pour une classe"""
    # 1. Récupérer la classe
    # 2. Obtenir les matières par défaut
    # 3. Créer les matières non existantes
    # 4. Afficher les messages
    # 5. Rediriger
```

## ✨ Avantages

### Gain de temps
- **Avant**: Saisir manuellement 7 à 11 matières par classe
- **Après**: 1 clic pour charger toutes les matières

### Cohérence
- Matières standardisées par niveau
- Coefficients corrects dès le départ
- Codes uniformes

### Flexibilité
- Possibilité de modifier après chargement
- Ajout manuel toujours disponible
- Pas de remplacement des matières existantes

## 🔄 Workflow complet

1. **Créer une classe** dans "Gérer les Classes"
2. **Aller dans "Gérer les Matières"**
3. **Sélectionner la classe**
4. **Cliquer sur "Charger matières par défaut"**
5. **Confirmer**
6. ✅ **Toutes les matières sont ajoutées!**
7. **Modifier si nécessaire** (coefficients, noms, etc.)
8. **Ajouter des matières supplémentaires** si besoin

## 📝 Personnalisation

Pour modifier les matières par défaut, éditez le fichier:
`notes/matieres_par_defaut.py`

Exemple pour ajouter une matière:
```python
'COLLEGE_7': [
    # ... matières existantes ...
    {'nom': 'INFORMATIQUE', 'code': 'INFO', 'coefficient': 1.0},
]
```

## 🎓 Exemples d'utilisation

### Scénario 1: Nouvelle classe de 7ème
1. Créer la classe "7ème A"
2. Charger les matières par défaut
3. 11 matières ajoutées automatiquement
4. Prêt à créer des évaluations!

### Scénario 2: Classe de Terminale
1. Créer la classe "Terminale S"
2. Charger les matières par défaut
3. 7 matières ajoutées
4. Ajouter "INFORMATIQUE" manuellement si nécessaire

### Scénario 3: Classe de CM2
1. Créer la classe "CM2 B"
2. Charger les matières par défaut
3. 9 matières ajoutées
4. Modifier les coefficients si besoin

## ✅ Résumé

- ✅ **Matières définies** pour tous les niveaux (Garderie → Terminale)
- ✅ **Bouton de chargement** dans l'interface
- ✅ **Détection automatique** du niveau
- ✅ **Gestion des doublons** intelligente
- ✅ **Messages informatifs** clairs
- ✅ **Personnalisable** facilement

Cette fonctionnalité permet de gagner un temps considérable lors de la configuration initiale des classes! 🚀
