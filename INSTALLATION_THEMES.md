# Installation des Thèmes de Couleurs

## 🚀 GUIDE D'INSTALLATION RAPIDE

**Fonctionnalité**: Personnalisation des couleurs du bulletin  
**Temps d'installation**: 5 minutes  
**Statut**: ✅ Prêt à installer

---

## 📋 Étapes d'Installation

### 1. Créer la Migration

```bash
python manage.py makemigrations notes
```

**Résultat attendu**:
```
Migrations for 'notes':
  notes\migrations\0XXX_themebulletin.py
    - Create model ThemeBulletin
```

### 2. Appliquer la Migration

```bash
python manage.py migrate notes
```

**Résultat attendu**:
```
Running migrations:
  Applying notes.0XXX_themebulletin... OK
```

### 3. Créer les Thèmes par Défaut

```bash
python create_default_themes.py
```

**Résultat attendu**:
```
================================================================================
CRÉATION DES THÈMES PAR DÉFAUT
================================================================================

1. Création du thème Classique...
   ✅ Thème Classique créé

2. Création du thème Vert Nature...
   ✅ Thème Vert Nature créé

3. Création du thème Violet Royal...
   ✅ Thème Violet Royal créé

4. Création du thème Orange Dynamique...
   ✅ Thème Orange Dynamique créé

================================================================================
RÉSUMÉ
================================================================================

Nombre total de thèmes: 4
  - Classique: Actif, Par défaut
  - Vert Nature: Actif
  - Violet Royal: Actif
  - Orange Dynamique: Actif

✅ Thèmes créés avec succès !
```

### 4. Vérifier dans l'Admin

```
1. Aller sur http://127.0.0.1:8000/admin/
2. Se connecter
3. Aller dans Notes → Thèmes de bulletin
4. Vous devriez voir 4 thèmes
```

---

## ✅ Vérification

### Test 1: Voir les Thèmes

```
1. Admin → Notes → Thèmes de bulletin
2. Vous devriez voir:
   - Classique (Actif, Par défaut)
   - Vert Nature (Actif)
   - Violet Royal (Actif)
   - Orange Dynamique (Actif)
```

### Test 2: Modifier un Thème

```
1. Cliquer sur "Classique"
2. Vous devriez voir:
   - Sélecteurs de couleurs
   - Aperçu des couleurs
   - Cases à cocher Actif/Par défaut
3. Modifier une couleur
4. Enregistrer
```

### Test 3: Appliquer au Bulletin

```
1. Aller sur /notes/bulletins/
2. Sélectionner une classe et un élève
3. Le bulletin devrait utiliser les couleurs du thème
```

---

## 🎨 Utilisation

### Changer le Thème

**Méthode 1: Via l'Admin**:
```
1. Admin → Thèmes de bulletin
2. Cliquer sur le thème souhaité
3. Cocher "Par défaut"
4. Enregistrer
5. Rafraîchir le bulletin
```

**Méthode 2: Créer un Nouveau Thème**:
```
1. Admin → Thèmes de bulletin → Ajouter
2. Nom: "Mon Thème"
3. Choisir les couleurs
4. Cocher "Actif" et "Par défaut"
5. Enregistrer
```

### Thème par École

```
1. Admin → Thèmes de bulletin → Ajouter
2. Nom: "Thème École X"
3. École: Sélectionner l'école
4. Choisir les couleurs
5. Cocher "Actif" et "Par défaut"
6. Enregistrer
```

**Note**: Le thème de l'école a priorité sur le thème global.

---

## 🎨 Thèmes Disponibles

### 1. Classique (Par défaut)

**Couleurs**:
- Primaire: #2c3e50 (Bleu foncé)
- Secondaire: #3498db (Bleu clair)
- Accent: #e74c3c (Rouge)

**Utilisation**: Professionnel, sobre, adapté à toutes les écoles

### 2. Vert Nature

**Couleurs**:
- Primaire: #27ae60 (Vert)
- Secondaire: #2ecc71 (Vert clair)
- Accent: #f39c12 (Orange)

**Utilisation**: Dynamique, écologique, moderne

### 3. Violet Royal

