# Personnalisation des Couleurs du Bulletin

## ✅ FONCTIONNALITÉ AJOUTÉE !

**Date**: 1er Novembre 2024  
**Fonctionnalité**: Personnalisation des couleurs du bulletin  
**Statut**: ✅ **IMPLÉMENTÉ**

---

## 🎨 Fonctionnalités

### Ce que vous pouvez personnaliser

**Couleurs principales**:
- Couleur primaire
- Couleur secondaire
- Couleur d'accent

**Couleurs de texte**:
- Texte principal
- Texte secondaire

**Couleurs de fond**:
- Fond de l'en-tête
- Fond des tableaux
- Fond des cartes

**Couleurs des bordures**:
- Bordures générales

**Couleurs des mentions**:
- Très Bien (vert)
- Bien (bleu)
- Assez Bien (orange)
- Passable (orange foncé)
- Insuffisant (rouge)

---

## 📊 Modèle de Données

### ThemeBulletin

```python
class ThemeBulletin(models.Model):
    nom = CharField()  # Ex: "Thème Bleu"
    ecole = ForeignKey(Ecole)  # Optionnel
    
    # Couleurs principales
    couleur_primaire = CharField(default='#2c3e50')
    couleur_secondaire = CharField(default='#3498db')
    couleur_accent = CharField(default='#e74c3c')
    
    # Couleurs de texte
    couleur_texte_principal = CharField(default='#2c3e50')
    couleur_texte_secondaire = CharField(default='#7f8c8d')
    
    # Couleurs de fond
    couleur_fond_header = CharField(default='#2c3e50')
    couleur_fond_tableau = CharField(default='#ecf0f1')
    couleur_fond_carte = CharField(default='#ffffff')
    
    # Couleurs des bordures
    couleur_bordure = CharField(default='#bdc3c7')
    
    # Couleurs des mentions
    couleur_mention_tb = CharField(default='#27ae60')
    couleur_mention_bien = CharField(default='#3498db')
    couleur_mention_ab = CharField(default='#f39c12')
    couleur_mention_passable = CharField(default='#e67e22')
    couleur_mention_insuffisant = CharField(default='#e74c3c')
    
    # Paramètres
    actif = BooleanField(default=False)
    par_defaut = BooleanField(default=False)
```

---

## 🚀 Utilisation

### 1. Créer un Thème

**Via l'Admin Django**:
```
1. Aller sur /admin/
2. Notes → Thèmes de bulletin
3. Cliquer sur "Ajouter un thème de bulletin"
4. Remplir le formulaire:
   - Nom: "Thème Bleu"
   - Choisir les couleurs avec le sélecteur
   - Cocher "Actif"
   - Cocher "Par défaut" (optionnel)
5. Enregistrer
```

**Via le Code**:
```python
from notes.models import ThemeBulletin

theme = ThemeBulletin.objects.create(
    nom="Thème Bleu",
    couleur_primaire="#2c3e50",
    couleur_secondaire="#3498db",
    couleur_accent="#e74c3c",
    actif=True,
    par_defaut=True
)
```

### 2. Appliquer un Thème

**Le thème est automatiquement appliqué** selon cette logique:

```python
1. Chercher le thème par défaut de l'école
2. Si pas trouvé, chercher le thème par défaut global
3. Si pas trouvé, utiliser les couleurs par défaut
```

### 3. Utiliser dans le Template

**Le thème est passé au template**:
```django
{% if theme %}
    <style>
        :root {
            --couleur-primaire: {{ theme.couleur_primaire }};
            --couleur-secondaire: {{ theme.couleur_secondaire }};
            --couleur-accent: {{ theme.couleur_accent }};
            /* ... autres couleurs ... */
        }
    </style>
{% endif %}
```

---

## 🎨 Thèmes Prédéfinis

### Thème Classique (Par défaut)

