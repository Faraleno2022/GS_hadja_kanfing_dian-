# 📊 Système de Calcul des Notes - Guinée

## 🎯 SYSTÈME GUINÉEN

### 1. Structure des Notes

**Trimestre** (3 par an):
```
Trimestre = 3 Devoirs + 1 Composition

Calcul:
- Moyenne des 3 devoirs = (D1 + D2 + D3) / 3
- Moyenne du trimestre = (Moyenne Devoirs + Composition) / 2
```

**Semestre** (2 par an):
```
Semestre = 6 Devoirs + 1 Composition

Calcul:
- Moyenne des 6 devoirs = (D1 + D2 + D3 + D4 + D5 + D6) / 6
- Moyenne du semestre = (Moyenne Devoirs + Composition) / 2
```

### 2. Moyenne par Matière

**Formule**:
```
Moyenne Matière = Somme des moyennes de périodes / Nombre de périodes
```

**Exemple Trimestre**:
```
Trimestre 1: 14/20
Trimestre 2: 15/20
Trimestre 3: 16/20

Moyenne Annuelle = (14 + 15 + 16) / 3 = 15/20
```

**Exemple Semestre**:
```
Semestre 1: 14/20
Semestre 2: 16/20

Moyenne Annuelle = (14 + 16) / 2 = 15/20
```

### 3. Moyenne Générale

**Avec Coefficients**:
```
Moyenne Générale = Somme(Moyenne Matière × Coefficient) / Somme(Coefficients)
```

**Exemple**:
```
FRANÇAIS (Coef 4): 15/20 → 15 × 4 = 60
MATH (Coef 4): 14/20 → 14 × 4 = 56
HISTOIRE (Coef 2): 16/20 → 16 × 2 = 32
GÉOGRAPHIE (Coef 2): 13/20 → 13 × 2 = 26

Total Points: 60 + 56 + 32 + 26 = 174
Total Coefficients: 4 + 4 + 2 + 2 = 12

Moyenne Générale = 174 / 12 = 14.5/20
```

### 4. Mentions et Appréciations

**Échelle des Mentions**:
```
18 - 20  → Excellent
16 - 17.99 → Très Bien
14 - 15.99 → Bien
12 - 13.99 → Assez Bien
10 - 11.99 → Passable
0 - 9.99  → Insuffisant
```

### 5. Rang de l'Élève

**Classement**:
```
Rang = Position selon moyenne générale décroissante
1er → Meilleure moyenne
2ème → Deuxième meilleure
...
Dernier → Plus faible moyenne
```

### 6. Gestion des Absents

**Règles**:
```
- Absent à un devoir: Ne compte pas dans la moyenne des devoirs
- Absent à la composition: Moyenne = Moyenne des devoirs uniquement
- Absent à tous les devoirs: Moyenne = Composition uniquement
- Absent partout: Pas de moyenne
```

**Exemple**:
```
D1: 15, D2: Absent, D3: 14, Composition: 16

Moyenne Devoirs = (15 + 14) / 2 = 14.5
Moyenne Trimestre = (14.5 + 16) / 2 = 15.25
```

### 7. Notes Mensuelles

**Utilisation**:
```
Notes mensuelles = Suivi continu
Ne remplacent pas les devoirs/compositions
Peuvent servir de référence pour les devoirs
```

### 8. Bulletin Trimestriel/Semestriel

**Contenu**:
```
Pour chaque matière:
- Devoirs (D1, D2, D3...)
- Composition
- Moyenne de la matière
- Coefficient
- Total points (Moyenne × Coef)

Totaux:
- Somme des points
- Somme des coefficients
- Moyenne générale
- Rang
- Mention
- Appréciation générale
```

---

## 🔢 IMPLÉMENTATION

### Calcul Automatique

**Quand calculer**:
```
✅ Après chaque saisie de note
✅ Lors de la consultation
✅ Lors de la génération de bulletin
✅ En temps réel si possible
```

**Ce qui doit être calculé**:
```
1. Moyenne des devoirs par période
2. Moyenne de la période (devoirs + composition)
3. Moyenne annuelle de la matière
4. Total points par matière (moyenne × coefficient)
5. Moyenne générale de l'élève
6. Rang de l'élève dans la classe
7. Mention de l'élève
8. Appréciation automatique
```

### Stockage

**Tables nécessaires**:
```
- NoteEleve: Notes individuelles
- MoyennePeriode: Moyennes par période/matière
- MoyenneAnnuelle: Moyennes annuelles par matière
- MoyenneGenerale: Moyenne générale de l'élève
- Classement: Rang de l'élève
```

---

## ✅ VALIDATION

**Règles de validation**:
```
✅ Note entre 0 et 20
✅ Coefficient > 0
✅ Au moins 1 note pour calculer une moyenne
✅ Gestion des absents
✅ Arrondi à 2 décimales
```

**Cas particuliers**:
```
- Élève absent à toutes les évaluations: "Non évalué"
- Matière sans note: Ne compte pas dans la moyenne générale
- Note > 20: Erreur de saisie
- Note < 0: Erreur de saisie
```

---

## 🎓 EXEMPLE COMPLET

### Élève: Mamadou BAH - 7ème Année

**Trimestre 1 - FRANÇAIS (Coef 4)**:
```
Devoir 1: 15/20
Devoir 2: 14/20
Devoir 3: 16/20
Composition: 17/20

Moyenne Devoirs = (15 + 14 + 16) / 3 = 15/20
Moyenne Trimestre = (15 + 17) / 2 = 16/20
```

**Trimestre 1 - MATHÉMATIQUES (Coef 4)**:
```
Devoir 1: 12/20
Devoir 2: 13/20
Devoir 3: 14/20
Composition: 15/20

Moyenne Devoirs = (12 + 13 + 14) / 3 = 13/20
Moyenne Trimestre = (13 + 15) / 2 = 14/20
```

**Trimestre 1 - HISTOIRE (Coef 2)**:
```
Devoir 1: 16/20
Devoir 2: 15/20
Devoir 3: 17/20
Composition: 16/20

Moyenne Devoirs = (16 + 15 + 17) / 3 = 16/20
Moyenne Trimestre = (16 + 16) / 2 = 16/20
```

**Moyenne Générale Trimestre 1**:
```
FRANÇAIS: 16 × 4 = 64
MATH: 14 × 4 = 56
HISTOIRE: 16 × 2 = 32

Total: 152
Coefficients: 10

Moyenne Générale = 152 / 10 = 15.2/20
Mention: Bien
Rang: À calculer selon la classe
```

---

## 🎯 PRIORITÉS D'IMPLÉMENTATION

1. **Calcul moyennes de période** ✅
2. **Calcul moyenne générale** ✅
3. **Attribution des mentions** ✅
4. **Calcul des rangs** ✅
5. **Gestion des absents** ✅
6. **Bulletin automatique** 🔄
7. **Statistiques de classe** 🔄

---

**Ce système garantit des calculs conformes au système éducatif guinéen !**
