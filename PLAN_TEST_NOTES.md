# 🧪 Plan de Test - Module Notes

## 📋 CHECKLIST AVANT TEST

### Vérifications Préalables

- [ ] Serveur Django démarré
- [ ] Base de données accessible
- [ ] Utilisateur connecté
- [ ] Au moins une classe créée
- [ ] Au moins une matière créée
- [ ] Au moins des élèves dans la classe

---

## 🎯 TEST 1: Gestion des Classes

### Étapes:

1. **Accéder à la page**
   ```
   URL: http://127.0.0.1:8000/notes/classes/
   ```
   ✅ Attendu: Page s'affiche avec statistiques

2. **Ajouter une classe**
   - Nom: "Classe Test"
   - Niveau: Primaire 1ère
   - Année: 2024-2025
   - Effectif: 25
   - ☑ Classe active
   
   ✅ Attendu: Message "✅ Classe créée avec succès!"

3. **Modifier la classe**
   - Cliquer sur ✏️
   - Changer effectif: 30
   - Enregistrer
   
   ✅ Attendu: Message "✅ Classe modifiée avec succès!"

4. **Supprimer la classe**
   - Cliquer sur 🗑️
   - Confirmer
   
   ✅ Attendu: Classe supprimée ou désactivée

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 2: Gestion des Matières

### Étapes:

1. **Accéder à la page**
   ```
   URL: http://127.0.0.1:8000/notes/matieres/
   ```
   ✅ Attendu: Page s'affiche

2. **Sélectionner une classe Primaire**
   - Choisir: 1ère année
   
   ✅ Attendu: Pas de champ "Coefficient"

3. **Ajouter une matière**
   - Nom: Mathématiques Test
   - Code: MATH_TEST
   - (Pas de coefficient affiché)
   - ☑ Matière active
   
   ✅ Attendu: Message "✅ Matière ajoutée avec succès!"

4. **Vérifier le coefficient**
   - Regarder dans la liste
   
   ✅ Attendu: Coefficient = 1.00

5. **Modifier la matière**
   - Cliquer sur ✏️
   - Changer nom: "Mathématiques Modifié"
   - Enregistrer
   
   ✅ Attendu: Message "✅ Matière modifiée avec succès!"

6. **Tester avec classe Secondaire**
   - Sélectionner: 7ème année
   - Ajouter une matière
   
   ✅ Attendu: Champ "Coefficient" visible

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 3: Saisie des Notes (PRINCIPAL)

### Étapes:

1. **Accéder à la page**
   ```
   URL: http://127.0.0.1:8000/notes/saisir/
   ```
   ✅ Attendu: Page avec section bleue de sélection

2. **Sélectionner les paramètres**
   - Classe: 1ère année
   - Matière: FRANÇAIS
   - Type de Note: Composition
   - Période: TRIMESTRE_1
   - Cliquer "Charger"
   
   ✅ Attendu: 
   - Liste des élèves affichée
   - Bouton PDF visible
   - Tableau de saisie prêt

3. **Vérifier les élèves**
   ```
   ✅ Attendu: 
   - Matricules affichés
   - Noms et prénoms corrects
   - Champs de saisie vides
   - Cases "Absent" décochées
   ```

4. **Saisir des notes**
   
   **Élève 1**: 
   - Note: 15
   - Absent: ☐
   
   **Élève 2**: 
   - Note: 18.5
   - Absent: ☐
   
   **Élève 3**: 
   - Note: (vide)
   - Absent: ☑
   
   **Élève 4**: 
   - Note: 12
   - Absent: ☐
   
   **Élève 5**: 
   - Note: 16.75
   - Absent: ☐

5. **Sauvegarder**
   - Cliquer "Sauvegarder Toutes les Notes"
   
   ✅ Attendu:
   - Bouton désactivé
   - Message "Sauvegarde en cours..."
   - Barre de progression 0% → 100%
   - Toast "✅ X note(s) sauvegardée(s) avec succès"
   - Bouton réactivé après 2 secondes

6. **Vérifier la console**
   ```
   F12 → Console
   ```
   ✅ Attendu: Pas d'erreur JavaScript

7. **Vérifier la réponse réseau**
   ```
   F12 → Network → Chercher "sauvegarder-notes"
   ```
   ✅ Attendu:
   - Status: 200 OK
   - Response: {"success": true, "notes_sauvegardees": X}

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 4: Vérification Base de Données

### Étapes:

1. **Accéder à l'admin Django**
   ```
   URL: http://127.0.0.1:8000/admin/
   ```

2. **Aller dans Notes → Note Eleve**
   
   ✅ Attendu: Voir les notes créées

3. **Vérifier les données**
   
   Pour chaque note:
   - ☐ Élève correct
   - ☐ Évaluation correcte
   - ☐ Note correcte (15, 18.5, NULL, 12, 16.75)
   - ☐ Absent = True pour élève 3
   - ☐ saisi_par = votre utilisateur
   - ☐ date_saisie = aujourd'hui

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 5: Génération PDF