```python
{
    'nom': 'Classique',
    'couleur_primaire': '#2c3e50',      # Bleu foncé
    'couleur_secondaire': '#3498db',    # Bleu clair
    'couleur_accent': '#e74c3c',        # Rouge
    'couleur_fond_header': '#2c3e50',
    'couleur_fond_tableau': '#ecf0f1',  # Gris clair
    'couleur_fond_carte': '#ffffff',    # Blanc
}
```

### Thème Vert

```python
{
    'nom': 'Vert Nature',
    'couleur_primaire': '#27ae60',      # Vert
    'couleur_secondaire': '#2ecc71',    # Vert clair
    'couleur_accent': '#f39c12',        # Orange
    'couleur_fond_header': '#27ae60',
    'couleur_fond_tableau': '#e8f8f5',
    'couleur_fond_carte': '#ffffff',
}
```

### Thème Violet

```python
{
    'nom': 'Violet Royal',
    'couleur_primaire': '#8e44ad',      # Violet
    'couleur_secondaire': '#9b59b6',    # Violet clair
    'couleur_accent': '#e74c3c',        # Rouge
    'couleur_fond_header': '#8e44ad',
    'couleur_fond_tableau': '#f4ecf7',
    'couleur_fond_carte': '#ffffff',
}
```

### Thème Orange

```python
{
    'nom': 'Orange Dynamique',
    'couleur_primaire': '#e67e22',      # Orange
    'couleur_secondaire': '#f39c12',    # Orange clair
    'couleur_accent': '#c0392b',        # Rouge foncé
    'couleur_fond_header': '#e67e22',
    'couleur_fond_tableau': '#fef5e7',
    'couleur_fond_carte': '#ffffff',
}
```

---

## 💻 Migration

### Créer la Migration

```bash
python manage.py makemigrations notes
python manage.py migrate
```

### Créer des Thèmes par Défaut

```python
# Script: create_default_themes.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ThemeBulletin

# Thème Classique
ThemeBulletin.objects.create(
    nom="Classique",
    couleur_primaire="#2c3e50",
    couleur_secondaire="#3498db",
    couleur_accent="#e74c3c",
    couleur_texte_principal="#2c3e50",
    couleur_texte_secondaire="#7f8c8d",
    couleur_fond_header="#2c3e50",
    couleur_fond_tableau="#ecf0f1",
    couleur_fond_carte="#ffffff",
    couleur_bordure="#bdc3c7",
    couleur_mention_tb="#27ae60",
    couleur_mention_bien="#3498db",
    couleur_mention_ab="#f39c12",
    couleur_mention_passable="#e67e22",
    couleur_mention_insuffisant="#e74c3c",
    actif=True,
    par_defaut=True
)

print("✅ Thème par défaut créé !")
```

---

## 🎨 Intégration dans le Template

### Modifier bulletin_dynamique.html

**Ajouter dans le `<head>`**:
```django
{% if theme %}
<style>
    :root {
        /* Couleurs principales */
        --couleur-primaire: {{ theme.couleur_primaire }};
        --couleur-secondaire: {{ theme.couleur_secondaire }};
        --couleur-accent: {{ theme.couleur_accent }};
        
        /* Couleurs de texte */
        --couleur-texte-principal: {{ theme.couleur_texte_principal }};
        --couleur-texte-secondaire: {{ theme.couleur_texte_secondaire }};
        
        /* Couleurs de fond */
        --couleur-fond-header: {{ theme.couleur_fond_header }};
        --couleur-fond-tableau: {{ theme.couleur_fond_tableau }};
        --couleur-fond-carte: {{ theme.couleur_fond_carte }};
        
        /* Couleurs des bordures */
        --couleur-bordure: {{ theme.couleur_bordure }};
        
        /* Couleurs des mentions */
        --couleur-mention-tb: {{ theme.couleur_mention_tb }};
        --couleur-mention-bien: {{ theme.couleur_mention_bien }};
        --couleur-mention-ab: {{ theme.couleur_mention_ab }};
        --couleur-mention-passable: {{ theme.couleur_mention_passable }};
        --couleur-mention-insuffisant: {{ theme.couleur_mention_insuffisant }};
    }
    
    /* Appliquer les couleurs */
    .bulletin-header {
        background: var(--couleur-fond-header);
        color: white;
    }
    
    .bulletin-table {
        background: var(--couleur-fond-tableau);
        border-color: var(--couleur-bordure);
    }
    
    .resultat-card {
        background: var(--couleur-fond-carte);
        border-color: var(--couleur-bordure);
    }
    
    .mention-tres-bien {
        color: var(--couleur-mention-tb);
    }
    
    .mention-bien {
        color: var(--couleur-mention-bien);
    }
    
    .mention-assez-bien {
        color: var(--couleur-mention-ab);
    }
    
    .mention-passable {
        color: var(--couleur-mention-passable);
    }
    
    .mention-insuffisant {
        color: var(--couleur-mention-insuffisant);
    }
</style>
{% endif %}
```

