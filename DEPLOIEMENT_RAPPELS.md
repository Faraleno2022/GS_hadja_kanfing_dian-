# 🚀 Guide de Déploiement - Système de Rappels de Paiement

## 📋 Étapes de déploiement sur le serveur de production

### 1. 🔄 Mise à jour du code source

```bash
# Connexion au serveur
ssh myschoolgn@www.myschoolgn.space

# Navigation vers le répertoire du projet
cd /home/myschoolgn/GS_hadja_kanfing_dian-

# Sauvegarde de sécurité
cp -r . ../backup_$(date +%Y%m%d_%H%M%S)

# Mise à jour depuis GitHub
git pull origin main
```

### 2. 🔧 Vérification des nouveaux fichiers

```bash
# Vérifier que les nouveaux fichiers sont présents
ls -la paiements/rappels.py
ls -la paiements/views_rappels.py
ls -la paiements/management/commands/envoyer_rappels_paiement.py
ls -la templates/paiements/gerer_rappels.html
```

### 3. 🗄️ Migrations de base de données

```bash
# Activer l'environnement virtuel
source venv/bin/activate  # ou source env/bin/activate

# Créer les migrations si nécessaire
python manage.py makemigrations

# Appliquer les migrations
python manage.py migrate
```

### 4. 📦 Installation des dépendances (si nouvelles)

```bash
# Mettre à jour les packages Python
pip install -r requirements.txt

# Vérifier les imports
python manage.py check
```

### 5. 🔐 Configuration des permissions

```bash
# Vérifier les permissions des fichiers
chmod 644 paiements/rappels.py
chmod 644 paiements/views_rappels.py
chmod 755 paiements/management/commands/envoyer_rappels_paiement.py
chmod 644 templates/paiements/gerer_rappels.html

# Propriétaire correct
chown myschoolgn:myschoolgn -R paiements/
chown myschoolgn:myschoolgn -R templates/paiements/
```

### 6. 🧪 Test du système

```bash
# Test de la commande de rappels (mode simulation)
python manage.py envoyer_rappels_paiement --dry-run --limite 5

# Vérification de l'interface web
python manage.py runserver 0.0.0.0:8000
# Puis tester : http://www.myschoolgn.space:8000/paiements/rappels/
```

### 7. 🔄 Redémarrage des services

```bash
# Redémarrer Apache/Nginx (selon la configuration)
sudo systemctl restart apache2
# ou
sudo systemctl restart nginx

# Redémarrer Gunicorn si utilisé
sudo systemctl restart gunicorn
```

### 8. ⏰ Configuration de l'automatisation (optionnel)

```bash
# Éditer le crontab pour automatiser les rappels
crontab -e

# Ajouter ces lignes pour l'automatisation :

# Rappels SMS quotidiens à 9h00
0 9 * * * cd /home/myschoolgn/GS_hadja_kanfing_dian- && /home/myschoolgn/GS_hadja_kanfing_dian-/venv/bin/python manage.py envoyer_rappels_paiement --canal SMS --limite 100 >> /var/log/rappels_sms.log 2>&1

# Rappels WhatsApp le mercredi à 14h00
0 14 * * 3 cd /home/myschoolgn/GS_hadja_kanfing_dian- && /home/myschoolgn/GS_hadja_kanfing_dian-/venv/bin/python manage.py envoyer_rappels_paiement --canal WHATSAPP --limite 50 >> /var/log/rappels_whatsapp.log 2>&1

# Sauvegarder le crontab
crontab -l > /home/myschoolgn/crontab_backup.txt
```

## ✅ Vérification post-déploiement

### 1. 🌐 Test de l'interface web

Accédez aux URLs suivantes pour vérifier le bon fonctionnement :

- **Gestion des rappels** : `https://www.myschoolgn.space/paiements/rappels/`
- **Élèves en retard** : `https://www.myschoolgn.space/paiements/rappels/eleves-retard/`
- **Statistiques** : `https://www.myschoolgn.space/paiements/rappels/statistiques/`

### 2. 🧪 Test de la commande

