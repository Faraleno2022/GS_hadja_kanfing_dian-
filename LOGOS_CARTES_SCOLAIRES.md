# Intégration des Logos sur les Cartes Scolaires

## Date: 8 Novembre 2024

## Fonctionnalité Implémentée
Ajout de trois emplacements de logos sur chaque carte scolaire pour renforcer l'identité visuelle et la sécurité.

## Emplacements des Logos

### 1. **Logo en Filigrane (Arrière-plan)**
- **Position**: Centre de la carte
- **Taille**: 30mm
- **Opacité**: 6% (très transparent)
- **Rotation**: 15 degrés
- **But**: Effet filigrane professionnel, anti-falsification
- **Visible**: Derrière tout le contenu de la carte

### 2. **Logo dans l'En-tête**
- **Position**: Gauche de l'en-tête bleu
- **Taille**: 8mm
- **Présentation**: Dans un cercle blanc
- **But**: Identification claire de l'école
- **Accompagnement**: Nom de l'école à droite

### 3. **Logo sur le Cadre Photo**
- **Position**: Coin supérieur gauche du cadre photo
- **Taille**: 5mm
- **Opacité**: 70% (semi-transparent)
- **Présentation**: Dans un cercle blanc
- **But**: Marque d'authenticité et de sécurité

## Comportement Sans Logo

Si l'école n'a pas de logo uploadé:
- **Filigrane**: Initiales de l'école (3 premières lettres)
- **En-tête**: Initiales dans le cercle blanc (2 premières lettres)
- **Cadre photo**: Première lettre de l'école

## Code Modifié

### Fichier: `eleves/carte_scolaire_generator.py`

#### Fonction `_dessiner_carte_simple`

1. **Ajout du filigrane** (lignes 584-618):
```python
# FILIGRANE DU LOGO (arrière-plan)
c.saveState()
c.setFillAlpha(0.06)  # Très transparent
# Rotation et dessin du logo
c.translate(x + width/2, y + height/2)
c.rotate(15)
c.drawImage(logo_path, ...)
```

2. **Logo dans l'en-tête** (lignes 630-664):
```python
# Logo dans l'en-tête (à gauche)
logo_size = 8*mm
# Cercle blanc pour le logo
c.circle(logo_x + logo_size/2, ...)
# Insertion du logo
c.drawImage(logo_path, ...)
```

3. **Logo sur cadre photo** (lignes 679-717):
```python
# Petit logo dans le coin supérieur gauche
corner_logo_size = 5*mm
c.setFillAlpha(0.7)  # Semi-transparent
# Dessin du logo
c.drawImage(logo_path, ...)
```

## Tests Effectués

### Test 1: Carte Individuelle
- Script: `test_logos_cartes.py`
- Résultat: ✅ Succès
- PDF généré: `test_logos_cartes.pdf` (9 KB)

### Test 2: Classe Complète
- Script: `test_logos_classe_complete.py`
- Classe: 7ÈME ANNÉE (40 élèves)
- Résultat: ✅ Succès
- PDF généré: `cartes_classe_logos_19.pdf` (114 KB)
- Statistiques: 120 logos au total (3 par carte × 40 cartes)

## Avantages

### 🔒 **Sécurité**
- Difficile à falsifier grâce au filigrane
- Multiple points d'identification
- Logo semi-transparent sur la photo

### 🎨 **Esthétique**
- Design professionnel
- Identité visuelle cohérente
- Effet filigrane subtil

### 🏢 **Identité**
- Renforcement de l'image de l'école
- Reconnaissance immédiate
- Uniformité des documents

## Configuration Requise

### Logo de l'École
- Format: PNG, JPG, JPEG
- Taille recommandée: 500×500px minimum
- Fond transparent préféré (PNG)
- Upload via: Admin Django → Écoles → Logo

### Si Pas de Logo
Le système génère automatiquement des initiales:
- Filigrane: 3 premières lettres
- En-tête: 2 premières lettres  
- Photo: 1ère lettre

## Impact Visuel

```
┌─────────────────────────────────────────┐
│ [LOGO] NOM DE L'ÉCOLE          (EN-TÊTE)│
├─────────────────────────────────────────┤
│        💧 FILIGRANE CENTRAL              │
│ ┌────┐                                   │
│ │📷🔵│  INFORMATIONS ÉLÈVE               │
│ └────┘                                   │
│         (Logo coin photo)                │
│                                          │
│         💧 (Logo transparent)            │
│                                          │
├─────────────────────────────────────────┤
│ Année scolaire 2024-2025                 │
└─────────────────────────────────────────┘
```

## Fichiers Créés
- `LOGOS_CARTES_SCOLAIRES.md` (cette documentation)
- `test_logos_cartes.py` (test unitaire)
- `test_logos_classe_complete.py` (test classe entière)

## Exemples Générés
- `test_logos_cartes.pdf` - Exemple avec 2 cartes
- `cartes_classe_logos_19.pdf` - Classe complète avec logos

## Statut
✅ **FONCTIONNEL** - Les logos sont correctement intégrés sur les trois emplacements
