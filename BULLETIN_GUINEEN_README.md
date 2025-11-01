# Bulletin de Notes Guinéen - Guide d'Utilisation

## Vue d'ensemble

Le système de bulletin guinéen a été intégré dans votre application Django de gestion scolaire. Il permet de gérer les notes mensuelles (Octobre à Mai) et les compositions selon le système éducatif guinéen, avec support pour les systèmes semestriel et trimestriel.

## Nouveaux Modèles

### 1. NoteMensuelle
Stocke les notes mensuelles des élèves pour chaque matière.

**Champs:**
- `eleve`: Référence à l'élève
- `matiere`: Référence à la matière
- `mois`: Mois de la note (OCTOBRE à MAI)
- `annee_scolaire`: Année scolaire (ex: 2024-2025)
- `note`: Note sur 20
- `absent`: Booléen pour marquer l'absence

### 2. CompositionNote
Stocke les notes de composition pour chaque période.

**Champs:**
- `eleve`: Référence à l'élève
- `matiere`: Référence à la matière
- `periode`: Période (SEMESTRE_1, SEMESTRE_2, TRIMESTRE_1, TRIMESTRE_2, TRIMESTRE_3)
- `annee_scolaire`: Année scolaire
- `note`: Note sur 20
- `absent`: Booléen pour marquer l'absence

## Principe de Calcul

### Système Semestriel

**Semestre 1:**
- Note de Cours = (Octobre + Novembre + Décembre + Janvier) ÷ 4
- Note Semestre 1 = (Note de Cours + Composition S1) ÷ 2

**Semestre 2:**
- Note de Cours = (Février + Mars + Avril + Mai) ÷ 4
- Note Semestre 2 = (Note de Cours + Composition S2) ÷ 2

**Moyenne Annuelle:**
- Moyenne Annuelle = (Note Semestre 1 + Note Semestre 2) ÷ 2

### Système Trimestriel

**Trimestre 1:**
- Note de Cours = (Octobre + Novembre + Décembre) ÷ 3
- Note Trimestre 1 = (Note de Cours + Composition T1) ÷ 2

**Trimestre 2:**
- Note de Cours = (Janvier + Février + Mars) ÷ 3
- Note Trimestre 2 = (Note de Cours + Composition T2) ÷ 2

**Trimestre 3:**
- Note de Cours = (Avril + Mai) ÷ 2
- Note Trimestre 3 = (Note de Cours + Composition T3) ÷ 2

**Moyenne Annuelle:**
- Moyenne Annuelle = (Trimestre 1 + Trimestre 2 + Trimestre 3) ÷ 3

## Utilisation

### 1. Accès au Bulletin Guinéen

Accédez au bulletin via l'URL: `/notes/bulletin-guineen/`

### 2. Saisie des Notes

#### Via l'Interface Admin Django

1. Connectez-vous à l'admin Django: `/admin/`
2. Allez dans **Notes > Notes mensuelles** pour saisir les notes mensuelles
3. Allez dans **Notes > Notes de composition** pour saisir les compositions

#### Champs requis pour NoteMensuelle:
- Élève
- Matière
- Mois (sélectionner parmi OCTOBRE à MAI)
- Année scolaire (format: 2024-2025)
- Note (sur 20)
- Absent (cocher si l'élève était absent)

#### Champs requis pour CompositionNote:
- Élève
- Matière
- Période (SEMESTRE_1, SEMESTRE_2, etc.)
- Année scolaire
- Note (sur 20)
- Absent (cocher si l'élève était absent)

### 3. Génération du Bulletin

1. Accédez à `/notes/bulletin-guineen/`
2. Sélectionnez une classe
3. Choisissez le système (Semestriel ou Trimestriel)
4. Le bulletin s'affiche avec toutes les notes et calculs automatiques
5. Utilisez le bouton "Imprimer" pour imprimer le bulletin

## Fonctionnalités

### ✅ Implémenté

- ✅ Modèles de données pour notes mensuelles et compositions
- ✅ Interface admin pour saisie des notes
- ✅ Vue pour affichage du bulletin
- ✅ Template HTML avec design professionnel
- ✅ Calculs automatiques selon le système choisi
- ✅ Support impression (format A4 paysage)
- ✅ Système semestriel et trimestriel
- ✅ Affichage des formules de calcul
- ✅ Sections pour signatures (Professeur, Directeur, Parent)

### 🔄 À Développer (Optionnel)

- Génération PDF du bulletin guinéen
- Saisie en masse des notes mensuelles
- Import/Export Excel des notes
- Statistiques par classe
- Graphiques de progression
- Envoi automatique par email

## Structure des Fichiers

```
notes/
├── models.py                    # Modèles NoteMensuelle et CompositionNote
├── views.py                     # Vue bulletin_guineen()
├── urls.py                      # Route /bulletin-guineen/
├── admin.py                     # Configuration admin
└── migrations/
    └── 0003_compositionnote_notemensuelle.py

templates/notes/
└── bulletin_guineen.html        # Template du bulletin
```

## Mentions selon la Moyenne

- **Excellent**: ≥ 16/20
- **Très Bien**: 14-15.99/20
- **Bien**: 12-13.99/20
- **Assez Bien**: 10-11.99/20
- **Insuffisant**: < 10/20

## Support

Pour toute question ou problème:
1. Vérifiez que les migrations sont appliquées: `python manage.py migrate`
2. Vérifiez que les notes sont bien saisies dans l'admin
3. Assurez-vous que l'année scolaire correspond entre la classe et les notes

## Exemple de Données de Test

Pour tester le système, vous pouvez créer des notes mensuelles et de composition via l'admin Django pour un élève dans une classe donnée.

**Exemple pour un élève en Mathématiques:**
- Octobre: 14/20
- Novembre: 15/20
- Décembre: 13/20
- Janvier: 16/20
- Composition Semestre 1: 15/20

Le système calculera automatiquement:
- Note de Cours S1 = (14+15+13+16)/4 = 14.5
- Note Semestre 1 = (14.5+15)/2 = 14.75

---

**Version:** 1.0  
**Date:** Octobre 2024  
**Auteur:** Système de Gestion Scolaire
