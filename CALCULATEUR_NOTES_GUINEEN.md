# 🎓 Calculateur de Notes - Système Éducatif Guinéen

## 📋 Vue d'Ensemble

Système intelligent de calcul de notes conforme aux normes du système éducatif guinéen, prenant en charge tous les niveaux scolaires et les différentes combinaisons possibles.

---

## 🏫 Niveaux Supportés

| Niveau | Notation | Système | Coefficients |
|--------|----------|---------|--------------|
| **Maternelle** | Appréciations | - | Non |
| **Primaire** | /10 | Trimestriel | Non |
| **Collège** | /20 | Trim./Semestriel | Oui |
| **Lycée** | /20 | Trim./Semestriel | Oui |

---

## 📊 Formules de Calcul

### Primaire
```
Moyenne Annuelle = (Composition 1 + Composition 2 + Composition 3) / 3
```

### Secondaire (Collège & Lycée)

#### 1. Moyenne d'une Période
```
Moyenne Période = (Moyenne Cours × 40%) + (Composition × 60%)
```

#### 2. Moyenne Cours
```
Moyenne Cours = Somme des moyennes mensuelles / Nombre de mois
```

#### 3. Moyenne Annuelle d'une Matière
```
Système Trimestriel: (T1 + T2 + T3) / 3
Système Semestriel: (S1 + S2) / 2
```

#### 4. Moyenne Générale Annuelle
```
Moyenne Générale = Σ(Moyenne Matière × Coefficient) / Σ(Coefficients)
```

---

## 🔧 Utilisation

### Installation

Les fichiers sont déjà dans le projet :
- `notes/calculateur_notes_guineen.py` - Calculateur standalone
- `notes/integration_calculateur.py` - Intégration Django

### Test Rapide

```bash
python tester_calculateur_notes.py
```

---

## 💻 Exemples de Code

### 1. Secondaire - Système Semestriel

```python
from notes.calculateur_notes_guineen import EleveSecondaire, SystemeEvaluation

# Créer un élève
eleve = EleveSecondaire("CAMARA", "Mariama", "9ème Année", SystemeEvaluation.SEMESTRE)

# Ajouter une matière
eleve.ajouter_matiere("Mathématiques", coefficient=4)

# Ajouter les notes du semestre 1
notes_s1 = {
    'octobre': [13, 15],
    'novembre': [12, 14],
    'decembre': [16, 15],
    'janvier': [11, 13, 14]
}
eleve.ajouter_notes_periode("Mathématiques", notes_s1, composition=12)

# Ajouter les notes du semestre 2
notes_s2 = {
    'mars': [15, 14],
    'avril': [16, 15],
    'mai': [17, 16],
    'juin': [14, 15]
}
eleve.ajouter_notes_periode("Mathématiques", notes_s2, composition=14)

# Calculer le bulletin annuel
bulletin = eleve.calculer_moyenne_generale()
print(bulletin)
```

**Résultat :**
```
{
    'eleve': 'Mariama CAMARA',
    'classe': '9ème Année',
    'systeme': 'semestre',
    'matieres': [
        {
            'matiere': 'Mathématiques',
            'moyenne': 13.61,
            'coefficient': 4,
            'points': 54.44
        }
    ],
    'moyenne_generale': 13.61,
    'total_points': 54.44,
    'total_coefficients': 4
}
```

---

### 2. Primaire

```python
from notes.calculateur_notes_guineen import ElevePrimaire

# Créer un élève
eleve = ElevePrimaire("DIALLO", "Fatou", "4ème Année")

# Ajouter une matière
eleve.ajouter_matiere("Mathématiques")

# Ajouter les 3 compositions trimestrielles
eleve.ajouter_composition("Mathématiques", 8.0)  # Composition 1
eleve.ajouter_composition("Mathématiques", 7.5)  # Composition 2
eleve.ajouter_composition("Mathématiques", 9.0)  # Composition 3

# Calculer le bulletin annuel
bulletin = eleve.calculer_moyenne_generale()
print(bulletin)
```

**Résultat :**
```
{
    'eleve': 'Fatou DIALLO',
    'classe': '4ème Année',
    'matieres': [
        {
            'matiere': 'Mathématiques',
            'moyenne': 8.17,
            'coefficient': None
        }
    ],
    'moyenne_generale': 8.17
}
```

---

### 3. Intégration Django

