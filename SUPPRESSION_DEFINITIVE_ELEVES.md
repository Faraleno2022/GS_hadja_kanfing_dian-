# Suppression Définitive des Élèves

## Vue d'ensemble

Cette fonctionnalité permet aux utilisateurs autorisés de supprimer définitivement un élève avec tous ses éléments associés (paiements, abonnements bus et cantine) de la base de données.

## Nouvelle Permission

### Champ ajouté au modèle `Profil`

```python
peut_supprimer_eleves_definitivement = models.BooleanField(
    default=False, 
    verbose_name="Peut supprimer les élèves définitivement"
)
```

### Qui peut supprimer définitivement ?

1. **Administrateurs** (superuser/staff) : Permission automatique
2. **Utilisateurs avec permission spécifique** : Les utilisateurs dont le profil a `peut_supprimer_eleves_definitivement = True`

## Fonctionnement

### 1. Vérification de Permission

Lorsqu'un utilisateur tente de supprimer un élève :

- **Avec permission** : Option de suppression définitive disponible (cochée par défaut)
- **Sans permission** : Suppression douce uniquement (élève marqué comme "EXCLU")

### 2. Éléments Supprimés

Lors d'une suppression définitive, les éléments suivants sont supprimés :

- ✅ **L'élève** lui-même
- ✅ **Tous ses paiements** (historique complet)
- ✅ **Tous ses abonnements bus** (actifs et expirés)
- ✅ **Tous ses abonnements cantine** (actifs et expirés)

### 3. Traçabilité

Avant la suppression, toutes les informations sont sauvegardées dans la corbeille système (`SystemLog`) :

```python
{
    'eleve_id': 123,
    'matricule': 'PN3-001',
    'nom_complet': 'Jean Dupont',
    'classe': 'Primaire 3ème',
    'paiements_supprimes': ['REC-001 - 500000 GNF', ...],
    'abonnements_bus_supprimes': ['Mensuel - 50000 GNF', ...],
    'abonnements_cantine_supprimes': ['Mensuel - 30000 GNF', ...],
    'verification_code_used': True,
    'user_agent': '...'
}
```

## Interface Utilisateur

### Page de Confirmation

L'interface affiche :

1. **Informations de l'élève** : Nom, matricule, classe, école, statut
2. **Éléments associés** :
   - Nombre de paiements
   - Nombre d'abonnements bus
   - Nombre d'abonnements cantine
3. **Avertissements** : Liste des conséquences de la suppression
4. **Code de vérification** : Champ sécurisé (9 chiffres)
5. **Option de suppression** :
   - Checkbox "Suppression définitive" (si autorisé)
   - Message d'information (si non autorisé)

### Messages de Confirmation

#### Avec permission
```
☑️ Suppression définitive (supprime l'élève et tous ses éléments associés)
ℹ️ Si décoché, l'élève sera marqué comme "EXCLU" (soft delete) et ses données seront conservées.
```

#### Sans permission
```
⚠️ Suppression douce (Soft Delete)
L'élève sera marqué comme "EXCLU" et ses données seront conservées.
Vous n'avez pas la permission de supprimer définitivement un élève. Contactez un administrateur si nécessaire.
```

## Sécurité

### Code de Vérification

- **Code requis** : `625196629` (9 chiffres)
- **Validation côté serveur** : Le code n'est jamais exposé au client
- **Vérification stricte** : Échec = annulation de la suppression

### Protection contre les erreurs

