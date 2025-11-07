# 📚 Documentation : Suppression Définitive des Enseignants

## 📅 Date d'implémentation
**7 novembre 2024**

## 🎯 Objectif
Ajouter la possibilité de supprimer définitivement un enseignant avec tous ses états de salaire, affectations et présences, tout en conservant une traçabilité complète dans la corbeille.

## 🔒 Système de Sécurité Multi-Niveaux

### 1. Authentification
- Décorateur `@login_required` obligatoire
- Seuls les utilisateurs connectés peuvent accéder

### 2. Permissions
- **Superusers** : Suppression définitive automatique
- **Utilisateurs avec permission** : `profil.peut_supprimer_enseignants_definitivement = True`
- **Autres utilisateurs** : Soft delete uniquement (statut → DÉMISSIONNAIRE)

### 3. Code de Vérification
- Code unique : **625196629**
- Obligatoire pour toute suppression
- Même code que pour les élèves (cohérence)

### 4. Double Confirmation
- Confirmation JavaScript dans le navigateur
- Message détaillant toutes les conséquences

## 🔧 Modifications Techniques

### 1. Base de Données

#### Nouveau Champ dans le Modèle Profil
```python
# utilisateurs/models.py (ligne 44)
peut_supprimer_enseignants_definitivement = models.BooleanField(
    default=False, 
    verbose_name="Peut supprimer les enseignants définitivement"
)
```

#### Migration Créée
```
utilisateurs/migrations/0009_profil_peut_supprimer_enseignants_definitivement.py
```

### 2. Vue de Suppression

#### Fichier Modifié
`salaires/views.py` (fonction `supprimer_enseignant`, lignes 1726-1864)

#### Fonctionnalités Ajoutées
- ✅ Vérification de la permission
- ✅ Comptage des éléments associés
- ✅ Code de vérification (625196629)
- ✅ Suppression définitive avec transaction atomique
- ✅ Soft delete (statut → DÉMISSIONNAIRE)
- ✅ Logging dans SystemLog
- ✅ Journalisation dans JournalActivite

### 3. Template de Confirmation

#### Nouveau Fichier
`templates/salaires/confirmer_suppression_enseignant.html`

#### Caractéristiques
- Design cohérent avec la suppression des élèves
- Zone de danger visuelle
- Affichage des éléments qui seront supprimés
- Checkbox pour suppression définitive (si permission)
- Validation JavaScript du code

## 📊 Comportement Selon les Permissions

### Utilisateur AVEC Permission

```
Interface:
✅ Case "Suppression définitive" VISIBLE et COCHÉE
✅ Message explicatif des conséquences

Actions:
- Si cochée → Suppression DÉFINITIVE
  - Enseignant supprimé de la base
  - États de salaire supprimés
  - Affectations supprimées  
  - Présences supprimées
  - Log dans SystemLog (corbeille)
  
- Si décochée → Soft delete
  - Statut → DÉMISSIONNAIRE
  - Toutes les données conservées
```

### Utilisateur SANS Permission

```
Interface:
⚠️ PAS de case "Suppression définitive"
⚠️ Message: "Vous n'avez pas la permission..."

Action unique:
- Soft delete automatique
  - Statut → DÉMISSIONNAIRE
  - Toutes les données conservées
  - Log dans JournalActivite
```

### Superuser / Admin

```
Comportement:
✅ Suppression définitive PAR DÉFAUT
✅ Peut décocher pour soft delete si nécessaire
✅ Log automatique de debug
```

## 🗑️ Système de Corbeille

### Suppression Définitive
```python
SystemLog.objects.create(
    action='SUPPRESSION_DEFINITIVE_ENSEIGNANT',
    description=f"Suppression définitive de l'enseignant...",
    details={
        'enseignant_id': id,
        'nom_complet': nom,
        'ecole': ecole,
        'type_enseignant': type,
        'salaire_fixe': salaire,
        'taux_horaire': taux,
        'etats_supprimes': [...],
        'affectations_supprimees': [...],
        'verification_code_used': True
    }
)
```

### Soft Delete
```python
JournalActivite.objects.create(
    action='DESACTIVATION',
    type_objet='ENSEIGNANT',
    description=f"Désactivation de l'enseignant (statut → Démissionnaire)"
)
```

## 🛠️ Scripts Utilitaires

### 1. fix_suppression_enseignants.py

#### Commandes Disponibles
```bash
# Diagnostic général
python fix_suppression_enseignants.py

# Diagnostiquer un utilisateur
python fix_suppression_enseignants.py --diagnostic USERNAME

# Activer la permission
python fix_suppression_enseignants.py --activer USERNAME

# Lister les utilisateurs avec permission
python fix_suppression_enseignants.py --liste

# Afficher les statistiques
python fix_suppression_enseignants.py --stats

# Test de simulation
python fix_suppression_enseignants.py --test
```

### 2. test_suppression_enseignants.py

#### Tests Automatisés
- ✅ Test avec permission (suppression définitive)
- ✅ Test sans permission (soft delete)
- ✅ Vérification de la corbeille
- ✅ Statistiques
- ✅ Création de données test
- ✅ Nettoyage optionnel

## 📋 Guide d'Utilisation

### Pour l'Administrateur

#### 1. Appliquer la Migration
```bash
python manage.py migrate
```

#### 2. Activer la Permission pour un Utilisateur
```bash
python fix_suppression_enseignants.py --activer USERNAME
```

#### 3. Vérifier les Permissions
```bash
python fix_suppression_enseignants.py --liste
```

### Pour l'Utilisateur Final

#### 1. Accéder à la Liste des Enseignants
URL : `/salaires/enseignants/`

