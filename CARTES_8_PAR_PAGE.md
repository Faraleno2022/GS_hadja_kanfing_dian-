# Optimisation: 8 Cartes Scolaires par Page

## Date: 8 Novembre 2024

## Amélioration Implémentée
Passage de 4 à 8 cartes par page A4 avec informations centrées pour une meilleure lisibilité et économie de papier.

## Changements Principaux

### 1. **Nouvelle Disposition**
- **Ancien**: Grille 2×2 (4 cartes)
- **Nouveau**: Grille 4×2 (8 cartes)
- **Réduction**: 50% du nombre de pages

### 2. **Dimensions Ajustées**

| Élément | Ancien | Nouveau | Réduction |
|---------|---------|---------|-----------|
| En-tête | 12mm | 8mm | -33% |
| Photo | 20mm | 15mm | -25% |
| Logo en-tête | 8mm | 5mm | -37% |
| Logo photo | 5mm | 3mm | -40% |
| Filigrane | 30mm | 20mm | -33% |
| Marges | 15mm | 10mm | -33% |
| Espacement | 10mm | 5mm | -50% |

### 3. **Tailles de Police**

| Texte | Ancien | Nouveau |
|-------|---------|---------|
| Nom élève | 9pt | 7pt |
| Matricule | 7pt | 6pt |
| Classe | 7pt | 6pt |
| Date naissance | 7pt | 5pt |
| Contact | 6pt | 5pt |
| Année scolaire | 5pt | 4pt |

### 4. **Position des Informations**
- **Décalage horizontal**: 8mm (au lieu de 3mm)
- **Effet**: Informations mieux centrées dans la carte
- **Lisibilité**: Améliorée malgré la taille réduite

## Disposition sur la Page A4

```
┌─────────────────────────────────────┐
│                                     │
│  ┌─────────┐      ┌─────────┐      │
│  │ Carte 1 │      │ Carte 2 │      │  Ligne 1
│  └─────────┘      └─────────┘      │
│                                     │
│  ┌─────────┐      ┌─────────┐      │
│  │ Carte 3 │      │ Carte 4 │      │  Ligne 2
│  └─────────┘      └─────────┘      │
│                                     │
│  ┌─────────┐      ┌─────────┐      │
│  │ Carte 5 │      │ Carte 6 │      │  Ligne 3
│  └─────────┘      └─────────┘      │
│                                     │
│  ┌─────────┐      ┌─────────┐      │
│  │ Carte 7 │      │ Carte 8 │      │  Ligne 4
│  └─────────┘      └─────────┘      │
│                                     │
└─────────────────────────────────────┘
```

## Code Modifié

### Fichier: `carte_scolaire_generator.py`

#### Fonction `generer_cartes_classe_moderne`
```python
# Grille 4x2 (8 cartes)
positions = []
for row in range(4):  # 4 lignes
    for col in range(2):  # 2 colonnes
        x = margin + col * (card_width + h_spacing)
        y = page_height - margin - (row + 1) * card_height - row * v_spacing
        positions.append((x, y))

# Nouvelle page après 8 cartes
if card_count % 8 == 0:
    c.showPage()
```

#### Fonction `_dessiner_carte_simple`
```python
# Informations décalées vers le centre
info_x = photo_x + photo_size + 8*mm  # Était 3*mm
info_y = y + height - header_height - 6*mm
```

## Optimisations du Texte

### Abréviations Utilisées
- "Matricule:" → "Mat:"
- "Classe:" → "Cl:"
- "Contact urgence:" → "Contact:"
- "Année scolaire" → "AS"
- "Né(e) le:" → Date directement
- "Tél:" → Numéro directement

### Troncatures
- Nom école: 25 caractères max
- Nom élève: 25 caractères max
- Classe: 18 caractères max
- Lieu naissance: 20 caractères max
- Adresse: 25 caractères max

## Résultats des Tests

### Classe 7ÈME ANNÉE (40 élèves)
- **Ancien format**: 10 pages
- **Nouveau format**: 5 pages
- **Économie**: 50% de papier
- **Taille PDF**: 106 KB (légèrement réduit)

## Avantages

### 📊 **Économiques**
- 50% moins de papier
- Impression plus rapide
- Coûts réduits de moitié

### 🎨 **Visuels**
- Informations mieux centrées
- Format plus compact
- Toujours lisible malgré la réduction

### 🌱 **Écologiques**
- Moins de papier consommé
- Empreinte carbone réduite
- Stockage plus compact

## Recommandations d'Impression

### Paramètres
- Format: A4 (210×297mm)
- Orientation: Portrait
- Marges: Aucune (déjà incluses)
- Échelle: 100% (ne pas ajuster)
- Qualité: Normale ou Haute

### Découpe
- Utiliser un massicot pour précision
- Lignes de découpe virtuelles aux espacements
- Coins arrondis optionnels (rayon 4mm)

## Cas d'Usage

### Idéal Pour
- ✅ Classes nombreuses (>20 élèves)
- ✅ Impressions en masse
- ✅ Budget limité
- ✅ Stockage compact

### Moins Adapté Pour
- ❌ Cartes premium individuelles
- ❌ Élèves avec beaucoup d'informations
- ❌ Impression sur cartes PVC

## Fichiers de Test
- `test_8_cartes_page.py` - Script de test
- `cartes_8_par_page_19.pdf` - Exemple généré

## Statut
✅ **FONCTIONNEL** - 8 cartes par page avec informations centrées et optimisées