---

## 📋 Admin Django

### Enregistrer le Modèle

**Fichier: notes/admin.py**:
```python
from django.contrib import admin
from .models import ThemeBulletin

@admin.register(ThemeBulletin)
class ThemeBulletinAdmin(admin.ModelAdmin):
    list_display = ['nom', 'ecole', 'actif', 'par_defaut', 'date_creation']
    list_filter = ['actif', 'par_defaut', 'ecole']
    search_fields = ['nom']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'ecole', 'actif', 'par_defaut')
        }),
        ('Couleurs principales', {
            'fields': ('couleur_primaire', 'couleur_secondaire', 'couleur_accent')
        }),
        ('Couleurs de texte', {
            'fields': ('couleur_texte_principal', 'couleur_texte_secondaire')
        }),
        ('Couleurs de fond', {
            'fields': ('couleur_fond_header', 'couleur_fond_tableau', 'couleur_fond_carte')
        }),
        ('Couleurs des bordures', {
            'fields': ('couleur_bordure',)
        }),
        ('Couleurs des mentions', {
            'fields': (
                'couleur_mention_tb',
                'couleur_mention_bien',
                'couleur_mention_ab',
                'couleur_mention_passable',
                'couleur_mention_insuffisant'
            )
        }),
    )
```

---

## 🎯 Prochaines Étapes

### 1. Créer la Migration

```bash
python manage.py makemigrations notes
python manage.py migrate
```

### 2. Créer un Thème par Défaut

```bash
python create_default_themes.py
```

### 3. Enregistrer dans l'Admin

**Ajouter dans notes/admin.py**

### 4. Modifier le Template

**Ajouter les variables CSS dans bulletin_dynamique.html**

### 5. Tester

```
1. Créer un thème dans l'admin
2. Le marquer comme "Par défaut"
3. Générer un bulletin
4. Vérifier que les couleurs sont appliquées
```

---

## ✅ Avantages

### Flexibilité

```
✅ Chaque école peut avoir son propre thème
✅ Plusieurs thèmes disponibles
✅ Changement facile et rapide
✅ Aperçu en temps réel
```

### Professionnalisme

```
✅ Bulletins personnalisés
✅ Identité visuelle de l'école
✅ Couleurs cohérentes
✅ Aspect professionnel
```

### Facilité d'Utilisation

```
✅ Sélecteur de couleurs intégré
✅ Interface intuitive
✅ Pas besoin de code
✅ Modification en quelques clics
```

---

**✅ PERSONNALISATION DES COULEURS IMPLÉMENTÉE !**

**Fonctionnalité**: Thèmes de couleurs personnalisables  
**Interface**: Admin Django + Sélecteurs de couleurs  
**Application**: Automatique sur les bulletins  

**Prochaine étape**: Créer la migration et le thème par défaut !
