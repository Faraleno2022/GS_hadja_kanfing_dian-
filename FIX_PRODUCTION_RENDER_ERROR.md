# Fix: NameError 'render' is not defined - Production Server

## 🔴 Problème Identifié

**Erreur** : `NameError: name 'render' is not defined`  
**Fichier** : `/home/myschoolgn/GS_hadja_kanfing_dian-/eleves/views.py`, ligne 165  
**URL** : `https://www.myschoolgn.space/eleves/liste/`  
**Date** : 6 novembre 2025, 14:49 UTC

## 🔍 Diagnostic

Le serveur de production a une version obsolète ou corrompue du fichier `eleves/views.py`.

**Vérification locale** : ✅ Le fichier local est correct
- L'import `render` existe bien à la ligne 1 : `from django.shortcuts import render, get_object_or_404, redirect`
- La fonction `liste_eleves` utilise correctement `render` aux lignes 159 et 167

**Cause probable** :
1. Le serveur n'a pas été mis à jour avec la dernière version du code
2. Cache Python (.pyc) corrompu sur le serveur
3. Problème de synchronisation Git sur le serveur

## 🛠️ Solution : Commandes à Exécuter sur le Serveur

### Étape 1 : Se Connecter au Serveur

```bash
ssh myschoolgn@www.myschoolgn.space
# ou
ssh myschoolgn@[IP_DU_SERVEUR]
```

### Étape 2 : Aller dans le Répertoire du Projet

```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
```

### Étape 3 : Vérifier l'État Git

```bash
git status
git log --oneline -5
```

### Étape 4 : Mettre à Jour le Code depuis GitHub

```bash
# Sauvegarder les modifications locales si nécessaire
git stash

# Récupérer la dernière version
git fetch origin
git pull origin main

# Vérifier que le pull a réussi
git log --oneline -5
```

**Résultat attendu** : Le dernier commit devrait être `96d7472` ou plus récent.

### Étape 5 : Vérifier le Fichier views.py

```bash
# Vérifier que l'import render existe
head -25 eleves/views.py | grep "from django.shortcuts import"
```

**Résultat attendu** :
```python
from django.shortcuts import render, get_object_or_404, redirect
```

### Étape 6 : Supprimer les Fichiers Cache Python

```bash
# Supprimer tous les fichiers .pyc et __pycache__
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Ou plus simple
python3 -m compileall -f eleves/
```

### Étape 7 : Redémarrer les Services

#### Option A : Redémarrer uWSGI

```bash
# Si uWSGI est géré par systemd
sudo systemctl restart uwsgi

# Ou si c'est un service spécifique
sudo systemctl restart uwsgi-myschoolgn

# Vérifier le statut
sudo systemctl status uwsgi
```

#### Option B : Redémarrer via touch (si configuré)

```bash
# Si uWSGI est configuré avec touch-reload
touch /home/myschoolgn/GS_hadja_kanfing_dian-/reload.txt
# ou
touch /tmp/uwsgi-reload.txt
```

#### Option C : Redémarrer Nginx + uWSGI

```bash
sudo systemctl restart nginx
sudo systemctl restart uwsgi
```

### Étape 8 : Vérifier les Logs

```bash
# Logs uWSGI
sudo tail -f /var/log/uwsgi/myschoolgn.log
# ou
sudo journalctl -u uwsgi -f

# Logs Nginx
sudo tail -f /var/log/nginx/error.log
```

### Étape 9 : Tester l'Application

```bash
# Depuis le serveur
curl -I https://www.myschoolgn.space/eleves/liste/

# Ou depuis votre navigateur
# Ouvrir : https://www.myschoolgn.space/eleves/liste/
```

## 📋 Script Complet de Déploiement

Créez un fichier `deploy.sh` sur le serveur :

```bash
#!/bin/bash
# Script de déploiement pour myschoolgn.space

echo "🚀 Déploiement en cours..."

# Aller dans le répertoire du projet
cd /home/myschoolgn/GS_hadja_kanfing_dian- || exit 1

# Sauvegarder les modifications locales
echo "📦 Sauvegarde des modifications locales..."
git stash

# Mettre à jour le code
echo "⬇️ Récupération de la dernière version..."
git fetch origin
git pull origin main

# Afficher le dernier commit
echo "✅ Dernier commit:"
git log --oneline -1

# Supprimer les caches Python
echo "🧹 Nettoyage des caches Python..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Collecter les fichiers statiques
echo "📦 Collecte des fichiers statiques..."
source /home/myschoolgn/venv/bin/activate
python manage.py collectstatic --noinput

# Appliquer les migrations
echo "🗄️ Application des migrations..."
python manage.py migrate --noinput

# Redémarrer uWSGI
echo "🔄 Redémarrage d'uWSGI..."
sudo systemctl restart uwsgi

# Vérifier le statut
echo "✅ Vérification du statut..."
sudo systemctl status uwsgi --no-pager

echo "🎉 Déploiement terminé!"
```

