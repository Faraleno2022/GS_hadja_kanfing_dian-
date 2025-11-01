# 🚀 Déploiement en Production - Conversion Majuscules

**Date:** 23 octobre 2025  
**Objectif:** Convertir les données existantes en production en MAJUSCULES

---

## ⚠️ IMPORTANT

Les modifications de code (formulaires avec conversion automatique) sont déjà déployées via GitHub, **MAIS** les données existantes en base de données ne sont pas automatiquement converties.

Il faut exécuter une commande de migration sur le serveur de production.

---

## 📋 Étapes de Déploiement

### **1. Se connecter au serveur de production**

```bash
# Via SSH (exemple)
ssh utilisateur@votre-serveur.com

# Ou via PythonAnywhere, Heroku, etc.
# Accéder à la console Bash
```

### **2. Aller dans le répertoire du projet**

```bash
cd /chemin/vers/votre/projet
# Exemple PythonAnywhere: cd ~/myschool--main
```

### **3. Activer l'environnement virtuel**

```bash
source venv/bin/activate
# Ou sur PythonAnywhere: source /home/votre_username/venv/bin/activate
```

### **4. Mettre à jour le code depuis GitHub**

```bash
git pull origin master
```

Cela va télécharger:
- ✅ Les formulaires avec conversion automatique
- ✅ La commande `convertir_majuscules`
- ✅ Toute la documentation

### **5. Tester la commande en mode DRY-RUN (recommandé)**

```bash
python manage.py convertir_majuscules --dry-run
```

**Résultat attendu:**
```
Mode DRY-RUN: Aucune modification ne sera appliquée

📚 Conversion des élèves...
  - Élève: diallo → DIALLO
  - Prénom: ibrahima → IBRAHIMA
  ...

👨‍👩‍👧 Conversion des responsables...
  - Responsable: Diallo → DIALLO
  ...

📊 Statistiques:
  - Élèves modifiés: 150
  - Responsables modifiés: 200
  - Classes modifiées: 25
  - Écoles modifiées: 1
  - TOTAL: 376 enregistrements

⚠️  Mode DRY-RUN: Aucune modification n'a été appliquée
```

### **6. Faire une sauvegarde de la base de données**

**TRÈS IMPORTANT avant de modifier les données !**

#### **SQLite:**
```bash
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)
```

#### **PostgreSQL:**
```bash
pg_dump nom_base > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### **MySQL:**
```bash
mysqldump nom_base > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### **PythonAnywhere:**
```bash
# Via l'interface web: Databases > Download
# Ou en ligne de commande:
cp /home/username/db.sqlite3 /home/username/backups/db_$(date +%Y%m%d).sqlite3
```

### **7. Exécuter la conversion**

```bash
python manage.py convertir_majuscules
```

**Résultat attendu:**
```
📚 Conversion des élèves...
👨‍👩‍👧 Conversion des responsables...
🏫 Conversion des classes...
🏢 Conversion des écoles...

============================================================
✅ Conversion terminée avec succès!

📊 Statistiques:
  - Élèves modifiés: 150
  - Responsables modifiés: 200
  - Classes modifiées: 25
  - Écoles modifiées: 1
  - TOTAL: 376 enregistrements

✅ Toutes les modifications ont été enregistrées en base de données
```

### **8. Vérifier les données**

```bash
python manage.py shell
```

```python
from eleves.models import Eleve, Responsable

# Vérifier un élève
eleve = Eleve.objects.first()
print(f"Nom: {eleve.nom}")  # Devrait être en MAJUSCULES
print(f"Prénom: {eleve.prenom}")  # Devrait être en MAJUSCULES

# Vérifier un responsable
resp = Responsable.objects.first()
print(f"Nom: {resp.nom}")  # Devrait être en MAJUSCULES
print(f"Prénom: {resp.prenom}")  # Devrait être en MAJUSCULES
```

### **9. Redémarrer l'application (si nécessaire)**

#### **PythonAnywhere:**
- Aller sur l'onglet "Web"
- Cliquer sur "Reload" pour redémarrer l'application

#### **Heroku:**
```bash
heroku restart
```

#### **Serveur avec Gunicorn/uWSGI:**
```bash
sudo systemctl restart gunicorn
# ou
sudo systemctl restart uwsgi
```

### **10. Tester sur le site web**

1. Aller sur votre site en production
2. Vérifier la liste des élèves
3. Les noms devraient maintenant être en MAJUSCULES
4. Ajouter un nouvel élève en minuscules
5. Vérifier qu'il est automatiquement converti en MAJUSCULES

---

## 🔍 Dépannage

### **Problème 1: Commande introuvable**

**Erreur:**
```
Unknown command: 'convertir_majuscules'
```

