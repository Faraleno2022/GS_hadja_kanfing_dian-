# 💳 Cartes Scolaires PVC - Guide d'Impression Professionnelle

## 📋 Vue d'ensemble
Système optimisé pour l'impression de cartes scolaires sur support PVC rigide avec filigrane du logo de l'école.

## 🎯 Caractéristiques PVC

### 📐 Spécifications Techniques
- **Format**: CR80 standard (85.6mm x 53.98mm)
- **Épaisseur recommandée**: 0.76mm (30mil)
- **Matériau**: PVC blanc brillant ou mat
- **Impression**: Offset, sérigraphie ou sublimation thermique
- **Résolution**: 300 DPI minimum

### 🔐 Éléments de Sécurité

1. **Filigrane du Logo**
   - Position: Centre de la carte
   - Opacité: 6-8% pour subtilité
   - Rotation: 15° pour effet professionnel
   - Taille: 40mm pour visibilité optimale

2. **Micro-texte de Sécurité**
   - Bande inférieure avec nom de l'école répété
   - Police 3pt difficile à reproduire
   - Couleur gris clair (#e5e7eb)

3. **Marquage PVC**
   - Indicateur "PVC CARD" en bas
   - Numéro de série unique (#XXXXXX)

### 🖨️ Options d'Impression

#### Version Standard
```
URL: /eleves/{id}/carte-scolaire-pdf/
Format: PDF standard pour impression bureau
```

#### Version PVC Professionnelle
```
URL: /eleves/{id}/carte-scolaire-pdf/?format=pvc
Format: PDF haute qualité avec marques de découpe
```

## 🛠️ Utilisation

### Interface Web
1. Ouvrir la carte d'un élève
2. Cliquer sur **"Format PVC Pro"** (bouton jaune)
3. Le PDF téléchargé inclut:
   - Marques de découpe (crop marks)
   - Fond perdu (bleed) de 3mm
   - Filigrane intégré
   - Résolution optimisée

### Paramètres d'Impression
```python
# Dans carte_scolaire_generator.py
generer_carte_pvc_haute_qualite(
    eleve=eleve,
    response=response,
    with_crop_marks=True  # Activer/désactiver marques
)
```

## 🎨 Design Optimisé PVC

### Couleurs CMYK
- Bleu principal: `#004494` (100% compatible CMYK)
- Noir texte: `#000000` (noir pur)
- Gris: Optimisés pour impression

### Éléments Visuels
- **En-tête**: Fond bleu uni (meilleur rendu PVC)
- **Photo**: Zone définie 24x30mm
- **Texte**: Polices Arial/Helvetica (vectorielles)
- **Bordures**: 2pt pour visibilité sur PVC

## 📊 Workflow de Production

### 1. Préparation
```bash
# Générer les cartes pour une classe
python manage.py generer_cartes_pvc --classe="6ème A"
```

### 2. Vérification
- Ouvrir le PDF dans Adobe Acrobat Pro
- Vérifier les marques de découpe
- Valider le filigrane visible

### 3. Impression
**Imprimante carte PVC recommandée:**
- Evolis Primacy
- Fargo HDP5000
- Zebra ZXP Series 7

**Paramètres:**
- Mode: Couleur CMJN
- Résolution: 300 DPI
- Overlay: Protection UV recommandée
- Lamination: Optionnelle pour durabilité

## 🔧 Personnalisation

### Modifier le Filigrane
```python
# Dans generer_carte_pvc_haute_qualite()
c.setFillAlpha(0.06)  # Ajuster transparence (0.01-0.15)
c.rotate(15)  # Ajuster angle rotation
filigrane_size = 40*mm  # Ajuster taille
```

### Activer les Marques de Découpe
```python
# Ligne 340 dans carte_scolaire_generator.py
if False:  # Changer en True
    # Les marques seront visibles
```

### Ajuster le Fond Perdu
```python
bleed = 3*mm  # Standard
# Peut être augmenté à 5mm si nécessaire
```

## 📐 Gabarit pour Designers

### Dimensions Zones
```
Zone totale: 85.6 x 53.98 mm
Zone sûre: 81.6 x 49.98 mm (2mm marge)
Zone photo: 24 x 30 mm
Zone texte: 45 x 35 mm
En-tête: 85.6 x 12 mm
```

### Exports Graphiques
- Format: PDF/X-1a ou PDF/X-4
- Profil couleur: Fogra39 (ISO Coated v2)
- Incorporation polices: 100%
- Images: 300 DPI minimum

## ⚠️ Points d'Attention

### Qualité Photo
- Résolution minimale: 300x375 pixels
- Format: JPEG haute qualité
- Compression: Minimale pour PVC

### Durabilité
- Test de résistance UV recommandé
- Vernis ou lamination pour usage intensif
- Stockage à l'abri de la chaleur

### Sécurité
- Ne pas exposer les numéros de série publiquement
- Garder une base de données des cartes émises
- Prévoir un système de remplacement

## 🚀 Commandes Rapides

### Génération Individuelle
```bash
# Standard
curl http://localhost:8000/eleves/123/carte-scolaire-pdf/

# PVC Pro
curl http://localhost:8000/eleves/123/carte-scolaire-pdf/?format=pvc
```

### Génération en Masse
```python
# Script Python
from eleves.carte_scolaire_generator import generer_carte_pvc_haute_qualite
from eleves.models import Eleve

for eleve in Eleve.objects.filter(classe__nom="6ème A"):
    generer_carte_pvc_haute_qualite(eleve, response)
```

## 📈 Coûts Estimés

### Par Carte
- PVC vierge: 0.15-0.30€
- Impression couleur: 0.20-0.40€
- Lamination: 0.10-0.20€
- **Total: 0.45-0.90€ par carte**

### Par École (500 élèves)
- Matériel: 225-450€
- Main d'œuvre: Variable
- Durée production: 2-3 jours

## ✅ Checklist Pré-Impression

- [ ] Photos élèves haute résolution
- [ ] Logo école vectoriel (SVG/AI)
- [ ] Informations élèves validées
- [ ] Imprimante PVC calibrée
- [ ] Stock cartes PVC suffisant
- [ ] Ruban couleur YMCKO
- [ ] Overlay de protection
- [ ] Système de découpe configuré

## 📞 Support Technique

Pour toute question sur l'impression PVC:
- Documentation: `/docs/cartes-pvc/`
- Email: support@ecole-moderne.com
- Hotline: +224 XXX XXX XXX

---

**Version**: 1.0  
**Date**: 7 Novembre 2024  
**Auteur**: Système de Gestion Scolaire Moderne