#### 2. Sélectionner un Enseignant
Cliquer sur le nom ou "Détails"

#### 3. Cliquer sur "Supprimer"
Bouton rouge dans la page de détail

#### 4. Remplir le Formulaire
- Entrer le code : **625196629**
- Cocher/décocher "Suppression définitive" (si disponible)
- Confirmer l'action

## 📊 Statistiques et Monitoring

### Requêtes SQL Utiles

```sql
-- Enseignants démissionnaires (soft delete)
SELECT COUNT(*) FROM salaires_enseignant 
WHERE statut = 'DEMISSIONNAIRE';

-- Suppressions définitives dans la corbeille
SELECT COUNT(*) FROM administration_systemlog 
WHERE action = 'SUPPRESSION_DEFINITIVE_ENSEIGNANT';

-- Utilisateurs avec permission
SELECT COUNT(DISTINCT u.id) 
FROM auth_user u
LEFT JOIN utilisateurs_profil p ON u.id = p.user_id
WHERE u.is_superuser = TRUE 
   OR p.peut_supprimer_enseignants_definitivement = TRUE;
```

### Django Shell

```python
# Compter les enseignants démissionnaires
from salaires.models import Enseignant
Enseignant.objects.filter(statut='DEMISSIONNAIRE').count()

# Voir les dernières suppressions
from administration.models import SystemLog
SystemLog.objects.filter(
    action='SUPPRESSION_DEFINITIVE_ENSEIGNANT'
).order_by('-created_at')[:5]

# Activer la permission pour un utilisateur
from django.contrib.auth.models import User
from utilisateurs.models import Profil

user = User.objects.get(username='USERNAME')
profil, _ = Profil.objects.get_or_create(user=user)
profil.peut_supprimer_enseignants_definitivement = True
profil.save()
```

## 🔄 Comparaison avec la Suppression des Élèves

| Aspect | Élèves | Enseignants |
|--------|--------|-------------|
| **Permission** | `peut_supprimer_eleves_definitivement` | `peut_supprimer_enseignants_definitivement` |
| **Code vérification** | 625196629 | 625196629 (même) |
| **Soft delete statut** | EXCLU | DEMISSIONNAIRE |
| **Action SystemLog** | SUPPRESSION_DEFINITIVE | SUPPRESSION_DEFINITIVE_ENSEIGNANT |
| **Éléments supprimés** | Paiements, abonnements | États salaire, affectations, présences |

## ⚠️ Points d'Attention

### 1. Impact de la Suppression Définitive
- **Irréversible** : Aucune récupération possible
- **États de salaire** : Historique financier perdu
- **Affectations** : Historique des classes perdu
- **Présences** : Historique de pointage perdu

### 2. Recommandations
- Préférer le **soft delete** (décocher la case) pour conserver l'historique
- La suppression définitive uniquement si vraiment nécessaire
- Toujours vérifier les éléments associés avant suppression
- Faire des sauvegardes régulières de la base de données

### 3. Sécurité
- Ne jamais partager le code de vérification
- Limiter les permissions aux utilisateurs de confiance
- Auditer régulièrement les suppressions via SystemLog

## 📁 Fichiers Créés/Modifiés

### Nouveaux Fichiers
1. `fix_suppression_enseignants.py` - Script de diagnostic et activation
2. `test_suppression_enseignants.py` - Tests automatisés
3. `templates/salaires/confirmer_suppression_enseignant.html` - Interface de confirmation
4. `SUPPRESSION_ENSEIGNANTS_DOCUMENTATION.md` - Cette documentation
5. `utilisateurs/migrations/0009_profil_peut_supprimer_enseignants_definitivement.py` - Migration

### Fichiers Modifiés
1. `utilisateurs/models.py` - Ajout du champ de permission
2. `salaires/views.py` - Mise à jour de la fonction `supprimer_enseignant`

## 🚀 Déploiement

### Étapes sur le Serveur de Production

```bash
# 1. Se connecter au serveur
ssh myschoolgn@www.myschoolgn.space

# 2. Aller dans le projet
cd /home/myschoolgn/GS_hadja_kanfing_dian-

# 3. Mettre à jour le code
git pull origin main

# 4. Activer le virtualenv
source /home/myschoolgn/venv/bin/activate

# 5. Appliquer la migration
python manage.py migrate

# 6. Collecter les statiques (si nécessaire)
python manage.py collectstatic --noinput

# 7. Redémarrer uWSGI
sudo systemctl restart uwsgi

# 8. Activer la permission pour un utilisateur
python fix_suppression_enseignants.py --activer LACINET
```

## 📞 Support

### En Cas de Problème
1. Vérifier les logs : `sudo tail -f /var/log/uwsgi/myschoolgn.log`
2. Tester la permission : `python fix_suppression_enseignants.py --diagnostic USERNAME`
3. Vérifier la migration : `python manage.py showmigrations utilisateurs`

### Messages d'Erreur Courants

| Erreur | Cause | Solution |
|--------|-------|----------|
| "Code de vérification incorrect" | Code erroné | Saisir 625196629 |
| "Vous n'avez pas la permission..." | Permission manquante | Activer avec le script |
| "L'enseignant n'existe pas..." | ID invalide | Vérifier l'existence |

---

## ✅ Checklist de Validation

- [ ] Migration appliquée
- [ ] Permission activée pour au moins un utilisateur
- [ ] Test de suppression définitive réussi
- [ ] Test de soft delete réussi
- [ ] Vérification dans la corbeille
- [ ] Documentation lue et comprise

---

**Date de création** : 7 novembre 2024  
**Statut** : ✅ Implémenté et testé  
**Code de vérification** : **625196629**
