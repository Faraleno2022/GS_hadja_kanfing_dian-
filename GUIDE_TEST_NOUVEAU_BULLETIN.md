# Guide de Test - Nouveau Bulletin

## 🧪 TESTS DU NOUVEAU BULLETIN

**Date**: 31 Octobre 2024  
**Objectif**: Tester le nouveau système de bulletin  
**Statut**: ✅ **PRÊT**

---

## 📋 Étapes de Test

### 1. Vérification Rapide

**Commande**:
```bash
python manage.py shell < test_nouveau_bulletin.py
```

**Résultat Attendu**:
```
🧪 TEST DU NOUVEAU BULLETIN
================================================================================

📚 Classes disponibles:
   1. 1ère année (ID: 5)
   2. 2ème année (ID: 6)
   ...

🎯 Test avec la classe: 1ère année (ID: 5)
   ✅ 20 élève(s) trouvé(s)
   👤 Élève test: BAH OUSMANE (ID: 123)
   📖 6 matière(s)
   📝 Notes Octobre: 6
   📝 Compositions T1: 6

🌐 URL DE TEST
================================================================================

✅ Accéder au bulletin:
   http://127.0.0.1:8000/notes/bulletins/

✅ URL directe:
   http://127.0.0.1:8000/notes/bulletins/?classe_id=5&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=123

✅ NOTES DISPONIBLES - Le bulletin devrait s'afficher correctement!
```

---

## 🎯 Test Complet

### Étape 1: Générer les Notes (Si Nécessaire)

**Si pas de notes**:
```bash
python manage.py shell < test_bulletin_classe.py
```

**Résultat**:
- Notes mensuelles créées: 360
- Compositions créées: 120
- Total: 480 notes

### Étape 2: Accéder au Bulletin

**URL**:
```
http://127.0.0.1:8000/notes/bulletins/
```

**Ou**:
```
http://127.0.0.1:8000/notes/bulletin-guineen/
```

### Étape 3: Sélectionner les Paramètres

**Formulaire**:
1. **Classe**: Sélectionner "1ère année"
2. **Système**: Sélectionner "Trimestre"
3. **Période**: Sélectionner "1er Trimestre"
4. **Élève**: Sélectionner un élève

### Étape 4: Vérifier le Bulletin

**Éléments à Vérifier**:
```
✅ En-tête "RÉPUBLIQUE DE GUINÉE"
✅ Logo de l'école (si configuré)
✅ Nom de l'école
✅ Année scolaire: 2024-2025
✅ Période: 1er Trimestre
✅ Informations élève complètes
✅ Tableau des notes avec toutes les matières
✅ Coefficients affichés
✅ Notes /20 calculées
✅ Total des points
✅ Moyenne générale
✅ Rang (ex: 3ème / 25)
✅ Mention (badge coloré)
✅ Appréciation du conseil
✅ 3 zones de signature
✅ Date et lieu
```

---

## 🔍 Tests Détaillés

### Test 1: Affichage du Formulaire

**URL**: `http://127.0.0.1:8000/notes/bulletins/`

**Vérifications**:
```
✅ Formulaire de sélection visible
✅ Liste déroulante "Classe" remplie
✅ Boutons radio "Système" (Semestre/Trimestre)
✅ Message d'information si rien sélectionné
```

### Test 2: Sélection Classe

**Action**: Sélectionner une classe

**Vérifications**:
```
✅ Liste "Système" activée
✅ Liste "Période" activée selon le système
✅ Liste "Élève" remplie avec les élèves de la classe
```

### Test 3: Génération du Bulletin

**Action**: Sélectionner tous les paramètres

**Vérifications**:
```
✅ Bulletin affiché en dessous du formulaire
✅ Toutes les sections présentes
✅ Calculs corrects
✅ Bouton "Imprimer" visible
```

### Test 4: Calculs

**Vérifier**:
```
✅ Moyenne par matière = (Moy mois + Composition) / 2
✅ Points = Moyenne × Coefficient
✅ Total points = Somme des points
✅ Moyenne générale = Total points / Total coefficients
✅ Rang correct (comparé aux autres élèves)
```

### Test 5: Impression

**Action**: Cliquer sur "Imprimer le Bulletin"

**Vérifications**:
```
✅ Aperçu avant impression s'ouvre
✅ Format A4
✅ Formulaire de sélection masqué
✅ Bulletin seul visible
✅ Mise en page correcte
```

### Test 6: Filigrane

**Vérifier** (si logo configuré):
```
✅ Logo en en-tête visible
✅ Logo en filigrane au centre (transparent)
✅ Opacité correcte (5%)
```

### Test 7: Mentions

**Tester différentes moyennes**:
```
✅ ≥ 16: Badge vert "Très Bien"
✅ ≥ 14: Badge bleu "Bien"
✅ ≥ 12: Badge jaune "Assez Bien"
✅ ≥ 10: Badge orange "Passable"
✅ < 10: Badge rouge "Insuffisant"
```

### Test 8: Rang

**Vérifier**:
```
✅ Rang correct (1er, 2ème, 3ème, etc.)
✅ Gestion des ex-aequo
✅ Format: "3ème / 25"
```

---

## 📊 Scénarios de Test

