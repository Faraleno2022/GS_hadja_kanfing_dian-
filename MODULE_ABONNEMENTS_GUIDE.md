# Module Abonnements Bus et Cantine - Guide Complet

## ✅ Modèles Créés

Le module `abonnements` a été créé avec les modèles suivants:

### 1. TypeAbonnement
- Types: Bus, Cantine, Garderie, Étude
- Tarifs: Mensuel, Trimestriel, Annuel

### 2. Itineraire (Bus)
- Nom, quartiers desservis
- Horaires matin/soir
- Capacité

### 3. MenuCantine
- Menus par jour/semaine
- Entrée, plat, accompagnement, dessert

### 4. AbonnementBus
- Élève, itinéraire, durée
- Points de montée/descente
- Contact d'urgence

### 5. AbonnementCantine
- Élève, durée, montant
- Régime alimentaire
- Allergies

### 6. PresenceCantine
- Suivi quotidien
- Menu du jour

---

## 📝 Étapes d'Installation

### Étape 1: Ajouter à settings.py

```python
INSTALLED_APPS = [
    # ... apps existantes
    'abonnements',
]
```

### Étape 2: Créer les migrations

```bash
python manage.py makemigrations abonnements
python manage.py migrate abonnements
```

### Étape 3: Configurer l'admin

Fichier: `abonnements/admin.py`

```python
from django.contrib import admin
from .models import (
    TypeAbonnement, Itineraire, MenuCantine,
    Abonnement, AbonnementBus, AbonnementCantine,
    PresenceCantine
)

@admin.register(TypeAbonnement)
class TypeAbonnementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'tarif_mensuel', 'tarif_trimestriel', 'tarif_annuel', 'actif')
    list_filter = ('actif', 'nom')
    search_fields = ('nom', 'description')

@admin.register(Itineraire)
class ItineraireAdmin(admin.ModelAdmin):
    list_display = ('nom', 'heure_depart_matin', 'heure_retour_soir', 'capacite', 'nombre_abonnes', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'quartiers')

@admin.register(MenuCantine)
class MenuCantineAdmin(admin.ModelAdmin):
    list_display = ('jour', 'semaine', 'date_menu', 'plat_principal', 'actif')
    list_filter = ('jour', 'semaine', 'actif')
    search_fields = ('plat_principal', 'entree', 'dessert')
    date_hierarchy = 'date_menu'

@admin.register(AbonnementBus)
class AbonnementBusAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'itineraire', 'duree', 'date_debut', 'date_fin', 'statut')
    list_filter = ('statut', 'duree', 'itineraire')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule')
    date_hierarchy = 'date_debut'
    autocomplete_fields = ['eleve']

@admin.register(AbonnementCantine)
class AbonnementCantineAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'duree', 'regime_alimentaire', 'date_debut', 'date_fin', 'statut')
    list_filter = ('statut', 'duree', 'regime_alimentaire')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule')
    date_hierarchy = 'date_debut'
    autocomplete_fields = ['eleve']

@admin.register(PresenceCantine)
class PresenceCantineAdmin(admin.ModelAdmin):
    list_display = ('abonnement', 'date', 'present', 'menu')
    list_filter = ('present', 'date')
    search_fields = ('abonnement__eleve__nom', 'abonnement__eleve__prenom')
    date_hierarchy = 'date'
```

### Étape 4: Créer les URLs

Fichier: `abonnements/urls.py`

```python
from django.urls import path
from . import views

app_name = 'abonnements'

urlpatterns = [
    # Bus
    path('bus/', views.liste_abonnements_bus, name='liste_bus'),
    path('bus/nouveau/', views.creer_abonnement_bus, name='creer_bus'),
    path('bus/<int:pk>/', views.detail_abonnement_bus, name='detail_bus'),
    path('bus/<int:pk>/modifier/', views.modifier_abonnement_bus, name='modifier_bus'),
    
    # Cantine
    path('cantine/', views.liste_abonnements_cantine, name='liste_cantine'),
    path('cantine/nouveau/', views.creer_abonnement_cantine, name='creer_cantine'),
    path('cantine/<int:pk>/', views.detail_abonnement_cantine, name='detail_cantine'),
    path('cantine/<int:pk>/modifier/', views.modifier_abonnement_cantine, name='modifier_cantine'),
    
    # Présences cantine
    path('cantine/presences/', views.presences_cantine, name='presences_cantine'),
    
    # Itinéraires
    path('itineraires/', views.liste_itineraires, name='liste_itineraires'),
    
    # Menus
    path('menus/', views.liste_menus, name='liste_menus'),
]
```

