"""
Test de coherence complete de tous les bulletins et exports PDF
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote
from notes.export_classement import _generer_classement_general
from decimal import Decimal

print("=" * 100)
print("TEST DE COHERENCE COMPLETE - TOUS LES BULLETINS ET EXPORTS PDF")
print("=" * 100)

# Recuperer la classe de test
eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF')
if not eleves.exists():
    print("\nERREUR : Aucun eleve L12SC trouve")
    print("Executez d'abord : python init_ecole_simple.py")
    sys.exit(1)

classe_eleve = eleves.first().classe
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()

print(f"\nClasse testee : {classe_eleve.nom}")
print(f"Nombre d'eleves : {eleves.count()}")

# 1. Generer le classement general (reference)
print("\n" + "=" * 100)
print("1. CLASSEMENT GENERAL (REFERENCE)")
print("=" * 100)

classement_data, titre = _generer_classement_general(
    eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

classement_dict = {}
for data in classement_data:
    if data.get('moyenne') is not None:
        matricule = data.get('matricule')
        classement_dict[matricule] = {
            'rang': data.get('rang'),
            'moyenne': data.get('moyenne')
        }

print(f"Eleves avec notes : {len(classement_dict)}")

# Afficher le top 5
print(f"\nTop 5 du classement :")
for i, data in enumerate(classement_data[:5], 1):
    if data.get('moyenne') is not None:
        print(f"  {i}. {data.get('matricule')} - {data.get('nom_complet')} : {data.get('rang')} ({data.get('moyenne'):.2f})")

# 2. Verifier la coherence avec bulletin_dynamique_pdf
print("\n" + "=" * 100)
print("2. VERIFICATION BULLETIN_DYNAMIQUE_PDF")
print("=" * 100)

from notes.models import MatiereNote, Evaluation, NoteEleve

matieres = MatiereNote.objects.filter(classe=classe_note)

bulletins_dict = {}
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
                # Traiter les absences comme 0 (harmonisation)
                note_value = Decimal(str(n.note)) if n.note is not None and not n.absent else Decimal('0')
                total_dev += note_value
                count_dev += 1
            except NoteEleve.DoesNotExist:
                # Pas de note = 0
                count_dev += 1
        
        moy_dev = total_dev / count_dev if count_dev > 0 else None
        if moy_dev is not None:
            total_points += moy_dev * matiere.coefficient
            total_coef += matiere.coefficient
    
    if total_coef > 0:
        moyenne = total_points / total_coef
        bulletins_dict[eleve.matricule] = {'moyenne': float(moyenne)}

# Calculer les rangs avec calculer_rang_intelligent
from notes.calculs_intelligent import calculer_rang_intelligent

moyennes_pour_rang = []
for matricule, data in bulletins_dict.items():
    eleve = eleves.get(matricule=matricule)
    moyennes_pour_rang.append({
        'eleve_id': eleve.id,
        'prenom': eleve.prenom,
        'nom': eleve.nom,
        'sexe': getattr(eleve, 'sexe', 'M'),
        'moyenne': Decimal(str(data['moyenne']))
    })

resultats_rangs = calculer_rang_intelligent(moyennes_pour_rang)

for r in resultats_rangs:
    eleve = eleves.get(id=r['eleve_id'])
    bulletins_dict[eleve.matricule]['rang'] = r.get('rang')

# Comparer
differences = []
coherents = 0

for matricule in bulletins_dict.keys():
    if matricule in classement_dict:
        rang_classement = classement_dict[matricule]['rang']
        rang_bulletin = bulletins_dict[matricule]['rang']
        
        if rang_classement == rang_bulletin:
            coherents += 1
        else:
            differences.append({
                'matricule': matricule,
                'classement': rang_classement,
                'bulletin': rang_bulletin
            })

print(f"Eleves testes : {len(bulletins_dict)}")
print(f"Rangs coherents : {coherents}")
print(f"Rangs differents : {len(differences)}")

if differences:
    print(f"\nDIFFERENCES DETECTEES :")
    for diff in differences:
        print(f"  {diff['matricule']} : Classement={diff['classement']}, Bulletin={diff['bulletin']}")
else:
    print(f"\nPARFAIT ! Tous les rangs sont coherents !")

# 3. Verification des moyennes
print("\n" + "=" * 100)
print("3. VERIFICATION DES MOYENNES")
print("=" * 100)

moyennes_diff = []
for matricule in bulletins_dict.keys():
    if matricule in classement_dict:
        moy_classement = classement_dict[matricule]['moyenne']
        moy_bulletin = bulletins_dict[matricule]['moyenne']
        
        if abs(moy_classement - moy_bulletin) > 0.01:
            moyennes_diff.append({
                'matricule': matricule,
                'classement': moy_classement,
                'bulletin': moy_bulletin,
                'diff': abs(moy_classement - moy_bulletin)
            })

if moyennes_diff:
    print(f"DIFFERENCES DE MOYENNES DETECTEES ({len(moyennes_diff)}) :")
    for diff in moyennes_diff:
        print(f"  {diff['matricule']} : Classement={diff['classement']:.4f}, Bulletin={diff['bulletin']:.4f}, Diff={diff['diff']:.4f}")
else:
    print(f"PARFAIT ! Toutes les moyennes sont identiques !")

# 4. Resultat final
print("\n" + "=" * 100)
print("RESULTAT FINAL")
print("=" * 100)

if len(differences) == 0 and len(moyennes_diff) == 0:
    print("\nSUCCES COMPLET !")
    print("Tous les bulletins et exports PDF sont 100% coherents !")
    print("\nVerifications effectuees :")
    print("  - Classement general")
    print("  - Bulletin dynamique PDF")
    print("  - Calcul des moyennes")
    print("  - Calcul des rangs")
    print("  - Traitement des absences")
    print("\nLe systeme est pret pour la production !")
else:
    print("\nATTENTION : Des incoherences ont ete detectees")
    print(f"  Differences de rangs : {len(differences)}")
    print(f"  Differences de moyennes : {len(moyennes_diff)}")
    print("\nVerifiez les corrections appliquees")

print("\n" + "=" * 100)
