# Correction de l'affichage du nom de l'école sur les cartes scolaires

## Date : 11 novembre 2024

## Problème résolu
Le nom de l'école était tronqué (coupé) sur les cartes scolaires. Les limites étaient :
- Carte individuelle : 30 caractères + "..."
- Carte PVC haute qualité : 35 caractères
- Cartes en masse : 22 caractères

## Solution implémentée
Adaptation dynamique de la taille de police selon la longueur du nom de l'école, permettant l'affichage complet sans troncature.

### Modifications apportées dans `eleves/carte_scolaire_generator.py`

#### 1. Carte individuelle (lignes 144-157)
- **Avant** : Troncature à 30 caractères
- **Après** : 
  - Police de 11pt pour noms ≤ 25 caractères
  - Police de 9pt pour noms entre 26-35 caractères
  - Police de 8pt pour noms > 35 caractères

#### 2. Carte PVC haute qualité (lignes 502-514)
- **Avant** : Troncature à 35 caractères
- **Après** :
  - Police de 10pt pour noms ≤ 25 caractères
  - Police de 8pt pour noms entre 26-35 caractères
  - Police de 7pt pour noms > 35 caractères

#### 3. Cartes en masse/classe (lignes 697-725)
- **Avant** : Troncature à 22 caractères
- **Après** :
  - Police de 5pt pour noms ≤ 22 caractères
  - Police de 4.5pt pour noms entre 23-30 caractères
  - Police de 4pt pour noms > 30 caractères
  - **NOUVEAUTÉ** : Division sur deux lignes pour noms > 40 caractères

## Avantages de la solution
1. ✅ **Nom complet visible** : Plus de troncature du nom de l'école
2. ✅ **Adaptation automatique** : La taille s'ajuste selon la longueur
3. ✅ **Lisibilité préservée** : Les polices restent lisibles même réduites
4. ✅ **Compatibilité PVC** : Optimisé pour l'impression sur cartes PVC
5. ✅ **Support noms très longs** : Division intelligente sur deux lignes

## Exemples de rendu

### Nom court (≤22 caractères)
```
ÉCOLE PRIMAIRE MAMADOU
→ Police normale (5-11pt selon le type)
```

### Nom moyen (23-35 caractères)
```
GROUPE SCOLAIRE HADJA KANFING DIAN
→ Police moyenne (4.5-9pt selon le type)
```

### Nom long (>35 caractères)
```
COMPLEXE SCOLAIRE INTERNATIONAL DE GUINÉE
→ Police réduite (4-8pt selon le type)
```

### Nom très long (>40 caractères) - Cartes en masse uniquement
```
INSTITUT SUPÉRIEUR DES SCIENCES ET TECHNOLOGIES APPLIQUÉES
→ Division sur deux lignes :
  Ligne 1 : INSTITUT SUPÉRIEUR DES SCIENCES
  Ligne 2 : ET TECHNOLOGIES APPLIQUÉES
```

## URLs concernées
- `/eleves/{id}/carte-scolaire-pdf/` - Carte individuelle
- `/eleves/{id}/carte-scolaire-pdf/?format=pvc` - Carte PVC haute qualité
- `/eleves/classe/{id}/cartes-scolaires-pdf/` - Cartes en masse

## Tests recommandés
1. Tester avec un nom d'école court (< 20 caractères)
2. Tester avec un nom moyen (25-35 caractères)
3. Tester avec un nom long (> 40 caractères)
4. Vérifier la lisibilité sur impression réelle
5. Valider sur cartes PVC physiques

## Impact
- Aucun impact sur les autres fonctionnalités
- Amélioration de la qualité visuelle des cartes
- Meilleure représentation de l'identité de l'école
- Conformité aux standards professionnels

## Fichiers modifiés
- `eleves/carte_scolaire_generator.py` : 3 sections modifiées

## Note importante
Cette modification s'ajoute aux améliorations précédentes :
- Filigrane renforcé (15% d'opacité)
- Format PVC CR80 certifié
- Support des photos manquantes
- Système de suppression avec permissions

## Statut : ✅ COMPLÉTÉ
