# 🚨 DÉPLOIEMENT URGENT - FIX ERREUR PANDAS

## ⚡ ACTIONS IMMÉDIATES (2 minutes)

### 1️⃣ Connexion au serveur
```bash
ssh myschoolgn@www.myschoolgn.space
```

### 2️⃣ Installation des dépendances
```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
source /home/myschoolgn/venv/bin/activate
pip install pandas==2.0.3 openpyxl==3.1.2
touch ecole_moderne/wsgi.py
```

### 3️⃣ Vérification
Ouvrir dans le navigateur : https://www.myschoolgn.space/

## ✅ Le site devrait être accessible immédiatement !

---

## 📋 Si le problème persiste

### Option A : Redémarrage des services
```bash
sudo systemctl restart uwsgi
sudo systemctl restart nginx
```

### Option B : Vérification des logs
```bash
tail -f /var/log/uwsgi/app/myschoolgn.log
```

### Option C : Test d'importation
```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
python manage.py shell
>>> import pandas
>>> import openpyxl
>>> exit()
```

## 🎯 Résultat attendu
- ✅ Site accessible
- ✅ Pas d'erreur 500
- ✅ Fonctionnalité d'importation de notes disponible à /notes/importer/

## 📞 Support
En cas de problème persistant, vérifier :
1. Version Python : `python --version` (doit être 3.13.1)
2. Environnement virtuel actif : `which pip` (doit pointer vers /home/myschoolgn/venv/)
3. Permissions fichiers : `ls -la notes/` (tous les fichiers doivent appartenir à myschoolgn)

## 📅 Temps estimé
- Installation : 1-2 minutes
- Redémarrage uWSGI : 10 secondes
- Total : moins de 3 minutes