**Couleurs**:
- Primaire: #8e44ad (Violet)
- Secondaire: #9b59b6 (Violet clair)
- Accent: #e74c3c (Rouge)

**Utilisation**: Élégant, distingué, prestigieux

### 4. Orange Dynamique

**Couleurs**:
- Primaire: #e67e22 (Orange)
- Secondaire: #f39c12 (Orange clair)
- Accent: #c0392b (Rouge foncé)

**Utilisation**: Énergique, chaleureux, accueillant

---

## 🔧 Personnalisation Avancée

### Créer un Thème Personnalisé

**Via l'Admin**:
```
1. Admin → Thèmes de bulletin → Ajouter
2. Remplir:
   - Nom: "Mon Thème Perso"
   - Couleur primaire: Choisir
   - Couleur secondaire: Choisir
   - Couleur accent: Choisir
   - ... (autres couleurs)
3. Cocher "Actif"
4. Enregistrer
```

**Via le Code**:
```python
from notes.models import ThemeBulletin

theme = ThemeBulletin.objects.create(
    nom="Mon Thème",
    couleur_primaire="#123456",
    couleur_secondaire="#abcdef",
    # ... autres couleurs
    actif=True,
    par_defaut=True
)
```

---

## 📊 Structure des Couleurs

### Où sont Utilisées les Couleurs

**Couleur Primaire**:
- En-tête du bulletin
- Titres principaux
- Boutons principaux

**Couleur Secondaire**:
- Sous-titres
- Liens
- Éléments interactifs

**Couleur Accent**:
- Éléments importants
- Alertes
- Highlights

**Couleurs de Fond**:
- Header: En-tête du bulletin
- Tableau: Lignes du tableau de notes
- Carte: Cartes de résultats (moyenne, rang, etc.)

**Couleurs des Mentions**:
- Très Bien: ≥ 16/20
- Bien: ≥ 14/20
- Assez Bien: ≥ 12/20
- Passable: ≥ 10/20
- Insuffisant: < 10/20

---

## ⚠️ Dépannage

### Problème 1: Thème Non Appliqué

**Solution**:
```
1. Vérifier que le thème est "Actif"
2. Vérifier qu'un thème est "Par défaut"
3. Rafraîchir la page du bulletin (Ctrl+F5)
4. Vider le cache du navigateur
```

### Problème 2: Couleurs Incorrectes

**Solution**:
```
1. Admin → Thèmes de bulletin
2. Vérifier les codes couleur (format #RRGGBB)
3. Modifier si nécessaire
4. Enregistrer
5. Rafraîchir le bulletin
```

### Problème 3: Plusieurs Thèmes "Par défaut"

**Solution**:
```
Le système désactive automatiquement les autres thèmes
quand vous en marquez un comme "Par défaut".
Si problème persiste:
1. Décocher "Par défaut" sur tous les thèmes
2. Cocher "Par défaut" sur un seul thème
3. Enregistrer
```

---

## 📝 Notes Importantes

### Format des Couleurs

**Toujours utiliser le format hexadécimal**:
```
✅ Correct: #2c3e50
✅ Correct: #fff
❌ Incorrect: rgb(44, 62, 80)
❌ Incorrect: blue
```

### Thème par École vs Global

**Priorité**:
```
1. Thème par défaut de l'école
2. Thème par défaut global
3. Couleurs par défaut du système
```

### Performance

**Les thèmes n'affectent pas les performances**:
```
✅ Pas de requête supplémentaire
✅ Chargement instantané
✅ Compatible avec tous les navigateurs
```

---

## ✅ Checklist Finale

```
☑ Migration créée
☑ Migration appliquée
☑ Thèmes par défaut créés
☑ Thèmes visibles dans l'admin
☑ Thème "Classique" marqué comme par défaut
☑ Bulletin affiche les couleurs du thème
```

---

**✅ INSTALLATION TERMINÉE !**

**Fonctionnalité**: Thèmes de couleurs opérationnels  
**Thèmes disponibles**: 4 thèmes prédéfinis  
**Personnalisation**: Illimitée via l'admin  

**Prochaine étape**: Créer vos propres thèmes !
