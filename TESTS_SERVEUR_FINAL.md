# TESTS À EXÉCUTER SUR LE SERVEUR

## 🎯 Objectif

Vérifier que toutes les fonctionnalités fonctionnent correctement sur le serveur de production.

---

## 📋 CHECKLIST COMPLÈTE

### 1. Déploiement

```bash
ssh myschoolgn@www.myschoolgn.space
cd /home/myschoolgn/GS_hadja_kanfing_dian-

# Pull les modifications
git pull origin main

# Vérifier les fichiers
ls -l test_*.py *.md

# Redémarrer
touch ecole_moderne/wsgi.py
```

**Attendu** :
- ✅ Tous les fichiers sont présents
- ✅ Pas d'erreur Git
- ✅ Serveur redémarré

---

### 2. Test Performance Rangs

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
python test_performance_rangs.py
```

**Attendu** :
- ✅ Cache fonctionne (amélioration > 95%)
- ✅ Temps avec cache < 1ms
- ✅ Résultats identiques avec/sans cache
- ✅ TOP 5 affiché correctement

**Résultat Obtenu** :
```
✅ Amélioration : 100.0%
✅ Temps avec cache : 0.09 ms
✅ Temps sans cache : 1425.83 ms
```

---

### 3. Test Import Notes

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
python test_import_notes.py
```

**Attendu** :
- ✅ Template généré correctement
- ✅ Validation fonctionne
- ✅ Simulation réussie
- ✅ Évaluations trouvées
- ✅ Notes existantes affichées

**À Vérifier** :
- Nombre d'élèves dans le template
- Colonnes présentes (Matricule, Nom, Prénom, Note, Absent)
- Pas d'erreur de validation

---

### 4. Test Import Élèves

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
python test_import_eleves.py
```

**Attendu** :
- ✅ Template généré correctement
- ✅ Validation fonctionne
- ✅ Génération matricules OK
- ✅ Création responsables OK

**À Vérifier** :
- Format des matricules (ex: L12SL-001)
- Colonnes présentes (Nom, Prénom, Sexe, Date Naissance)
- Pas d'erreur de validation

---

### 5. Test Rapide Global

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
bash test_import_rapide.sh
```

**Attendu** :
- ✅ Tous les tests passent
- ✅ URLs affichées correctement
- ✅ Pas d'erreur Python

---

## 🌐 TESTS MANUELS SUR LE SITE

### A. Test Classement Web

**URL** : `https://www.myschoolgn.space/notes/consulter/?classe_id=7&periode=OCTOBRE`

**À Vérifier** :
- [ ] Page se charge rapidement (< 1 seconde)
- [ ] Classement affiché correctement
- [ ] Rangs corrects (1er, 2ème, 3ème...)
- [ ] Moyennes affichées
- [ ] Accord grammatical correct (1er pour garçon, 1ère pour fille)

### B. Test Bulletin PDF

**URL** : `https://www.myschoolgn.space/notes/bulletins/classe/pdf/?classe_id=7&periode=OCTOBRE&system_type=mensuel`

**À Vérifier** :
- [ ] PDF se génère rapidement (< 5 secondes)
- [ ] Rangs sur les bulletins correspondent au classement
- [ ] Pas d'erreur NameError
- [ ] Moyennes correctes
- [ ] Mise en page correcte

### C. Test Import Notes

**URL** : `https://www.myschoolgn.space/notes/importer/`

**À Vérifier** :
- [ ] Page se charge correctement
- [ ] Sélection classe/matière fonctionne
- [ ] Bouton "Télécharger template" fonctionne
- [ ] Template téléchargé contient les élèves
- [ ] Upload de fichier fonctionne
- [ ] Import réussit avec un fichier valide

**Étapes** :
1. Sélectionner classe : "12 SÉRIE SCIENTIFIQUE"
2. Sélectionner matière : "Mathématique"
3. Sélectionner type : "MENSUELLE"
4. Cliquer sur "Télécharger template"
5. Vérifier le fichier Excel téléchargé
6. Remplir quelques notes (2-3 élèves)
7. Uploader le fichier
8. Vérifier le résultat

### D. Test Import Élèves

**URL** : `https://www.myschoolgn.space/eleves/importer/`

**À Vérifier** :
- [ ] Page se charge correctement
- [ ] Sélection classe fonctionne
- [ ] Bouton "Télécharger template" fonctionne
- [ ] Template téléchargé est correct
- [ ] Upload de fichier fonctionne
- [ ] Import réussit avec un fichier valide

**Étapes** :
1. Sélectionner classe : "7ème Année"
2. Cliquer sur "Télécharger template"
3. Vérifier le fichier Excel téléchargé
4. Remplir quelques élèves (2-3 élèves de test)
5. Uploader le fichier
6. Vérifier le résultat (matricules générés)

### E. Test Export Classement

**URL** : `https://www.myschoolgn.space/notes/consulter/?classe_id=7&periode=OCTOBRE`

**À Vérifier** :
- [ ] Bouton "Exporter Classement" visible
- [ ] Dropdown fonctionne (Général, Par matière)
- [ ] Export Excel fonctionne
- [ ] Export PDF fonctionne
- [ ] Fichiers téléchargés sont corrects

---

## 🔍 VÉRIFICATIONS SPÉCIFIQUES