### Étapes:

1. **Sur la page de saisie**
   ```
   Avec classe + matière + période sélectionnées
   ```

2. **Cliquer sur bouton PDF**
   
   ✅ Attendu:
   - Nouvel onglet s'ouvre
   - PDF s'affiche
   - Format paysage A4

3. **Vérifier le contenu du PDF**
   
   ✅ Attendu:
   - Titre: "Liste de Saisie des Notes - [Classe]"
   - Sous-titre: "Matière: [Matière] | Période: [Période]"
   - Tableau avec colonnes:
     * N°
     * Matricule
     * Nom
     * Prénom
     * Note /20 (vide)
     * Absent (vide)
     * Observations (vide)
   - Tous les élèves listés
   - Numérotation correcte

4. **Tester l'impression**
   - Ctrl+P
   
   ✅ Attendu: Aperçu d'impression correct

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 6: Validation des Notes

### Étapes:

1. **Tester note invalide (trop haute)**
   - Saisir: 25
   - Sauvegarder
   
   ✅ Attendu: Erreur "Note invalide (0-20)"

2. **Tester note invalide (négative)**
   - Saisir: -5
   - Sauvegarder
   
   ✅ Attendu: Erreur "Note invalide (0-20)"

3. **Tester format invalide**
   - Saisir: "abc"
   - Sauvegarder
   
   ✅ Attendu: Erreur "Format de note invalide"

4. **Tester note décimale**
   - Saisir: 15,5 (virgule)
   - Sauvegarder
   
   ✅ Attendu: Accepté et converti en 15.5

5. **Tester note avec point**
   - Saisir: 15.5 (point)
   - Sauvegarder
   
   ✅ Attendu: Accepté

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 7: Gestion des Absents

### Étapes:

1. **Marquer un élève absent**
   - Cocher "Absent"
   - Laisser note vide
   - Sauvegarder
   
   ✅ Attendu: 
   - Sauvegarde réussie
   - En BDD: note = NULL, absent = True

2. **Élève absent avec note**
   - Cocher "Absent"
   - Saisir note: 15
   - Sauvegarder
   
   ✅ Attendu: 
   - Sauvegarde réussie
   - En BDD: note = NULL (priorité à l'absence)

3. **Décocher absent**
   - Décocher "Absent"
   - Saisir note: 14
   - Sauvegarder
   
   ✅ Attendu:
   - Sauvegarde réussie
   - En BDD: note = 14, absent = False

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 8: Mise à Jour des Notes

### Étapes:

1. **Saisir des notes initiales**
   - Élève 1: 15
   - Sauvegarder
   
   ✅ Attendu: Note créée

2. **Modifier la note**
   - Changer: 17
   - Sauvegarder
   
   ✅ Attendu:
   - Note mise à jour (pas de doublon)
   - En BDD: note = 17

3. **Vérifier en BDD**
   - Admin → Note Eleve
   
   ✅ Attendu: 
   - Une seule entrée pour cet élève/évaluation
   - Note = 17

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 9: Raccourci Clavier

### Étapes:

1. **Sur la page de saisie**
   - Saisir quelques notes

2. **Appuyer sur Ctrl+S**
   
   ✅ Attendu:
   - Sauvegarde déclenchée
   - Pas de sauvegarde navigateur
   - Notes sauvegardées

**Résultat**: ☐ PASS / ☐ FAIL

---

## 🎯 TEST 10: Périodes Dynamiques

### Étapes:

1. **Sélectionner classe Primaire**
   
   ✅ Attendu: Périodes = Trimestres uniquement

2. **Sélectionner classe Secondaire**
   - Système: Semestriel
   
   ✅ Attendu: Périodes = Semestres

3. **Changer système**
   - Système: Trimestriel
   
   ✅ Attendu: Périodes = Trimestres

**Résultat**: ☐ PASS / ☐ FAIL

---

## 📊 RÉSULTATS GLOBAUX

### Tests Réussis: __ / 10

### Tests Échoués: __ / 10

### Bugs Trouvés:

1. ___________________________________
2. ___________________________________
3. ___________________________________

### Notes:

___________________________________
___________________________________
___________________________________

---

## ✅ VALIDATION FINALE

- [ ] Tous les tests passent
- [ ] Aucun bug critique
- [ ] Performance acceptable
- [ ] Interface intuitive
- [ ] Données sauvegardées correctement

---

## 🎯 COMMANDES UTILES

### Démarrer le serveur
```bash
python manage.py runserver
```

### Accéder à l'admin
```
URL: http://127.0.0.1:8000/admin/
```

### Voir les logs
```
Console du serveur Django
```

### Ouvrir la console navigateur
```
F12 → Console
F12 → Network
```

---

## 📝 RAPPORT DE TEST

**Date**: _______________
**Testeur**: _______________
**Version**: 1.0
**Statut**: ☐ PASS / ☐ FAIL

**Commentaires**:
___________________________________
___________________________________
___________________________________

**Signature**: _______________
