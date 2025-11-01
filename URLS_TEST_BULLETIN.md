# 🔗 URLs de Test - Bulletin Dynamique

## 🌐 Serveur de Test

**URL Base:** http://127.0.0.1:8001/  
**Statut:** ✅ En cours d'exécution  
**Port:** 8001

---

## 📋 URLs Principales

### 1. Accueil
```
http://127.0.0.1:8001/
```

### 2. Tableau de Bord des Notes
```
http://127.0.0.1:8001/notes/
```

### 3. Bulletin Dynamique (Interface de sélection)
```
http://127.0.0.1:8001/notes/bulletins/
```

### 4. Gestion des Classes
```
http://127.0.0.1:8001/notes/classes/
```

### 5. Gestion des Matières
```
http://127.0.0.1:8001/notes/matieres/
```

### 6. Gestion des Évaluations
```
http://127.0.0.1:8001/notes/evaluations/
```

---

## 🎯 URL de Test avec Données Réelles

### Bulletin pour BAH IBRAHIMA - Trimestre 1

**URL Complète:**
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=805
```

**Détails:**
- **Classe:** 2ème année (ID: 6)
- **Élève:** BAH IBRAHIMA (ID: 805)
- **Système:** Trimestre
- **Période:** TRIMESTRE_1

**Résultats attendus:**
- Moyenne Générale: **14.69/20**
- Mention: **Bien**
- Rang: Calculé automatiquement

---

## 📊 Paramètres de l'URL

### Structure de l'URL
```
/notes/bulletins/?classe_id={ID}&system_type={TYPE}&periode={PERIODE}&eleve_id={ID}
```

### Paramètres disponibles:

#### 1. `classe_id` (Requis)
- ID de la classe dans ClasseNote
- Exemple: `6` pour "2ème année"

#### 2. `system_type` (Requis)
Options:
- `mensuel` - Bulletin mensuel
- `trimestre` - Bulletin trimestriel
- `semestre` - Bulletin semestriel
- `annuel` - Bulletin annuel

#### 3. `periode` (Requis selon le système)

**Pour système mensuel:**
- `OCTOBRE`
- `NOVEMBRE`
- `DECEMBRE`
- `JANVIER`
- `FEVRIER`
- `MARS`
- `AVRIL`
- `MAI`
- `JUIN`

**Pour système trimestriel:**
- `TRIMESTRE_1`
- `TRIMESTRE_2`
- `TRIMESTRE_3`

**Pour système semestriel:**
- `SEMESTRE_1`
- `SEMESTRE_2`

**Pour système annuel:**
- `ANNUEL`

#### 4. `eleve_id` (Optionnel)
- ID de l'élève
- Si omis, affiche seulement la structure

---

## 🧪 Exemples d'URLs de Test

### Test 1: Système Mensuel - Octobre
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=mensuel&periode=OCTOBRE&eleve_id=805
```

### Test 2: Système Trimestriel - 2ème Trimestre
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=trimestre&periode=TRIMESTRE_2&eleve_id=805
```

### Test 3: Système Semestriel - 1er Semestre
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=semestre&periode=SEMESTRE_1&eleve_id=805
```

### Test 4: Sans élève (affichage de la structure)
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=trimestre&periode=TRIMESTRE_1
```

### Test 5: Avec autre élève
```
http://127.0.0.1:8001/notes/bulletins/?classe_id=6&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=816
```
*CAMARA RAMATA (ID: 816)*

---

## 📱 Tests à Effectuer

### ✅ Test 1: Affichage de base
1. Accéder à l'URL de test principale
2. Vérifier que toutes les matières s'affichent
3. Vérifier que les colonnes sont correctes (2 pour trimestre)

### ✅ Test 2: Calculs
1. Vérifier la colonne "Moy. Continue"
2. Vérifier la colonne "Composition"
3. Vérifier que la moyenne = (MC + Comp×2) / 3
4. Vérifier les points = Moyenne × Coefficient
5. Vérifier la moyenne générale

### ✅ Test 3: Système mensuel
1. Changer `system_type=mensuel`
2. Changer `periode=OCTOBRE`
3. Vérifier qu'une seule colonne s'affiche
4. Vérifier que la moyenne = moyenne continue

### ✅ Test 4: Absences
1. Créer une absence pour un élève
2. Vérifier que "ABS" s'affiche
3. Vérifier que la note n'est pas comptée

### ✅ Test 5: Impression
1. Cliquer sur le bouton d'impression
2. Vérifier la mise en page
3. Vérifier que tout est lisible

### ✅ Test 6: Plusieurs élèves
1. Tester avec différents `eleve_id`
2. Vérifier que les calculs changent
3. Vérifier que le rang est différent

---

## 🔧 Débogage

### Si l'URL ne fonctionne pas:

1. **Vérifier que le serveur tourne:**
   ```bash
   python manage.py runserver 8001
   ```

2. **Vérifier les IDs:**
   - Classe ID: Doit exister dans ClasseNote
   - Eleve ID: Doit exister dans Eleve
   - Les deux doivent correspondre

3. **Vérifier les données:**
   - La classe doit avoir des matières
   - Les matières doivent avoir des évaluations
   - Les évaluations doivent avoir des notes

4. **Consulter les logs:**
   - Regarder la console du serveur Django
   - Vérifier les erreurs SQL éventuelles

---

## 📊 Données Disponibles pour Tests

### Classes Actives (7)
- ID 6: 2ème année
- ID 7: 3ème année
- (Autres classes disponibles)

### Élèves de la 2ème année (20 total)
- ID 805: BAH IBRAHIMA
- ID 816: CAMARA RAMATA
- ID 819: CHERIF CELLOU
- ID 810: CHERIF HADJA
- ID 814: CISSE TENIN

### Matières de la 2ème année (9)
- ANGLAIS (Coef: 2)
- ECM (Coef: 1)
- EPS (Coef: 1)
- FRANÇAIS (Coef: 4)
- GEOGRAPHIE (Coef: 2)
- HISTOIRE (Coef: 2)
- MATHEMATIQUE (Coef: 4)
- SCIENCES NATURELLES (Coef: 2)
- SCIENCES PHYSIQUES (Coef: 2)

### Évaluations disponibles
- TRIMESTRE_1: 27 évaluations
- TRIMESTRE_2: (vérifier)
- TRIMESTRE_3: (vérifier)

---

## 💡 Conseils

1. **Commencez par l'URL de test principale** pour vérifier que tout fonctionne

2. **Testez les différents systèmes** (mensuel, trimestre, semestre)

3. **Testez avec plusieurs élèves** pour vérifier le rang

4. **Vérifiez l'impression** en mode aperçu avant impression

5. **Créez plus de notes** si nécessaire avec `creer_donnees_test.py`

---

## 🚀 Prochaines Étapes

1. ✅ Tester toutes les URLs ci-dessus
2. ⏭️ Vérifier l'affichage sur différents navigateurs
3. ⏭️ Tester l'impression PDF
4. ⏭️ Vérifier la cohérence des données
5. ⏭️ Valider avec des utilisateurs réels

---

**Date:** 1er novembre 2025  
**Serveur:** http://127.0.0.1:8001/  
**Statut:** ✅ Opérationnel
