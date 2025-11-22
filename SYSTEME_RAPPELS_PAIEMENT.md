# 📱 Système de Rappels de Paiement

## 🎯 Vue d'ensemble

Le système de rappels de paiement permet d'envoyer automatiquement des messages aux parents d'élèves en retard de paiement via SMS, WhatsApp, email ou appel téléphonique.

## ✨ Fonctionnalités principales

### 1. 🔍 Détection automatique des retards
- Analyse des échéanciers de paiement
- Identification des élèves en retard (avec période de grâce configurable)
- Calcul du montant des impayés
- Suivi du nombre de jours de retard

### 2. 📨 Messages personnalisés par niveau
- **Premier rappel** : Message poli et informatif
- **Deuxième rappel** : Message urgent
- **Dernier rappel** : Message avec menace de suspension

### 3. 🌐 Multi-canaux de communication
- **SMS** : Messages courts et directs
- **WhatsApp** : Messages formatés avec emojis
- **Email** : Messages détaillés avec en-têtes
- **Appel** : Suivi des appels téléphoniques

### 4. 🤖 Automatisation complète
- Génération automatique des rappels
- Commande Django pour l'automatisation
- Interface d'administration intuitive
- Statistiques et rapports détaillés

## 📋 Composants du système

### Modèles de données
- **`Relance`** : Journal des rappels envoyés
- **`EcheancierPaiement`** : Échéanciers des élèves
- **`ConfigurationPaiement`** : Configuration des frais par classe

### Modules Python
- **`rappels.py`** : Gestionnaire principal des rappels
- **`views_rappels.py`** : Vues Django pour l'interface
- **`envoyer_rappels_paiement.py`** : Commande d'automatisation

### Templates
- **`gerer_rappels.html`** : Interface principale
- **`eleves_en_retard.html`** : Liste des élèves en retard
- **`statistiques_rappels.html`** : Tableau de bord

## 🚀 Installation et configuration

### 1. Fichiers créés
```
paiements/
├── rappels.py                    # Gestionnaire principal
├── views_rappels.py             # Vues Django
├── management/
│   └── commands/
│       └── envoyer_rappels_paiement.py  # Commande automatique
└── urls.py                      # URLs mises à jour

templates/paiements/
└── gerer_rappels.html          # Interface principale
```

### 2. URLs ajoutées
```python
# Système de rappels de paiement
path('rappels/', views_rappels.gerer_rappels, name='gerer_rappels'),
path('rappels/creer-automatiques/', views_rappels.creer_rappels_automatiques, name='creer_rappels_automatiques'),
path('rappels/eleves-retard/', views_rappels.eleves_en_retard, name='eleves_en_retard'),
# ... autres URLs
```

### 3. Permissions requises
- `can_manage_payments` : Gestion complète des rappels
- `can_view_payments` : Consultation des rappels

## 💻 Utilisation

### Interface web

#### 1. Accès principal
```
https://www.myschoolgn.space/paiements/rappels/
```

#### 2. Fonctionnalités disponibles
- **Tableau de bord** : Statistiques en temps réel
- **Rappels automatiques** : Génération en masse
- **Rappels individuels** : Création manuelle
- **Élèves en retard** : Liste détaillée
- **Statistiques** : Rapports et analyses

### Commande automatique

#### Utilisation de base
```bash
python manage.py envoyer_rappels_paiement
```

#### Options avancées
```bash
# Rappels SMS (par défaut)
python manage.py envoyer_rappels_paiement --canal SMS --limite 50

# Rappels WhatsApp
python manage.py envoyer_rappels_paiement --canal WHATSAPP --limite 100

# Mode simulation (test)
python manage.py envoyer_rappels_paiement --dry-run

# Forcer l'envoi (ignorer les rappels récents)
python manage.py envoyer_rappels_paiement --force

# Filtrer par école
python manage.py envoyer_rappels_paiement --ecole-id 1
```

## 📨 Templates de messages

### SMS
```
🏫 École Moderne
Cher(e) parent de {prenom} {nom},
Votre enfant a un solde impayé de {solde:,.0f} GNF.
Échéance dépassée: {date_echeance}
Merci de régulariser rapidement.
Contact: {telephone_ecole}
```

### WhatsApp
```
🏫 *École Moderne*

Bonjour,

Nous vous informons que votre enfant *{prenom} {nom}* ({classe}) a un solde impayé de *{solde:,.0f} GNF*.

📅 Échéance dépassée: {date_echeance}
💰 Montant dû: {solde:,.0f} GNF

Merci de régulariser ce paiement dans les plus brefs délais.

📞 Contact: {telephone_ecole}
🏫 Administration
```

### Niveaux de rappel
1. **Premier rappel** : Message informatif et poli
2. **Deuxième rappel** : Message urgent avec délai
3. **Dernier rappel** : Message avec menace de suspension

## 📊 Statistiques et rapports

