# 📅 Guide Complet - Notes Mensuelles (Système Guinéen)

## ✅ Fonctionnalité Ajoutée

Le système de gestion de notes supporte maintenant les **bulletins mensuels** conformément au système guinéen d'évaluation.

---

## 📊 Périodes Mensuelles Disponibles

1. **OCTOBRE**
2. **NOVEMBRE**
3. **DÉCEMBRE**
4. **JANVIER**
5. **FÉVRIER**
6. **MARS**
7. **AVRIL**
8. **MAI**
9. **JUIN**

---

## 🚀 Utilisation Rapide (Mode Automatique)

### Créer des notes mensuelles en une commande :

```bash
python gerer_notes_mensuelles.py --auto
```

**Ce que fait cette commande :**
- ✅ Crée 3 évaluations par matière (2 devoirs + 1 composition)
- ✅ Saisit automatiquement des notes pour les 5 premiers élèves
- ✅ Génère un bulletin exemple pour le 1er élève
- ✅ Fournit l'URL pour consulter le bulletin

**Résultat attendu :**
```
✅ 27 évaluations créées pour OCTOBRE
✅ 135 notes créées
📊 Bulletin affiché pour BAH IBRAHIMA
   Moyenne générale: 12.95/20
   Mention: Assez Bien
```

---

## 🎯 Utilisation Manuelle (Mode Interactif)

### Lancer le menu interactif :

```bash
python gerer_notes_mensuelles.py
```

### Options disponibles :

#### 1️⃣ Créer des évaluations mensuelles
- Créer les devoirs et compositions pour un mois donné
- Par défaut : 2 devoirs + 1 composition par matière

#### 2️⃣ Saisir des notes mensuelles  
- Générer automatiquement des notes aléatoires
- Choisir le nombre d'élèves

#### 3️⃣ Afficher un bulletin mensuel
- Voir l'aperçu du bulletin d'un élève
- Obtenir l'URL pour le bulletin complet

#### 4️⃣ Tout faire automatiquement
- Combine les étapes 1 et 2
- Solution rapide pour tests

---

## 🌐 Consulter les Bulletins Mensuels

### URL Type :
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=mensuel&periode=OCTOBRE&eleve_id=805
```

### Paramètres Requis :

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `classe_id` | ID de la classe | 6 |
| `system_type` | Type de bulletin | **mensuel** |
| `periode` | Mois (MAJUSCULES) | OCTOBRE |
| `eleve_id` | ID de l'élève | 805 |

---

## 📋 Format du Bulletin Mensuel

### Structure d'affichage :

| MATIÈRE | NOTE | COEF | POINTS |
|---------|------|------|--------|
| ANGLAIS | 10.57 | 2 | 21.15 |
| ECM | 12.66 | 1 | 12.66 |
| EPS | 13.47 | 1 | 13.47 |
| ... | ... | ... | ... |
| **TOTAL** | | **20** | **259.07** |

**MOYENNE GÉNÉRALE:** 12.95/20  
**MENTION:** Assez Bien

### Caractéristiques :
- ✅ **1 seule colonne** (NOTE) au lieu de 2
- ✅ La note affichée = **moyenne de tous les devoirs et compositions du mois**
- ✅ Pas de séparation devoirs/compositions (contrairement aux trimestres)

---

## 🔧 Fonctionnement Technique

### Calcul de la Note Mensuelle :

```python
# Pour chaque matière
notes_du_mois = [devoir1, devoir2, composition]
note_affichee = moyenne(notes_du_mois)

# Points
points = note_affichee × coefficient_matiere

# Moyenne générale
moyenne_generale = somme(points) / somme(coefficients)
```

### Différence avec le Système Trimestriel :

| Aspect | Mensuel | Trimestriel |
|--------|---------|-------------|
| Colonnes | 1 (Note) | 2 (Moy. Continue, Composition) |
| Calcul | Moyenne simple | Pondération 1:2 |
| Formule | `Σ notes / nb notes` | `(MC + Comp×2) / 3` |

---

## 📚 Exemples d'Utilisation

### Exemple 1 : Créer notes pour Octobre

```bash
python gerer_notes_mensuelles.py --auto
```

### Exemple 2 : Créer notes pour Novembre (mode interactif)

```bash
python gerer_notes_mensuelles.py
```

Puis choisir :
- Option **4** (Tout faire automatiquement)
- Classe ID : **6**
- Mois : **NOVEMBRE**
- Nombre d'élèves : **10**

### Exemple 3 : Créer plusieurs mois d'un coup

```python
# Créer un script personnalisé
from gerer_notes_mensuelles import creer_evaluations_mensuelles, saisir_notes_mensuelles

