# 📋 Guide du Système de Pointage des Enseignants

## 🎯 Vue d'ensemble

Le système de pointage permet de suivre la présence quotidienne des enseignants avec un suivi détaillé des heures de travail, des absences et des retards.

---

## 🚀 Fonctionnalités Principales

### 1. **Pointage Quotidien**
- Pointage multiple d'enseignants en une seule action
- Sélection de la date de pointage
- Statuts disponibles :
  - ✅ **PRÉSENT** : Enseignant présent
  - ❌ **ABSENT** : Enseignant absent
  - ⏰ **RETARD** : Enseignant en retard
  - 🏖️ **CONGÉ** : Enseignant en congé
  - 🏥 **MALADIE** : Enseignant malade
  - 📝 **PERMISSION** : Enseignant en permission

### 2. **Suivi des Heures**
- Enregistrement de l'heure d'arrivée
- Enregistrement de l'heure de départ
- Calcul automatique des heures travaillées
- Possibilité de saisie manuelle des heures

### 3. **Gestion des Justificatifs**
- Marquage des absences/retards justifiés
- Champ observations pour motifs détaillés

### 4. **Rapports et Statistiques**
- Rapport par enseignant et période
- Statistiques en temps réel :
  - Total des présents
  - Total des absents
  - Total des retards
  - Heures travaillées
  - Absences injustifiées
- Export CSV pour analyse externe

---

## 📍 Accès aux Fonctionnalités

### URLs Disponibles

| Fonctionnalité | URL | Description |
|----------------|-----|-------------|
| **Liste des présences** | `/salaires/presences/` | Vue d'ensemble avec filtres |
| **Pointer présence** | `/salaires/presences/pointer/` | Interface de pointage |
| **Modifier présence** | `/salaires/presences/<id>/modifier/` | Modification d'un pointage |
| **Supprimer présence** | `/salaires/presences/<id>/supprimer/` | Suppression sécurisée |
| **Rapport** | `/salaires/presences/rapport/` | Rapport détaillé |
| **Export CSV** | `/salaires/presences/export/csv/` | Export des données |

---

## 🎨 Guide d'Utilisation

### 1. Pointer la Présence Quotidienne

1. Accédez à **Salaires** > **Pointage des Présences**
2. Cliquez sur **Pointer Présence**
3. Sélectionnez la date du pointage
4. Cochez les enseignants à pointer
5. Pour chaque enseignant :
   - Sélectionnez le statut (Présent, Absent, etc.)
   - Saisissez l'heure d'arrivée (optionnel)
   - Saisissez l'heure de départ (optionnel)
   - Saisissez les heures travaillées (optionnel, calculé auto)
   - Cochez "Justifié" si nécessaire
   - Ajoutez des observations si besoin
6. Cliquez sur **Enregistrer le Pointage**

### 2. Consulter les Présences

1. Accédez à **Salaires** > **Pointage des Présences**
2. Utilisez les filtres :
   - **Date début / Date fin** : Période à consulter
   - **Enseignant** : Filtrer par enseignant spécifique
   - **Statut** : Filtrer par type de présence
3. Consultez les statistiques en haut de page
4. Modifiez ou supprimez un pointage si nécessaire

### 3. Générer un Rapport

1. Cliquez sur **Rapport** dans la page des présences
2. Sélectionnez la période (date début/fin)
3. Filtrez par enseignant si souhaité
4. Consultez le tableau récapitulatif :
   - Nombre de présences par type
   - Total des heures travaillées
   - Absences injustifiées
5. Exportez en CSV si nécessaire

### 4. Exporter les Données

1. Dans la liste des présences ou le rapport
2. Cliquez sur **Exporter CSV**
3. Le fichier téléchargé contient :
   - Date, Enseignant, Statut
   - Heures d'arrivée et de départ
   - Heures travaillées
   - Justification et observations

---

## 💡 Conseils et Bonnes Pratiques

### ✅ Pointage Efficace

1. **Pointage quotidien** : Effectuez le pointage chaque jour pour un suivi précis
2. **Heures précises** : Saisissez les heures d'arrivée/départ pour un calcul exact
3. **Justificatifs** : Documentez toujours les absences avec observations
4. **Vérification** : Consultez régulièrement les rapports pour détecter les anomalies

### ⚠️ Gestion des Absences

1. **Absences justifiées** : Cochez systématiquement si justificatif fourni
2. **Observations détaillées** : Précisez le motif (maladie, congé, etc.)
3. **Suivi** : Identifiez rapidement les absences injustifiées répétées

### 📊 Utilisation des Rapports

1. **Rapport mensuel** : Générez un rapport en fin de mois
2. **Analyse** : Identifiez les tendances (retards fréquents, absences)
3. **Calcul salaires** : Utilisez les heures travaillées pour les enseignants horaires
4. **Export** : Conservez les exports CSV pour archivage

---

## 🔧 Fonctionnalités Techniques

### Calcul Automatique des Heures

Le système calcule automatiquement les heures travaillées :
```
Heures travaillées = Heure de départ - Heure d'arrivée
```

Si les heures ne sont pas saisies, vous pouvez entrer manuellement le nombre d'heures.

### Contraintes et Validations

- **Unicité** : Un seul pointage par enseignant et par jour
- **Date** : La date de pointage est obligatoire
- **Statut** : Le statut est obligatoire (défaut : PRÉSENT)
- **Heures** : Les heures sont optionnelles mais recommandées

### Index de Base de Données

Le système utilise des index optimisés pour :
- Recherche rapide par enseignant et date
- Filtrage par date et statut
- Performances optimales même avec beaucoup de données

---

## 🎓 Interface Admin Django

Les super-administrateurs ont accès à l'interface admin Django :

**URL** : `/admin/salaires/presenceenseignant/`

**Fonctionnalités** :
- Vue liste avec tous les champs
- Filtres avancés (statut, date, école, justification)
- Recherche par nom d'enseignant
- Hiérarchie par date pour navigation rapide
- Édition en masse

---

## 📈 Statistiques Disponibles

### Vue Liste
- **Total Pointages** : Nombre total de pointages
- **Présents** : Nombre d'enseignants présents
- **Absents** : Nombre d'enseignants absents
- **Retards** : Nombre de retards enregistrés

### Rapport Détaillé
Pour chaque enseignant :
- Nombre de présences
- Nombre d'absences (justifiées/injustifiées)
- Nombre de retards
- Nombre de congés, maladies, permissions
- Total des heures travaillées
- Absences injustifiées

---

## 🔐 Sécurité et Permissions

- ✅ Accès réservé aux utilisateurs connectés
- ✅ Filtrage automatique par école de l'utilisateur
- ✅ Traçabilité : Enregistrement de l'utilisateur qui a pointé
- ✅ Horodatage : Date de création et modification automatiques
- ✅ Validation des données côté serveur

---

## 📞 Support

Pour toute question ou problème :
1. Consultez ce guide
2. Vérifiez les messages d'erreur affichés
3. Contactez l'administrateur système

---

## 🎉 Résumé

Le système de pointage des enseignants offre :
- ✅ Pointage rapide et efficace
- ✅ Suivi détaillé des heures
- ✅ Gestion des absences et justificatifs
- ✅ Rapports complets et exports
- ✅ Interface intuitive et moderne
- ✅ Sécurité et traçabilité

**Bonne utilisation du système de pointage !** 🚀
