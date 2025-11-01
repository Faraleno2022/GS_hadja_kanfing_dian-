# 📊 Génération de Données de Test - Module Notes

## 🎯 Description

Ce document explique comment générer des données de test pour le module de gestion des notes.

## ✅ Données Générées

La commande `generer_donnees_test` crée automatiquement:

- **Classes (Notes)**: Une ClasseNote pour chaque classe d'élèves existante
- **Matières**: 9-11 matières par classe selon le niveau (avec coefficients)
- **Évaluations**: 3 évaluations par matière et par trimestre (Devoir 1, Devoir 2, Composition)
- **Notes**: Notes aléatoires pour tous les élèves actifs de chaque classe

### 📚 Matières Générées

**Matières communes (tous niveaux):**
- FRANÇAIS (Coef: 4)
- MATHEMATIQUE (Coef: 4)
- ANGLAIS (Coef: 2)
- HISTOIRE (Coef: 2)
- GEOGRAPHIE (Coef: 2)
- SCIENCES PHYSIQUES (Coef: 2)
- SCIENCES NATURELLES (Coef: 2)
- EPS (Coef: 1)
- ECM (Coef: 1)

**Matières supplémentaires (Lycée 11ème et 12ème):**
- PHILOSOPHIE (Coef: 3)
- CHIMIE (Coef: 2)

### 📝 Évaluations par Période

Pour chaque matière et chaque trimestre:
- **Devoir 1** (Coef: 1, Note sur: 20)
- **Devoir 2** (Coef: 1, Note sur: 20)
- **Composition** (Coef: 2, Note sur: 20)

**Total:** 3 trimestres × 3 évaluations × nombre de matières

### 🎲 Génération des Notes

Les notes sont générées de manière réaliste selon 4 profils d'élèves:

| Profil | Plage de notes | Probabilité |
|--------|---------------|-------------|
| **Faible** | 5-9/20 | 15% |
| **Moyen** | 10-13/20 | 40% |
| **Bon** | 14-16/20 | 30% |
| **Excellent** | 17-20/20 | 15% |

- Variation aléatoire de ±2 points autour du profil
- 5% de chance d'absence à une évaluation

## 🚀 Utilisation

### Commande de Base

Génère des données pour toutes les classes:

```bash
python manage.py generer_donnees_test
```

### Options Disponibles

#### 1. Générer pour une classe spécifique

```bash
python manage.py generer_donnees_test --classe "7ème"
```

Génère uniquement pour les classes contenant "7ème" dans leur nom.

#### 2. Supprimer les données existantes avant génération

```bash
python manage.py generer_donnees_test --clear
```

⚠️ **ATTENTION**: Cette option supprime TOUTES les données de notes existantes:
- Notes d'élèves
- Évaluations
- Matières
- Classes (Notes)

#### 3. Combiner les options

```bash
python manage.py generer_donnees_test --classe "11ème" --clear
```

## 📊 Vérifier les Données Générées

Après génération, vérifiez les données avec:

```bash
python verifier_donnees_test.py
```

**Résultat attendu:**
```
============================================================
📊 RÉSUMÉ DES DONNÉES DE TEST GÉNÉRÉES
============================================================

✅ Classes (Notes): 8
   - 1ère année
   - 2ème année
   - 3ème année
   - 7ème année
   - garderie
   - petite section
   - 10ème année
   - 11ème série littéraire

✅ Matières: 74

✅ Évaluations: 666
   - Trimestre 1: 222
   - Trimestre 2: 222
   - Trimestre 3: 222

✅ Notes d'élèves: 180

✅ Élèves avec notes: 2
   - LENO FARA: 99 notes
   - LENO FARA: 81 notes

============================================================
✅ Données de test prêtes!
============================================================
```

## 🎯 Cas d'Usage

### 1. Première Installation

```bash
# Générer toutes les données de test
python manage.py generer_donnees_test
```

### 2. Réinitialiser les Données

```bash
# Supprimer et régénérer toutes les données
python manage.py generer_donnees_test --clear
```

### 3. Tester une Classe Spécifique

```bash
# Générer uniquement pour le collège 7ème
python manage.py generer_donnees_test --classe "7ème"
```

### 4. Ajouter des Données pour une Nouvelle Classe

```bash
# Générer pour une nouvelle classe sans toucher aux autres
python manage.py generer_donnees_test --classe "12ème"
```

## 📈 Utilisation des Données

Une fois générées, les données sont utilisables dans:

### 1. Saisie des Notes (`/notes/saisir/`)
- Toutes les évaluations sont créées
- Les notes peuvent être modifiées

### 2. Génération de Bulletins (`/notes/bulletins/`)
- Sélectionner une classe et une période
- Voir les moyennes calculées
- Télécharger les bulletins PDF

### 3. Statistiques (`/notes/statistiques/`)
- Visualiser les graphiques
- Analyser les performances
- Voir le top 10 des élèves

## ⚙️ Configuration Technique

### Structure des Données

```
ClasseNote (8 classes)
├── MatiereNote (9-11 matières par classe)
│   └── Evaluation (9 évaluations par matière: 3 par trimestre)
│       └── NoteEleve (notes pour chaque élève actif)
```

### Calculs Automatiques

**Moyenne par matière:**
```
Moyenne = Σ(note_sur_20 × coef_eval) / Σ(coef_eval)
```

**Moyenne générale:**
```
Moyenne = Σ(moyenne_matière × coef_matière) / Σ(coef_matière)
```

## 🔧 Dépannage

### Problème: "Aucune classe trouvée"

**Solution:** Assurez-vous d'avoir des classes d'élèves dans le module `eleves`:
```bash
python manage.py shell
>>> from eleves.models import Classe
>>> Classe.objects.all()
```

### Problème: "IntegrityError: NOT NULL constraint failed"

**Solution:** Le champ `ecole` est requis. Vérifiez que vos classes ont une école associée.

### Problème: Notes non affichées

**Solution:** 
1. Vérifiez que les élèves sont actifs (`statut='ACTIF'`)
2. Vérifiez la correspondance entre ClasseNote et Classe (module eleves)

## 📝 Notes Importantes

- Les données générées sont **aléatoires** mais **réalistes**
- Les notes respectent une distribution normale
- Chaque élève a un profil cohérent (pas de variation extrême)
- Les absences sont rares (5%)
- Les évaluations sont datées du jour de génération

## 🎓 Exemple Complet

```bash
# 1. Supprimer les anciennes données
python manage.py generer_donnees_test --clear

# 2. Vérifier la génération
python verifier_donnees_test.py

# 3. Tester l'application
# - Aller sur /notes/statistiques/
# - Sélectionner une classe et une période
# - Voir les graphiques et statistiques

# 4. Générer des bulletins
# - Aller sur /notes/bulletins/
# - Sélectionner une classe et une période
# - Télécharger les PDF
```

## ✅ Résultat Final

Après génération, vous aurez:
- ✅ Des classes configurées avec leurs matières
- ✅ Des évaluations pour 3 trimestres
- ✅ Des notes réalistes pour tous les élèves
- ✅ Des statistiques visualisables
- ✅ Des bulletins PDF générables

**Prêt à tester toutes les fonctionnalités du module Notes!** 🎉
