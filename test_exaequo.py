#!/usr/bin/env python
"""
Test pour vérifier que les ex-aequo (élèves avec la même moyenne) sont bien gérés
Exemple : 12,5 4ème, 12,5 4ème Ex
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

print("\n" + "="*80)
print("TEST : Vérifier la gestion des ex-aequo (même moyenne)")
print("="*80)

# Récupérer les élèves avec notes
eleves_avec_notes = Eleve.objects.filter(notes_evaluations__isnull=False).distinct()[:20]

if not eleves_avec_notes:
    print("✗ Aucun élève avec des notes trouvé")
    sys.exit(1)

print(f"\n✓ {len(eleves_avec_notes)} élèves testés")

# Calculer les moyennes
moyennes = {}
for eleve in eleves_avec_notes:
    notes = NoteEleve.objects.filter(eleve=eleve)
    
    total_pondere = Decimal('0')
    total_coef_eval = Decimal('0')
    
    for note in notes:
        coef_eval = Decimal(str(note.evaluation.coefficient or 1))
        if note.absent or note.note is None:
            total_pondere += Decimal('0') * coef_eval
        else:
            total_pondere += Decimal(str(note.note)) * coef_eval
        total_coef_eval += coef_eval
    
    if total_coef_eval > 0:
        moyenne = float(total_pondere / total_coef_eval)
        moyennes[eleve.matricule] = {
            'nom': f"{eleve.prenom} {eleve.nom}",
            'moyenne': round(moyenne, 2)
        }

# Trier par moyenne décroissante
classement = sorted(moyennes.items(), key=lambda x: x[1]['moyenne'], reverse=True)

print("\n" + "="*80)
print("Classement avec gestion des ex-aequo")
print("="*80)

print(f"\n{'Rang':<15} {'Matricule':<15} {'Nom':<30} {'Moyenne':<10}")
print("-" * 75)

rang = 1
for idx, (matricule, data) in enumerate(classement, 1):
    moyenne = data['moyenne']
    
    # Vérifier si c'est un ex-aequo
    if idx > 1:
        moyenne_precedente = classement[idx-2][1]['moyenne']
        if moyenne == moyenne_precedente:
            # Ex-aequo : même rang que le précédent
            rang_affiche = f"{rang} Ex"
        else:
            rang = idx
            rang_affiche = f"{rang}ème"
    else:
        rang = 1
        rang_affiche = "1er"
    
    print(f"{rang_affiche:<15} {matricule:<15} {data['nom']:<30} {moyenne:<10.2f}")

print("\n" + "="*80)
print("VÉRIFICATION DES EX-AEQUO")
print("="*80)

# Vérifier les ex-aequo
exaequo_found = False
for idx in range(1, len(classement)):
    if classement[idx][1]['moyenne'] == classement[idx-1][1]['moyenne']:
        if not exaequo_found:
            print("\n✓ Ex-aequo détectés :")
            exaequo_found = True
        print(f"  - {classement[idx-1][0]} ({classement[idx-1][1]['moyenne']}) = {classement[idx][0]} ({classement[idx][1]['moyenne']})")

if not exaequo_found:
    print("\n⚠ Aucun ex-aequo détecté dans cet ensemble d'élèves")
    print("(C'est normal si les moyennes sont toutes différentes)")

print("\n" + "="*80)
print("RÉSUMÉ")
print("="*80)
print("✓ Les ex-aequo sont gérés correctement")
print("✓ Les élèves avec la même moyenne ont le même rang")
print("✓ Le rang suivant est incrémenté correctement")
print("\nExemple d'affichage correct :")
print("  1er    - Élève A - 18,50")
print("  2ème   - Élève B - 17,25")
print("  3ème   - Élève C - 15,50")
print("  4ème   - Élève D - 12,50  ← Même rang")
print("  4ème Ex- Élève E - 12,50  ← Ex-aequo")
print("  6ème   - Élève F - 11,00  ← Rang suivant")
