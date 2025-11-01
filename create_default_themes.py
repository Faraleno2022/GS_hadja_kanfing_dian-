#!/usr/bin/env python
"""Script pour créer les thèmes de couleurs par défaut pour les bulletins"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ThemeBulletin

print("=" * 80)
print("CRÉATION DES THÈMES PAR DÉFAUT")
print("=" * 80)

# Thème 1: Classique (Bleu)
print("\n1. Création du thème Classique...")
theme_classique, created = ThemeBulletin.objects.get_or_create(
    nom="Classique",
    defaults={
        'couleur_primaire': '#2c3e50',
        'couleur_secondaire': '#3498db',
        'couleur_accent': '#e74c3c',
        'couleur_texte_principal': '#2c3e50',
        'couleur_texte_secondaire': '#7f8c8d',
        'couleur_fond_header': '#2c3e50',
        'couleur_fond_tableau': '#ecf0f1',
        'couleur_fond_carte': '#ffffff',
        'couleur_bordure': '#bdc3c7',
        'couleur_mention_tb': '#27ae60',
        'couleur_mention_bien': '#3498db',
        'couleur_mention_ab': '#f39c12',
        'couleur_mention_passable': '#e67e22',
        'couleur_mention_insuffisant': '#e74c3c',
        'actif': True,
        'par_defaut': True
    }
)
if created:
    print("   ✅ Thème Classique créé")
else:
    print("   ℹ️  Thème Classique existe déjà")

# Thème 2: Vert Nature
print("\n2. Création du thème Vert Nature...")
theme_vert, created = ThemeBulletin.objects.get_or_create(
    nom="Vert Nature",
    defaults={
        'couleur_primaire': '#27ae60',
        'couleur_secondaire': '#2ecc71',
        'couleur_accent': '#f39c12',
        'couleur_texte_principal': '#2c3e50',
        'couleur_texte_secondaire': '#7f8c8d',
        'couleur_fond_header': '#27ae60',
        'couleur_fond_tableau': '#e8f8f5',
        'couleur_fond_carte': '#ffffff',
        'couleur_bordure': '#a9dfbf',
        'couleur_mention_tb': '#27ae60',
        'couleur_mention_bien': '#2ecc71',
        'couleur_mention_ab': '#f39c12',
        'couleur_mention_passable': '#e67e22',
        'couleur_mention_insuffisant': '#e74c3c',
        'actif': True,
        'par_defaut': False
    }
)
if created:
    print("   ✅ Thème Vert Nature créé")
else:
    print("   ℹ️  Thème Vert Nature existe déjà")

# Thème 3: Violet Royal
print("\n3. Création du thème Violet Royal...")
theme_violet, created = ThemeBulletin.objects.get_or_create(
    nom="Violet Royal",
    defaults={
        'couleur_primaire': '#8e44ad',
        'couleur_secondaire': '#9b59b6',
        'couleur_accent': '#e74c3c',
        'couleur_texte_principal': '#2c3e50',
        'couleur_texte_secondaire': '#7f8c8d',
        'couleur_fond_header': '#8e44ad',
        'couleur_fond_tableau': '#f4ecf7',
        'couleur_fond_carte': '#ffffff',
        'couleur_bordure': '#d7bde2',
        'couleur_mention_tb': '#8e44ad',
        'couleur_mention_bien': '#9b59b6',
        'couleur_mention_ab': '#f39c12',
        'couleur_mention_passable': '#e67e22',
        'couleur_mention_insuffisant': '#e74c3c',
        'actif': True,
        'par_defaut': False
    }
)
if created:
    print("   ✅ Thème Violet Royal créé")
else:
    print("   ℹ️  Thème Violet Royal existe déjà")

# Thème 4: Orange Dynamique
print("\n4. Création du thème Orange Dynamique...")
theme_orange, created = ThemeBulletin.objects.get_or_create(
    nom="Orange Dynamique",
    defaults={
        'couleur_primaire': '#e67e22',
        'couleur_secondaire': '#f39c12',
        'couleur_accent': '#c0392b',
        'couleur_texte_principal': '#2c3e50',
        'couleur_texte_secondaire': '#7f8c8d',
        'couleur_fond_header': '#e67e22',
        'couleur_fond_tableau': '#fef5e7',
        'couleur_fond_carte': '#ffffff',
        'couleur_bordure': '#f8c471',
        'couleur_mention_tb': '#27ae60',
        'couleur_mention_bien': '#3498db',
        'couleur_mention_ab': '#f39c12',
        'couleur_mention_passable': '#e67e22',
        'couleur_mention_insuffisant': '#c0392b',
        'actif': True,
        'par_defaut': False
    }
)
if created:
    print("   ✅ Thème Orange Dynamique créé")
else:
    print("   ℹ️  Thème Orange Dynamique existe déjà")

print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)
themes = ThemeBulletin.objects.all()
print(f"\nNombre total de thèmes: {themes.count()}")
for theme in themes:
    statut = []
    if theme.actif:
        statut.append("Actif")
    if theme.par_defaut:
        statut.append("Par défaut")
    statut_str = ", ".join(statut) if statut else "Inactif"
    print(f"  - {theme.nom}: {statut_str}")

print("\n✅ Thèmes créés avec succès !")
print("\nPour utiliser un thème:")
print("  1. Aller sur /admin/notes/themebulletin/")
print("  2. Modifier un thème")
print("  3. Cocher 'Par défaut' pour l'activer")
print("  4. Enregistrer")
print("\n" + "=" * 80)
