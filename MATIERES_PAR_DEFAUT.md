# Matières par Défaut - Module Notes

## ✅ Fonctionnalité implémentée!

Un système de chargement automatique des matières par défaut a été créé selon les niveaux scolaires.

## 📚 Matières définies par niveau

### Collège 7ème et 8ème
| Matière | Code | Coefficient |
|---------|------|-------------|
| MATHEMATIQUE | MATH | 2.0 |
| DICTEE ET OUEST | DICT | 2.0 |
| REDACTION | REDA | 1.0 |
| PHYSIQUE | PHY | 1.0 |
| CHIMIE | CHIM | 1.0 |
| HISTOIRE | HIST | 1.0 |
| GEOGRAPHIE | GEO | 1.0 |
| E.C.M | ECM | 1.0 |
| BIOLOGIE | BIO | 1.0 |
| ANGLAIS | ANG | 1.0 |
| E.P.S | EPS | 1.0 |

**Total: 11 matières**

### Collège 9ème
| Matière | Code | Coefficient |
|---------|------|-------------|
| MATHEMATIQUE | MATH | 4.0 |
| PHYSIQUE | PHY | 3.0 |
| CHIMIE | CHIM | 3.0 |
| ANGLAIS | ANG | 2.0 |
| ECONOMIE | ECO | 2.0 |
| PHYLOSOPHIE | PHILO | 2.0 |
| BIOLOGIE | BIO | 1.0 |
| FRANCAIS | FR | 2.0 |
| GEOLOGIE | GEOL | 1.0 |

**Total: 9 matières**

### Collège 10ème
| Matière | Code | Coefficient |
|---------|------|-------------|
| BIOLOGIE | BIO | 3.0 |
| PHYSIQUE | PHY | 3.0 |
| CHIMIE | CHIM | 3.0 |
| ANGLAIS | ANG | 2.0 |
| ECONOMIE | ECO | 2.0 |
| PHYLOSOPHIE | PHILO | 2.0 |
| MATHEMATIQUE | MATH | 2.0 |
| FRANCAIS | FR | 2.0 |
| GEOLOGIE | GEOL | 1.0 |

**Total: 9 matières**

### Lycée 11ème, 12ème et Terminale
| Matière | Code | Coefficient |
|---------|------|-------------|
| Francais | FR | 4.0 |
| PHYLOSOPHIE | PHILO | 3.0 |
| ANGLAIS | ANG | 3.0 |
| MATHEMATIQUE | MATH | 2.0 |
| GEOGRAPHIE | GEO | 2.0 |
| HISTOIRE | HIST | 2.0 |
| ECONOMIE | ECO | 2.0 |

**Total: 7 matières**

### Primaire (1ère à 6ème)
| Matière | Code | Coefficient |
|---------|------|-------------|
| MATHEMATIQUE | MATH | 2.0 |
| FRANCAIS | FR | 2.0 |
| LECTURE | LECT | 1.0 |
| DICTEE | DICT | 1.0 |
| SCIENCES | SCI | 1.0 |
| HISTOIRE-GEOGRAPHIE | HG | 1.0 |
| E.C.M | ECM | 1.0 |
| ANGLAIS | ANG | 1.0 |
| E.P.S | EPS | 1.0 |

**Total: 9 matières**

### Maternelle et Garderie
| Matière | Code | Coefficient |
|---------|------|-------------|
| LECTURE | LECT | 1.0 |
| ECRITURE | ECR | 1.0 |
| CALCUL | CALC | 1.0 |
| DESSIN | DESS | 1.0 |
| CHANT | CHANT | 1.0 |

**Total: 5 matières**

## 🎯 Utilisation

### Dans l'interface web

1. Accédez à **Gérer les Matières** (`/notes/matieres/`)
2. Sélectionnez une classe
3. Cliquez sur le bouton **"Charger matières par défaut"** (vert avec icône magique ✨)
4. Confirmez l'action
5. Les matières correspondant au niveau de la classe seront automatiquement ajoutées

### Fonctionnement intelligent

- ✅ **Détection automatique** du niveau de la classe
- ✅ **Vérification des doublons** - Ne crée pas de matières déjà existantes
- ✅ **Messages informatifs** :
  - Nombre de matières ajoutées
  - Nombre de matières déjà existantes
- ✅ **Confirmation** avant chargement
- ✅ **Redirection** automatique vers la classe

## 📁 Fichiers créés

### `notes/matieres_par_defaut.py`
Fichier contenant:
- Dictionnaire `MATIERES_PAR_NIVEAU` avec toutes les matières par niveau
- Fonction `obtenir_matieres_par_niveau(niveau)` pour récupérer les matières

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
