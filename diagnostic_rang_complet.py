"""
Script de diagnostic complet pour vérifier la cohérence des rangs
entre le classement et les bulletins
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote, NoteEleve, Evaluation, MatiereNote
from decimal import Decimal

print("\n" + "="*80)
print("DIAGNOSTIC COMPLET DES RANGS - CLASSEMENT vs BULLETINS")
print("="*80)

# Paramètres
classe_nom = "12 SÉRIE SCIENTIFIQUE"
periode = "OCTOBRE"

# Trouver la ClasseNote
classe_note = ClasseNote.objects.filter(nom__icontains=classe_nom).first()
if not classe_note:
    print(f"❌ ClasseNote '{classe_nom}' non trouvée")
    sys.exit(1)

print(f"\n✅ ClasseNote trouvée : {classe_note.nom} (ID: {classe_note.id})")
print(f"   Année scolaire : {classe_note.annee_scolaire}")

# Trouver la classe élève correspondante
from eleves.models import Classe as ClasseEleve
classe_eleve = ClasseEleve.objects.filter(
    nom=classe_note.nom,
    annee_scolaire=classe_note.annee_scolaire,
    ecole=classe_note.ecole
).first()

if not classe_eleve:
    print(f"❌ ClasseEleve correspondante non trouvée")
    sys.exit(1)

print(f"✅ ClasseEleve trouvée : {classe_eleve.nom} (ID: {classe_eleve.id})")

# Récupérer tous les élèves actifs
eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('prenom', 'nom')
print(f"✅ Nombre d'élèves actifs : {eleves.count()}")

# Récupérer les matières
matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
print(f"✅ Nombre de matières : {matieres.count()}")

print("\n" + "-"*80)
print("CALCUL DES MOYENNES POUR CHAQUE ÉLÈVE")
print("-"*80)

moyennes_eleves = []

for eleve in eleves:
    total_points = Decimal('0')
    total_coefficients = Decimal('0')
    
    for matiere in matieres:
        # Récupérer les évaluations de la période
        evaluations = Evaluation.objects.filter(
            matiere=matiere,
            periode=periode
        ).order_by('date_evaluation')
        
        if not evaluations.exists():
            continue
        
        # Calculer la moyenne de la matière
        total_devoirs = Decimal('0')
        count_devoirs = 0
        
        for evaluation in evaluations:
            try:
                note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                # Traiter les absences comme 0
                if note_obj.note is not None and not note_obj.absent:
                    note_value = Decimal(str(note_obj.note))
                else:
                    note_value = Decimal('0')
                
                total_devoirs += note_value
                count_devoirs += 1
            except NoteEleve.DoesNotExist:
                # Pas de note = 0
                count_devoirs += 1
        
        if count_devoirs > 0:
            moyenne_matiere = total_devoirs / count_devoirs
            total_points += moyenne_matiere * matiere.coefficient
            total_coefficients += matiere.coefficient
    
    if total_coefficients > 0:
        moyenne_generale = (total_points / total_coefficients).quantize(Decimal('0.01'))
        moyennes_eleves.append({
            'eleve': eleve,
            'moyenne': moyenne_generale,
            'matricule': eleve.matricule,
            'nom_complet': f"{eleve.prenom} {eleve.nom}",
            'sexe': getattr(eleve, 'sexe', 'M')
        })

print(f"\n✅ Élèves avec moyenne : {len(moyennes_eleves)}")

# Calculer les rangs avec calculer_rang_intelligent
print("\n" + "-"*80)
print("CALCUL DES RANGS AVEC calculer_rang_intelligent()")
print("-"*80)

from notes.calculs_intelligent import calculer_rang_intelligent

moyennes_pour_rang = []
for data in moyennes_eleves:
    moyennes_pour_rang.append({
        'eleve_id': data['eleve'].id,
        'prenom': data['eleve'].prenom,
        'nom': data['eleve'].nom,
        'sexe': data['sexe'],
        'moyenne': data['moyenne']
    })

resultats_rangs = calculer_rang_intelligent(moyennes_pour_rang)

# Créer un dictionnaire pour accès rapide
rangs_dict = {}
for r in resultats_rangs:
    rangs_dict[r['eleve_id']] = {
        'rang': r.get('rang'),
        'rang_num': r.get('rang_num')
    }

# Afficher le classement complet
print("\n" + "="*80)
print("CLASSEMENT COMPLET")
print("="*80)
print(f"{'Rang':8} | {'Matricule':15} | {'Nom Complet':35} | {'Moyenne':8} | {'Sexe':5}")
print("-"*80)

for data in moyennes_eleves:
    eleve_id = data['eleve'].id
    rang_info = rangs_dict.get(eleve_id, {})
    rang_str = rang_info.get('rang', '-')
    
    print(f"{rang_str:8} | {data['matricule']:15} | {data['nom_complet']:35} | {data['moyenne']:8.2f} | {data['sexe']:5}")

# Vérifier quelques élèves spécifiques
print("\n" + "="*80)
print("VÉRIFICATION ÉLÈVES SPÉCIFIQUES")
print("="*80)

eleves_test = [
    "HAÏDARA",
    "LOUAMMOU",
    "DIALLO Alpha",
    "BANGOURA"
]

for nom_test in eleves_test:
    for data in moyennes_eleves:
        if nom_test.upper() in data['nom_complet'].upper():
            eleve_id = data['eleve'].id
            rang_info = rangs_dict.get(eleve_id, {})
            
            print(f"\n📌 {data['nom_complet']}")
            print(f"   Matricule : {data['matricule']}")
            print(f"   Moyenne : {data['moyenne']:.2f}")
            print(f"   Sexe : {data['sexe']}")
            print(f"   Rang complet : {rang_info.get('rang')}")
            print(f"   Rang numérique : {rang_info.get('rang_num')}")
            break

print("\n" + "="*80)
print("ANALYSE DES DIFFÉRENCES POSSIBLES")
print("="*80)

print("\n🔍 Points à vérifier :")
print("1. Le classement web utilise-t-il la même période ?")
print("2. Les bulletins utilisent-ils la même méthode de calcul ?")
print("3. Y a-t-il des différences dans le traitement des absences ?")
print("4. Les coefficients des matières sont-ils identiques ?")

print("\n" + "="*80 + "\n")