1. **Vérification de permission** : Avant toute suppression définitive
2. **Transaction atomique** : Tout ou rien (rollback en cas d'erreur)
3. **Logs détaillés** : Traçabilité complète dans `SystemLog`
4. **Confirmation double** : Code + confirmation JavaScript

## Attribution de la Permission

### Via l'interface d'administration Django

1. Accéder à **Admin** > **Utilisateurs** > **Profils**
2. Sélectionner le profil de l'utilisateur
3. Cocher **"Peut supprimer les élèves définitivement"**
4. Enregistrer

### Via le code (script)

```python
from utilisateurs.models import Profil

# Attribuer la permission à un utilisateur
profil = Profil.objects.get(user__username='nom_utilisateur')
profil.peut_supprimer_eleves_definitivement = True
profil.save()
```

## Migration

### Appliquer la migration

```bash
python manage.py migrate utilisateurs
```

### Migration créée

```
utilisateurs/migrations/0007_profil_peut_supprimer_eleves_definitivement.py
+ Add field peut_supprimer_eleves_definitivement to profil
```

## Cas d'Usage

### Scénario 1 : Administrateur supprime un élève avec données

**Contexte** : Élève avec 5 paiements, 2 abonnements bus, 1 abonnement cantine

**Action** :
1. Administrateur accède à la page de suppression
2. Voit l'option "Suppression définitive" cochée
3. Saisit le code de vérification
4. Confirme

**Résultat** :
- Élève supprimé
- 5 paiements supprimés
- 2 abonnements bus supprimés
- 1 abonnement cantine supprimé
- Log créé dans la corbeille avec tous les détails

### Scénario 2 : Comptable sans permission

**Contexte** : Comptable tente de supprimer un élève

**Action** :
1. Comptable accède à la page de suppression
2. Voit un message indiquant qu'il n'a pas la permission
3. Saisit le code de vérification
4. Confirme

**Résultat** :
- Élève marqué comme "EXCLU" (soft delete)
- Paiements et abonnements conservés
- Historique créé

### Scénario 3 : Utilisateur autorisé choisit soft delete

**Contexte** : Utilisateur avec permission décoche "Suppression définitive"

**Action** :
1. Utilisateur accède à la page de suppression
2. Décoche "Suppression définitive"
3. Saisit le code de vérification
4. Confirme

**Résultat** :
- Élève marqué comme "EXCLU" (soft delete)
- Données conservées

## Recommandations

### ✅ Bonnes Pratiques

1. **Limiter les permissions** : N'attribuer qu'aux utilisateurs de confiance
2. **Former les utilisateurs** : Expliquer l'irréversibilité de l'action
3. **Vérifier avant suppression** : S'assurer que c'est vraiment nécessaire
4. **Consulter la corbeille** : Vérifier régulièrement les logs de suppression

### ⚠️ Avertissements

1. **Action irréversible** : Aucun moyen de récupérer les données supprimées
2. **Impact sur les rapports** : Les statistiques historiques seront affectées
3. **Perte de traçabilité** : Seuls les logs dans la corbeille restent
4. **Vérifier les dépendances** : S'assurer qu'aucun autre système ne dépend de ces données

## Support et Dépannage

### Problème : L'option de suppression définitive n'apparaît pas

**Solution** :
1. Vérifier que la migration a été appliquée : `python manage.py showmigrations utilisateurs`
2. Vérifier que l'utilisateur a la permission dans son profil
3. Vérifier que l'utilisateur est bien connecté

### Problème : Erreur lors de la suppression

**Solution** :
1. Vérifier les logs d'erreur Django
2. Vérifier que tous les modèles liés sont correctement configurés
3. Vérifier les permissions de base de données

### Problème : Code de vérification refusé

**Solution** :
1. S'assurer de saisir exactement `625196629`
2. Vérifier qu'il n'y a pas d'espaces
3. Réessayer avec un copier-coller si nécessaire

## Changelog

### Version 1.0 (28 octobre 2025)

- ✨ Ajout de la permission `peut_supprimer_eleves_definitivement`
- ✨ Suppression des abonnements bus et cantine
- ✨ Interface utilisateur améliorée avec compteurs
- ✨ Logs détaillés dans la corbeille système
- 🔒 Vérification stricte des permissions
- 📝 Documentation complète

## Fichiers Modifiés

1. **utilisateurs/models.py** : Ajout du champ de permission
2. **utilisateurs/migrations/0007_*.py** : Migration de la base de données
3. **eleves/views.py** : Logique de suppression mise à jour
4. **templates/eleves/confirmer_suppression.html** : Interface utilisateur
5. **SUPPRESSION_DEFINITIVE_ELEVES.md** : Cette documentation
