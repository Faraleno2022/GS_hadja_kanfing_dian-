#!/usr/bin/env python
"""
Test pour vérifier que les ex-aequo sont bien gérés avec la nouvelle logique
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.export_classement import _calculer_rangs

print("\n" + "="*80)
print("TEST : Vérifier la gestion des ex-aequo avec _calculer_rangs")
print("="*80)

# Créer des données de test avec ex-aequo
classement_test = [
    {'matricule': 'A', 'nom_complet': 'Élève A', 'moyenne': 18.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},
    {'matricule': 'B', 'nom_complet': 'Élève B', 'moyenne': 17.25, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},
    {'matricule': 'C', 'nom_complet': 'Élève C', 'moyenne': 15.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},
    {'matricule': 'D', 'nom_complet': 'Élève D', 'moyenne': 12.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},  # Ex-aequo
    {'matricule': 'E', 'nom_complet': 'Élève E', 'moyenne': 12.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},  # Ex-aequo
    {'matricule': 'F', 'nom_complet': 'Élève F', 'moyenne': 12.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},  # Ex-aequo
    {'matricule': 'G', 'nom_complet': 'Élève G', 'moyenne': 11.00, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},
    {'matricule': 'H', 'nom_complet': 'Élève H', 'moyenne': 10.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},
    {'matricule': 'I', 'nom_complet': 'Élève I', 'moyenne': 10.50, 'absent': False, 'pas_de_notes': False, 'nb_notes': 5},  # Ex-aequo
    {'matricule': 'J', 'nom_complet': 'Élève J', 'moyenne': None, 'absent': True, 'pas_de_notes': False, 'nb_notes': 0},  # Pas de notes
]

print("\nDonnées de test :")
for item in classement_test:
    if item['moyenne']:
        print(f"  {item['matricule']} : {item['moyenne']}")
    else:
        print(f"  {item['matricule']} : Pas de notes")

# Appliquer la fonction _calculer_rangs
classement_resultat = _calculer_rangs(classement_test)

print("\n" + "="*80)
print("Résultat après _calculer_rangs")
print("="*80)

print(f"\n{'Rang':<15} {'Matricule':<12} {'Nom':<20} {'Moyenne':<10}")
print("-" * 60)

for item in classement_resultat:
    if item['moyenne'] is not None:
        rang = item['rang']
        print(f"{rang}ème{'':<10} {item['matricule']:<12} {item['nom_complet']:<20} {item['moyenne']:<10.2f}")
    else:
        print(f"{'N/A':<15} {item['matricule']:<12} {item['nom_complet']:<20} {'Pas de notes':<10}")

print("\n" + "="*80)
print("VÉRIFICATION DES EX-AEQUO")
print("="*80)

# Vérifier les ex-aequo
print("\n✓ Vérification des rangs :")

# Élève A : 1er
assert classement_resultat[0]['rang'] == 1, "Élève A devrait être 1er"
print(f"  ✓ Élève A (18.50) : rang = 1 (correct)")

# Élève B : 2ème
assert classement_resultat[1]['rang'] == 2, "Élève B devrait être 2ème"
print(f"  ✓ Élève B (17.25) : rang = 2 (correct)")

# Élève C : 3ème
assert classement_resultat[2]['rang'] == 3, "Élève C devrait être 3ème"
print(f"  ✓ Élève C (15.50) : rang = 3 (correct)")

# Élève D : 4ème
assert classement_resultat[3]['rang'] == 4, "Élève D devrait être 4ème"
print(f"  ✓ Élève D (12.50) : rang = 4 (correct)")

# Élève E : 4ème (ex-aequo)
assert classement_resultat[4]['rang'] == 4, "Élève E devrait être 4ème (ex-aequo)"
print(f"  ✓ Élève E (12.50) : rang = 4 (ex-aequo - correct)")

# Élève F : 4ème (ex-aequo)
assert classement_resultat[5]['rang'] == 4, "Élève F devrait être 4ème (ex-aequo)"
print(f"  ✓ Élève F (12.50) : rang = 4 (ex-aequo - correct)")

# Élève G : 7ème (après 3 ex-aequo)
assert classement_resultat[6]['rang'] == 7, "Élève G devrait être 7ème"
print(f"  ✓ Élève G (11.00) : rang = 7 (correct - après 3 ex-aequo)")

# Élève H : 8ème
assert classement_resultat[7]['rang'] == 8, "Élève H devrait être 8ème"
print(f"  ✓ Élève H (10.50) : rang = 8 (correct)")

# Élève I : 8ème (ex-aequo)
assert classement_resultat[8]['rang'] == 8, "Élève I devrait être 8ème (ex-aequo)"
print(f"  ✓ Élève I (10.50) : rang = 8 (ex-aequo - correct)")

# Élève J : N/A (pas de notes)
assert classement_resultat[9]['rang'] == '-', "Élève J devrait avoir rang = '-'"
print(f"  ✓ Élève J (pas de notes) : rang = '-' (correct)")

print("\n" + "="*80)
print("RÉSUMÉ")
print("="*80)
print("✓ Tous les tests sont passés !")
print("✓ Les ex-aequo sont gérés correctement")
print("✓ Les rangs sont calculés correctement")
print("\nExemple d'affichage correct :")
print("  1er    - Élève A - 18,50")
print("  2ème   - Élève B - 17,25")
print("  3ème   - Élève C - 15,50")
print("  4ème   - Élève D - 12,50  ← Même rang")
print("  4ème   - Élève E - 12,50  ← Ex-aequo")
print("  4ème   - Élève F - 12,50  ← Ex-aequo")
print("  7ème   - Élève G - 11,00  ← Rang suivant (7ème, pas 5ème)")
print("  8ème   - Élève H - 10,50")
print("  8ème   - Élève I - 10,50  ← Ex-aequo")
print("\n🎉 Les ex-aequo sont maintenant correctement gérés !")
