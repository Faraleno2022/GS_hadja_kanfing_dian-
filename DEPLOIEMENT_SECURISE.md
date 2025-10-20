# 🚀 GUIDE DE DÉPLOIEMENT SÉCURISÉ - PythonAnywhere

**Date:** 07/10/2025  
**Projet:** MySchool GN - Système de Gestion Scolaire

---

## 📋 PRÉ-REQUIS

- ✅ Compte PythonAnywhere actif
- ✅ Accès SSH au serveur
- ✅ Git configuré avec accès au repository
- ✅ Fichier .env local créé (ne pas le commiter!)

---

## 🔐 ÉTAPE 1 : CONFIGURATION SÉCURISÉE

### 1.1 Connexion SSH à PythonAnywhere

```bash
ssh myschoolgn@ssh.pythonanywhere.com
```

### 1.2 Mise à jour du code

```bash
cd ~/GS_hadja_kanfing_dian-

# Sauvegarder la page d'accueil personnalisée
cp templates/home.html templates/home.html.backup

# Pull des dernières modifications
git pull origin main

# Restaurer la page d'accueil
cp templates/home.html.backup templates/home.html

# Protéger définitivement home.html
git update-index --assume-unchanged templates/home.html
```

### 1.3 Créer le fichier .env SÉCURISÉ

```bash
nano ~/GS_hadja_kanfing_dian-/.env
```

**Contenu du .env (ADAPTER LES VALEURS) :**

```env
# ===== SÉCURITÉ CRITIQUE =====
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<GÉNÉRER_CLÉ_ALÉATOIRE_64_CARACTÈRES>

# ===== BASE DE DONNÉES =====
DJANGO_DB_ENGINE=sqlite

# ===== AUTHENTIFICATION =====
BLOCK_SUPERUSER_PUBLIC_LOGIN=true
MAX_LOGIN_ATTEMPTS=5
LOGIN_BLOCK_DURATION=300

# ===== TWILIO (Optionnel) =====
TWILIO_ENABLED=false

# ===== SÉCURITÉ AVANCÉE =====
IP_BLOCK_DURATION=86400
MAX_CONNECTIONS_PER_IP=10
ADMIN_WHITELIST_IPS=
```

### 1.4 Générer SECRET_KEY sécurisée

```bash
cd ~/GS_hadja_kanfing_dian-
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Copier la clé générée et la coller dans .env**

### 1.5 Sécuriser les permissions

```bash
chmod 600 ~/GS_hadja_kanfing_dian-/.env
chmod 600 ~/GS_hadja_kanfing_dian-/db.sqlite3
chmod 755 ~/GS_hadja_kanfing_dian-/logs
```

---

## 📦 ÉTAPE 2 : MISE À JOUR DÉPENDANCES

### 2.1 Activer l'environnement virtuel

```bash
cd ~/GS_hadja_kanfing_dian-
source venv/bin/activate
```

### 2.2 Mettre à jour les packages

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Vérifier les vulnérabilités

```bash
pip install safety
safety check
```

---

## 🗄️ ÉTAPE 3 : BASE DE DONNÉES

### 3.1 Appliquer les migrations

```bash
python manage.py migrate
```

### 3.2 Collecter les fichiers statiques

```bash
python manage.py collectstatic --noinput
```

### 3.3 Créer un backup

```bash
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
```

---

## ✅ ÉTAPE 4 : VÉRIFICATIONS SÉCURITÉ

### 4.1 Check de déploiement Django

```bash
python manage.py check --deploy
```

**Résultat attendu :** `System check identified no issues (0 silenced).`

### 4.2 Vérifier les variables d'environnement

```bash
python manage.py shell
```

```python
from django.conf import settings
print(f"DEBUG: {settings.DEBUG}")  # Doit être False
print(f"SECRET_KEY définie: {bool(settings.SECRET_KEY and settings.SECRET_KEY != 'dev-unsafe-key')}")  # Doit être True
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
exit()
```

### 4.3 Tester les middlewares de sécurité

```bash
python manage.py shell
```

```python
from django.conf import settings
middlewares = settings.MIDDLEWARE
print("Middlewares de sécurité actifs:")
for m in middlewares:
    if 'security' in m.lower() or 'csrf' in m.lower():
        print(f"  ✅ {m}")
exit()
```

---

## 🌐 ÉTAPE 5 : CONFIGURATION WEB

### 5.1 Recharger l'application

```bash
touch /var/www/myschoolgn_pythonanywhere_com_wsgi.py
```

### 5.2 Vérifier les logs

```bash
tail -f ~/GS_hadja_kanfing_dian-/logs/security.log
```

### 5.3 Tester HTTPS

```bash
curl -I https://www.myschoolgn.space/
```

**Vérifier les headers de sécurité :**
- ✅ `Strict-Transport-Security`
- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`

---