```bash
# Test avec simulation
python manage.py envoyer_rappels_paiement --dry-run --limite 3

# Si le test fonctionne, test réel avec 1 rappel
python manage.py envoyer_rappels_paiement --limite 1
```

### 3. 📊 Vérification des données

```bash
# Vérifier la création des rappels dans la base
python manage.py shell
>>> from paiements.models import Relance
>>> Relance.objects.count()
>>> Relance.objects.last()  # Voir le dernier rappel créé
```

## 🔧 Configuration avancée

### 1. 📱 Configuration SMS (Twilio)

Si vous souhaitez activer l'envoi réel de SMS, ajoutez dans `settings.py` :

```python
# Configuration Twilio pour SMS
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_PHONE_NUMBER = '+224XXXXXXXX'  # Numéro guinéen
```

### 2. 📧 Configuration Email

Pour les rappels par email, configurez SMTP dans `settings.py` :

```python
# Configuration Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'ecole@myschoolgn.space'
EMAIL_HOST_PASSWORD = 'your_app_password'
DEFAULT_FROM_EMAIL = 'École Moderne <ecole@myschoolgn.space>'
```

### 3. 📱 Configuration WhatsApp Business

Pour WhatsApp Business API :

```python
# Configuration WhatsApp Business
WHATSAPP_BUSINESS_ACCOUNT_ID = 'your_account_id'
WHATSAPP_ACCESS_TOKEN = 'your_access_token'
WHATSAPP_PHONE_NUMBER_ID = 'your_phone_number_id'
```

## 📝 Logs et monitoring

### 1. 📊 Fichiers de logs

Créez les répertoires de logs :

```bash
sudo mkdir -p /var/log/ecole/
sudo chown myschoolgn:myschoolgn /var/log/ecole/
```

### 2. 🔍 Monitoring des rappels

```bash
# Voir les logs des rappels SMS
tail -f /var/log/rappels_sms.log

# Voir les logs des rappels WhatsApp
tail -f /var/log/rappels_whatsapp.log

# Statistiques quotidiennes
python manage.py envoyer_rappels_paiement --dry-run | grep "RÉSUMÉ" -A 10
```

## 🚨 Dépannage

### Problèmes courants et solutions

#### 1. Erreur d'import
```bash
# Vérifier la structure des fichiers
python -c "from paiements.rappels import gestionnaire_rappels; print('OK')"
```

#### 2. Permissions insuffisantes
```bash
# Corriger les permissions
chmod -R 755 paiements/management/
chown -R myschoolgn:myschoolgn paiements/
```

#### 3. Base de données
```bash
# Réinitialiser les migrations si problème
python manage.py migrate paiements zero
python manage.py migrate paiements
```

#### 4. Interface web non accessible
```bash
# Vérifier les URLs
python manage.py show_urls | grep rappels

# Redémarrer le serveur web
sudo systemctl restart apache2
```

## 📞 Support

### Contacts en cas de problème

- **Technique** : Vérifier les logs et la documentation
- **Fonctionnel** : Tester avec des données réelles
- **Urgence** : Désactiver temporairement le cron

### Rollback en cas de problème

```bash
# Revenir à la version précédente
cd /home/myschoolgn/GS_hadja_kanfing_dian-
git log --oneline -5  # Voir les derniers commits
git reset --hard 3e1429e  # Revenir au commit précédent

# Redémarrer les services
sudo systemctl restart apache2
```

## 🎉 Fonctionnalités disponibles après déploiement

### ✅ Interface d'administration
- Création manuelle de rappels
- Génération automatique en masse
- Consultation des statistiques
- Gestion des élèves en retard

### ✅ Automatisation
- Commande Django fonctionnelle
- Possibilité d'automatisation via cron
- Logs détaillés des opérations

### ✅ Multi-canaux
- SMS (avec configuration Twilio)
- WhatsApp (avec Business API)
- Email (avec SMTP)
- Appels (suivi manuel)

### ✅ Rapports
- Statistiques en temps réel
- Historique des rappels
- Analyse par canal et période

---

**Date de déploiement** : 22 novembre 2025  
**Version déployée** : 1.0.0  
**Commit** : ffba86f  
**Statut** : ✅ Prêt pour la production