for mois in ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE']:
    creer_evaluations_mensuelles(6, mois)
    saisir_notes_mensuelles(6, mois, 10)
```

---

## 🎓 Cas d'Usage

### Cas 1 : École avec système mensuel strict
- Créer les bulletins mois par mois
- Consulter l'évolution mensuelle des élèves
- Impression mensuelle des bulletins

### Cas 2 : École mixte (mensuel + trimestriel)
- Bulletin mensuel pour le suivi continu
- Bulletin trimestriel pour l'évaluation officielle
- Les deux systèmes coexistent sans conflit

### Cas 3 : Tests et démonstrations
- Mode automatique pour créer rapidement des données
- Tester le système avant utilisation réelle

---

## 🔍 Vérification et Débogage

### Vérifier les évaluations créées :

```python
from notes.models import Evaluation

# Compter les évaluations d'Octobre
evals = Evaluation.objects.filter(periode='OCTOBRE')
print(f"Évaluations Octobre: {evals.count()}")

# Par matière
for matiere in matieres:
    count = Evaluation.objects.filter(matiere=matiere, periode='OCTOBRE').count()
    print(f"{matiere.nom}: {count} évaluations")
```

### Vérifier les notes saisies :

```python
from notes.models import NoteEleve

# Notes d'un élève pour Octobre
notes = NoteEleve.objects.filter(
    eleve_id=805,
    evaluation__periode='OCTOBRE'
)
print(f"Notes saisies: {notes.count()}")
```

---

## 📝 Migration Appliquée

Une migration a été créée et appliquée pour ajouter les périodes mensuelles :

```bash
Applying notes.0007_ajouter_periodes_mensuelles... OK
```

**Fichier:** `notes/migrations/0007_ajouter_periodes_mensuelles.py`

**Changement:** Ajout de 9 nouvelles périodes au modèle `Evaluation`

---

## ⚠️ Points Importants

### 1. Périodes en MAJUSCULES
✅ Correct : `OCTOBRE`, `NOVEMBRE`  
❌ Incorrect : `octobre`, `Octobre`

### 2. Paramètre system_type
✅ Correct : `system_type=mensuel`  
❌ Incorrect : `system_type=trimestre` (affichera 2 colonnes)

### 3. Compatibilité
- Les notes mensuelles n'affectent PAS les trimestres
- Chaque système est indépendant
- Même classe, même élève, périodes différentes

### 4. Année scolaire
Les dates sont configurées pour :
- **Octobre-Décembre** : 2024
- **Janvier-Juin** : 2025

---

## 🚀 URLs de Test Générées

### Octobre
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=mensuel&periode=OCTOBRE&eleve_id=805
```

### Novembre
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=mensuel&periode=NOVEMBRE&eleve_id=805
```

### Décembre
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=mensuel&periode=DECEMBRE&eleve_id=805
```

---

## 📊 Statistiques Après Création Automatique

Pour la classe **2ème année** (ID: 6) :

| Élément | Quantité |
|---------|----------|
| Matières | 9 |
| Évaluations par mois | 27 (3 par matière) |
| Notes par élève | 27 |
| Total notes pour 5 élèves | 135 |

---

## 🎯 Prochaines Étapes

1. ✅ **Tester** : Consulter l'URL générée dans le navigateur
2. ✅ **Créer** : Générer des notes pour d'autres mois
3. ✅ **Imprimer** : Utiliser la fonction d'impression du bulletin
4. ✅ **Étendre** : Appliquer à d'autres classes

---

## 💡 Astuces

### Créer rapidement toute l'année :

```bash
# Créer notes pour tous les mois
for mois in OCTOBRE NOVEMBRE DECEMBRE JANVIER FEVRIER MARS AVRIL MAI JUIN
do
    python -c "
from gerer_notes_mensuelles import creer_evaluations_mensuelles, saisir_notes_mensuelles
creer_evaluations_mensuelles(6, '$mois')
saisir_notes_mensuelles(6, '$mois', 10)
"
done
```

### Supprimer les notes d'un mois :

```python
from notes.models import Evaluation, NoteEleve

# Supprimer toutes les évaluations d'Octobre
Evaluation.objects.filter(periode='OCTOBRE').delete()
# Les notes associées seront supprimées automatiquement (CASCADE)
```

---

## 📞 Support

Si vous rencontrez des problèmes :

1. **Vérifiez** que la migration est appliquée
2. **Consultez** les logs du serveur Django
3. **Testez** avec le mode automatique d'abord
4. **Examinez** les données créées dans la base

---

**Dernière mise à jour:** 1er novembre 2025  
**Version:** 1.0  
**Statut:** ✅ Fonctionnel et testé
