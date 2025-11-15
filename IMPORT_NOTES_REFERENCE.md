# 📚 Référence Rapide - Import de Notes

## 🚀 Accès Direct
```
https://www.myschoolgn.space/notes/importer/
```

## 📝 Workflow en 3 étapes

### 1️⃣ Télécharger le template
- Sélectionner : Classe → Matière → Période
- Cliquer : "Télécharger Template Excel"
- Résultat : Fichier Excel avec élèves pré-remplis

### 2️⃣ Remplir les notes
```excel
| Matricule | Prénom | Nom | Note | Absent |
|-----------|---------|-----|------|--------|
| 6A-001    | Ali     | BAH | 15.5 | NON    |
```

### 3️⃣ Importer le fichier
- Uploader le fichier complété
- Cliquer : "Importer les Notes"
- Vérifier : Statistiques d'import

## ✅ Formats acceptés
- Excel (.xlsx) ⭐ Recommandé
- Excel ancien (.xls)
- CSV (.csv)

## 📊 Types d'importation

| Type | Périodes disponibles |
|------|---------------------|
| **Notes Mensuelles** | Oct, Nov, Déc, Jan, Fév, Mar, Avr, Mai |
| **Compositions** | Trim 1, Trim 2, Trim 3, Sem 1, Sem 2 |
| **Évaluations** | Devoirs, Contrôles, Examens |

## ⚠️ Règles importantes
- Notes entre **0 et 20**
- Absent = **OUI** ou **NON**
- Ne pas modifier les **matricules**
- Respecter les **noms de colonnes**

## 🎯 Gain de temps
- **Manuel** : 30 min pour 30 notes
- **Import** : 2 min pour 30 notes
- **Économie** : 93% de temps gagné

## 🔧 Dépannage rapide

| Problème | Solution |
|----------|----------|
| "Matricule introuvable" | Vérifier que l'élève existe |
| "Note invalide" | Doit être entre 0 et 20 |
| "Colonnes manquantes" | Utiliser le template fourni |
| "Format non supporté" | Utiliser .xlsx, .xls ou .csv |

## 📱 Support API

```javascript
// Récupérer matières d'une classe
fetch('/notes/api/matieres-classe/?classe_id=1')

// Récupérer évaluations d'une matière  
fetch('/notes/api/evaluations-matiere/?matiere_id=5')
```

## ✨ Fonctionnalités clés
- ✅ Templates automatiques
- ✅ Validation en temps réel
- ✅ Gestion des absents
- ✅ Mise à jour des notes existantes
- ✅ Transaction sécurisée (rollback si erreur)
- ✅ Statistiques d'import détaillées

---
**Disponible maintenant** : [Importer des notes →](https://www.myschoolgn.space/notes/importer/)
