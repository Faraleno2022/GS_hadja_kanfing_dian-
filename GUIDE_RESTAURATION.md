# 🗑️ Guide de Restauration - Système de Corbeille

## 📋 Vue d'ensemble

Le système de restauration permet de récupérer les élèves supprimés définitivement avec le code de vérification `625196629`. Toutes les suppressions définitives sont automatiquement sauvegardées dans la corbeille pour permettre une restauration ultérieure.

## 🔍 Accès à la Corbeille

### Navigation :
1. **Menu Administration** → **Corbeille** (réservé aux super-administrateurs)
2. **URL directe** : `/administration/corbeille/`

### Permissions requises :
- ✅ **Super-administrateur** (is_superuser + is_staff)
- ❌ **Comptables** : Accès refusé (sécurité)

## 📊 Interface de la Corbeille

### Statistiques affichées :
- **Total suppressions** : Nombre total d'éléments supprimés
- **Suppressions aujourd'hui** : Suppressions du jour
- **Suppressions cette semaine** : Suppressions des 7 derniers jours

### Informations par élément :
- **Nom complet** de l'élève supprimé
- **Matricule original** 
- **Classe** au moment de la suppression
- **Nombre de paiements** supprimés avec l'élève
- **Code de vérification** utilisé (625196629)
- **Utilisateur** qui a effectué la suppression
- **Date et heure** de la suppression
- **Adresse IP** de l'utilisateur

## 🔄 Processus de Restauration

### 1. Sélection de l'élément
- Parcourir la liste des suppressions dans la corbeille
- Identifier l'élève à restaurer par son nom/matricule
- Vérifier que la classe existe encore

### 2. Lancement de la restauration
```javascript
// Clic sur le bouton "Restaurer"
restaurerElement(logId)
```

### 3. Confirmation
- **Popup de confirmation** : "Êtes-vous sûr de vouloir restaurer cet élément ?"
- **Information** : Un nouvel élève sera créé avec un matricule modifié

### 4. Traitement automatique
```python
# Processus côté serveur
1. Vérification des permissions (super-admin uniquement)
2. Récupération des données de suppression
3. Vérification que l'élément n'a pas déjà été restauré
4. Validation de l'existence de la classe
5. Création du nouvel élève avec matricule modifié
6. Enregistrement de l'action de restauration
```

## ⚙️ Détails Techniques

### Données sauvegardées lors de la suppression :
```json
{
    "eleve_id": 123,
    "matricule": "ABC123",
    "nom_complet": "Jean DUPONT",
    "classe": "6ème A - École Primaire",
    "paiements_supprimes": [
        "REC20250001 - 50000 GNF",
        "REC20250002 - 75000 GNF"
    ],
    "code_verification": "625196629",
    "user_agent": "Mozilla/5.0..."
}
```

### Restauration - Nouveau matricule :
- **Format** : `{MATRICULE_ORIGINAL}_RESTAURE`
- **Exemple** : `ABC123` → `ABC123_RESTAURE`
- **Raison** : Éviter les conflits avec d'éventuels nouveaux élèves

### Limitations de la restauration :
- ❌ **Paiements perdus** : Les paiements ne sont PAS restaurés
- ❌ **Classe supprimée** : Impossible de restaurer si la classe n'existe plus
- ❌ **Déjà restauré** : Un élément ne peut être restauré qu'une seule fois
- ✅ **Données élève** : Nom, prénom, matricule modifié, statut ACTIF

## 🛡️ Sécurité et Audit

### Traçabilité complète :
- **Log de suppression** : Action `SUPPRESSION_DEFINITIVE`
- **Log de restauration** : Action `RESTORE`
- **Détails enregistrés** : IDs originaux et nouveaux, utilisateur, IP, timestamp

### Vérifications de sécurité :
```python
# Permissions
if not is_super_admin(user):
    return HttpResponseForbidden()

# Déjà restauré ?
if SystemLog.objects.filter(action='RESTORE', details__original_log_id=log_id).exists():
    return JsonResponse({'error': 'Déjà restauré'})

# Classe existe ?
if not classe:
    return JsonResponse({'error': 'Classe inexistante'})
```

## 📱 Interface Utilisateur

### États du bouton de restauration :
- 🟢 **"Restaurer"** : Prêt à restaurer
- 🔄 **"Restauration..."** : En cours (spinner)
- ✅ **"Restauré"** : Succès (bouton vert, désactivé)

### Messages d'alerte :
- ✅ **Succès** : "Élève restauré avec succès. Nouveau matricule: ABC123_RESTAURE"
- ❌ **Erreur** : "Impossible de restaurer: la classe n'existe plus"
- ⚠️ **Déjà restauré** : "Cet élément a déjà été restauré"

### Détails techniques (collapsible) :
- **JSON complet** des données de suppression
- **Métadonnées** de la suppression originale
- **Informations de debug** pour les administrateurs

## 🔧 Maintenance et Nettoyage

### Nettoyage automatique (recommandé) :
```python
# Supprimer les logs de plus de 1 an
old_logs = SystemLog.objects.filter(
    timestamp__lt=timezone.now() - timedelta(days=365)
)
old_logs.delete()
```

### Commandes utiles :
```bash
# Voir les suppressions récentes
python manage.py shell
>>> from administration.models import SystemLog
>>> SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE').count()

# Voir les restaurations
>>> SystemLog.objects.filter(action='RESTORE').count()
```

## 🚨 Cas d'Usage Typiques

### 1. Suppression accidentelle
- Élève supprimé par erreur avec le code 625196629
- Restauration immédiate depuis la corbeille
- Nouveau matricule généré automatiquement

### 2. Changement d'école
- Élève transféré vers une autre école
- Suppression dans l'ancienne école
- Restauration possible si retour nécessaire

### 3. Erreur de saisie
- Mauvaises informations saisies
- Suppression et recréation propre
- Historique conservé dans la corbeille

## ⚠️ Points d'Attention

### Avant restauration :
1. **Vérifier la classe** : S'assurer qu'elle existe encore
2. **Nouveau matricule** : Informer l'utilisateur du changement
3. **Paiements perdus** : Les recréer manuellement si nécessaire
4. **Responsables** : Vérifier les liens avec les parents

### Après restauration :
1. **Mettre à jour** les informations si nécessaire
2. **Recréer les paiements** perdus
3. **Vérifier les liens** avec les responsables
4. **Informer l'équipe** de la restauration

## 📞 Support

En cas de problème avec la restauration :
1. Vérifier les logs dans `/administration/logs/`
2. Consulter la console du navigateur (F12)
3. Vérifier les permissions utilisateur
4. Contacter l'administrateur système

---

**Note importante** : La restauration crée un NOUVEL élève avec un matricule modifié. Ce n'est pas une restauration exacte, mais une recréation basée sur les données sauvegardées.
