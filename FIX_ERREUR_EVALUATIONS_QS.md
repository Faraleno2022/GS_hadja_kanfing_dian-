# FIX: Erreur evaluations_qs non défini

## 🔴 PROBLÈME

Erreur lors de la génération des bulletins PDF de classe:
```
NameError: name 'evaluations_qs' is not defined
Ligne: /home/myschoolgn/GS_hadja_kanfing_dian-/notes/views.py, ligne 5621
URL: /notes/bulletins/classe/pdf/
```

## 🔍 CAUSE

Le serveur de production a une **version obsolète** du code. La variable `evaluations_qs` n'existe plus dans la dernière version - elle a été renommée en `evaluations`.

## ✅ SOLUTION

### Déploiement sur le serveur

Connectez-vous au serveur et exécutez:

```bash
ssh myschoolgn@www.myschoolgn.space
cd /home/myschoolgn/GS_hadja_kanfing_dian-
chmod +x deployer_correctif_bulletins.sh
./deployer_correctif_bulletins.sh
```

### OU Commandes manuelles

```bash
ssh myschoolgn@www.myschoolgn.space
cd /home/myschoolgn/GS_hadja_kanfing_dian-

# Récupérer les dernières modifications
git fetch origin
git reset --hard origin/main

# Nettoyer les caches
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# Redémarrer
touch ecole_moderne/wsgi.py
```

## 📝 MODIFICATIONS APPORTÉES

### Fichier: `notes/views.py` (ligne 5660)

**Avant** (version serveur):
```python
evaluations_qs = Evaluation.objects.filter(...)
for evaluation in evaluations_qs:
    ...
```

**Après** (version locale/GitHub):
```python
evaluations = Evaluation.objects.filter(
    matiere=matiere,
    periode=periode
).order_by('date_evaluation')

for evaluation in evaluations:
    ...
```

## 🎯 COMMITS CONCERNÉS

- **9bd8443**: Séparation téléphone et email sur lignes distinctes
- **1a2e141**: Fix suppression de l'adresse dans PDF
- **66709fe**: Ajout export PDF des classements
- **de6043c**: Fix periode_classement UnboundLocalError
- **18a7941**: Consultation notes avec classement

## ✅ VÉRIFICATION

Après le déploiement, testez:

1. Accédez à: https://www.myschoolgn.space/notes/consulter/
2. Sélectionnez une classe, période et type
3. Cliquez sur **"Exporter Bulletins Classe (PDF)"**
4. Le PDF devrait se générer sans erreur

## 📊 STATUT

- ✅ Code local: À jour (commit 9bd8443)
- ✅ GitHub: À jour (commit 9bd8443)
- ❌ Serveur production: Obsolète (nécessite mise à jour)
- 🎯 Action requise: Déployer sur production

## 📅 DATE

17 novembre 2025 - 09:39 UTC
