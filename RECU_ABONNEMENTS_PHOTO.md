# 📄 Reçus d'Abonnements avec Photo de l'Élève

## Vue d'ensemble

Les reçus PDF pour les abonnements bus et cantine incluent maintenant la photo de l'élève pour une meilleure identification et un aspect plus professionnel.

## Fonctionnalités

### 🚌 Reçu Abonnement Bus

**URL** : `/bus/<abo_id>/recu/pdf/`

**Contenu du reçu** :
- Logo de l'école (en haut à gauche)
- Photo de l'élève (en haut à droite) ou placeholder avec initiales
- Titre professionnel : "REÇU ABONNEMENT BUS SCOLAIRE"
- Nom de l'école
- Informations de l'élève :
  - Nom complet et matricule
  - Classe
  - École
- Détails de l'abonnement :
  - Périodicité (Mensuel, Annuel, Tranche 1/2/3)
  - Montant (en GNF)
  - Date de début
  - Date d'expiration
  - Durée en jours
  - Zone
  - Point d'arrêt
  - Contact parent

### 🍽️ Reçu Abonnement Cantine

**URL** : `/bus/cantine/<abo_id>/recu/pdf/`

**Contenu du reçu** :
- Logo de l'école (en haut à gauche)
- Photo de l'élève (en haut à droite) ou placeholder avec initiales
- Titre professionnel : "REÇU ABONNEMENT CANTINE SCOLAIRE"
- Nom de l'école
- Informations de l'élève :
  - Nom complet et matricule
  - Classe
  - École
- Détails de l'abonnement :
  - Type de repas (Déjeuner, Goûter, Complet)
  - Périodicité (Journalier, Hebdomadaire, Mensuel, Trimestriel, Annuel)
  - Montant (en GNF)
  - Date de début
  - Date d'expiration
  - Durée en jours
  - Régime alimentaire (si spécifié)
  - Allergies (si spécifiées)
  - Contact parent
- Date d'émission du reçu
- Zone de signature et cachet

## Gestion de la Photo

### Photo Disponible
- La photo de l'élève est affichée dans un cadre de 100x100 pixels
- L'aspect ratio est préservé
- Le nom complet de l'élève est affiché sous la photo

### Photo Non Disponible
- Un placeholder élégant est généré automatiquement
- Affiche les initiales de l'élève (2 premières lettres)
- Cadre avec coins arrondis
- Texte "Pas de photo" en petit
- Nom complet de l'élève sous le placeholder

## Architecture Technique

### Backend

#### Bus (views.py)
```python
@login_required
@require_school_object(model=AbonnementBus, pk_kwarg='abo_id', field_path='eleve__classe__ecole')
def generer_recu_abonnement_pdf(request, abo_id):
    """Génère un reçu PDF pour un abonnement bus avec photo de l'élève"""
```

#### Cantine (views_cantine.py)
```python
@login_required
@require_school_object(model=AbonnementCantine, pk_kwarg='abo_id', field_path='eleve__classe__ecole')
def generer_recu_cantine_pdf(request, abo_id):
    """Génère un reçu PDF pour un abonnement cantine avec photo de l'élève"""
```

### Sécurité

- **Authentification requise** : `@login_required`
- **Vérification école** : `@require_school_object` garantit que l'utilisateur ne peut accéder qu'aux abonnements de son école
- **Filigrane** : Logo de l'école en filigrane pour éviter les falsifications
- **Gestion des erreurs** : Fallback gracieux si la photo ou le logo n'est pas disponible

### Dépendances

- **ReportLab** : Génération de PDF
- **Pillow** : Traitement des images
- Django >= 3.2

## Utilisation

### Depuis l'Interface Web

1. **Bus** : Accéder à la liste des abonnements bus
2. Cliquer sur le bouton "Reçu PDF" pour un abonnement
3. Le PDF s'ouvre dans le navigateur ou se télécharge

**Cantine** : Même processus depuis la liste des abonnements cantine

### Depuis le Code

```python
# Générer un reçu bus
from django.urls import reverse
url = reverse('bus:recu_pdf', kwargs={'abo_id': 123})

# Générer un reçu cantine
url = reverse('bus:recu_cantine_pdf', kwargs={'abo_id': 456})
```

