# GUIDE COMPLET D'IMPORT - NOTES ET ÉLÈVES

## 🎯 Objectif

Ce guide explique comment utiliser les fonctions d'import pour :
- ✅ Importer des notes en masse (Excel/CSV)
- ✅ Importer des élèves en masse (Excel/CSV)
- ✅ Vérifier que tout fonctionne correctement

---

## 📊 IMPORT DE NOTES

### 1. Accès à la Fonction

**URL** : `https://www.myschoolgn.space/notes/importer/`

**Permissions requises** :
- Utilisateur connecté
- Accès à la classe concernée

### 2. Processus d'Import

#### Étape 1 : Télécharger le Template

1. Aller sur `/notes/importer/`
2. Sélectionner la **classe**
3. Sélectionner la **matière**
4. Sélectionner le **type** (Mensuelle, Composition, Évaluation)
5. Cliquer sur **"Télécharger le template"**

**Le template contient** :
- Liste de tous les élèves actifs de la classe
- Colonnes pré-remplies (Matricule, Nom, Prénom)
- Colonnes à remplir (Note, Absent, Observation)

#### Étape 2 : Remplir le Template

```excel
| Matricule    | Nom      | Prénom   | Note | Absent | Observation |
|--------------|----------|----------|------|--------|-------------|
| L12SL-001    | BALDE    | ALPHA    | 15.5 | Non    |             |
| L12SL-002    | DIALLO   | AISSATOU | 18.0 | Non    | Excellent   |
| L12SL-003    | BARRY    | AMADOU   |      | Oui    | Absent      |
```

**Règles** :
- ✅ **Note** : Entre 0 et 20 (décimales autorisées)
- ✅ **Absent** : "Oui" ou "Non" (ou vide = Non)
- ✅ **Observation** : Texte libre (optionnel)
- ⚠️  Si Absent = "Oui", la note n'est pas obligatoire

#### Étape 3 : Importer le Fichier

1. Retourner sur `/notes/importer/`
2. Sélectionner les mêmes paramètres (classe, matière, type)
3. Sélectionner la **période** (OCTOBRE, NOVEMBRE, etc.)
4. Uploader le fichier Excel rempli
5. Cliquer sur **"Importer"**

#### Étape 4 : Vérifier les Résultats

Le système affiche :
- ✅ Nombre de notes importées avec succès
- ❌ Nombre d'erreurs
- 📋 Liste détaillée des erreurs (si présentes)
- 📊 Statistiques (notes créées, mises à jour, absents)

### 3. Types d'Import

#### A. Import Mensuel (MENSUELLE)

- Crée une évaluation pour le mois
- Nom automatique : "Devoir Octobre", "Devoir Novembre", etc.
- Une seule note par élève pour la période

#### B. Import Composition (COMPOSITION)

- Crée une évaluation de type composition
- Nom automatique : "Composition 1", "Composition 2", etc.
- Coefficient généralement plus élevé

#### C. Import Évaluation Spécifique

- Importe des notes pour une évaluation existante
- Nécessite de sélectionner l'évaluation
- Met à jour les notes existantes

### 4. Gestion des Erreurs

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Matricule non trouvé" | Élève n'existe pas | Vérifier le matricule |
| "Note invalide" | Note < 0 ou > 20 | Corriger la note |
| "Colonne manquante" | Template modifié | Re-télécharger le template |
| "Élève inactif" | Statut ≠ ACTIF | Réactiver l'élève |

---

## 👥 IMPORT D'ÉLÈVES

### 1. Accès à la Fonction

**URL** : `https://www.myschoolgn.space/eleves/importer/`

**Permissions requises** :
- Utilisateur connecté
- Droits d'administration ou de gestion des élèves

### 2. Processus d'Import

#### Étape 1 : Télécharger le Template

1. Aller sur `/eleves/importer/`
2. Sélectionner la **classe**
3. Cliquer sur **"Télécharger le template"**

**Le template contient** :
- Colonnes pour toutes les informations élève
- Format pré-défini
- Exemples de données

#### Étape 2 : Remplir le Template

```excel
| Nom    | Prénom   | Sexe | Date Naissance | Lieu Naissance | Téléphone Responsable | Nom Responsable |
|--------|----------|------|----------------|----------------|----------------------|-----------------|
| DIALLO | MAMADOU  | M    | 2008-05-15     | Conakry        | +224621234567        | DIALLO Ibrahima |
| SOW    | FATOUMATA| F    | 2009-03-20     | Labé           | +224622345678        | SOW Aissatou    |
```

**Colonnes obligatoires** :
- ✅ Nom
- ✅ Prénom
- ✅ Sexe (M ou F)
- ✅ Date de naissance (format: AAAA-MM-JJ)

**Colonnes optionnelles** :
- Lieu de naissance
- Téléphone responsable
- Nom responsable
- Lien de parenté
- Adresse
- etc.

#### Étape 3 : Importer le Fichier

1. Retourner sur `/eleves/importer/`
2. Sélectionner la **classe**
3. Uploader le fichier Excel rempli
4. Cliquer sur **"Importer"**

#### Étape 4 : Vérifier les Résultats

Le système affiche :
- ✅ Nombre d'élèves importés
- 📋 Matricules générés automatiquement
- ❌ Erreurs éventuelles
- 📊 Statistiques d'import

### 3. Génération Automatique

#### Matricules

