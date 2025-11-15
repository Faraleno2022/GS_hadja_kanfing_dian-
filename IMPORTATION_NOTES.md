# 📥 Importation de Notes - Guide Complet

**Date:** 15 novembre 2024  
**Fonctionnalité:** Importation massive de notes depuis fichiers Excel/CSV  
**Statut:** ✅ Prêt pour utilisation

---

## 🎯 Fonctionnalités

### Types d'importation supportés

1. **Notes Mensuelles** (système guinéen: Octobre → Mai)
2. **Notes de Composition** (Trimestres/Semestres)
3. **Notes d'Évaluation** (Devoirs, Contrôles, Examens)

### Formats supportés

- ✅ Excel (.xlsx, .xls)
- ✅ CSV (.csv)

---

## 📋 Prérequis

### Dépendances Python requises

```bash
pip install pandas openpyxl
```

Ou ajoutez dans `requirements.txt`:
```txt
pandas>=2.0.0
openpyxl>=3.1.0
```

---

## 🚀 Utilisation

### 1. Accéder à l'interface d'importation

```
URL: /notes/importer/
Menu: Notes → Importer des Notes
```

### 2. Processus d'importation

#### Étape 1: Sélection des paramètres
- **Type de notes** : Mensuelle, Composition ou Évaluation
- **Classe** : Sélectionner la classe concernée
- **Matière** : Sélectionner la matière
- **Période** : Choisir la période (mois, trimestre, semestre)
- **Année scolaire** : Format 2024-2025

#### Étape 2: Télécharger le template
- Cliquer sur "Télécharger le Template"
- Un fichier Excel est généré avec tous les élèves de la classe

#### Étape 3: Remplir les notes
- Ouvrir le fichier Excel téléchargé
- **NE PAS modifier** les colonnes Matricule, Prénom, Nom
- Remplir uniquement les colonnes:
  - `Note` : Note sur 20 (laisser vide si absent)
  - `Absent` : OUI ou NON

#### Étape 4: Uploader le fichier
- Sélectionner le fichier complété
- Cliquer sur "Importer les Notes"

### 3. Résultat de l'importation

Le système affiche:
- ✅ Nombre de notes créées
- 🔄 Nombre de notes mises à jour
- 👤 Nombre d'absents
- ❌ Nombre d'erreurs

---

## 📝 Format du fichier Excel

### Structure requise

| Matricule | Prénom | Nom | Note | Absent |
|-----------|--------|-----|------|--------|
| CL10-001  | Jean   | DUPONT | 15.5 | NON |
| CL10-002  | Marie  | MARTIN | | OUI |
| CL10-003  | Paul   | BERNARD | 17.0 | NON |

### Règles de validation

1. **Matricule**: Obligatoire, doit correspondre à un élève existant
2. **Note**: Entre 0 et 20 (vide si absent)
3. **Absent**: 
   - Valeurs acceptées pour OUI: `OUI`, `O`, `YES`, `Y`, `1`, `TRUE`
   - Valeurs acceptées pour NON: `NON`, `N`, `NO`, `0`, `FALSE`, (vide)

---

## ⚙️ Fichiers créés

### 1. Module d'importation
**Fichier:** `notes/import_notes.py`

Classes:
- `ImportNotesValidator` : Valide les données importées
- `ImportNotesProcessor` : Traite l'importation
- `ImportNotesError` : Exception personnalisée

Fonctions:
- `lire_fichier_import()` : Lit Excel/CSV
- `generer_template_excel()` : Génère le template

### 2. Vues
**Fichier:** `notes/views_import.py`

Vues:
- `importer_notes()` : Vue principale d'importation
- `telecharger_template_import()` : Génère et télécharge le template
- `get_matieres_classe()` : API AJAX pour les matières
- `get_evaluations_matiere()` : API AJAX pour les évaluations

### 3. Template HTML
**Fichier:** `templates/notes/importer_notes.html`

Interface utilisateur avec:
- Formulaire d'upload
- Sélection dynamique (AJAX)
- Instructions intégrées
- Validation côté client

### 4. URLs
**Fichier:** `notes/urls.py`

Routes ajoutées:
- `/notes/importer/` : Page d'importation
- `/notes/template-import/` : Téléchargement template
- `/notes/api/matieres-classe/` : API matières
- `/notes/api/evaluations-matiere/` : API évaluations

---

## 🔒 Sécurité

### Permissions requises
- Utilisateur connecté (`@login_required`)
- Permission de gestion des notes (`can_manage_notes`)

