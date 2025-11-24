"""
Diagnostic rapide pour la classe 11ème Série littéraire
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe

print("\n" + "="*80)
print("🔍 DIAGNOSTIC RAPIDE - 11ÈME SÉRIE LITTÉRAIRE")
print("="*80)

# 1. Chercher la ClasseNote
print("\n1️⃣ RECHERCHE DE LA CLASSE DANS ClasseNote:")
classes_11 = ClasseNote.objects.filter(nom__icontains='11')

if classes_11.exists():
    for cn in classes_11:
        nb_matieres = MatiereNote.objects.filter(classe=cn).count()
        print(f"✅ ID {cn.id}: {cn.nom} ({cn.annee_scolaire})")
        print(f"   • École: {cn.ecole.nom}")
        print(f"   • Matières configurées: {nb_matieres}")
        
        # Compter les notes existantes
        nb_notes = NoteMensuelle.objects.filter(
            matiere__classe=cn
        ).values('eleve').distinct().count()
        print(f"   • Élèves avec notes: {nb_notes}")
        
        classe_note_id = cn.id
else:
    print("❌ Aucune ClasseNote pour 11ème trouvée")
    classe_note_id = None

# 2. Chercher les élèves
print("\n2️⃣ RECHERCHE DES ÉLÈVES 11ÈME:")

# Par matricule (commençant par 2025/08)
eleves_2025 = Eleve.objects.filter(matricule__startswith='2025/08')

if eleves_2025.exists():
    print(f"✅ {eleves_2025.count()} élèves avec matricule 2025/08xxx")
    
    # Afficher les classes de ces élèves
    classes_uniques = set()
    for e in eleves_2025:
        classes_uniques.add((e.classe.nom, e.classe.annee_scolaire, e.classe.id))
    
    print("\nClasses de ces élèves:")
    for nom, annee, cid in classes_uniques:
        nb = eleves_2025.filter(classe__id=cid).count()
        print(f"   • {nom} ({annee}) - ID {cid}: {nb} élèves")
else:
    print("❌ Aucun élève avec matricule 2025/08xxx")

# Recherche par nom de classe
eleves_11 = Eleve.objects.filter(
    classe__nom__icontains='11',
    statut__in=['ACTIF', 'INSCRIT']
)

if eleves_11.exists():
    print(f"\n✅ {eleves_11.count()} élèves en classe contenant '11'")
    for e in eleves_11[:3]:
        print(f"   • {e.matricule} - {e.nom} {e.prenom} ({e.classe.nom})")

# 3. Solution proposée
print("\n" + "="*80)
print("💡 SOLUTION PROPOSÉE")
print("="*80)

if classe_note_id:
    print(f"\n✅ ClasseNote trouvée (ID: {classe_note_id})")
    print("   Commande pour créer des notes TEST:")
    print(f"\n   python -c \"")
    print(f"import os, django")
    print(f"os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')")
    print(f"django.setup()")
    print(f"from notes.models import NoteMensuelle, ClasseNote, MatiereNote")
    print(f"from eleves.models import Eleve")
    print(f"import random")
    print(f"from decimal import Decimal")
    print(f"")
    print(f"classe = ClasseNote.objects.get(id={classe_note_id})")
    print(f"matieres = MatiereNote.objects.filter(classe=classe)")
    print(f"")
    print(f"# Trouver les élèves")
    print(f"eleves = Eleve.objects.filter(matricule__startswith='2025/08', statut__in=['ACTIF', 'INSCRIT'])")
    print(f"")
    print(f"notes_creees = 0")
    print(f"for eleve in eleves:")
    print(f"    for matiere in matieres:")
    print(f"        if not NoteMensuelle.objects.filter(eleve=eleve, matiere=matiere, mois='OCTOBRE', annee_scolaire=classe.annee_scolaire).exists():")
    print(f"            note = Decimal(str(random.uniform(10, 17))).quantize(Decimal('0.1'))")
    print(f"            NoteMensuelle.objects.create(")
    print(f"                eleve=eleve, matiere=matiere, mois='OCTOBRE',")
    print(f"                annee_scolaire=classe.annee_scolaire,")
    print(f"                note=note, absent=False, observations='Note test'")
    print(f"            )")
    print(f"            notes_creees += 1")
    print(f"")
    print(f"print(f'✅ {{notes_creees}} notes créées!')\"")
    
else:
    print("\n❌ PROBLÈME : Aucune ClasseNote configurée pour 11ème")
    print("\nSOLUTION :")
    print("1. Se connecter à l'admin Django")
    print("2. Créer une ClasseNote pour '11ème Série littéraire'")
    print("3. Ajouter les matières correspondantes")
    print("4. Relancer ce script")

print("\n" + "="*80)