```python
from notes.integration_calculateur import obtenir_bulletin_complet

# Dans une vue Django
def vue_bulletin_annuel(request, eleve_id):
    classe_id = request.GET.get('classe_id')
    
    resultat = obtenir_bulletin_complet(eleve_id, classe_id)
    
    if resultat['success']:
        return render(request, 'notes/bulletin_annuel.html', {
            'bulletin': resultat['bulletin']
        })
    else:
        messages.error(request, resultat['error'])
        return redirect('notes:liste_eleves')
```

---

## 📐 Calcul Détaillé - Exemple Complet

### Élève : Mariama CAMARA (9ème Année)
### Matière : Mathématiques (Coef 4)
### Système : Semestriel

#### **SEMESTRE 1**

**Notes mensuelles :**
- Octobre : 13, 15 → Moyenne = **14.00**
- Novembre : 12, 14 → Moyenne = **13.00**
- Décembre : 16, 15 → Moyenne = **15.50**
- Janvier : 11, 13, 14 → Moyenne = **12.67**

**Moyenne Cours S1 :**
```
(14.00 + 13.00 + 15.50 + 12.67) / 4 = 13.79
```

**Composition S1 :** 12.00

**Note Semestre 1 :**
```
(13.79 × 0.40) + (12.00 × 0.60) = 5.52 + 7.20 = 12.72
```

---

#### **SEMESTRE 2**

**Notes mensuelles :**
- Mars : 15, 14 → Moyenne = **14.50**
- Avril : 16, 15 → Moyenne = **15.50**
- Mai : 17, 16 → Moyenne = **16.50**
- Juin : 14, 15 → Moyenne = **14.50**

**Moyenne Cours S2 :**
```
(14.50 + 15.50 + 16.50 + 14.50) / 4 = 15.25
```

**Composition S2 :** 14.00

**Note Semestre 2 :**
```
(15.25 × 0.40) + (14.00 × 0.60) = 6.10 + 8.40 = 14.50
```

---

#### **MOYENNE ANNUELLE MATHÉMATIQUES**

```
(12.72 + 14.50) / 2 = 13.61/20
```

#### **POINTS**

```
13.61 × 4 (coefficient) = 54.44 points
```

---

## 🎯 Caractéristiques Clés

### ✅ Respect des Normes Guinéennes

- **Pondération 40/60** : Cours (40%) + Composition (60%)
- **Notation par niveau** : /10 (primaire), /20 (secondaire)
- **Systèmes flexibles** : Trimestriel ou Semestriel
- **Coefficients** : Uniquement pour le secondaire

### ✅ Gestion Intelligente

- **Notes mensuelles** : Groupées par mois
- **Calculs automatiques** : Moyennes de cours, périodes, annuelles
- **Validation** : Vérification du nombre de périodes
- **Flexibilité** : Nombre variable de notes par mois

### ✅ Intégration Django

- **Compatible** : Avec les modèles Django existants
- **Mapping automatique** : Périodes → Mois
- **Bulletins complets** : Génération automatique
- **Rang** : Calcul du classement (à implémenter)

---

## 📂 Structure des Fichiers

```
GS_hadja_kanfing_dian--main/
├── notes/
│   ├── calculateur_notes_guineen.py       # Calculateur standalone
│   ├── integration_calculateur.py         # Intégration Django
│   └── models.py                          # Modèles Django
├── tester_calculateur_notes.py            # Script de test
└── CALCULATEUR_NOTES_GUINEEN.md          # Cette documentation
```

---

## 🧪 Tests

### Exécuter les Tests

```bash
# Test standalone (sans Django)
python tester_calculateur_notes.py

# Test avec Django
python manage.py shell
>>> from notes.calculateur_notes_guineen import exemple_complet
>>> exemple_complet()
```

### Résultat Attendu

```
================================================================================
                    EXEMPLE: SECONDAIRE - SYSTÈME SEMESTRIEL
================================================================================
[...]
MOYENNE GÉNÉRALE: 12.75/20
================================================================================

================================================================================
                    EXEMPLE: SECONDAIRE - SYSTÈME TRIMESTRIEL
================================================================================
[...]
MOYENNE GÉNÉRALE: 13.84/20
================================================================================

================================================================================
                           EXEMPLE: PRIMAIRE
================================================================================
[...]
MOYENNE GÉNÉRALE: 8.08/10
================================================================================

✅ SYSTÈME COMPLET OPÉRATIONNEL
```

---

## 🔄 Intégration avec le Système Existant

### Mapping des Périodes

