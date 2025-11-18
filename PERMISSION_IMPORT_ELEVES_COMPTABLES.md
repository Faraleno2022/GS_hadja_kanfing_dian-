# Permission d'Importation d'Élèves pour les Comptables

## 📋 Résumé des modifications

Une nouvelle permission a été ajoutée au système pour permettre aux comptables d'importer des élèves depuis des fichiers Excel/CSV.

## 🔧 Modifications effectuées

### 1. **Modèle Profil** (`utilisateurs/models.py`)
- Ajout du champ `peut_importer_eleves` (BooleanField, défaut: False)
- Ligne 38 : `peut_importer_eleves = models.BooleanField(default=False, verbose_name="Peut importer des élèves")`

### 2. **Vue d'importation d'élèves** (`eleves/views_import.py`)
- Modification de la vérification des permissions (lignes 33-42)
- Ancien système : Vérifiait uniquement `is_staff` et groupes
- **Nouveau système** : Accepte aussi les utilisateurs avec `profil.peut_importer_eleves = True`

```python
peut_importer = (
    request.user.is_staff or 
    request.user.is_superuser or
    request.user.groups.filter(name__in=['Administrateurs', 'Directeurs']).exists() or
    (hasattr(request.user, 'profil') and request.user.profil.peut_importer_eleves)
)
```

## 🚀 Déploiement

### Étape 1 : Créer la migration
```bash
python manage.py makemigrations utilisateurs
```

### Étape 2 : Appliquer la migration
```bash
python manage.py migrate utilisateurs
```

### Étape 3 : Activer la permission pour les comptables

#### Option A : Activer pour TOUS les comptables
```bash
python activer_import_eleves_comptables.py
```

#### Option B : Activer pour un comptable spécifique
```bash
python activer_import_eleves_comptables.py username_comptable
```

## ✅ Vérification

Après le déploiement, les comptables avec la permission pourront :
- Accéder à la page `/eleves/importer/`
- Importer des élèves depuis des fichiers Excel/CSV
- Générer des templates d'importation

## 📊 Qui peut importer des élèves ?

| Rôle | Accès | Condition |
|------|-------|-----------|
| **Administrateur** | ✅ Oui | Automatique (is_superuser) |
| **Directeur** | ✅ Oui | Automatique (is_staff) |
| **Comptable** | ✅ Oui | Si `peut_importer_eleves = True` |
| **Secrétaire** | ❌ Non | Pas de permission |
| **Enseignant** | ❌ Non | Pas de permission |
| **Surveillant** | ❌ Non | Pas de permission |

## 🔐 Sécurité

- La permission est granulaire et peut être activée/désactivée par utilisateur
- Les comptables ne peuvent importer que pour leur école (filtrage automatique)
- Toutes les actions sont tracées dans le journal d'activité
- Validation complète des données avant importation

## 📝 Notes

- La permission par défaut est `False` pour les nouveaux comptables
- Les administrateurs peuvent modifier cette permission dans l'interface d'administration Django
- Le script `activer_import_eleves_comptables.py` peut être exécuté plusieurs fois en toute sécurité

## 🔗 Fichiers modifiés

- ✏️ `utilisateurs/models.py` - Ajout du champ permission
- ✏️ `eleves/views_import.py` - Modification de la vérification des permissions
- ✨ `activer_import_eleves_comptables.py` - Script d'activation (nouveau)
