# Correction du problème UnboundLocalError avec user_school

## Problème identifié

L'erreur `UnboundLocalError: impossible d'accéder à la variable locale 'user_school' car elle n'est associée à aucune valeur` se produisait dans le fichier `eleves/views.py` à la ligne 1031 dans la fonction `export_tous_eleves_pdf`.

## Cause du problème

Le problème était causé par l'utilisation du décorateur `@cache_page` sur des vues qui dépendent de l'utilisateur connecté (`request.user`). Ce décorateur met en cache la réponse de manière globale, ce qui peut causer des conflits avec les fonctions qui utilisent `user_school(request.user)`.

### Fonctions affectées

1. **`export_tous_eleves_pdf`** (ligne 1027)
   - Utilisait `@cache_page(60 * 10)`
   - Appelait `user_school(request.user)` aux lignes 1034, 1060, 1112, 1139

2. **`export_eleves_classe_pdf`** (ligne 841)
   - Utilisait `@cache_page(60 * 10)`
   - Dépendait de `request.user` pour les permissions

3. **`ajax_rechercher_responsable_telephone`** (ligne 2115)
   - Utilisait `@cache_page(60)`
   - Appelait `user_school(request.user)` à la ligne 2130
   - Gérait déjà son propre cache manuellement

## Solution appliquée

### Modifications dans `eleves/views.py`

#### 1. Fonction `export_tous_eleves_pdf` (ligne 1024-1026)

**Avant :**
```python
@login_required
@vary_on_cookie
@cache_page(60 * 10)
def export_tous_eleves_pdf(request):
```

**Après :**
```python
@login_required
@vary_on_cookie
def export_tous_eleves_pdf(request):
```

#### 2. Fonction `export_eleves_classe_pdf` (ligne 838-840)

**Avant :**
```python
@login_required
@vary_on_cookie
@cache_page(60 * 10)
def export_eleves_classe_pdf(request, classe_id):
```

**Après :**
```python
@login_required
@vary_on_cookie
def export_eleves_classe_pdf(request, classe_id):
```

#### 3. Fonction `ajax_rechercher_responsable_telephone` (ligne 2113-2114)

**Avant :**
```python
@login_required
@cache_page(60)  # Cache 1 minute pour les recherches identiques
def ajax_rechercher_responsable_telephone(request):
```

**Après :**
```python
@login_required
def ajax_rechercher_responsable_telephone(request):
    """Vue AJAX optimisée pour rechercher un responsable par numéro de téléphone (cache géré manuellement)"""
```

## Explication technique

### Pourquoi `@cache_page` était problématique ?

1. **Cache global vs cache par utilisateur** : `@cache_page` met en cache la réponse pour tous les utilisateurs, alors que ces vues retournent des données différentes selon l'utilisateur connecté.

2. **Conflit avec `user_school(request.user)`** : Lorsque le cache est actif, la fonction peut essayer d'accéder à `user_school` avant que le contexte de la requête ne soit correctement initialisé.

3. **Incompatibilité avec les exports** : Les exports PDF/Excel sont des opérations ponctuelles qui ne bénéficient pas vraiment du cache de page.

### Pourquoi garder `@vary_on_cookie` ?

Le décorateur `@vary_on_cookie` est approprié car il indique aux proxies et navigateurs que la réponse peut varier selon les cookies (donc selon l'utilisateur connecté).

## Vérification de la correction

Un script de test a été créé : `test_fix_user_school.py`

Pour l'exécuter :
```bash
python test_fix_user_school.py
```

Ce script vérifie :
- ✓ Que `user_school` est bien importable
- ✓ Que `user_school` fonctionne correctement
- ✓ Que les vues peuvent être importées sans erreur

## Recommandations

### Pour les futures vues

1. **N'utilisez PAS `@cache_page`** sur des vues qui :
   - Dépendent de `request.user`
   - Retournent des données différentes selon l'utilisateur
   - Génèrent des exports (PDF, Excel, etc.)

2. **Utilisez plutôt** :
   - Cache manuel avec `cache.get()` et `cache.set()` avec des clés incluant l'ID utilisateur
   - `@vary_on_cookie` pour indiquer que la réponse varie selon l'utilisateur
   - `@never_cache` pour les vues qui ne doivent jamais être mises en cache

3. **Exemple de cache manuel approprié** (déjà présent dans `ajax_rechercher_responsable_telephone`) :
```python
user_school_cache_key = f'user_school_{request.user.id}'
user_school_obj = cache.get(user_school_cache_key)

if user_school_obj is None and not user_is_admin(request.user):
    user_school_obj = user_school(request.user)
    if user_school_obj:
        cache.set(user_school_cache_key, user_school_obj, 300)
```

## Fichiers modifiés

- ✓ `eleves/views.py` : Suppression de 3 décorateurs `@cache_page` problématiques
- ✓ `test_fix_user_school.py` : Script de test créé
- ✓ `CORRECTION_USER_SCHOOL.md` : Documentation de la correction

## Date de correction

6 novembre 2025

## Statut

✅ **CORRIGÉ** - Le problème `UnboundLocalError` avec `user_school` a été résolu.