### Via API/Lien Direct

```bash
# Reçu bus
GET /bus/123/recu/pdf/

# Reçu cantine
GET /bus/cantine/456/recu/pdf/
```

## Configuration

### Upload de Photos

Les photos des élèves doivent être uploadées via :
- Le formulaire d'ajout/modification d'élève
- L'interface d'administration Django

**Chemin de stockage** : `media/eleves/photos/`

### Logo de l'École

Le logo de l'école peut être configuré :
1. Via l'administration Django (modèle `Ecole`)
2. Fallback automatique vers `static/logos/logo.png`

## Exemples de Mise en Page

### Structure du Reçu

```
┌─────────────────────────────────────────────┐
│  [Logo École]      REÇU ABONNEMENT      [Photo] │
│                    Nom École                    │
├─────────────────────────────────────────────┤
│                                                 │
│  Élève : Prénom NOM (Matricule)                │
│  Classe : 6ème A                                │
│  École : Groupe Scolaire XYZ                    │
│  Type : Mensuel                                 │
│  Montant : 150 000 GNF                          │
│  Début : 01/09/2024                             │
│  Expiration : 30/09/2024                        │
│  Durée : 30 jours                               │
│  Zone : Quartier ABC                            │
│  Point d'arrêt : Marché Central                 │
│  Contact parent : +224 XXX XXX XXX              │
│                                                 │
│  Reçu émis le 02/11/2025                        │
│                                                 │
│                    Signature et cachet          │
│                    ___________________          │
└─────────────────────────────────────────────┘
```

## Améliorations Apportées

### ✅ Avant
- Reçu simple sans photo
- Titre basique
- Pas de logo d'école

### ✨ Après
- Photo de l'élève ou placeholder élégant
- Logo de l'école
- Titre professionnel
- Mise en page améliorée
- Informations plus complètes
- Zone de signature
- Date d'émission

## Tests

### Test Manuel

1. Créer un abonnement bus/cantine pour un élève
2. Uploader une photo pour l'élève (optionnel)
3. Générer le reçu PDF
4. Vérifier :
   - ✅ Photo affichée correctement (ou placeholder)
   - ✅ Logo de l'école présent
   - ✅ Toutes les informations affichées
   - ✅ Mise en page professionnelle

### Test Sans Photo

1. Créer un abonnement pour un élève sans photo
2. Générer le reçu
3. Vérifier :
   - ✅ Placeholder avec initiales
   - ✅ Texte "Pas de photo"
   - ✅ Nom de l'élève sous le placeholder

## Dépannage

### La photo ne s'affiche pas
- Vérifier que le fichier photo existe dans `media/eleves/photos/`
- Vérifier les permissions de lecture du fichier
- Vérifier que Pillow est installé : `pip install Pillow`

### Le logo ne s'affiche pas
- Vérifier que le logo est configuré pour l'école
- Vérifier le fallback : `static/logos/logo.png`
- Vérifier que `collectstatic` a été exécuté

### Erreur ReportLab
```bash
pip install reportlab
```

### Erreur de permissions
- Vérifier que l'utilisateur a accès à l'école de l'abonnement
- Le décorateur `@require_school_object` bloque l'accès non autorisé

## Bonnes Pratiques

### Photos des Élèves
- **Format recommandé** : JPEG ou PNG
- **Taille recommandée** : 300x300 pixels minimum
- **Poids maximum** : 2 MB
- **Fond** : Uni de préférence

### Logo de l'École
- **Format** : PNG avec transparence
- **Taille** : 200x200 pixels minimum
- **Qualité** : Haute résolution pour l'impression

## Changelog

### Version 1.0 (2025-11-02)
- ✨ Ajout de la photo de l'élève sur les reçus bus
- ✨ Ajout de la photo de l'élève sur les reçus cantine
- 🎨 Amélioration de la mise en page
- 🔒 Placeholder élégant si pas de photo
- 📝 Logo de l'école en en-tête
- 🖊️ Zone de signature et cachet
- 📅 Date d'émission du reçu