Le système génère automatiquement les matricules :
- Format : `{PREFIXE_CLASSE}-{NUMERO}`
- Exemple : `L12SL-001`, `L12SL-002`, etc.
- Numérotation séquentielle automatique

#### Responsables

Si un responsable avec le même téléphone existe :
- ✅ Réutilisation du responsable existant
- ✅ Pas de doublon

Sinon :
- ✅ Création automatique du responsable
- ✅ Lien avec l'élève

### 4. Gestion des Erreurs

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Nom manquant" | Colonne vide | Remplir le nom |
| "Sexe invalide" | Valeur ≠ M ou F | Corriger (M ou F) |
| "Date invalide" | Format incorrect | Utiliser AAAA-MM-JJ |
| "Doublon" | Élève existe déjà | Vérifier les données |

---

## 🧪 TESTS DE VÉRIFICATION

### Test 1 : Import de Notes

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
python test_import_notes.py
```

**Vérifie** :
- ✅ Génération du template
- ✅ Validation des données
- ✅ Simulation d'import
- ✅ Vérification des évaluations
- ✅ Vérification des notes existantes

### Test 2 : Import d'Élèves

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
python test_import_eleves.py
```

**Vérifie** :
- ✅ Génération du template
- ✅ Validation des données
- ✅ Génération des matricules
- ✅ Création des responsables
- ✅ Import complet

---

## 📋 CHECKLIST D'UTILISATION

### Avant l'Import

- [ ] Télécharger le template approprié
- [ ] Vérifier que toutes les colonnes obligatoires sont présentes
- [ ] Remplir les données correctement
- [ ] Vérifier les formats (dates, notes, sexe)
- [ ] Sauvegarder le fichier en Excel (.xlsx)

### Pendant l'Import

- [ ] Sélectionner les bons paramètres (classe, matière, période)
- [ ] Uploader le fichier
- [ ] Attendre la fin du traitement
- [ ] Ne pas fermer la page pendant l'import

### Après l'Import

- [ ] Vérifier le nombre d'éléments importés
- [ ] Lire les messages d'erreur (si présents)
- [ ] Corriger les erreurs et ré-importer si nécessaire
- [ ] Vérifier les données dans l'application

---

## 🎯 BONNES PRATIQUES

### 1. Préparation des Données

✅ **À FAIRE** :
- Utiliser le template fourni
- Vérifier les données avant import
- Faire un test avec 2-3 lignes d'abord
- Garder une copie du fichier original

❌ **À ÉVITER** :
- Modifier les en-têtes de colonnes
- Supprimer des colonnes obligatoires
- Utiliser des formats de date différents
- Importer des fichiers trop volumineux (> 500 lignes)

### 2. Gestion des Erreurs

✅ **En cas d'erreur** :
1. Lire attentivement le message d'erreur
2. Identifier la ligne problématique
3. Corriger dans le fichier Excel
4. Ré-importer uniquement les lignes corrigées

### 3. Import Progressif

Pour les grandes classes (> 50 élèves) :
1. Diviser le fichier en plusieurs parties
2. Importer par groupes de 20-30
3. Vérifier après chaque import
4. Continuer avec le groupe suivant

---

## 🔧 DÉPANNAGE

### Problème : "Template ne se télécharge pas"

**Solutions** :
1. Vérifier la connexion internet
2. Essayer un autre navigateur
3. Vider le cache du navigateur
4. Vérifier que la classe/matière existe

### Problème : "Import échoue sans message"

**Solutions** :
1. Vérifier la taille du fichier (< 5 MB)
2. Vérifier le format (Excel .xlsx)
3. Vérifier les permissions utilisateur
4. Consulter les logs serveur

### Problème : "Notes ne s'affichent pas après import"

**Solutions** :
1. Rafraîchir la page (F5)
2. Vider le cache (Ctrl+F5)
3. Vérifier la période sélectionnée
4. Vérifier que l'évaluation est active

---

## 📊 EXEMPLES PRATIQUES

### Exemple 1 : Import de Notes Mensuelles

```
Classe : 12 SÉRIE SCIENTIFIQUE
Matière : Mathématique
Type : MENSUELLE
Période : OCTOBRE

Fichier : notes_maths_octobre.xlsx
Contenu : 18 élèves, 15 notes + 3 absents
Résultat : ✅ 18 notes importées (15 avec note, 3 absents)
```

### Exemple 2 : Import d'Élèves

```
Classe : 7ème Année
Fichier : eleves_7eme.xlsx
Contenu : 25 nouveaux élèves

Résultat :
- ✅ 25 élèves créés
- ✅ 25 matricules générés (7A-001 à 7A-025)
- ✅ 18 responsables créés (7 réutilisés)
```

---

## ✅ CONCLUSION

Les fonctions d'import sont **opérationnelles** et **testées** :

- ✅ **Import de notes** : `/notes/importer/`
- ✅ **Import d'élèves** : `/eleves/importer/`
- ✅ **Templates disponibles**
- ✅ **Validation automatique**
- ✅ **Gestion des erreurs**
- ✅ **Tests de vérification**

**Utilisez les templates fournis et suivez ce guide pour un import réussi !** 🚀

---

## 📞 Support

En cas de problème :

1. Exécuter les tests : `python test_import_notes.py`
2. Consulter les logs : `/home/myschoolgn/GS_hadja_kanfing_dian-/logs/django.log`
3. Vérifier les permissions utilisateur
4. Consulter ce guide

**Tout est documenté et testé !** ✅
