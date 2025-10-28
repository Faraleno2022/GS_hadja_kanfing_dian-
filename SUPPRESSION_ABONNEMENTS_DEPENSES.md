# Fonctionnalité de Suppression Définitive - Abonnements et Dépenses

## Vue d'ensemble

Cette fonctionnalité ajoute la possibilité de supprimer définitivement les abonnements (bus et cantine) et les dépenses, avec un système de permissions granulaires pour contrôler l'accès.

## Modifications apportées

### 1. Modèle de permissions (`utilisateurs/models.py`)

Ajout d'un nouveau champ de permission dans le modèle `Profil` :
- `peut_supprimer_abonnements` : Permission pour supprimer les abonnements (bus et cantine)

### 2. Décorateurs de permissions (`utilisateurs/permissions.py`)

Ajout d'un nouveau décorateur :
- `@can_delete_subscriptions` : Vérifie si l'utilisateur a la permission de supprimer des abonnements

Mise à jour des fonctions utilitaires :
- `get_user_permissions()` : Inclut maintenant `can_delete_subscriptions`
- `check_comptable_restrictions()` : Inclut maintenant `cannot_delete_subscriptions`

### 3. Vues de suppression

#### Abonnements Bus (`bus/views.py`)
- **Nouvelle vue** : `supprimer_abonnement_bus(request, abo_id)`
  - Décorateurs : `@login_required`, `@can_delete_subscriptions`, `@require_school_object`
  - Suppression définitive avec confirmation
  - Message de succès après suppression

#### Abonnements Cantine (`bus/views_cantine.py`)
- **Vue mise à jour** : `supprimer_abonnement_cantine(request, pk)`
  - Ajout du décorateur `@can_delete_subscriptions`
  - Message mis à jour pour indiquer la suppression définitive

#### Dépenses (`depenses/views.py`)
- **Nouvelle vue** : `supprimer_depense(request, depense_id)`
  - Décorateurs : `@login_required`, `@can_delete_expenses`, `@require_school_object`
  - Suppression définitive avec confirmation
  - Supprime également les pièces justificatives et l'historique associés

### 4. URLs

#### Bus (`bus/urls.py`)
- Ajout : `path('<int:abo_id>/supprimer/', views.supprimer_abonnement_bus, name='supprimer_abonnement_bus')`

#### Dépenses (`depenses/urls.py`)
- Ajout : `path('<int:depense_id>/supprimer/', views.supprimer_depense, name='supprimer_depense')`

### 5. Templates de confirmation

#### Bus (`templates/bus/confirmer_suppression.html`)
- Nouveau template pour confirmer la suppression d'un abonnement bus
- Affiche les détails de l'abonnement
- Avertissement sur le caractère irréversible

#### Cantine (`templates/bus/cantine/confirmer_suppression.html`)
- Template mis à jour pour souligner la suppression définitive
- Texte du bouton modifié : "Confirmer la Suppression Définitive"

#### Dépenses (`templates/depenses/confirm_delete_depense.html`)
- Nouveau template pour confirmer la suppression d'une dépense
- Affiche les détails complets de la dépense
- Alerte sur la suppression des pièces justificatives et de l'historique
- Avertissement sur le caractère irréversible

## Configuration des permissions

### Pour les Super-utilisateurs et Administrateurs
- Ont automatiquement toutes les permissions, y compris `can_delete_subscriptions` et `can_delete_expenses`

### Pour les autres rôles
Les permissions doivent être configurées individuellement dans le profil utilisateur :
1. Accéder à l'administration Django
2. Modifier le profil de l'utilisateur
3. Cocher les cases :
   - `peut_supprimer_abonnements` : Pour supprimer les abonnements
   - `peut_supprimer_depenses` : Pour supprimer les dépenses

## Migration de base de données

Une migration a été créée automatiquement :
```
utilisateurs/migrations/0008_profil_peut_supprimer_abonnements.py
```

Pour appliquer la migration :
```bash
python manage.py migrate utilisateurs
```

## Sécurité

### Contrôles d'accès
1. **Authentification** : L'utilisateur doit être connecté (`@login_required`)
2. **Permission** : L'utilisateur doit avoir la permission appropriée
3. **École** : Les utilisateurs non-admin ne peuvent supprimer que les éléments de leur école (`@require_school_object`)
4. **Confirmation** : Une page de confirmation est affichée avant toute suppression

### Caractère irréversible
- Toutes les pages de confirmation affichent un avertissement clair
- Les suppressions sont définitives et ne peuvent pas être annulées
- Pour les dépenses, les pièces justificatives et l'historique sont également supprimés

## Utilisation

### Supprimer un abonnement bus
1. Accéder à la liste des abonnements bus
2. Cliquer sur l'abonnement à supprimer
3. Cliquer sur le bouton "Supprimer"
4. Confirmer la suppression sur la page de confirmation

### Supprimer un abonnement cantine
1. Accéder à la liste des abonnements cantine
2. Cliquer sur l'abonnement à supprimer
3. Cliquer sur le bouton "Supprimer"
4. Confirmer la suppression sur la page de confirmation

### Supprimer une dépense
1. Accéder au détail d'une dépense
2. Cliquer sur le bouton "Supprimer"
3. Vérifier les informations affichées (pièces justificatives, historique)
4. Confirmer la suppression sur la page de confirmation

## Messages utilisateur

### Succès
- Abonnement bus : "Abonnement bus supprimé définitivement pour [nom de l'élève]"
- Abonnement cantine : "Abonnement cantine supprimé définitivement pour [nom de l'élève]"
- Dépense : "Dépense '[numéro] - [libellé]' supprimée définitivement."

### Erreur (permission refusée)
- "Vous n'êtes pas autorisé à supprimer des abonnements."
- "Vous n'êtes pas autorisé à supprimer des dépenses."

## Notes importantes

1. **Permissions distinctes** : Les permissions pour supprimer les abonnements et les dépenses sont séparées, permettant un contrôle granulaire
2. **Cascade** : La suppression d'un abonnement ou d'une dépense supprime également tous les objets liés (pièces justificatives, historique)
3. **Audit** : Il est recommandé de tenir un journal des suppressions pour des raisons de traçabilité
4. **Sauvegarde** : Assurez-vous d'avoir des sauvegardes régulières de la base de données avant d'effectuer des suppressions

## Fichiers modifiés

### Modèles
- `utilisateurs/models.py` - Ajout du champ `peut_supprimer_abonnements`

### Permissions
- `utilisateurs/permissions.py` - Ajout du décorateur `can_delete_subscriptions` et mise à jour des fonctions utilitaires

### Vues
- `bus/views.py` - Ajout de `supprimer_abonnement_bus()`
- `bus/views_cantine.py` - Mise à jour de `supprimer_abonnement_cantine()`
- `depenses/views.py` - Ajout de `supprimer_depense()`

### URLs
- `bus/urls.py` - Ajout de l'URL pour la suppression des abonnements bus
- `depenses/urls.py` - Ajout de l'URL pour la suppression des dépenses

### Templates
- `templates/bus/confirmer_suppression.html` - Nouveau
- `templates/bus/cantine/confirmer_suppression.html` - Mis à jour
- `templates/depenses/confirm_delete_depense.html` - Nouveau

### Migrations
- `utilisateurs/migrations/0008_profil_peut_supprimer_abonnements.py` - Nouvelle migration
