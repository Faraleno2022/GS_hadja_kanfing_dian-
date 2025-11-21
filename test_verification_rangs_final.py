"""
Script de vérification finale des rangs
Teste les 3 sources : Classement, Export, Bulletin
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote, NoteEleve
from notes.export_classement import _generer_classement_general
from notes.calculs_intelligent import formater_rang_intelligent

print("\n" + "="*80)
print("TEST DE VÉRIFICATION FINALE DES RANGS")
print("="*80)

# Trouver l'élève LOUAMMOU Jean David
eleve = Eleve.objects.filter(
    nom__icontains="LOUAMMOU", 
    prenom__icontains="Jean", 
    statut='ACTIF'
).first()

if not eleve:
    print("❌ Élève LOUAMMOU Jean David non trouvé")
    sys.exit(1)

print(f"\n✅ Élève trouvé : {eleve.nom} {eleve.prenom} ({eleve.matricule})")
print(f"   Sexe : {getattr(eleve, 'sexe', 'M')}")

# Récupérer les notes pour trouver la ClasseNote
notes = NoteEleve.objects.filter(eleve=eleve, evaluation__periode='OCTOBRE')
if not notes.exists():
    print("❌ Aucune note trouvée pour OCTOBRE")
    sys.exit(1)

classe_note = notes.first().evaluation.matiere.classe
print(f"   ClasseNote : {classe_note.nom}")

# Récupérer tous les élèves de la classe
eleves = Eleve.objects.filter(classe=eleve.classe, statut='ACTIF')
total_eleves = eleves.count()
print(f"   Effectif : {total_eleves} élèves")

# Générer le classement
classement_data, _ = _generer_classement_general(eleves, classe_note, 'mensuelle', 'OCTOBRE')

print("\n" + "-"*80)
print("TEST 1 : CLASSEMENT GÉNÉRAL (Export)")
print("-"*80)

for data in classement_data[:3]:  # Top 3
    print(f"{data.get('rang'):12} | {data.get('matricule'):12} | {data.get('nom_complet'):30} | {data.get('moyenne'):.2f}")

# Trouver LOUAMMOU dans le classement
louammou_data = None
for data in classement_data:
    if data.get('matricule') == eleve.matricule:
        louammou_data = data
        break

if louammou_data:
    print(f"\n✅ LOUAMMOU Jean David trouvé dans le classement")
    print(f"   Rang affiché : {louammou_data.get('rang')}")
    print(f"   Rang numérique : {louammou_data.get('rang_num')}")
    print(f"   Moyenne : {louammou_data.get('moyenne'):.2f}")
    
    # Vérifier le format
    rang_str = louammou_data.get('rang')
    if '/' in rang_str:
        print(f"   ✅ Format avec total : {rang_str}")
    else:
        print(f"   ✅ Format sans total : {rang_str}")

print("\n" + "-"*80)
print("TEST 2 : FONCTION formater_rang_intelligent")
print("-"*80)

rang_num = louammou_data.get('rang_num') if louammou_data else 10
sexe = getattr(eleve, 'sexe', 'M')

# Test avec total
rang_avec_total = formater_rang_intelligent(rang_num, sexe, total_eleves)
print(f"Avec total (rang={rang_num}, sexe={sexe}, total={total_eleves})")
print(f"   Résultat : {rang_avec_total}")

# Test sans total
rang_sans_total = formater_rang_intelligent(rang_num, sexe)
print(f"\nSans total (rang={rang_num}, sexe={sexe})")
print(f"   Résultat : {rang_sans_total}")

print("\n" + "-"*80)
print("TEST 3 : VÉRIFICATION DU CODE views.py")
print("-"*80)

# Lire le code pour vérifier
import inspect
from notes.views import consulter_notes

source = inspect.getsource(consulter_notes)
if "formater_rang_intelligent(rang_num, sexe)" in source:
    print("✅ Code consulter_notes : Utilise formater_rang_intelligent SANS total")
elif "formater_rang_intelligent(rang_num, sexe, total_eleves_avec_moyenne)" in source:
    print("❌ Code consulter_notes : Utilise formater_rang_intelligent AVEC total")
else:
    print("⚠️  Code consulter_notes : Format non détecté")

print("\n" + "="*80)
print("RÉSUMÉ DES TESTS")
print("="*80)

print("\n📊 Format attendu selon la source :")
print("   - Classement web (consulter_notes) : 10ème (SANS /18)")
print("   - Export PDF/Excel classement : 10ème/18 (AVEC /18)")
print("   - Bulletin PDF : Rang: 10ème/18 (AVEC /18)")

print("\n📋 Format actuel détecté :")
if louammou_data:
    rang_export = louammou_data.get('rang')
    print(f"   - Export classement : {rang_export}")
    
print(f"   - Fonction avec total : {rang_avec_total}")
print(f"   - Fonction sans total : {rang_sans_total}")

print("\n" + "="*80)
print("Pour tester sur le web :")
print("1. Classement : https://www.myschoolgn.space/notes/consulter/")
print("2. Export PDF : Cliquer sur 'Exporter Classement' → PDF")
print("3. Bulletin : https://www.myschoolgn.space/notes/bulletin-dynamique/")
print("="*80 + "\n")