| Code Django | Mois Correspondants |
|-------------|---------------------|
| `TRIMESTRE_1` | Octobre, Novembre, Décembre |
| `TRIMESTRE_2` | Janvier, Février, Mars |
| `TRIMESTRE_3` | Avril, Mai, Juin |
| `SEMESTRE_1` | Octobre à Janvier |
| `SEMESTRE_2` | Mars à Juin |

### Mapping des Types d'Évaluation

| Type Django | Utilisation Calculateur |
|-------------|-------------------------|
| `DEVOIR` | Notes mensuelles (40%) |
| `COMPOSITION` | Note de composition (60%) |

---

## 📊 Bulletins Générés

### Bulletin Secondaire

```
================================================================================
BULLETIN ANNUEL - SEMESTRE
================================================================================
Élève: Mariama CAMARA
Classe: 9ème Année
================================================================================
MATIÈRE                        MOYENNE    COEF   POINTS    
--------------------------------------------------------------------------------
Mathématiques                  13.61      4      54.44     
Français                       12.00      4      48.00     
Anglais                        13.72      2      27.44     
Sciences Physiques             11.04      2      22.08     
================================================================================
TOTAL POINTS: 151.96 / 12 coef
MOYENNE GÉNÉRALE: 12.66/20
================================================================================
```

### Bulletin Primaire

```
================================================================================
BULLETIN ANNUEL - PRIMAIRE
================================================================================
Élève: Fatou DIALLO
Classe: 4ème Année
================================================================================
MATIÈRE                        MOYENNE   
--------------------------------------------------------------------------------
Français                       8.00      
Mathématiques                  8.17      
Histoire-Géographie            7.50      
Sciences                       8.50      
================================================================================
MOYENNE GÉNÉRALE: 8.04/10
================================================================================
```

---

## 🚀 Utilisation en Production

### 1. Génération de Bulletins Annuels

```python
from notes.integration_calculateur import CalculateurDjango
from eleves.models import Eleve
from notes.models import ClasseNote

# Pour tous les élèves d'une classe
classe = ClasseNote.objects.get(nom="9ème Année")
eleves = Eleve.objects.filter(classe__nom=classe.nom, statut='ACTIF')

for eleve in eleves:
    bulletin = CalculateurDjango.calculer_moyenne_generale_annuelle(eleve, classe)
    print(f"{bulletin['eleve']}: {bulletin['moyenne_generale']}/20")
```

### 2. Vue Django pour Bulletin Annuel

```python
@login_required
def bulletin_annuel(request, eleve_id):
    """Vue pour afficher le bulletin annuel d'un élève"""
    eleve = get_object_or_404(Eleve, id=eleve_id)
    classe = eleve.classe
    
    # Obtenir le bulletin
    resultat = obtenir_bulletin_complet(eleve_id, classe.id)
    
    if resultat['success']:
        context = {
            'bulletin': resultat['bulletin'],
            'eleve': eleve
        }
        return render(request, 'notes/bulletin_annuel.html', context)
    else:
        messages.error(request, "Impossible de générer le bulletin")
        return redirect('notes:liste_eleves')
```

---

## 🎯 Avantages du Système

### ✅ Précision Mathématique
- Arrondis cohérents à 2 décimales
- Calculs conformes aux normes guinéennes
- Validation des données d'entrée

### ✅ Flexibilité
- Support de tous les niveaux scolaires
- Systèmes trimestriel et semestriel
- Nombre variable de notes par mois

### ✅ Maintenabilité
- Code bien structuré et documenté
- Tests unitaires intégrés
- Séparation des responsabilités

### ✅ Intégration
- Compatible avec Django
- Utilise les modèles existants
- Facile à étendre

---

## 📝 TODO / Améliorations Futures

- [ ] Calcul automatique du rang dans la classe
- [ ] Support des appréciations pour la maternelle
- [ ] Génération PDF des bulletins annuels
- [ ] Export Excel des résultats annuels
- [ ] Statistiques annuelles par classe
- [ ] Comparaison inter-périodes
- [ ] Graphiques d'évolution annuelle

---

## 📞 Support

Pour toute question ou problème :
1. Consulter les exemples dans `calculateur_notes_guineen.py`
2. Exécuter le script de test : `python tester_calculateur_notes.py`
3. Vérifier la documentation de l'intégration dans `integration_calculateur.py`

---

**Date de création** : 2 novembre 2025  
**Version** : 1.0  
**Statut** : ✅ **OPÉRATIONNEL**  
**Conforme** : Système éducatif guinéen
