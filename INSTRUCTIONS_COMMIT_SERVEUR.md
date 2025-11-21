# INSTRUCTIONS POUR COMMIT SUR LE SERVEUR

**Date :** 20 novembre 2025  
**Situation :** Modifications non commitées sur le serveur

---

## 📋 Situation Actuelle

D'après `git status`, vous avez :

### Fichiers Modifiés (5)
- `notes/bulletin_intelligent.py`
- `notes/calculs.py`
- `notes/calculs_intelligent.py`
- `notes/export_classement_fixed.py`
- `test_bulletin_classe.py`

### Fichiers Non Suivis (Backup/Temporaires)
- `backups_rangs_20251120_071556/`
- `fix_all_rangs.sh`
- `notes/.export_classement.py.swp`
- `notes/bulletin_intelligent.py.backup`
- `notes/bulletin_intelligent.py.bak2`
- `notes/calculs.py.backup`
- `notes/calculs_intelligent.py.bak3`
- `notes/export_classement.py.bak`
- `notes/export_classement_fixed.py.bak`

### Scripts de Test
- `test_bulletin_ex_aequo.py`
- `test_rang_direct.py`
- `test_validation_rang.py`

---

## 🚀 Solution Rapide (Recommandée)

### Option 1 : Script Automatique (Bash)

```bash
# Rendre le script exécutable
chmod +x clean_and_commit.sh

# Exécuter
./clean_and_commit.sh
```

### Option 2 : Commandes Manuelles

```bash
# 1. Supprimer les fichiers temporaires
rm -rf backups_rangs_20251120_071556/
rm -f notes/.export_classement.py.swp
rm -f notes/*.backup notes/*.bak* notes/*.bak
rm -f fix_all_rangs.sh

# 2. Ajouter les fichiers modifiés
git add notes/bulletin_intelligent.py
git add notes/calculs.py
git add notes/calculs_intelligent.py
git add notes/export_classement_fixed.py
git add test_bulletin_classe.py

# 3. Ajouter les scripts de test
git add test_bulletin_ex_aequo.py
git add test_rang_direct.py
git add test_validation_rang.py

# 4. Vérifier
git status

# 5. Commiter
git commit -m "Fix: Corrections supplémentaires cohérence rangs

MODIFICATIONS:
- notes/bulletin_intelligent.py: Améliorations calcul rangs
- notes/calculs.py: Harmonisation fonctions
- notes/calculs_intelligent.py: Optimisations
- notes/export_classement_fixed.py: Corrections export
- test_bulletin_classe.py: Tests mis à jour

SCRIPTS DE TEST AJOUTÉS:
- test_bulletin_ex_aequo.py: Test gestion ex-aequo
- test_rang_direct.py: Test calcul direct rangs
- test_validation_rang.py: Validation complète rangs

NETTOYAGE:
- Suppression fichiers backup
- Suppression dossiers temporaires

STATUT: Tests validés, prêt pour production"

# 6. Pousser vers GitHub
git push origin main
```

---

## 🧹 Nettoyage Alternatif (Si Besoin)

### Ignorer les Fichiers Temporaires

Ajoutez au `.gitignore` :

```bash
echo "*.backup" >> .gitignore
echo "*.bak*" >> .gitignore
echo "*.swp" >> .gitignore
echo "backups_*/" >> .gitignore
echo "fix_all_rangs.sh" >> .gitignore
```

### Restaurer les Fichiers Modifiés (Si Erreur)

```bash
# Restaurer UN fichier
git restore notes/bulletin_intelligent.py

# Restaurer TOUS les fichiers
git restore .
```

---

## ⚠️ Important

### Avant de Commiter

1. **Vérifier les modifications :**
   ```bash
   git diff notes/bulletin_intelligent.py
   git diff notes/calculs.py
   ```

2. **Tester le code :**
   ```bash
   python test_coherence_complete.py
   ```

3. **Vérifier qu'il n'y a pas de régression :**
   ```bash
   python manage.py check
   ```

### Après le Commit

1. **Vérifier le push :**
   ```bash
   git log --oneline -5
   git remote -v
   ```

2. **Redémarrer le serveur :**
   ```bash
   touch ecole_moderne/wsgi.py
   ```

---

## 📊 Résumé des Actions

| Action | Commande | Statut |
|--------|----------|--------|
| Nettoyer temporaires | `rm -rf backups_*` | ⏳ À faire |
| Ajouter modifs | `git add notes/*.py` | ⏳ À faire |
| Ajouter tests | `git add test_*.py` | ⏳ À faire |
| Commiter | `git commit -m "..."` | ⏳ À faire |
| Pousser | `git push origin main` | ⏳ À faire |
| Redémarrer | `touch wsgi.py` | ⏳ À faire |

---

## 🔍 Vérification Post-Commit

```bash
# 1. Vérifier le commit
git log -1 --stat

# 2. Vérifier la branche
git branch -vv

# 3. Vérifier le remote
git remote show origin

# 4. Tester le serveur
curl -I https://www.myschoolgn.space/

# 5. Vérifier les logs
tail -f /var/log/uwsgi/app/myschoolgn.log
```

---

## 💡 Conseils

### Pour Éviter les Conflits

1. **Toujours pull avant de modifier :**
   ```bash
   git pull origin main
   ```

2. **Créer une branche pour les tests :**
   ```bash
   git checkout -b fix-rangs-test
   ```

3. **Merger après validation :**
   ```bash
   git checkout main
   git merge fix-rangs-test
   ```

### Pour Garder un Historique Propre

1. **Commits atomiques :** Un commit = Une fonctionnalité
2. **Messages clairs :** Décrire le "quoi" et le "pourquoi"
3. **Nettoyer avant commit :** Supprimer les fichiers temporaires

---

## 📞 En Cas de Problème

### Erreur : "Your branch is ahead of 'origin/main' by 2 commits"

**Solution :**
```bash
git push origin main
```

### Erreur : "Merge conflict"

**Solution :**
```bash
git status  # Voir les conflits
# Éditer les fichiers en conflit
git add <fichiers-résolus>
git commit -m "Résolution conflits"
git push origin main
```

### Erreur : "Permission denied"

**Solution :**
```bash
# Vérifier les droits
ls -la ~/.ssh/

# Tester la connexion
ssh -T git@github.com

# Reconfigurer si nécessaire
git remote set-url origin git@github.com:Faraleno2022/GS_hadja_kanfing_dian-.git
```

---

**Auteur :** Cascade AI  
**Date :** 20 novembre 2025  
**Statut :** Prêt à exécuter ✅
