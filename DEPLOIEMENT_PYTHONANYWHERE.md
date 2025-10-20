# 🚀 Guide de Déploiement sur PythonAnywhere

## 📋 Étapes de Mise à Jour

### 1. **Connexion à PythonAnywhere**
```bash
# Se connecter à votre compte PythonAnywhere
# Aller dans l'onglet "Consoles" → "Bash"
```

### 2. **Navigation vers le Projet**
```bash
cd /home/votre_username/GS_hadja_kanfing_dian--main
# ou le chemin où se trouve votre projet
```

### 3. **Sauvegarde de Sécurité (Recommandé)**
```bash
# Créer une sauvegarde avant mise à jour
cp -r . ../backup_$(date +%Y%m%d_%H%M%S)
```

### 4. **Mise à Jour depuis GitHub**
```bash
# Récupérer les dernières modifications
git fetch origin

# Vérifier les changements
git log --oneline HEAD..origin/main

# Appliquer les mises à jour
git pull origin main
```

### 5. **Activation de l'Environnement Virtuel**
```bash
# Activer votre environnement virtuel
source /home/votre_username/.virtualenvs/votre_env/bin/activate
# ou
workon votre_env_name
```

### 6. **Installation des Dépendances (si nécessaire)**
```bash
# Mettre à jour les packages si requirements.txt a changé
pip install -r requirements.txt
```

### 7. **Migrations de Base de Données**
```bash
# Appliquer les nouvelles migrations
python manage.py migrate

# Vérifier que tout est OK
python manage.py check
```

### 8. **Collecte des Fichiers Statiques**
```bash
# Collecter les nouveaux fichiers statiques
python manage.py collectstatic --noinput
```

### 9. **Redémarrage de l'Application Web**
```bash
# Aller dans l'onglet "Web" de PythonAnywhere
# Cliquer sur "Reload votre_domaine.pythonanywhere.com"
```

## 🔍 Vérifications Post-Déploiement

### 1. **Tester les Nouvelles Fonctionnalités**
- ✅ Accès à `/administration/corbeille/`
- ✅ Suppression d'élève avec code `625196629`
- ✅ Restauration depuis la corbeille
- ✅ Menu Administration → Corbeille visible

### 2. **Vérifier les Logs**
```bash
# Consulter les logs d'erreur
tail -f /var/log/votre_username.pythonanywhere.com.error.log

# Consulter les logs d'accès
tail -f /var/log/votre_username.pythonanywhere.com.access.log
```

### 3. **Test de Fonctionnement**
- ✅ Connexion utilisateur
- ✅ Navigation dans les menus
- ✅ Fonctionnalités existantes
- ✅ Nouvelles fonctionnalités de restauration

## 🚨 En Cas de Problème

### **Rollback Rapide**
```bash
# Revenir à la version précédente
git log --oneline -5
git reset --hard COMMIT_PRECEDENT
python manage.py migrate
python manage.py collectstatic --noinput
# Redémarrer l'app web
```

### **Restaurer la Sauvegarde**
```bash
# Si problème majeur, restaurer la sauvegarde
rm -rf /home/votre_username/GS_hadja_kanfing_dian--main
cp -r ../backup_YYYYMMDD_HHMMSS /home/votre_username/GS_hadja_kanfing_dian--main
```

## 📊 Nouvelles Fonctionnalités Déployées

### **🗑️ Système de Corbeille**
- **URL** : `/administration/corbeille/`
- **Accès** : Super-administrateurs uniquement
- **Fonctionnalité** : Voir et restaurer les élèves supprimés

### **🔒 Suppression Sécurisée**
- **Code requis** : `625196629`
- **URL** : `/eleves/ID/supprimer/`
- **Fonctionnalité** : Suppression avec sauvegarde automatique

### **🔄 Restauration AJAX**
- **Interface** : Boutons "Restaurer" dans la corbeille
- **Sécurité** : Confirmations multiples
- **Résultat** : Nouvel élève avec matricule `_RESTAURE`

## 🔧 Commandes Utiles

### **Vérification État**
```bash
# Statut Git
git status

# Version déployée
git log --oneline -1

# État base de données
python manage.py showmigrations

# Test système
python manage.py check
```

### **Maintenance**
```bash
# Nettoyer les sessions expirées
python manage.py clearsessions

# Nettoyer les anciens logs (si commande existe)
python manage.py clear_old_logs

# Vérifier l'espace disque
df -h
```

## 📞 Support

En cas de problème lors du déploiement :

1. **Vérifier les logs** d'erreur PythonAnywhere
2. **Consulter la console** Bash pour les erreurs
3. **Tester en local** avant de redéployer
4. **Utiliser la sauvegarde** si nécessaire

---

**Note** : Remplacez `votre_username` et `votre_env` par vos vraies valeurs PythonAnywhere.