Rendre le script exécutable :

```bash
chmod +x deploy.sh
```

Exécuter le déploiement :

```bash
./deploy.sh
```

## 🔧 Vérifications Supplémentaires

### Vérifier la Version de Python

```bash
python3 --version
# Devrait être Python 3.13.1 selon l'erreur
```

### Vérifier Django

```bash
source /home/myschoolgn/venv/bin/activate
python -c "import django; print(django.VERSION)"
# Devrait être (5, 2, 6, 'final', 0)
```

### Vérifier les Imports dans Python

```bash
source /home/myschoolgn/venv/bin/activate
python manage.py shell
```

Dans le shell Python :

```python
from django.shortcuts import render
print(render)
# Devrait afficher : <function render at 0x...>

from eleves.views import liste_eleves
print(liste_eleves)
# Devrait afficher : <function liste_eleves at 0x...>
```

## 🚨 Si le Problème Persiste

### Option 1 : Vérifier les Permissions

```bash
# Vérifier que tous les fichiers appartiennent au bon utilisateur
ls -la /home/myschoolgn/GS_hadja_kanfing_dian-/eleves/views.py

# Corriger si nécessaire
sudo chown -R myschoolgn:myschoolgn /home/myschoolgn/GS_hadja_kanfing_dian-
```

### Option 2 : Recréer le Virtualenv

```bash
cd /home/myschoolgn
mv venv venv.old
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r GS_hadja_kanfing_dian-/requirements.txt
```

### Option 3 : Vérifier la Configuration uWSGI

```bash
# Vérifier le fichier de configuration uWSGI
cat /etc/uwsgi/apps-available/myschoolgn.ini
# ou
cat /home/myschoolgn/uwsgi.ini
```

Vérifier que :
- `chdir` pointe vers `/home/myschoolgn/GS_hadja_kanfing_dian-`
- `module` est `ecole_moderne.wsgi:application`
- `home` pointe vers `/home/myschoolgn/venv`

### Option 4 : Redéploiement Complet

```bash
cd /home/myschoolgn
rm -rf GS_hadja_kanfing_dian-
git clone https://github.com/Faraleno2022/GS_hadja_kanfing_dian-.git
cd GS_hadja_kanfing_dian-
source /home/myschoolgn/venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
sudo systemctl restart uwsgi
```

## 📝 Checklist de Déploiement

- [ ] Connexion SSH au serveur réussie
- [ ] Code mis à jour depuis GitHub (`git pull`)
- [ ] Dernier commit vérifié (`96d7472` ou plus récent)
- [ ] Import `render` vérifié dans `eleves/views.py`
- [ ] Caches Python supprimés (`.pyc` et `__pycache__`)
- [ ] Fichiers statiques collectés (`collectstatic`)
- [ ] Migrations appliquées (`migrate`)
- [ ] uWSGI redémarré
- [ ] Logs vérifiés (pas d'erreurs)
- [ ] Application testée dans le navigateur
- [ ] Page `/eleves/liste/` fonctionne ✅

## 📞 Support

Si le problème persiste après toutes ces étapes :

1. **Vérifier les logs détaillés** :
   ```bash
   sudo tail -100 /var/log/uwsgi/myschoolgn.log
   sudo tail -100 /var/log/nginx/error.log
   ```

2. **Activer le mode DEBUG temporairement** (ATTENTION : uniquement pour diagnostic) :
   - Éditer `/home/myschoolgn/GS_hadja_kanfing_dian-/ecole_moderne/settings.py`
   - Changer `DEBUG = False` en `DEBUG = True`
   - Redémarrer uWSGI
   - Tester
   - **IMPORTANT** : Remettre `DEBUG = False` après le test

3. **Contacter l'administrateur système** avec :
   - Les logs complets
   - La version de Python et Django
   - La configuration uWSGI

## ✅ Résolution Attendue

Après avoir suivi ces étapes, l'erreur `NameError: name 'render' is not defined` devrait être résolue.

**Temps estimé** : 5-10 minutes

---

**Date de création** : 6 novembre 2025  
**Dernière mise à jour** : 6 novembre 2025  
**Statut** : 🔴 En attente de déploiement sur le serveur de production
