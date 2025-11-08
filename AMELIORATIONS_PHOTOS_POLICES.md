# Améliorations: Photos Agrandies et Polices Augmentées

## Date: 8 Novembre 2024

## Améliorations Appliquées
Suite à la demande de rendre les cartes plus lisibles, j'ai agrandi les photos et augmenté toutes les polices.

## 1. Photo Agrandie et Remontée

### Dimensions Photo
| Élément | Avant | Après | Amélioration |
|---------|-------|-------|--------------|
| **Taille** | 12mm | 18mm | +50% |
| **Position Y** | y+4mm | y+12mm | Remontée |
| **Initiales** | 8pt | 12pt | +50% |

### Impact Visuel
- ✅ Photo 50% plus grande
- ✅ Positionnée plus haut sur la carte
- ✅ Meilleure visibilité du visage
- ✅ Initiales plus lisibles si pas de photo

## 2. Polices Augmentées

### Tableau Comparatif
| Information | Avant | Après | Augmentation |
|-------------|-------|-------|--------------|
| **Nom élève** | 6pt | 8pt | +33% |
| **Matricule** | 5pt | 7pt | +40% |
| **Classe** | 5pt | 6pt | +20% |
| **Date naissance** | 4pt | 5pt | +25% |
| **Lieu naissance** | 4pt | 5pt | +25% |
| **Contact titre** | 4pt | 5pt | +25% |
| **Contact infos** | 4pt | 5pt | +25% |
| **Année scolaire** | 3.5pt | 4pt | +14% |

## 3. Ajustements des Espacements

### Espacements Optimisés
- **Info position X**: photo + 4mm (ajusté pour photo plus grande)
- **Info position Y**: height - header - 3mm (position haute)
- **Entre sections**: 2-3.5mm (augmenté pour lisibilité)

## Code Modifié

### Fichier: `carte_scolaire_generator.py`

#### Photo Agrandie
```python
# Avant
photo_size = 12*mm
photo_y = y + 4*mm

# Après
photo_size = 18*mm  # Agrandi pour meilleure visibilité
photo_y = y + 12*mm  # Remonté plus haut sur la carte
```

#### Polices Augmentées
```python
# Nom élève
c.setFont(bold_font, 8)  # Était 6pt

# Matricule
c.setFont(main_font, 7)  # Était 5pt

# Classe
c.setFont(main_font, 6)  # Était 5pt

# Date et autres infos
c.setFont(main_font, 5)  # Était 4pt
```

## Résultat Visual

### Avant
```
┌────────────────────────┐
│ En-tête                │
├────────────────────────┤
│ [📷12mm]  Infos 4-6pt  │  ← Photo petite, texte petit
│  ↓4mm                  │
│                        │
└────────────────────────┘
```

### Après
```
┌────────────────────────┐
│ En-tête                │
├────────────────────────┤
│         Infos 5-8pt    │  ← Texte plus grand
│ [📷18mm]               │  ← Photo 50% plus grande
│  ↑12mm                 │  ← Remontée
└────────────────────────┘
```

## Avantages

### 🔍 **Lisibilité**
- Toutes les informations sont plus lisibles
- Photo plus grande permet meilleure identification
- Initiales visibles même de loin

### 📷 **Identification**
- Photo 18mm correspond mieux au standard
- Position centrale améliore l'équilibre
- Plus proche du format carte d'identité

### 👁️ **Visibilité**
- Polices augmentées de 20-40%
- Meilleur contraste
- Lecture facile même à distance

## Impact sur le Format

### Compatibilité Maintenue
- ✅ Toujours 8 cartes par page
- ✅ Format PVC CR80 (85.6×53.98mm) conservé
- ✅ Toutes les informations tiennent
- ✅ Logos toujours visibles

### Optimisations
- Textes légèrement raccourcis si nécessaire
- Espacements ajustés pour photo plus grande
- Équilibre visuel amélioré

## Tests Effectués

### Test Principal
- **Classe**: 7ÈME ANNÉE
- **Élèves**: 40
- **PDF généré**: 107 KB
- **Fichier**: `cartes_photos_agrandies_19.pdf`

### Validations
- ✅ Photo 18mm bien visible
- ✅ Position remontée correcte
- ✅ Toutes les polices augmentées
- ✅ Informations complètes et lisibles
- ✅ 8 cartes par page maintenues

## Comparaison Visuelle

### Photo
- **Taille**: 12mm → 18mm (+50%)
- **Surface**: 144mm² → 324mm² (+125%)
- **Position**: Basse → Centrale haute

### Textes
- **Nom**: Petit → Bien visible
- **Matricule**: Difficile → Lisible
- **Contact**: Minuscule → Correct

## Recommandations

### Pour l'Impression
- Utiliser qualité "Normale" ou "Haute"
- Papier blanc 80-100g/m²
- Éviter la réduction automatique

### Pour la Découpe
- Les cartes restent au format PVC standard
- Découpe au massicot recommandée
- Coins arrondis optionnels

## Fichiers Créés
- `AMELIORATIONS_PHOTOS_POLICES.md` (cette documentation)
- `test_photos_agrandies.py` (script de test)
- `cartes_photos_agrandies_19.pdf` (exemple généré)

## Statut
✅ **FONCTIONNEL** - Photos agrandies et polices augmentées avec succès