**Solution:**
```bash
# Vérifier que le fichier existe
ls eleves/management/commands/convertir_majuscules.py

# Si absent, faire git pull
git pull origin master

# Vérifier la structure des dossiers
ls -R eleves/management/
```

### **Problème 2: Toujours 0 modifications**

**Causes possibles:**
1. Les données sont déjà en majuscules
2. Problème de détection dans la commande

**Vérification:**
```bash
python manage.py shell
```
```python
from eleves.models import Eleve

# Vérifier un élève spécifique
e = Eleve.objects.first()
print(f"Nom actuel: [{e.nom}]")
print(f"Est en majuscules: {e.nom == e.nom.upper()}")
print(f"Nom en majuscules: [{e.nom.upper()}]")
```

### **Problème 3: Erreur de permission**

**Erreur:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Vérifier les permissions
ls -l db.sqlite3

# Donner les permissions si nécessaire
chmod 664 db.sqlite3
```

### **Problème 4: Les données ne s'affichent pas en majuscules**

**Causes possibles:**
1. CSS qui transforme l'affichage (`text-transform: capitalize`)
2. Filtre Django dans les templates (`|title`, `|capfirst`)

**Vérification:**
- Inspecter l'élément dans le navigateur (F12)
- Vérifier les fichiers CSS
- Vérifier les templates HTML

---

## 📱 Déploiement sur PythonAnywhere (Exemple détaillé)

### **Étape par étape:**

1. **Se connecter à PythonAnywhere**
   - Aller sur https://www.pythonanywhere.com
   - Se connecter avec votre compte

2. **Ouvrir une console Bash**
   - Onglet "Consoles"
   - Cliquer sur "Bash"

3. **Naviguer vers le projet**
   ```bash
   cd ~/myschool--main
   ```

4. **Activer l'environnement virtuel**
   ```bash
   source venv/bin/activate
   ```

5. **Mettre à jour depuis GitHub**
   ```bash
   git pull origin master
   ```

6. **Faire une sauvegarde**
   ```bash
   cp db.sqlite3 ~/backups/db_$(date +%Y%m%d_%H%M%S).sqlite3
   ```

7. **Tester en DRY-RUN**
   ```bash
   python manage.py convertir_majuscules --dry-run
   ```

8. **Exécuter la conversion**
   ```bash
   python manage.py convertir_majuscules
   ```

9. **Redémarrer l'application**
   - Aller sur l'onglet "Web"
   - Cliquer sur le bouton "Reload"

10. **Vérifier sur le site**
    - Ouvrir votre site
    - Vérifier que les noms sont en MAJUSCULES

---

## ✅ Checklist de Déploiement

- [ ] Se connecter au serveur de production
- [ ] Aller dans le répertoire du projet
- [ ] Activer l'environnement virtuel
- [ ] Faire `git pull origin master`
- [ ] Tester avec `--dry-run`
- [ ] **FAIRE UNE SAUVEGARDE DE LA BASE DE DONNÉES**
- [ ] Exécuter `python manage.py convertir_majuscules`
- [ ] Vérifier les statistiques affichées
- [ ] Tester dans le shell Django
- [ ] Redémarrer l'application
- [ ] Vérifier sur le site web
- [ ] Tester l'ajout d'un nouvel élève
- [ ] Supprimer la sauvegarde si tout est OK

---

## 🎯 Résultat Attendu

### **Avant:**
```
Nom: ibrahima diallo
Responsable: alhassane Diallo
Classe: 11 Série Littéraire
```

### **Après:**
```
Nom: IBRAHIMA DIALLO
Responsable: ALHASSANE DIALLO
Classe: 11 SÉRIE LITTÉRAIRE
```

---

## 📞 Support

Si vous rencontrez des problèmes:

1. **Vérifier les logs Django**
   ```bash
   tail -f /var/log/django/error.log
   ```

2. **Vérifier les logs du serveur web**
   ```bash
   tail -f /var/log/nginx/error.log
   # ou
   tail -f /var/log/apache2/error.log
   ```

3. **Restaurer la sauvegarde si nécessaire**
   ```bash
   cp db.sqlite3.backup db.sqlite3
   ```

4. **Contacter le support technique**

---

## 🔄 Pour les futures mises à jour

**Bonne nouvelle:** Une fois cette migration effectuée, vous n'aurez plus besoin de la refaire !

Toutes les **nouvelles données** saisies après cette migration seront **automatiquement converties en MAJUSCULES** grâce aux modifications dans les formulaires.

La commande `convertir_majuscules` n'est nécessaire que pour les données **déjà existantes** en base.

---

**Dernière mise à jour:** 23 octobre 2025  
**Auteur:** Cascade AI  
**Version:** 1.0
