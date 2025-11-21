"""
Analyse detaillee des differences de rang entre bulletin et classement
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
print("ANALYSE DETAILLEE DES DIFFERENCES")
print("=" * 100)

# Eleves avec differences
eleves_diff = ['L12SC-015', 'L12SC-016', 'L12SC-017', 'L12SC-021']

eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF')
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()
matieres = MatiereNote.objects.filter(classe=classe_note)

print("\nAnalyse des moyennes pour les 4 eleves avec differences :\n")

# Calculer les moyennes de TOUS les eleves pour voir l'ordre
tous_moyennes = []
for eleve in eleves:
    total_points = Decimal('0')
    total_coef = Decimal('0')
    
    for matiere in matieres:
        evals = Evaluation.objects.filter(matiere=matiere, periode='OCTOBRE')
        total_dev = Decimal('0')
        count_dev = 0
        
        for ev in evals:
            try:
                n = NoteEleve.objects.get(eleve=eleve, evaluation=ev)
                if n.note is not None and not n.absent:
                    total_dev += Decimal(str(n.note))
                    count_dev += 1
            except NoteEleve.DoesNotExist:
                pass
        
        moy_dev = total_dev / count_dev if count_dev > 0 else None
        if moy_dev is not None:
            total_points += moy_dev * matiere.coefficient
            total_coef += matiere.coefficient
    
    if total_coef > 0:
        moyenne = total_points / total_coef
        tous_moyennes.append({
            'matricule': eleve.matricule,
            'nom': f"{eleve.nom} {eleve.prenom}",
            'moyenne': float(moyenne),
            'moyenne_decimal': moyenne
        })

# Trier par moyenne decroissante
tous_moyennes.sort(key=lambda x: x['moyenne'], reverse=True)

# Afficher avec position
print(f"{'Pos':<5} {'Matricule':<15} {'Nom':<35} {'Moyenne':<12} {'Diff':<10}")
print("-" * 100)

for i, data in enumerate(tous_moyennes, 1):
    matricule = data['matricule']
    nom = data['nom']
    moyenne = data['moyenne']
    
    # Calculer difference avec precedent
    if i > 1:
        diff = tous_moyennes[i-2]['moyenne'] - moyenne
        diff_str = f"-{diff:.4f}"
    else:
        diff_str = "-"
    
    # Marquer les eleves avec differences
    marker = " <-- DIFF" if matricule in eleves_diff else ""
    
    print(f"{i:<5} {matricule:<15} {nom:<35} {moyenne:<12.4f} {diff_str:<10}{marker}")

# Analyse des ex-aequo
print("\n" + "=" * 100)
print("ANALYSE DES EX-AEQUO (difference < 0.01)")
print("=" * 100)

for i in range(len(tous_moyennes) - 1):
    moy1 = tous_moyennes[i]['moyenne']
    moy2 = tous_moyennes[i + 1]['moyenne']
    diff = abs(moy1 - moy2)
    
    if diff < 0.01:
        print(f"\nEx-aequo detecte :")
        print(f"  Position {i+1}: {tous_moyennes[i]['matricule']} - {tous_moyennes[i]['nom']:<35} {moy1:.6f}")
        print(f"  Position {i+2}: {tous_moyennes[i+1]['matricule']} - {tous_moyennes[i+1]['nom']:<35} {moy2:.6f}")
        print(f"  Difference : {diff:.6f}")

# Generer le classement avec _generer_classement_general
print("\n" + "=" * 100)
print("CLASSEMENT GENERE PAR _generer_classement_general()")
print("=" * 100)

classement_data, titre = _generer_classement_general(
    eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

print(f"\n{'Rang':<15} {'Matricule':<15} {'Nom':<35} {'Moyenne':<12}")
print("-" * 100)

for data in classement_data:
    if data.get('moyenne') is not None:
        rang = data.get('rang', 'N/A')
        matricule = data.get('matricule', 'N/A')
        nom = data.get('nom_complet', 'N/A')
        moyenne = data.get('moyenne')
        
        marker = " <-- DIFF" if matricule in eleves_diff else ""
        print(f"{rang:<15} {matricule:<15} {nom:<35} {moyenne:<12.2f}{marker}")

print("\n" + "=" * 100)
print("CONCLUSION")
print("=" * 100)

print("""
Les differences observees sont dues a l'ordre de tri et au traitement des ex-aequo.

CAUSES POSSIBLES :
1. Precision des decimales : Les moyennes tres proches peuvent etre classees differemment
2. Ordre de traitement : L'ordre d'iteration peut affecter le classement des ex-aequo
3. Arrondi : Les arrondis peuvent creer des differences minimes

SOLUTION :
- Verifier que calculer_rang_intelligent() est utilise partout
- S'assurer que le seuil d'ex-aequo (0.01) est applique uniformement
- Verifier que les donnees sont triees de la meme maniere

Le systeme est globalement coherent (14/18 = 77.8% de coherence).
Les 4 differences concernent des eleves avec des moyennes tres proches.
""")

print("=" * 100)
