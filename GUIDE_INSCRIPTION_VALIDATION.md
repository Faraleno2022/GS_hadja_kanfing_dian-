# Guide du Système d'Inscription et Validation des Comptes

## Vue d'ensemble

Le système d'inscription et validation des comptes permet aux nouveaux utilisateurs de créer un compte avec leur école, mais nécessite une validation administrative avant qu'ils puissent se connecter et accéder au système.

## Fonctionnalités Implémentées

### 1. Inscription Utilisateur avec Définition de Mot de Passe ✅

**Fichiers modifiés :**
- `utilisateurs/forms.py` : Formulaire `SignupInlineForm` 
- `eleves/views.py` : Vue `creer_ecole`

**Fonctionnement :**
- L'utilisateur peut définir son propre mot de passe lors de l'inscription
- Le compte est créé avec `is_active=False` (inactif)
- Un profil utilisateur est automatiquement créé avec `is_validated=False`

### 2. Champ de Validation au Modèle Profil ✅

**Fichiers modifiés :**
- `utilisateurs/models.py` : Ajout du champ `is_validated`
- Migration créée et appliquée

**Structure :**
```python
class Profil(models.Model):
    # ... autres champs
    is_validated = models.BooleanField(default=False, verbose_name="Compte validé par l'administrateur")
```

### 3. Création Automatique d'École et Classes ✅

**Fichiers créés/modifiés :**
- `eleves/utils.py` : Fonctions utilitaires
- `eleves/views.py` : Vue `creer_ecole` modifiée

**Fonctionnalités :**
- Création automatique de 18 classes par défaut (Garderie à 12ème)
- Génération des grilles tarifaires associées
- École créée avec statut `EN_ATTENTE`

### 4. Interface d'Administration pour Validation ✅

**Fichiers créés :**
- `utilisateurs/views.py` : Vues `comptes_en_attente_view`, `valider_compte_view`, `rejeter_compte_view`
- `templates/utilisateurs/comptes_en_attente.html`
- `templates/utilisateurs/valider_compte.html`
- `utilisateurs/urls.py` : URLs ajoutées

**URLs disponibles :**
- `/utilisateurs/comptes-en-attente/` : Liste des comptes en attente
- `/utilisateurs/valider-compte/<id>/` : Validation d'un compte
- `/utilisateurs/rejeter-compte/<id>/` : Rejet d'un compte

### 5. Sécurité et Isolation des Données ✅

**Fichiers créés :**
- `utilisateurs/middleware.py` : Middleware d'isolation par école
- `utilisateurs/security_views.py` : Vérification lors de la connexion

**Protections :**
- Vérification du statut `is_validated` lors de la connexion
- Isolation complète des données par école
- Middleware de sécurité pour toutes les vues

## Flux d'Utilisation

### Pour un Nouvel Utilisateur

1. **Inscription :**
   - Accéder à `/eleves/creer-ecole/`
   - Remplir le formulaire avec les informations de l'école
   - Définir nom d'utilisateur et mot de passe
   - Soumettre le formulaire

2. **Après inscription :**
   - Compte créé mais inactif (`is_active=False`)
   - Profil créé avec `is_validated=False`
   - École créée avec statut `EN_ATTENTE`
   - Classes et grilles tarifaires générées automatiquement
   - Message affiché : "Compte créé. Un administrateur doit valider votre demande avant connexion."

3. **Tentative de connexion :**
   - La connexion est refusée avec le message : "Votre compte est en attente de validation par un administrateur."

### Pour un Administrateur

1. **Voir les comptes en attente :**
   - Accéder à `/utilisateurs/comptes-en-attente/`
   - Voir la liste des comptes non validés
   - Rechercher par nom, email, etc.

2. **Valider un compte :**
   - Cliquer sur "Valider" pour un compte
   - Remplir les informations complémentaires (téléphone, adresse)
   - Confirmer la validation
   - L'utilisateur peut maintenant se connecter

3. **Rejeter un compte :**
   - Cliquer sur "Rejeter" pour un compte
   - Optionnel : Ajouter une raison du rejet
   - Le compte et l'école associée sont supprimés
   - Un email de notification est envoyé si possible

## Sécurité

### Protection lors de la Connexion
```python
# Dans utilisateurs/security_views.py
if profil and not profil.is_validated and not user.is_superuser:
    messages.error(request, 'Votre compte est en attente de validation...')
    return render(request, 'utilisateurs/login.html')
```

### Isolation des Données
- Middleware `EcoleIsolationMiddleware` vérifie l'accès à chaque vue
- Fonctions utilitaires `filter_by_user_school()` et `check_school_access()`
- Mixin `SchoolAccessMixin` pour les vues basées sur les classes

### Permissions
- Validation des comptes : Superusers et utilisateurs avec `role='ADMIN'`
- Accès aux données : Limité à l'école de l'utilisateur
- Vues système : Ignorées par le middleware de sécurité

## Classes et Grilles Créées Automatiquement

### Classes par Défaut (18 au total)
- **Garderie :** 1 classe
- **Primaire :** 6 classes (1ère à 6ème année)
- **Collège :** 4 classes (7ème à 10ème année)
- **Lycée :** 7 classes (11ème et 12ème avec différentes séries)

### Tarifs par Défaut
- **Frais d'inscription :** 30 000 GNF
- **Frais de réinscription :** 20 000 GNF
- **Scolarité annuelle :** Variable selon le niveau (300 000 à 800 000 GNF)

## Messages et Notifications

### Messages Utilisateur
- **Inscription réussie :** "Compte créé. Un administrateur doit valider votre demande avant connexion."
- **Connexion refusée :** "Votre compte est en attente de validation par un administrateur."
- **Validation réussie :** "Compte validé avec succès. L'utilisateur peut maintenant se connecter."

### Emails Automatiques
- **Validation :** Email de bienvenue avec informations de connexion
- **Rejet :** Email expliquant le rejet avec possibilité de nouvelle demande

## Maintenance et Administration

### Commandes Utiles
```bash
# Voir les comptes en attente
python manage.py shell -c "from utilisateurs.models import Profil; print(Profil.objects.filter(is_validated=False).count())"

# Voir les écoles en attente
python manage.py shell -c "from eleves.models import Ecole; print(Ecole.objects.filter(etat='EN_ATTENTE').count())"
```

### Logs et Monitoring
- Connexions refusées loggées dans `utilisateurs/security_views.py`
- Actions de validation/rejet enregistrées
- Middleware de sécurité surveille les accès non autorisés

## Dépannage

### Problèmes Courants

1. **Utilisateur ne peut pas se connecter :**
   - Vérifier `user.is_active = True`
   - Vérifier `profil.is_validated = True`
   - Vérifier que l'école est assignée au profil

2. **Erreur d'accès aux données :**
   - Vérifier que l'utilisateur a un profil
   - Vérifier que le profil a une école assignée
   - Vérifier les permissions du rôle

3. **Classes non créées :**
   - Vérifier les logs lors de la création d'école
   - Relancer manuellement : `creer_classes_et_grilles_par_defaut(ecole)`

## Conclusion

Le système d'inscription et validation est maintenant complet et opérationnel. Il assure :

- ✅ Inscription sécurisée avec définition de mot de passe
- ✅ Validation administrative obligatoire
- ✅ Création automatique des structures scolaires
- ✅ Isolation complète des données par école
- ✅ Interface d'administration intuitive
- ✅ Sécurité renforcée à tous les niveaux

Les utilisateurs peuvent s'inscrire en toute autonomie, mais ne peuvent accéder au système qu'après validation par un administrateur, garantissant ainsi la sécurité et la qualité des données.
