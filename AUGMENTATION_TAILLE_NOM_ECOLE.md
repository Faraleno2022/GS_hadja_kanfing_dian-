# Augmentation de la taille du nom de l'école sur les cartes scolaires

## Date : 11 novembre 2024

## Modification effectuée
Suite à la demande d'augmenter la visibilité du nom de l'école, toutes les tailles de police ont été augmentées de 2 à 3 points.

## Changements apportés

### 1. Tailles de police augmentées

#### Carte individuelle
| Longueur du nom | Ancienne taille | NOUVELLE TAILLE | Gain |
|-----------------|-----------------|-----------------|------|
| ≤25 caractères  | 11pt           | **14pt**        | +3pt |
| 26-35 caractères| 9pt            | **12pt**        | +3pt |
| >35 caractères  | 8pt            | **10pt**        | +2pt |

#### Carte PVC haute qualité
| Longueur du nom | Ancienne taille | NOUVELLE TAILLE | Gain |
|-----------------|-----------------|-----------------|------|
| ≤25 caractères  | 10pt           | **13pt**        | +3pt |
| 26-35 caractères| 8pt            | **11pt**        | +3pt |
| >35 caractères  | 7pt            | **9pt**         | +2pt |

#### Cartes en masse (8 par page)
| Longueur du nom | Ancienne taille | NOUVELLE TAILLE | Gain |
|-----------------|-----------------|-----------------|------|
| ≤22 caractères  | 5pt            | **8pt**         | +3pt |
| 23-30 caractères| 4.5pt          | **7pt**         | +2.5pt |
| >30 caractères  | 4pt            | **6pt**         | +2pt |

### 2. Améliorations structurelles

- **En-tête agrandi** : 14mm → **16mm** (+2mm) pour plus d'espace
- **Logo agrandi** : 10mm → **12mm** (+2mm) pour meilleure visibilité
- **Position ajustée** : Logo repositionné à height - 14mm
- **Informations** : Position ajustée pour le nouvel en-tête

## Exemple concret

Pour votre école **"GROUPE SCOLAIRE HADJA KANFING DIAN"** (34 caractères) :

- **Carte individuelle** : Police de **12pt** (avant : 9pt)
- **Carte PVC** : Police de **11pt** (avant : 8pt)  
- **Cartes en masse** : Police de **7pt** (avant : 4.5pt)

## Avantages

1. ✅ **Meilleure lisibilité** : Le nom est maintenant bien plus visible
2. ✅ **Présence renforcée** : L'identité de l'école est mise en avant
3. ✅ **Professionnalisme** : Les cartes ont un aspect plus premium
4. ✅ **Adaptabilité** : Les tailles s'ajustent toujours selon la longueur
5. ✅ **Compatibilité** : Fonctionne toujours avec l'impression PVC

## Fichiers modifiés

- `eleves/carte_scolaire_generator.py` :
  - Lignes 115, 122-124 : En-tête et logo agrandis
  - Lignes 148-154 : Nouvelles tailles carte individuelle
  - Lignes 506-512 : Nouvelles tailles carte PVC
  - Lignes 704-709 : Nouvelles tailles cartes en masse
  - Ligne 225 : Position informations ajustée

## Scripts de test créés

- `test_tailles_augmentees.py` : Affiche le tableau comparatif des tailles
- `test_nom_ecole_carte.py` : Test général du système

## URLs pour tester

- `/eleves/{id}/carte-scolaire-pdf/` - Carte individuelle
- `/eleves/{id}/carte-scolaire-pdf/?format=pvc` - Carte PVC
- `/eleves/classe/{id}/cartes-scolaires-pdf/` - Cartes en masse

## Impact visuel

### Avant
```
Nom école : [########] (petite police)
```

### Après
```
Nom école : [############] (POLICE AUGMENTÉE)
```

## Recommandations

1. Tester l'impression réelle pour valider la lisibilité
2. Vérifier sur différentes imprimantes PVC
3. S'assurer que les noms très longs restent lisibles
4. Ajuster si nécessaire selon les retours utilisateurs

## Statut : ✅ COMPLÉTÉ

Les tailles ont été augmentées avec succès. Le nom de l'école est maintenant bien plus visible sur toutes les cartes scolaires.