### Métriques disponibles
- **Total des rappels** (30 derniers jours)
- **Élèves en retard** (temps réel)
- **Montant total impayé** (GNF)
- **Élèves concernés** (nombre unique)
- **Taux de succès** par canal
- **Évolution temporelle** des rappels

### Rapports
- **Par canal** : SMS, WhatsApp, Email, Appel
- **Par statut** : Envoyé, En attente, Échec
- **Par période** : Hebdomadaire, mensuelle
- **Top élèves** : Plus de rappels reçus

## 🔧 Configuration avancée

### Personnalisation des messages
Modifiez les templates dans `rappels.py` :
```python
self.templates_messages = {
    'SMS': {
        'PREMIER_RAPPEL': """Votre message personnalisé...""",
        # ...
    }
}
```

### Période de grâce
Ajustez le délai avant considération comme "en retard" :
```python
# Dans detecter_eleves_en_retard()
jours_grace = 7  # 7 jours par défaut
```

### Fréquence des rappels
Modifiez l'intervalle entre rappels :
```python
# Dans calculer_niveau_rappel()
date_limite = timezone.now() - timedelta(days=30)  # 30 jours
```

## 🔒 Sécurité et permissions

### Contrôle d'accès
- **Administrateurs** : Accès complet
- **Gestionnaires** : Création et consultation
- **Consultants** : Consultation uniquement
- **Filtrage par école** : Automatique selon l'utilisateur

### Audit et traçabilité
- **Historique complet** des rappels
- **Utilisateur créateur** enregistré
- **Horodatage** précis
- **Statuts de livraison** trackés

## 📈 Intégration avec services externes

### SMS (Twilio)
```python
# Configuration dans settings.py
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_PHONE_NUMBER = '+1234567890'
```

### WhatsApp Business API
```python
# Configuration WhatsApp
WHATSAPP_BUSINESS_ACCOUNT_ID = 'your_account_id'
WHATSAPP_ACCESS_TOKEN = 'your_access_token'
```

### Email (SMTP)
```python
# Configuration email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
```

## 🚀 Automatisation avec Cron

### Configuration serveur
```bash
# Éditer le crontab
crontab -e

# Ajouter une tâche quotidienne à 9h00
0 9 * * * cd /home/myschoolgn/GS_hadja_kanfing_dian- && python manage.py envoyer_rappels_paiement --canal SMS --limite 100

# Rappels WhatsApp le mercredi à 14h00
0 14 * * 3 cd /home/myschoolgn/GS_hadja_kanfing_dian- && python manage.py envoyer_rappels_paiement --canal WHATSAPP --limite 50
```

## 📱 Interface mobile

### Responsive design
- **Adaptatif** : Fonctionne sur mobile et tablette
- **Touch-friendly** : Boutons optimisés pour le tactile
- **Performance** : Chargement rapide
- **Offline** : Fonctionnalités de base disponibles

## 🔍 Dépannage

### Problèmes courants

#### 1. Aucun élève en retard détecté
```bash
# Vérifier les échéanciers
python manage.py shell
>>> from paiements.models import EcheancierPaiement
>>> EcheancierPaiement.objects.count()
```

#### 2. Rappels non créés
```bash
# Mode debug
python manage.py envoyer_rappels_paiement --dry-run --limite 5
```

#### 3. Messages non formatés
- Vérifier les templates dans `rappels.py`
- Contrôler les variables de contexte
- Tester avec un élève spécifique

### Logs et debugging
```python
# Activer les logs dans settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'rappels.log',
        },
    },
    'loggers': {
        'paiements.rappels': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

## 📞 Support et maintenance

### Contacts techniques
- **Développeur** : Support technique
- **Administrateur système** : Configuration serveur
- **Responsable paiements** : Règles métier

### Mises à jour
- **Version actuelle** : 1.0.0
- **Dernière mise à jour** : 22 novembre 2025
- **Prochaine version** : Intégration IA pour messages adaptatifs

## 🎉 Avantages du système

### Pour l'école
- ✅ **Automatisation** : Gain de temps considérable
- ✅ **Efficacité** : Rappels systématiques et réguliers
- ✅ **Traçabilité** : Historique complet des communications
- ✅ **Personnalisation** : Messages adaptés au niveau de retard
- ✅ **Multi-canal** : Flexibilité dans la communication

### Pour les parents
- ✅ **Information claire** : Montants et échéances précis
- ✅ **Rappels réguliers** : Évite les oublis
- ✅ **Contact facile** : Coordonnées de l'école incluses
- ✅ **Respect** : Messages polis et professionnels

### Pour l'administration
- ✅ **Tableau de bord** : Vue d'ensemble en temps réel
- ✅ **Statistiques** : Analyse des performances
- ✅ **Contrôle** : Gestion fine des rappels
- ✅ **Sécurité** : Permissions et audit complets

---

**Date de création** : 22 novembre 2025  
**Version** : 1.0.0  
**Statut** : ✅ Production Ready  
**Maintenance** : Support continu
