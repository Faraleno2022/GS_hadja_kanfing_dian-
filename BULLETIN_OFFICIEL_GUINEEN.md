# 🇬🇳 Bulletin Officiel Guinéen - Mise à jour du 13/11/2024

## 📋 Nouvelles Caractéristiques de l'En-tête Officiel

### 1. Structure Hiérarchique Complète

L'en-tête du bulletin respecte maintenant l'ordre protocolaire officiel :

1. **RÉPUBLIQUE DE GUINÉE** (en majuscules, 16px)
2. **Travail-Justice-Solidarité** avec les couleurs du drapeau :
   - 🔴 **Travail** en rouge (#CE1126)
   - 🟡 **Justice** en jaune (#FCD116) 
   - 🟢 **Solidarité** en vert (#009460)
3. **MPU-A** (Ministère du Pré-Universitaire et de l'Alphabétisation)
4. **NOM DE L'ÉCOLE** (en majuscules)
5. **BULLETIN DE NOTES - [PÉRIODE]**
6. **Année Scolaire 2024-2025**

### 2. Drapeau National Guinéen 🇬🇳

- **Position** : Coin supérieur droit (à côté de la photo de l'élève)
- **Dimensions** : 30×20 pixels (réduit à 25×16px pour l'impression)
- **Composition** : Trois bandes verticales égales
  - Rouge : Symbolise le travail et le sacrifice
  - Jaune : Représente les richesses du sol guinéen
  - Vert : Évoque la végétation et l'agriculture

### 3. Mise en Page Améliorée

#### Positionnement des éléments :
- **Logo de l'école** : Coin supérieur gauche (60×60px)
- **Drapeau guinéen** : Haut droite, avant la photo
- **Photo de l'élève** : Coin supérieur droit (70×90px)
- **Textes officiels** : Centrés et hiérarchisés

#### Styles appliqués :
```css
.devise-nationale : Conteneur de la devise avec espacement
.devise-rouge : Couleur rouge pour "Travail"
.devise-jaune : Couleur jaune pour "Justice"  
.devise-vert : Couleur verte pour "Solidarité"
.ministere-education : Style pour MPU-A
.nom-ecole : Nom de l'école en majuscules
.drapeau-guinee : Conteneur du drapeau CSS
```

## 🎯 Améliorations Techniques

### Bulletin Individuel
- Affichage correct de tous les symboles nationaux
- Respect des couleurs officielles du drapeau
- Hiérarchie visuelle claire et professionnelle

### Export PDF de Classe
- Tous les bulletins incluent les symboles nationaux
- Drapeau rendu en CSS pur (pas d'image externe nécessaire)
- Optimisation pour l'impression avec tailles ajustées

## 📂 Fichiers Modifiés

1. **templates/notes/bulletin_dynamique.html**
   - Ajout de la devise nationale colorée
   - Intégration du drapeau guinéen en CSS
   - Réorganisation de l'en-tête avec MPU-A

2. **notes/views.py** 
   - Fonction `bulletins_dynamiques_classe_pdf` mise à jour
   - Styles CSS incluant les nouveaux éléments nationaux

## 🚀 Utilisation

### Pour un bulletin individuel :
1. Aller dans **Bulletin Dynamique**
2. Sélectionner classe, période et élève
3. Le bulletin affiche automatiquement tous les symboles nationaux

### Pour exporter toute une classe :
1. Sélectionner la classe et la période
2. Cliquer sur **"Exporter tous les bulletins de la classe"**
3. Le PDF généré contient tous les éléments officiels

## ✅ Conformité

Ce bulletin respecte :
- Les symboles nationaux de la République de Guinée
- L'ordre protocolaire officiel des institutions
- Les couleurs exactes du drapeau national
- Le format standard du Ministère de l'Éducation (MPU-A)

## 🎨 Aperçu Visuel de l'En-tête

```
        [Logo École]                              [Drapeau 🔴🟡🟢]    [Photo]
                           RÉPUBLIQUE DE GUINÉE
                    Travail-Justice-Solidarité
                              MPU-A
                        NOM DE L'ÉCOLE
                   BULLETIN DE NOTES - 1ER TRIMESTRE
                      Année Scolaire 2024-2025
```

## 📝 Notes Importantes

- Le drapeau est généré en CSS pur, aucune image externe n'est requise
- Les couleurs utilisées sont les couleurs officielles du drapeau guinéen
- L'ordre des éléments respecte le protocole institutionnel
- Compatible avec l'impression et l'export PDF

---

*Document créé le 13/11/2024 - Système de Gestion Scolaire Guinéen*
