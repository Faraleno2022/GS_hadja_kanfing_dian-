"""
Debug des moyennes pour identifier la source des differences
"""
import os
import sys
import django
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from notes.export_classement import _generer_classement_general

print("=" * 100)
print("DEBUG DES MOYENNES - COMPARAISON DETAILLEE")
print("=" * 100)

# Eleves avec differences
eleves_diff = ['L12SC-015', 'L12SC-016', 'L12SC-017', 'L12SC-021']

eleves = Eleve.objects.filter(matricule__in=eleves_diff).order_by('matricule')
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()
matieres = MatiereNote.objects.filter(classe=classe_note)

print(f"\nAnalyse des {len(eleves_diff)} eleves avec differences\n")

for eleve in eleves:
    print("=" * 100)
    print(f"ELEVE : {eleve.matricule} - {eleve.nom} {eleve.prenom}")
    print("=" * 100)
    
    total_points = Decimal('0')
    total_coef = Decimal('0')
    
    print(f"\n{'Matiere':<20} {'Note':<10} {'Absent':<10} {'Coef':<10} {'Points':<10}")
    print("-" * 70)
    
    for matiere in matieres:
        evals = Evaluation.objects.filter(matiere=matiere, periode='OCTOBRE')
        
        total_dev = Decimal('0')
        count_dev = 0
        absent = False
        
        for ev in evals:
            try:
                n = NoteEleve.objects.get(eleve=eleve, evaluation=ev)
                if n.absent or n.note is None:
                    absent = True
                    note_value = Decimal('0')
                else:
                    note_value = Decimal(str(n.note))
                
                total_dev += note_value
                count_dev += 1
            except NoteEleve.DoesNotExist:
                # Pas de note = 0
                count_dev += 1
        
        moy_mat = total_dev / count_dev if count_dev > 0 else Decimal('0')
        points = moy_mat * matiere.coefficient
        
        total_points += points
        total_coef += matiere.coefficient
        
        absent_str = "OUI" if absent else "NON"
        print(f"{matiere.nom:<20} {float(moy_mat):<10.2f} {absent_str:<10} {float(matiere.coefficient):<10.1f} {float(points):<10.2f}")
    
    moyenne_finale = total_points / total_coef if total_coef > 0 else Decimal('0')
    
    print("-" * 70)
    print(f"{'TOTAL':<20} {'':<10} {'':<10} {float(total_coef):<10.1f} {float(total_points):<10.2f}")
    print(f"\nMOYENNE GENERALE : {float(moyenne_finale):.4f}")
    print()

# Maintenant generer le classement et voir les moyennes
print("\n" + "=" * 100)
print("CLASSEMENT GENERAL (toutes les moyennes)")
print("=" * 100)

tous_eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF')
classement_data, titre = _generer_classement_general(
    tous_eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

print(f"\n{'Rang':<10} {'Matricule':<15} {'Nom':<35} {'Moyenne':<10}")
print("-" * 80)

for data in classement_data:
    if data.get('moyenne') is not None:
        rang = data.get('rang', 'N/A')
        matricule = data.get('matricule', 'N/A')
        nom = data.get('nom_complet', 'N/A')
        moyenne = data.get('moyenne')
        
        marker = " <-- DIFF" if matricule in eleves_diff else ""
        print(f"{rang:<10} {matricule:<15} {nom:<35} {moyenne:<10.2f}{marker}")

print("\n" + "=" * 100)
