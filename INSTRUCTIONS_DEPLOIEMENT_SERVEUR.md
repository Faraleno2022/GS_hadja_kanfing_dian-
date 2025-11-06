# 🚀 Instructions de Déploiement sur le Serveur de Production

## 🔴 Problème Actuel

**Erreur** : `NameError: name 'render' is not defined`  
**URL** : https://www.myschoolgn.space/eleves/liste/  
**Cause** : Le serveur de production a une version obsolète du code

## ✅ Solution en 3 Étapes

### Étape 1 : Se Connecter au Serveur

```bash
ssh myschoolgn@www.myschoolgn.space
```

Ou si vous avez une clé SSH configurée :
```bash
ssh -i ~/.ssh/votre_cle myschoolgn@www.myschoolgn.space
```

### Étape 2 : Exécuter le Script de Déploiement

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
chmod +x deploy_production.sh
./deploy_production.sh
```

Le script va automatiquement :
- ✅ Mettre à jour le code depuis GitHub
- ✅ Nettoyer les caches Python
- ✅ Collecter les fichiers statiques
- ✅ Appliquer les migrations
- ✅ Redémarrer uWSGI
- ✅ Vérifier que tout fonctionne

### Étape 3 : Vérifier

Ouvrir dans votre navigateur :
```
https://www.myschoolgn.space/eleves/liste/
```

L'erreur devrait être corrigée ! ✅

---

## 🛠️ Solution Manuelle (Alternative)

Si le script automatique ne fonctionne pas, voici les commandes manuelles :

```bash
# 1. Se connecter
ssh myschoolgn@www.myschoolgn.space

# 2. Aller dans le projet
cd /home/myschoolgn/GS_hadja_kanfing_dian-

# 3. Mettre à jour le code
git pull origin main

# 4. Nettoyer les caches
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 5. Activer le virtualenv
source /home/myschoolgn/venv/bin/activate

# 6. Collecter les statiques
python manage.py collectstatic --noinput

# 7. Appliquer les migrations
python manage.py migrate

# 8. Redémarrer uWSGI
sudo systemctl restart uwsgi

# 9. Vérifier le statut
sudo systemctl status uwsgi
```

---

## 📋 Vérifications Post-Déploiement

### 1. Vérifier que le code est à jour

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
git log --oneline -1
```

**Résultat attendu** : `f4eeaa6` ou plus récent

### 2. Vérifier l'import render

```bash
head -1 eleves/views.py
```

**Résultat attendu** :
```python
from django.shortcuts import render, get_object_or_404, redirect
```

### 3. Vérifier les logs

```bash
sudo tail -50 /var/log/uwsgi/myschoolgn.log
```

Pas d'erreurs = ✅

### 4. Tester l'application

```bash
curl -I https://www.myschoolgn.space/eleves/liste/
```

**Code HTTP attendu** : 200 ou 302 (redirection vers login)

---

## 🔍 Diagnostic en Cas de Problème

### Vérifier les Logs en Temps Réel

```bash
# Logs uWSGI
sudo tail -f /var/log/uwsgi/myschoolgn.log

# Logs système
sudo journalctl -u uwsgi -f

# Logs Nginx
sudo tail -f /var/log/nginx/error.log
```

### Tester l'Import Python

```bash
source /home/myschoolgn/venv/bin/activate
python manage.py shell
```

Dans le shell Python :
```python
from django.shortcuts import render
print(render)  # Devrait afficher : <function render at 0x...>

from eleves.views import liste_eleves
print(liste_eleves)  # Devrait afficher : <function liste_eleves at 0x...>
```

Si ça fonctionne dans le shell mais pas dans l'application, redémarrer uWSGI :
```bash
sudo systemctl restart uwsgi
```

---

## 📞 Support

### Fichiers de Documentation

1. **`SOLUTION_RAPIDE_RENDER_ERROR.txt`** - Guide ultra-rapide
2. **`FIX_PRODUCTION_RENDER_ERROR.md`** - Documentation complète
3. **`deploy_production.sh`** - Script de déploiement automatisé

### Commandes Utiles

```bash
# Statut des services
sudo systemctl status uwsgi
sudo systemctl status nginx

# Redémarrer les services
sudo systemctl restart uwsgi
sudo systemctl restart nginx

# Recharger uWSGI sans redémarrage complet
sudo systemctl reload uwsgi

# Vérifier la configuration Nginx
sudo nginx -t

# Voir les processus uWSGI
ps aux | grep uwsgi
```

---

## ⏱️ Temps Estimé

- **Avec script automatique** : 2-3 minutes
- **Manuellement** : 5-10 minutes

---

## ✅ Checklist de Déploiement

- [ ] Connexion SSH réussie
- [ ] Code mis à jour (`git pull`)
- [ ] Dernier commit vérifié (`f4eeaa6` ou plus récent)
- [ ] Import `render` présent dans `eleves/views.py`
- [ ] Caches Python supprimés
- [ ] Fichiers statiques collectés
- [ ] Migrations appliquées
- [ ] uWSGI redémarré
- [ ] Logs vérifiés (pas d'erreurs)
- [ ] Application testée dans le navigateur
- [ ] Page `/eleves/liste/` fonctionne ✅

---

## 🎯 Résultat Attendu

Après le déploiement :
- ✅ L'erreur `NameError: name 'render' is not defined` est corrigée
- ✅ La page https://www.myschoolgn.space/eleves/liste/ fonctionne
- ✅ Toutes les fonctionnalités sont opérationnelles

---

## 📝 Notes Importantes

1. **Sauvegarde** : Le script fait automatiquement un `git stash` des modifications locales
2. **Permissions** : Vous devez avoir les droits sudo pour redémarrer uWSGI
3. **Temps d'arrêt** : Le redémarrage d'uWSGI prend ~2-3 secondes
4. **Cache navigateur** : Videz le cache de votre navigateur si nécessaire (Ctrl+F5)

---

**Date** : 6 novembre 2025  
**Statut** : 🟡 En attente de déploiement sur le serveur  
**Priorité** : 🔴 HAUTE (erreur en production)

---

## 🚨 Après le Déploiement

Une fois le déploiement réussi, merci de :
1. Confirmer que l'erreur est corrigée
2. Tester les principales fonctionnalités
3. Vérifier les logs pour d'éventuelles autres erreurs

**Contact** : En cas de problème, consultez les logs et la documentation complète dans `FIX_PRODUCTION_RENDER_ERROR.md`