### 1. Cohérence des Rangs

**Objectif** : Vérifier que les rangs sont identiques partout

**Test** :
1. Aller sur le classement web : `/notes/consulter/?classe_id=7&periode=OCTOBRE`
2. Noter le TOP 3 (rangs et moyennes)
3. Générer un bulletin PDF pour un élève du TOP 3
4. Vérifier que le rang sur le bulletin correspond au classement
5. Exporter le classement Excel
6. Vérifier que le rang dans Excel correspond

**Attendu** :
- ✅ Rangs identiques sur web, PDF et Excel
- ✅ Moyennes identiques partout
- ✅ Ordre identique

### 2. Performance du Cache

**Objectif** : Vérifier que le cache améliore les performances

**Test** :
1. Vider le cache : `cache.clear()` dans Django shell
2. Charger le classement (noter le temps)
3. Recharger immédiatement (noter le temps)
4. Comparer les temps

**Attendu** :
- ✅ Premier chargement : 500-2000ms
- ✅ Deuxième chargement : < 100ms
- ✅ Amélioration > 90%

### 3. Recalcul Automatique

**Objectif** : Vérifier que les rangs se recalculent automatiquement

**Test** :
1. Noter le classement actuel
2. Modifier une note d'un élève
3. Recharger le classement
4. Vérifier que le rang a changé si nécessaire

**Attendu** :
- ✅ Rang recalculé automatiquement
- ✅ Nouveau classement correct
- ✅ Pas d'erreur

### 4. Import de Notes

**Objectif** : Vérifier l'import complet de notes

**Test** :
1. Télécharger le template pour une classe
2. Remplir 5 notes de test
3. Importer le fichier
4. Vérifier les résultats

**Attendu** :
- ✅ 5 notes importées
- ✅ Aucune erreur
- ✅ Notes visibles dans le système
- ✅ Moyennes recalculées

### 5. Import d'Élèves

**Objectif** : Vérifier l'import complet d'élèves

**Test** :
1. Télécharger le template pour une classe
2. Remplir 3 élèves de test
3. Importer le fichier
4. Vérifier les résultats

**Attendu** :
- ✅ 3 élèves importés
- ✅ Matricules générés automatiquement
- ✅ Responsables créés (si fournis)
- ✅ Aucune erreur

---

## 📊 RÉSULTATS ATTENDUS

### Tests Automatisés

| Test | Durée | Statut Attendu |
|------|-------|----------------|
| Performance rangs | 30s | ✅ RÉUSSI |
| Import notes | 20s | ✅ RÉUSSI |
| Import élèves | 20s | ✅ RÉUSSI |
| Test rapide | 60s | ✅ RÉUSSI |

### Tests Manuels

| Test | Durée | Statut Attendu |
|------|-------|----------------|
| Classement web | 2min | ✅ RÉUSSI |
| Bulletin PDF | 2min | ✅ RÉUSSI |
| Import notes | 5min | ✅ RÉUSSI |
| Import élèves | 5min | ✅ RÉUSSI |
| Export classement | 2min | ✅ RÉUSSI |

---

## ✅ VALIDATION FINALE

### Critères de Succès

- [ ] Tous les tests automatisés passent
- [ ] Tous les tests manuels réussissent
- [ ] Aucune erreur dans les logs
- [ ] Performance acceptable (< 2s pour classement)
- [ ] Cohérence des rangs vérifiée
- [ ] Import/Export fonctionnels

### Si Tout Est OK

```
✅ SYSTÈME VALIDÉ
✅ Prêt pour utilisation en production
✅ Tous les objectifs atteints
```

### Si Problèmes Détectés

1. Noter les erreurs précises
2. Consulter les logs : `/home/myschoolgn/GS_hadja_kanfing_dian-/logs/django.log`
3. Vérifier les fichiers modifiés
4. Corriger et re-tester

---

## 📝 RAPPORT DE TEST

### Template de Rapport

```
DATE: [Date du test]
TESTEUR: [Nom]
VERSION: [Commit hash]

TESTS AUTOMATISÉS:
- Performance rangs: [✅/❌] [Détails]
- Import notes: [✅/❌] [Détails]
- Import élèves: [✅/❌] [Détails]

TESTS MANUELS:
- Classement web: [✅/❌] [Détails]
- Bulletin PDF: [✅/❌] [Détails]
- Import notes: [✅/❌] [Détails]
- Import élèves: [✅/❌] [Détails]
- Export classement: [✅/❌] [Détails]

VÉRIFICATIONS:
- Cohérence rangs: [✅/❌] [Détails]
- Performance cache: [✅/❌] [Détails]
- Recalcul auto: [✅/❌] [Détails]

CONCLUSION:
[Système validé / Problèmes détectés]

NOTES:
[Observations supplémentaires]
```

---

## 🎊 CONCLUSION

Ce document liste **TOUS** les tests à effectuer pour valider le système.

**Exécutez-les dans l'ordre** et cochez au fur et à mesure.

**Une fois tous validés, le système est prêt pour production !** 🚀

---

## 📞 Support

En cas de problème pendant les tests :

1. Consulter les logs serveur
2. Vérifier les fichiers de documentation
3. Exécuter les tests de diagnostic
4. Noter précisément l'erreur rencontrée

**Tous les outils sont disponibles pour diagnostiquer !** ✅