### Scénario 1: Élève Excellent

**Données**:
- Moyenne générale: 17.5
- Rang: 1er

**Résultat Attendu**:
```
✅ Mention: "Très Bien" (badge vert)
✅ Rang: "1er / 25"
✅ Appréciation: "Excellent travail..."
```

### Scénario 2: Élève Moyen

**Données**:
- Moyenne générale: 11.2
- Rang: 15ème

**Résultat Attendu**:
```
✅ Mention: "Assez Bien" (badge jaune)
✅ Rang: "15ème / 25"
✅ Appréciation: "Travail satisfaisant..."
```

### Scénario 3: Élève en Difficulté

**Données**:
- Moyenne générale: 8.5
- Rang: 23ème

**Résultat Attendu**:
```
✅ Mention: "Insuffisant" (badge rouge)
✅ Rang: "23ème / 25"
✅ Appréciation: "Résultats insuffisants..."
```

### Scénario 4: Trimestre 2

**Action**: Sélectionner "2ème Trimestre"

**Vérifications**:
```
✅ Mois: Janvier, Février, Mars
✅ Composition: TRIMESTRE_2
✅ Calculs corrects
```

### Scénario 5: Système Semestre

**Action**: Sélectionner "Semestre" puis "1er Semestre"

**Vérifications**:
```
✅ Mois: Oct, Nov, Déc, Jan, Fév
✅ Composition: SEMESTRE_1
✅ Calculs corrects
```

---

## 🐛 Tests d'Erreur

### Test 1: Classe Sans Élèves

**Action**: Sélectionner une classe vide

**Résultat Attendu**:
```
✅ Message: "Aucun élève dans cette classe"
✅ Pas de crash
```

### Test 2: Élève Sans Notes

**Action**: Sélectionner un élève sans notes

**Résultat Attendu**:
```
✅ Bulletin affiché
✅ Notes à 0 ou "-"
✅ Moyenne: 0
✅ Pas de rang
```

### Test 3: Période Sans Notes

**Action**: Sélectionner une période sans notes saisies

**Résultat Attendu**:
```
✅ Bulletin affiché
✅ Toutes les notes à "-"
✅ Moyenne: 0
```

---

## ✅ Checklist de Test

### Interface
```
☐ Formulaire de sélection fonctionne
☐ Listes déroulantes remplies
☐ Sélection en cascade (classe → système → période → élève)
☐ Bouton "Imprimer" visible
```

### Affichage
```
☐ En-tête République de Guinée
☐ Logo école (si configuré)
☐ Informations élève complètes
☐ Tableau des notes lisible
☐ Toutes les matières affichées
☐ Coefficients visibles
```

### Calculs
```
☐ Moyenne par matière correcte
☐ Points par matière corrects
☐ Total des points correct
☐ Moyenne générale correcte
☐ Rang correct
☐ Mention correcte
```

### Impression
```
☐ Aperçu impression fonctionne
☐ Format A4
☐ Formulaire masqué à l'impression
☐ Mise en page correcte
```

### Responsive
```
☐ Affichage correct sur grand écran
☐ Affichage correct sur tablette
☐ Formulaire utilisable sur mobile
```

---

## 📝 Rapport de Test

### Template de Rapport

```
Date: ___________
Testeur: ___________

RÉSULTATS:
☐ Formulaire: OK / KO
☐ Affichage: OK / KO
☐ Calculs: OK / KO
☐ Impression: OK / KO
☐ Responsive: OK / KO

BUGS TROUVÉS:
1. ___________
2. ___________

COMMENTAIRES:
___________
___________
```

---

## 🎯 URLs de Test

### URL Principale
```
http://127.0.0.1:8000/notes/bulletins/
```

### URL avec Paramètres (Exemple)
```
http://127.0.0.1:8000/notes/bulletins/?classe_id=5&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=123
```

### URL Alternative
```
http://127.0.0.1:8000/notes/bulletin-guineen/
```

---

## 🔧 Commandes Utiles

### Vérifier les Notes
```bash
python manage.py shell

>>> from notes.models import NoteMensuelle, CompositionNote
>>> NoteMensuelle.objects.filter(annee_scolaire="2024-2025").count()
>>> CompositionNote.objects.filter(annee_scolaire="2024-2025").count()
```

### Générer des Notes de Test
```bash
python manage.py shell < test_bulletin_classe.py
```

### Vérification Rapide
```bash
python manage.py shell < test_nouveau_bulletin.py
```

---

## ✅ Résultat Attendu

### Bulletin Complet
```
✅ Format officiel République de Guinée
✅ Logo et filigrane
✅ Toutes les informations élève
✅ Tableau des notes complet
✅ Calculs automatiques corrects
✅ Rang et mention
✅ Appréciation du conseil
✅ 3 zones de signature
✅ Date et lieu
✅ Impression professionnelle
```

---

**🎉 GUIDE DE TEST COMPLET !**

**Vérification Rapide**: `python manage.py shell < test_nouveau_bulletin.py`  
**URL de Test**: http://127.0.0.1:8000/notes/bulletins/  
**Documentation**: Tous les scénarios couverts  
**Statut**: ✅ **PRÊT POUR LES TESTS**
