# Interface de Saisie des Notes Guinéennes - Guide d'Utilisation

## Vue d'ensemble

Une interface interactive de saisie des notes mensuelles et de composition a été ajoutée au système de gestion scolaire. Cette interface permet une saisie rapide et intuitive des notes selon le système guinéen.

## Accès à l'Interface

### Via le Menu
1. Connectez-vous à l'application
2. Allez dans **Notes** → **Saisie Notes Guinéennes**
3. Ou accédez directement via l'URL: `/notes/saisie-notes-guineen/`

## Fonctionnalités

### ✅ Sélection du Système
- **Semestriel**: Notes sur 2 semestres (Oct-Jan / Fév-Mai)
- **Trimestriel**: Notes sur 3 trimestres (Oct-Déc / Jan-Mars / Avr-Juin)

### ✅ Saisie par Élève
1. **Sélectionner une classe**
2. **Choisir un élève** dans la liste déroulante
3. Les notes existantes sont automatiquement chargées

### ✅ Interface de Saisie

#### Pour chaque matière:
- **Notes mensuelles** (Octobre à Mai)
  - Saisie directe des notes sur 20
  - Validation automatique (0-20)
  - Support des décimales (ex: 15.5)

- **Notes de composition**
  - Composition 1 (Semestre 1 ou Trimestre 1)
  - Composition 2 (Semestre 2 ou Trimestre 2)
  - Affichage distinct avec fond jaune

#### Sauvegarde:
- **Bouton par matière**: Sauvegarder une matière individuellement
- **Bouton global**: Sauvegarder toutes les matières en une fois

### ✅ Notifications
- Toast de confirmation après chaque sauvegarde
- Messages d'erreur en cas de problème
- Feedback visuel immédiat

## Workflow Recommandé

### 1. Préparation
```
1. Créer les classes dans le système
2. Ajouter les matières avec leurs coefficients
3. Inscrire les élèves dans les classes
```

### 2. Saisie des Notes
```
1. Sélectionner le système (Semestriel/Trimestriel)
2. Choisir la classe
3. Sélectionner un élève
4. Saisir les notes mensuelles pour chaque matière
5. Saisir les notes de composition
6. Sauvegarder (par matière ou tout en une fois)
7. Passer à l'élève suivant
```

### 3. Vérification
```
1. Aller dans "Bulletin Guinéen"
2. Sélectionner la classe et le système
3. Vérifier les calculs automatiques
4. Imprimer si nécessaire
```

## Caractéristiques Techniques

### Sauvegarde Automatique
- Les notes sont sauvegardées via AJAX
- Pas de rechargement de page
- Mise à jour immédiate en base de données

### Validation des Données
- Notes entre 0 et 20
- Support des décimales (2 chiffres après la virgule)
- Champs optionnels (laisser vide si pas de note)

### Gestion des Absences
- Pour l'instant, laisser le champ vide si l'élève est absent
- Fonctionnalité d'absence à venir dans une prochaine version

## Calculs Automatiques

Les calculs sont effectués automatiquement lors de la génération du bulletin:

### Système Semestriel
```
Note de Cours S1 = (Oct + Nov + Déc + Jan) ÷ 4
Note Semestre 1 = (Note de Cours S1 + Composition S1) ÷ 2

Note de Cours S2 = (Fév + Mars + Avr + Mai) ÷ 4
Note Semestre 2 = (Note de Cours S2 + Composition S2) ÷ 2

Moyenne Annuelle = (Note S1 + Note S2) ÷ 2
```

### Système Trimestriel
```
Note de Cours T1 = (Oct + Nov + Déc) ÷ 3
Note Trimestre 1 = (Note de Cours T1 + Composition T1) ÷ 2

Note de Cours T2 = (Jan + Fév + Mars) ÷ 3
Note Trimestre 2 = (Note de Cours T2 + Composition T2) ÷ 2

Moyenne Annuelle = (T1 + T2 + T3) ÷ 3
```

## Astuces et Conseils

### 💡 Saisie Rapide
- Utilisez la touche **Tab** pour passer d'un champ à l'autre
- Les notes sont validées automatiquement
- Pas besoin de cliquer sur "Sauvegarder" après chaque note

### 💡 Organisation
- Saisissez les notes par période (tous les mois d'octobre d'abord, puis novembre, etc.)
- Ou saisissez par élève (toutes les notes d'un élève avant de passer au suivant)

### 💡 Vérification
- Vérifiez régulièrement le bulletin généré
- Les calculs sont automatiques et instantanés
- Toute modification est immédiatement reflétée

## Sécurité

- ✅ Authentification requise
- ✅ Protection CSRF activée
- ✅ Validation côté serveur
- ✅ Historique des modifications (champ `cree_par`)

## Support des Navigateurs

L'interface fonctionne sur:
- ✅ Chrome/Edge (recommandé)
- ✅ Firefox
- ✅ Safari
- ⚠️ Internet Explorer (non supporté)

## Dépannage

### Problème: Les notes ne se sauvegardent pas
**Solution:**
1. Vérifiez votre connexion internet
2. Assurez-vous d'être connecté
3. Vérifiez que l'élève et la classe sont bien sélectionnés
4. Consultez la console du navigateur (F12) pour les erreurs

### Problème: Les notes existantes ne s'affichent pas
**Solution:**
1. Vérifiez que l'année scolaire correspond
2. Assurez-vous que le bon système est sélectionné (Semestriel/Trimestriel)
3. Rechargez la page (F5)

### Problème: Le bulletin est vide
**Solution:**
1. Vérifiez que les notes ont bien été sauvegardées
2. Assurez-vous que l'année scolaire correspond entre la classe et les notes
3. Vérifiez que les matières sont bien associées à la classe

## Améliorations Futures

### 🔄 En Développement
- Gestion des absences avec checkbox
- Import Excel des notes
- Export Excel des notes saisies
- Historique des modifications
- Validation en temps réel des notes
- Copie des notes d'une période à l'autre

### 💡 Suggestions Bienvenues
Si vous avez des suggestions d'amélioration, n'hésitez pas à les partager!

## Fichiers Modifiés

```
notes/
├── views.py                          # Vues saisie_notes_guineen et sauvegarder_notes_guineen
├── urls.py                           # Routes ajoutées
└── templatetags/
    └── notes_tags.py                 # Filtre get_item (existant)

templates/notes/
└── saisie_notes_guineen.html         # Interface de saisie

templates/
└── base.html                         # Menu mis à jour
```

## Contact et Support

Pour toute question ou problème:
1. Consultez d'abord ce guide
2. Vérifiez le fichier `BULLETIN_GUINEEN_README.md`
3. Contactez l'administrateur système

---

**Version:** 1.0  
**Date:** Octobre 2024  
**Système:** Gestion Scolaire - Notes Guinéennes