### Validation
- ✅ Vérification des matricules
- ✅ Validation des notes (0-20)
- ✅ Détection des doublons
- ✅ Transaction atomique (rollback en cas d'erreur)

---

## 📊 Gestion des erreurs

### Erreurs détectées

1. **Matricule introuvable**
   ```
   Ligne 5: Élève avec matricule 'CL10-999' introuvable
   ```

2. **Note invalide**
   ```
   Ligne 8: Note invalide (25.5) - doit être entre 0 et 20
   ```

3. **Format incorrect**
   ```
   Ligne 12: Format de note invalide (ABC)
   ```

4. **Colonnes manquantes**
   ```
   Colonnes manquantes: Note, Absent
   ```

### Avertissements

```
Ligne 10: Note manquante pour JEAN DUPONT
```

---

## 💡 Cas d'usage

### Cas 1: Importer notes mensuelles

```
Type: Notes Mensuelles
Classe: 10ÈME ANNÉE (A)
Matière: Mathématiques
Période: OCTOBRE
Année: 2024-2025
Fichier: notes_maths_octobre.xlsx
```

### Cas 2: Importer une composition

```
Type: Notes de Composition
Classe: 10ÈME ANNÉE (A)
Matière: Français
Période: TRIMESTRE_1
Année: 2024-2025
Fichier: compo_francais_t1.xlsx
```

### Cas 3: Importer notes d'évaluation

```
Type: Notes d'Évaluation
Classe: 10ÈME ANNÉE (A)
Matière: Anglais
Évaluation: Devoir 1 - Grammaire
Période: OCTOBRE
Année: 2024-2025
Fichier: devoir_anglais.xlsx
```

---

## 🔧 Configuration

### Paramètres Django

Aucune configuration spécifique requise. Les modèles existants sont utilisés:
- `NoteMensuelle`
- `CompositionNote`
- `NoteEleve` (avec `Evaluation`)

### Limites

- Taille maximale fichier: Définie par Django `DATA_UPLOAD_MAX_MEMORY_SIZE`
- Nombre d'élèves: Illimité (traité en transaction)
- Formats Excel: .xlsx, .xls (via openpyxl)

---

## 🧪 Tests

### Test 1: Import basique

1. Créer une classe avec quelques élèves
2. Télécharger le template
3. Remplir 3-4 notes
4. Importer
5. Vérifier dans "Consulter Notes"

### Test 2: Gestion des absents

1. Télécharger le template
2. Marquer 2 élèves comme absents (OUI)
3. Laisser leurs notes vides
4. Importer
5. Vérifier: notes à 0, absents marqués

### Test 3: Mise à jour

1. Importer des notes
2. Modifier le fichier Excel
3. Réimporter
4. Vérifier: notes mises à jour (pas de doublons)

---

## 📈 Statistiques d'importation

Après chaque importation, un résumé est affiché:

```
✅ Importation réussie!
   • 45 note(s) créée(s)
   • 2 note(s) mise(s) à jour
   • 3 absent(s)
   • 0 erreur(s)
```

---

## 🐛 Dépannage

### Problème 1: "Module pandas introuvable"

**Solution:**
```bash
pip install pandas openpyxl
```

### Problème 2: "Matières non chargées"

**Cause:** Problème AJAX  
**Solution:** Vérifier la console navigateur, recharger la page

### Problème 3: "Élève introuvable"

**Cause:** Matricule incorrect ou élève inactif  
**Solution:** Vérifier le matricule dans la liste des élèves

### Problème 4: "Colonnes manquantes"

**Cause:** Template modifié  
**Solution:** Télécharger à nouveau le template officiel

---

## 🎓 Bonnes pratiques

1. **Toujours utiliser le template généré** (garantit les bons matricules)
2. **Ne jamais modifier** les colonnes identité (Matricule, Prénom, Nom)
3. **Vérifier les notes** avant d'importer (erreurs de saisie)
4. **Tester avec peu d'élèves** avant import massif
5. **Faire une sauvegarde** avant import important

---

## 📞 Support

En cas de problème:
1. Vérifier les messages d'erreur affichés
2. Consulter cette documentation
3. Vérifier les logs Django
4. Contacter l'administrateur système

---

## 🔄 Évolutions futures possibles

- [ ] Import multi-matières en un fichier
- [ ] Import avec commentaires personnalisés
- [ ] Historique des importations
- [ ] Prévisualisation avant import
- [ ] Export/Import format JSON
- [ ] Validation avancée (règles métier)

---

**Auteur:** Cascade AI  
**Date:** 15 novembre 2024  
**Version:** 1.0  
**Statut:** ✅ Production Ready