## 🔒 ÉTAPE 6 : TESTS DE SÉCURITÉ

### 6.1 Test connexion

1. Ouvrir https://www.myschoolgn.space/utilisateurs/login/
2. Tenter 6 connexions échouées
3. Vérifier le blocage après 5 tentatives

### 6.2 Test CSRF

1. Ouvrir la console développeur
2. Vérifier présence du token CSRF dans les formulaires
3. Tenter une requête POST sans token → Doit être bloquée

### 6.3 Test session

1. Se connecter
2. Attendre 30 minutes d'inactivité
3. Vérifier déconnexion automatique

### 6.4 Test admin Django

1. Accéder à https://www.myschoolgn.space/admin/
2. Vérifier que seuls les utilisateurs staff peuvent accéder
3. Vérifier blocage IP si configuré

---

## 📊 ÉTAPE 7 : MONITORING

### 7.1 Configurer les logs

```bash
# Rotation des logs (crontab)
crontab -e
```

Ajouter :
```cron
# Rotation logs sécurité (tous les jours à 2h)
0 2 * * * cd ~/GS_hadja_kanfing_dian- && python manage.py clearsessions

# Backup quotidien (tous les jours à 3h)
0 3 * * * cd ~/GS_hadja_kanfing_dian- && python manage.py dumpdata > ~/backups/backup_$(date +\%Y\%m\%d).json

# Nettoyage anciens backups (garder 30 jours)
0 4 * * * find ~/backups -name "backup_*.json" -mtime +30 -delete
```

### 7.2 Surveiller les tentatives d'attaque

```bash
# Voir les IP bloquées
grep "IP_BLOCKED" ~/GS_hadja_kanfing_dian-/logs/security.log

# Voir les tentatives SQL Injection
grep "SQL_INJECTION" ~/GS_hadja_kanfing_dian-/logs/security.log

# Voir les tentatives XSS
grep "XSS_ATTEMPT" ~/GS_hadja_kanfing_dian-/logs/security.log
```

---

## 🚨 ÉTAPE 8 : PLAN D'URGENCE

### 8.1 En cas d'attaque détectée

```bash
# 1. Activer le mode maintenance
cd ~/GS_hadja_kanfing_dian-
python manage.py shell
```

```python
from administration.models import MaintenanceMode
m, _ = MaintenanceMode.objects.get_or_create(defaults={'is_active': False})
m.is_active = True
m.message = "Maintenance en cours pour raisons de sécurité"
m.save()
exit()
```

```bash
# 2. Analyser les logs
tail -100 ~/GS_hadja_kanfing_dian-/logs/security.log

# 3. Bloquer IP suspecte manuellement
python manage.py shell
```

```python
from django.core.cache import cache
cache.set('blocked_ip_XXX.XXX.XXX.XXX', True, 86400)  # 24h
exit()
```

### 8.2 Restauration depuis backup

```bash
# 1. Arrêter l'application
touch /var/www/myschoolgn_pythonanywhere_com_wsgi.py

# 2. Restaurer la base de données
cd ~/GS_hadja_kanfing_dian-
python manage.py flush --noinput
python manage.py loaddata ~/backups/backup_YYYYMMDD.json

# 3. Redémarrer
touch /var/www/myschoolgn_pythonanywhere_com_wsgi.py
```

---

## ✅ CHECKLIST FINALE

Avant de mettre en production, vérifier :

- [ ] ✅ DEBUG=false dans .env
- [ ] ✅ SECRET_KEY aléatoire générée
- [ ] ✅ .env avec permissions 600
- [ ] ✅ db.sqlite3 avec permissions 600
- [ ] ✅ Migrations appliquées
- [ ] ✅ Collectstatic exécuté
- [ ] ✅ `python manage.py check --deploy` sans erreur
- [ ] ✅ HTTPS fonctionnel
- [ ] ✅ Headers de sécurité présents
- [ ] ✅ Cookies SECURE activés
- [ ] ✅ Session expiration testée
- [ ] ✅ Rate limiting testé
- [ ] ✅ CSRF protection testée
- [ ] ✅ Backup automatique configuré
- [ ] ✅ Logs sécurité actifs
- [ ] ✅ Page d'accueil protégée (git assume-unchanged)
- [ ] ✅ Dépendances à jour
- [ ] ✅ Plan d'urgence documenté

---

## 📞 CONTACTS URGENCE

**En cas d'incident de sécurité :**

- **Téléphone:** +224 622 61 35 59
- **Email:** security@myschoolgn.space
- **Support PythonAnywhere:** help@pythonanywhere.com

---

## 📚 RESSOURCES

- [RAPPORT_SECURITE.md](./RAPPORT_SECURITE.md) - Audit complet de sécurité
- [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) - Checklist détaillée
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Déploiement sécurisé effectué par :** ___________  
**Date :** ___________  
**Signature :** ___________
