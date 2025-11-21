# 📚 GUIDE D'IMPORT DES NOTES - CM2 (6ÈME ANNÉE)

## ✅ ÉTAPE 1: Préparation Terminée

Les matières ont été créées automatiquement pour la classe CM2 :

| # | Matière | Code |
|---|---------|------|
| 1 | Dictée et Questions | MAT01 |
| 2 | Histoire | MAT02 |
| 3 | Rédaction | MAT03 |
| 4 | Géographie | MAT04 |
| 5 | Calcul | MAT05 |
| 6 | Sciences d'observation | MAT06 |
| 7 | Education Civique et Morale | MAT07 |
| 8 | Lecture | MAT08 |
| 9 | Anglais | MAT09 |

---

## 📋 ÉTAPE 2: Créer le Fichier Excel

### Option A: Via l'Interface Web (RECOMMANDÉ)

1. **Accédez à** : `/notes/importer/`

2. **Sélectionnez** :
   - Type: **Notes Mensuelles**
   - Classe: **CM2**
   - Matière: **Dictée et Questions** (commencer par la première)
   - Période: **NOVEMBRE**
   - Année: **2024-2025**

3. **Téléchargez le template** :
   - Cliquez sur "Télécharger le template Excel"
   - Le fichier contiendra automatiquement tous les élèves de CM2

4. **Remplissez les notes** dans le fichier Excel téléchargé

5. **Uploadez le fichier** complété

6. **Répétez** pour chaque matière

### Option B: Créer Manuellement le Fichier

**Format requis** :
```
Matricule, Prénom, Nom, Note, Absent
```

**Exemple** :
```csv
Matricule,Prénom,Nom,Note,Absent
2025/35008,BINTA,BAH,15.5,NON
2025/35013,OUSMANE,BAH,12,NON
2025/35011,LANSANA,BALDE,,OUI
```

---

## 👥 ÉTAPE 3: Liste des Élèves CM2

**40 élèves actifs** :

1. BINTA BAH (2025/35008)
2. OUSMANE BAH (2025/35013)
3. LANSANA BALDE (2025/35011)
4. IBRAHIMA BARRY (2025/35007)
5. YACINE BARRY (2025/18006)
6. TENIN CAMARA (2025/18014)
7. THIERNO CAMARA (2025/18017)
8. THIERNO CAMARA (2025/18019)
9. HADJA CHERIF (2025/18018)
10. ALSENY CISSE (2025/18013)
11. TENIN CISSE (2025/35020)
12. AMINATA CONDE (2025/35016)
13. DJÉNABOU CONDE (2025/35002)
14. FACINET CONDE (2025/35005)
15. OUMOU CONDE (2025/35006)
16. OUSMANE CONDE (2025/18003)
17. AMINATA CONTE (2025/35004)
18. HADJA CONTE (2025/18016)
19. OUMOU CONTE (2025/18004)
20. ABDOULAYE DIALLO (2025/18015)
21. ZAINAB DIALLO (2025/18012)
22. SALEMATOU DOUMBOUYA (2025/35010)
23. RAMATA FOFANA (2025/35018)
24. SEKOU FOFANA (2025/18001)
25. IBRAHIMA KABA (2025/18007)
26. ABOUBACAR KANTE (2025/18011)
27. SEKOU KANTE (2025/18005)
28. ZAINAB KANTE (2025/35014)
29. ALPHA KEITA (2025/35001)
30. NENE KEITA (2025/18008)
31. LANSANA KOUROUMA (2025/18009)
32. IBRAHIMA SOUMAH (2025/35015)
33. LANSANA SOW (2025/35017)
34. AMADOU SYLLA (2025/35019)
35. MARIAMA SYLLA (2025/35012)
36. YACINE SYLLA (2025/18010)
37. DJÉNABOU TOURE (2025/18020)
38. MOHAMED TOURE (2025/35009)
39. SALIOU TOURE (2025/35003)
40. YACINE TOURE (2025/18002)

---

## ⚠️ IMPORTANT: Correspondance des Noms

**Les noms dans votre image ne correspondent PAS aux noms dans la base de données.**

### Exemples de différences :

| Image | Base de Données |
|-------|-----------------|
| Nana Traoré | ❌ Pas trouvé |
| Ousmerkyl Diaby | ❌ Pas trouvé |
| Béatrice Sandouno | ❌ Pas trouvé |

**Les élèves dans la base sont différents !**

---

## 🎯 SOLUTION RECOMMANDÉE

### Utiliser l'Interface Web avec Template Automatique

1. **Accédez** : `http://localhost:8000/notes/importer/`

2. **Pour chaque matière** :
   
   a. Sélectionnez la matière
   
   b. Téléchargez le template (contient les bons matricules/noms)
   
   c. Remplissez les notes correspondantes
   
   d. Uploadez le fichier

### Exemple pour "Dictée et Questions" :

**Template téléchargé** :
```csv
Matricule,Prénom,Nom,Note,Absent
2025/35008,BINTA,BAH,,NON
2025/35013,OUSMANE,BAH,,NON
...
```

**Remplissez** :
```csv
Matricule,Prénom,Nom,Note,Absent
2025/35008,BINTA,BAH,6,NON
2025/35013,OUSMANE,BAH,6.5,NON
...
```

---

## 📊 Processus d'Import Complet

### Pour TOUTES les matières :

```bash
# 1. Dictée et Questions
- Télécharger template
- Remplir notes
- Uploader

# 2. Histoire
- Télécharger template
- Remplir notes
- Uploader

# 3. Rédaction
- Télécharger template
- Remplir notes
- Uploader

# ... et ainsi de suite pour les 9 matières
```

---

## 🚀 Scripts Disponibles

### Lister les élèves :
```bash
python lister_eleves_cm2.py
```

### Test d'import (sans enregistrement) :
```bash
python importer_notes_6eme_intelligent.py --test
```

### Import réel :
```bash
python importer_notes_6eme_intelligent.py --periode NOVEMBRE --annee 2024-2025
```

---

## ✅ Résumé

**Ce qui est prêt** :
- ✅ Classe CM2 identifiée
- ✅ 9 matières créées
- ✅ 40 élèves actifs
- ✅ Interface web fonctionnelle

**Ce qu'il faut faire** :
1. Utiliser l'interface web `/notes/importer/`
2. Télécharger les templates pour chaque matière
3. Remplir les notes dans les templates
4. Uploader les fichiers complétés

**Avantage** :
- ✅ Pas d'erreur de matricule
- ✅ Pas d'erreur de nom
- ✅ Validation automatique
- ✅ Import rapide et sûr

---

## 📞 Support

Si vous avez besoin d'aide :
- Les matières sont déjà créées
- Les élèves sont déjà dans la base
- Il suffit d'utiliser l'interface web standard

**URL** : `/notes/importer/`
