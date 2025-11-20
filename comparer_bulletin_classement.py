"""
Comparaison detaillee entre les rangs des bulletins et du classement
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
print("COMPARAISON BULLETIN vs CLASSEMENT")
print("=" * 100)

# 1. Recuperer la classe et les eleves
eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF').order_by('matricule')
if not eleves.exists():
    print("\nERREUR : Aucun eleve L12SC trouve")
    sys.exit(1)

classe_eleve = eleves.first().classe
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()

print(f"\nClasse : {classe_eleve.nom}")
print(f"Eleves : {eleves.count()}")

# 2. Generer le classement general
print("\n" + "=" * 100)
print("GENERATION DU CLASSEMENT GENERAL")
print("=" * 100)

classement_data, titre = _generer_classement_general(
    eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

# Creer un dictionnaire matricule -> rang du classement
classement_dict = {}
for eleve_data in classement_data:
    matricule = eleve_data.get('matricule')
    rang = eleve_data.get('rang')
    moyenne = eleve_data.get('moyenne')
    if matricule and rang:
        import re
        match = re.search(r'(\d+)', str(rang))
        rang_num = int(match.group(1)) if match else None
        classement_dict[matricule] = {
            'rang': rang,
            'rang_num': rang_num,
            'moyenne': moyenne
        }

# 3. Simuler le calcul du rang pour chaque bulletin individuel
print("\n" + "=" * 100)
print("SIMULATION DU CALCUL DES RANGS POUR LES BULLETINS INDIVIDUELS")
print("=" * 100)

# Recuperer les matieres
matieres = MatiereNote.objects.filter(classe=classe_note)

# Pour chaque eleve, calculer sa moyenne et son rang comme le fait bulletin_dynamique_pdf
bulletins_dict = {}

for eleve in eleves:
    # Calculer la moyenne de l'eleve
    total_points = Decimal('0')
    total_coef = Decimal('0')
    
    for matiere in matieres:
        evals = Evaluation.objects.filter(
            matiere=matiere,
            periode='OCTOBRE'
        )
        
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
        bulletins_dict[eleve.matricule] = {
            'eleve': eleve,
            'moyenne': float(moyenne)
        }

# Calculer les rangs pour les bulletins (simulation de bulletin_dynamique_pdf)
all_moyennes = [(mat, data['moyenne']) for mat, data in bulletins_dict.items()]
all_moyennes.sort(key=lambda x: x[1], reverse=True)

# Utiliser calculer_rang_intelligent
from notes.calculs_intelligent import calculer_rang_intelligent

moyennes_pour_rang = []
for matricule, moy in all_moyennes:
    eleve = bulletins_dict[matricule]['eleve']
    moyennes_pour_rang.append({
        'eleve_id': eleve.id,
        'prenom': eleve.prenom,
        'nom': eleve.nom,
        'sexe': getattr(eleve, 'sexe', 'M'),
        'moyenne': Decimal(str(moy))
    })

resultats_rangs = calculer_rang_intelligent(moyennes_pour_rang)

# Stocker les rangs des bulletins
for r in resultats_rangs:
    eleve_id = r['eleve_id']
    eleve = Eleve.objects.get(id=eleve_id)
    if eleve.matricule in bulletins_dict:
        bulletins_dict[eleve.matricule]['rang'] = r.get('rang')
        bulletins_dict[eleve.matricule]['rang_num'] = r.get('rang_num')

# 4. Comparaison detaillee
print("\n" + "=" * 100)
print("COMPARAISON DETAILLEE")
print("=" * 100)

print(f"\n{'Matricule':<15} {'Nom Complet':<35} {'Moyenne':<10} {'Classement':<15} {'Bulletin':<15} {'Status':<10}")
print("-" * 100)

differences = []
coherents = 0

for eleve in eleves.order_by('matricule'):
    matricule = eleve.matricule
    nom_complet = f"{eleve.nom} {eleve.prenom}"
    
    # Rang du classement
    classement_info = classement_dict.get(matricule, {})
    rang_classement = classement_info.get('rang', 'N/A')
    rang_classement_num = classement_info.get('rang_num')
    moyenne_classement = classement_info.get('moyenne')
    
    # Rang du bulletin
    bulletin_info = bulletins_dict.get(matricule, {})
    rang_bulletin = bulletin_info.get('rang', 'N/A')
    rang_bulletin_num = bulletin_info.get('rang_num')
    moyenne_bulletin = bulletin_info.get('moyenne')
    
    # Comparaison
    if rang_classement_num == rang_bulletin_num:
        status = "OK"
        coherents += 1
    else:
        status = "DIFFERENT"
        differences.append({
            'matricule': matricule,
            'nom': nom_complet,
            'classement': rang_classement,
            'bulletin': rang_bulletin,
            'moyenne_classement': moyenne_classement,
            'moyenne_bulletin': moyenne_bulletin
        })
    
    moyenne_str = f"{moyenne_classement:.2f}" if moyenne_classement else "N/A"
    
    print(f"{matricule:<15} {nom_complet:<35} {moyenne_str:<10} {rang_classement:<15} {rang_bulletin:<15} {status:<10}")

# 5. Resultat final
print("\n" + "=" * 100)
print("RESULTAT DE LA COMPARAISON")
print("=" * 100)

print(f"\nTotal eleves : {eleves.count()}")
print(f"Rangs coherents : {coherents}")
print(f"Rangs differents : {len(differences)}")

if len(differences) == 0:
    print("\n" + "=" * 100)
    print("PARFAIT ! TOUS LES RANGS SONT COHERENTS !")
    print("=" * 100)
    print("\nLes rangs affiches dans les bulletins individuels correspondent")
    print("exactement aux rangs du classement general.")
    print("\nLe systeme fonctionne correctement !")
else:
    print("\n" + "=" * 100)
    print("ATTENTION : DIFFERENCES DETECTEES")
    print("=" * 100)
    print("\nLes eleves suivants ont des rangs differents :")
    print(f"\n{'Matricule':<15} {'Nom':<35} {'Classement':<15} {'Bulletin':<15}")
    print("-" * 80)
    for diff in differences:
        print(f"{diff['matricule']:<15} {diff['nom']:<35} {diff['classement']:<15} {diff['bulletin']:<15}")
    
    print("\nCauses possibles :")
    print("1. Calcul de moyenne different entre classement et bulletin")
    print("2. Bug dans le calcul du rang d'une des deux fonctions")
    print("3. Donnees differentes utilisees (periode, type de notes, etc.)")

print("\n" + "=" * 100)
print("DETAILS TECHNIQUES")
print("=" * 100)
print(f"\nFonction classement : _generer_classement_general()")
print(f"Fonction bulletin : bulletin_dynamique_pdf() (simule)")
print(f"Fonction de calcul des rangs : calculer_rang_intelligent()")
print(f"Periode testee : OCTOBRE")
print(f"Type de notes : mensuelle")

print("\n" + "=" * 100)