### Étape 5: Ajouter au projet

Fichier: `ecole_moderne/urls.py`

```python
urlpatterns = [
    # ... autres URLs
    path('abonnements/', include('abonnements.urls')),
]
```

---

## 🎯 Fonctionnalités

### Abonnements Bus

#### Création
- Sélection élève
- Choix itinéraire
- Durée (mensuel/trimestriel/annuel)
- Points montée/descente
- Contact urgence

#### Gestion
- Liste des abonnés par itinéraire
- Statut (actif/suspendu/expiré)
- Renouvellement automatique
- Génération tickets bus

### Abonnements Cantine

#### Création
- Sélection élève
- Durée
- Régime alimentaire
- Allergies

#### Gestion
- Liste des abonnés
- Suivi présences quotidiennes
- Menus de la semaine
- Statistiques

---

## 📊 Script d'Initialisation

Fichier: `initialiser_abonnements.py`

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from abonnements.models import TypeAbonnement, Itineraire
from datetime import time

# Types d'abonnements
types = [
    {
        'nom': 'BUS',
        'description': 'Transport scolaire',
        'tarif_mensuel': 50000,
        'tarif_trimestriel': 135000,
        'tarif_annuel': 450000
    },
    {
        'nom': 'CANTINE',
        'description': 'Repas à la cantine',
        'tarif_mensuel': 40000,
        'tarif_trimestriel': 108000,
        'tarif_annuel': 360000
    },
    {
        'nom': 'GARDERIE',
        'description': 'Garderie après les cours',
        'tarif_mensuel': 30000,
        'tarif_trimestriel': 81000,
        'tarif_annuel': 270000
    },
]

for type_data in types:
    TypeAbonnement.objects.get_or_create(
        nom=type_data['nom'],
        defaults=type_data
    )

# Itinéraires
itineraires = [
    {
        'nom': 'Itinéraire 1 - Centre-ville',
        'quartiers': 'Kaloum\nColéah\nAlmamya',
        'heure_depart_matin': time(7, 0),
        'heure_retour_soir': time(16, 30),
        'capacite': 40
    },
    {
        'nom': 'Itinéraire 2 - Matoto',
        'quartiers': 'Matoto\nSangoyah\nKipé',
        'heure_depart_matin': time(6, 45),
        'heure_retour_soir': time(16, 45),
        'capacite': 40
    },
    {
        'nom': 'Itinéraire 3 - Ratoma',
        'quartiers': 'Ratoma\nKoléah\nHamdallaye',
        'heure_depart_matin': time(7, 15),
        'heure_retour_soir': time(16, 15),
        'capacite': 35
    },
]

for itin_data in itineraires:
    Itineraire.objects.get_or_create(
        nom=itin_data['nom'],
        defaults=itin_data
    )

print("✅ Données d'abonnements initialisées!")
```

---

## 🧪 Tests

```bash
# Créer les migrations
python manage.py makemigrations abonnements

# Appliquer les migrations
python manage.py migrate abonnements

# Initialiser les données
python initialiser_abonnements.py

# Accéder à l'admin
http://127.0.0.1:8000/admin/abonnements/
```

---

## 📋 Checklist

- [x] Modèles créés
- [ ] Admin configuré
- [ ] Migrations créées
- [ ] Migrations appliquées
- [ ] URLs configurées
- [ ] Vues créées
- [ ] Templates créés
- [ ] Données initiales
- [ ] Tests effectués

---

**🎉 MODULE ABONNEMENTS PRÊT À ÊTRE CONFIGURÉ !**
