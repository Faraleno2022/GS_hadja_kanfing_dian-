# Changement Automatique de Matricule lors du Changement de Classe

## 📋 Description

Cette fonctionnalité permet de **mettre à jour automatiquement le matricule d'un élève** lorsqu'il change de classe. Le système détecte le changement et génère un nouveau matricule correspondant au code de la nouvelle classe.

## ✨ Fonctionnalités

### 1. Détection Automatique du Changement
- Le système détecte automatiquement quand un élève change de classe
- Aucune action manuelle n'est requise de la part de l'utilisateur

### 2. Régénération du Matricule
- Le matricule est automatiquement régénéré avec le code de la nouvelle classe
- Format: `[PREFIXE_ECOLE/]CODE_CLASSE-XXX`
- Exemple: `AL-FUR/L11SC-001` → `AL-FUR/L12SC-015`

### 3. Historique Complet
- Un enregistrement d'historique est créé automatiquement
- Contient:
  - Ancienne classe
  - Nouvelle classe
  - Ancien matricule
  - Nouveau matricule
  - Date et heure du changement
  - Utilisateur ayant effectué le changement

### 4. Numérotation Intelligente
- Le nouveau matricule utilise le prochain numéro disponible dans la nouvelle classe
- Évite les doublons automatiquement
- Respecte le préfixe de l'école si configuré

## 🔧 Utilisation

### Depuis l'Interface Web

1. **Accéder à la modification d'un élève**
   - Aller dans "Élèves" → "Liste des élèves"
   - Cliquer sur "Modifier" pour l'élève concerné

2. **Changer la classe**
   - Sélectionner la nouvelle classe dans le menu déroulant
   - Cliquer sur "Enregistrer"

3. **Vérification automatique**
   - Le matricule est automatiquement mis à jour
   - Un message de confirmation s'affiche
   - L'historique est créé

### Exemple Pratique

**Situation initiale:**
- Élève: DIALLO Mamadou
- Classe: 11 SÉRIE SCIENTIFIQUE
- Matricule: `L11SC-005`

**Après changement vers "12 SÉRIE SCIENTIFIQUE":**
- Classe: 12 SÉRIE SCIENTIFIQUE
- Matricule: `L12SC-012` (nouveau numéro dans la nouvelle classe)

**Historique créé:**
```
Action: CHANGEMENT_CLASSE
Description: Changement de classe: 11 SÉRIE SCIENTIFIQUE → 12 SÉRIE SCIENTIFIQUE. 
             Ancien matricule: L11SC-005, Nouveau matricule: L12SC-012
Date: 06/11/2025 09:30
Utilisateur: admin@ecole.com
```

## 🔍 Détails Techniques

### Modèle Eleve (eleves/models.py)

La méthode `save()` a été modifiée pour:

1. **Détecter le changement de classe**
   ```python
   if self.pk:  # Si l'élève existe déjà
       old_instance = Eleve.objects.get(pk=self.pk)
       if old_instance.classe_id != self.classe_id:
           regenerer_matricule = True
   ```

2. **Régénérer le matricule**
   ```python
   if regenerer_matricule:
       # Génération automatique avec le code de la nouvelle classe
       code = _code_classe_from_nom_ou_niveau(self.classe)
       # ... logique de génération
   ```

3. **Créer l'historique**
   ```python
   HistoriqueEleve.objects.create(
       eleve=self,
       action='CHANGEMENT_CLASSE',
       description=f"Changement de classe: {ancienne} → {nouvelle}...",
       utilisateur=self._current_user
   )
   ```

### Vue modifier_eleve (eleves/views.py)

L'utilisateur actuel est passé à l'instance pour l'historique:

```python
eleve = form.save(commit=False)
eleve._current_user = request.user
eleve.save()
```

## 📊 Codes de Classe

Le système utilise les codes suivants pour générer les matricules:

| Niveau | Code |
|--------|------|
| Préscolaire 1 | PN1 |
| Préscolaire 2 | PN2 |
| Préscolaire 3 | PN3 |
| Préscolaire 4 | PN4 |
| 7ème année | A7 |
| 8ème année | A8 |
| 9ème année | A9 |
| 10ème année | A10 |
| 11ème Série Scientifique | L11SC |
| 11ème Série Littéraire | L11SL |
| 12ème Série Scientifique | L12SC |
| 12ème Série Littéraire | L12SL |

## ⚠️ Notes Importantes

1. **Unicité du Matricule**
   - Le système garantit que le nouveau matricule est unique
   - En cas de collision, le numéro est automatiquement incrémenté

2. **Préfixe d'École**
   - Si l'école a un préfixe configuré (ex: "AL-FUR/"), il est conservé
   - Le préfixe est détecté automatiquement depuis les matricules existants

3. **Historique**
   - Tous les changements sont tracés
   - L'historique est accessible depuis la fiche de l'élève

4. **Permissions**
   - Seuls les utilisateurs autorisés peuvent modifier la classe d'un élève
   - Les administrateurs ont accès à tous les élèves
   - Les utilisateurs normaux ne peuvent modifier que les élèves de leur école

## 🧪 Test

Un script de test est disponible: `test_changement_classe.py`

```bash
python test_changement_classe.py
```

Ce script:
- Sélectionne un élève
- Change sa classe
- Vérifie que le matricule a été mis à jour
- Affiche l'historique créé

## 📝 Exemple de Log

```
TEST: Changement automatique de matricule lors du changement de classe
======================================================================

📋 Élève sélectionné: DIALLO Mamadou
   Classe actuelle: 11 SÉRIE SCIENTIFIQUE
   Matricule actuel: L11SC-005

🔄 Changement vers: 12 SÉRIE SCIENTIFIQUE

✅ Changement effectué!
   Ancienne classe: 11 SÉRIE SCIENTIFIQUE
   Nouvelle classe: 12 SÉRIE SCIENTIFIQUE
   Ancien matricule: L11SC-005
   Nouveau matricule: L12SC-012

✅ SUCCESS: Le matricule a été automatiquement mis à jour!

📝 Historique créé:
   Date: 06/11/2025 09:30
   Description: Changement de classe: 11 SÉRIE SCIENTIFIQUE → 12 SÉRIE SCIENTIFIQUE. 
                Ancien matricule: L11SC-005, Nouveau matricule: L12SC-012
```

## 🔗 Fichiers Modifiés

- `eleves/models.py` - Logique de détection et régénération du matricule
- `eleves/views.py` - Passage de l'utilisateur actuel pour l'historique
- `test_changement_classe.py` - Script de test
- `CHANGEMENT_CLASSE_AUTO.md` - Cette documentation

## 🎯 Avantages

1. **Automatisation** - Plus besoin de modifier manuellement le matricule
2. **Traçabilité** - Historique complet des changements
3. **Cohérence** - Les matricules respectent toujours le format de la classe
4. **Sécurité** - Évite les doublons et les erreurs de saisie
5. **Simplicité** - Transparent pour l'utilisateur

---

**Date de création:** 06/11/2025  
**Version:** 1.0  
**Auteur:** Système de Gestion Scolaire
