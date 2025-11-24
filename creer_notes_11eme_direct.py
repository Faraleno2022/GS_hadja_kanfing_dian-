"""
Script DIRECT pour créer les notes de la classe 11ème Série littéraire
Sans questions, création immédiate
"""

import os
import sys
import django
import random
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from django.db import transaction

print("\n" + "="*80)
print("🎲 CRÉATION DIRECTE DE NOTES - 11ÈME SÉRIE LITTÉRAIRE")
print("="*80)

# Trouver la ClasseNote
classe_note = ClasseNote.objects.filter(nom__icontains='11').first()

if not classe_note:
    print("\n❌ Aucune ClasseNote pour 11ème trouvée")
    print("   Essayons de créer une ClasseNote...")
    
    # Récupérer l'école par défaut
    from ecoles.models import Ecole
    ecole = Ecole.objects.first()
    
    if ecole:
        # Créer la ClasseNote
        classe_note = ClasseNote.objects.create(
            nom="11ème Série littéraire",
            annee_scolaire="2025-2026",
            ecole=ecole
        )
        print(f"✅ ClasseNote créée : {classe_note.nom} (ID: {classe_note.id})")
        
        # Créer les matières littéraires de base
        matieres_litteraires = [
            ("Français", 3.0),
            ("Anglais", 2.0),
            ("Histoire", 2.0),
            ("Géographie", 2.0),
            ("Philosophie", 2.0),
            ("Education Civique", 1.0),
            ("EPS", 1.0),
            ("Arabe", 1.0),
        ]
        
        for nom, coef in matieres_litteraires:
            MatiereNote.objects.create(
                nom=nom,
                coefficient=coef,
                classe=classe_note
            )
        
        print(f"✅ {len(matieres_litteraires)} matières créées")
    else:
        print("❌ Aucune école trouvée, impossible de créer la ClasseNote")
        sys.exit(1)

print(f"\n✅ ClasseNote : {classe_note.nom} (ID: {classe_note.id})")

# Récupérer les matières
matieres = MatiereNote.objects.filter(classe=classe_note)

if not matieres.exists():
    print("⚠️ Aucune matière configurée, création des matières de base...")
    
    matieres_litteraires = [
        ("Français", 3.0),
        ("Anglais", 2.0),
        ("Histoire", 2.0),
        ("Géographie", 2.0),
        ("Philosophie", 2.0),
        ("Education Civique", 1.0),
        ("EPS", 1.0),
        ("Arabe", 1.0),
    ]
    
    for nom, coef in matieres_litteraires:
        MatiereNote.objects.get_or_create(
            nom=nom,
            classe=classe_note,
            defaults={'coefficient': coef}
        )
    
    matieres = MatiereNote.objects.filter(classe=classe_note)

print(f"📚 Matières : {matieres.count()}")

# Trouver les élèves
# Stratégie 1: Par matricule 2025/08xxx
eleves = Eleve.objects.filter(
    matricule__startswith='2025/08',
    statut__in=['ACTIF', 'INSCRIT']
)

if not eleves.exists():
    # Stratégie 2: Par nom de classe contenant 11
    eleves = Eleve.objects.filter(
        classe__nom__icontains='11',
        statut__in=['ACTIF', 'INSCRIT']
    )

if not eleves.exists():
    print("\n❌ Aucun élève trouvé pour la classe 11ème")
    
    # Lister quelques élèves disponibles
    print("\nÉlèves disponibles (échantillon):")
    sample = Eleve.objects.filter(statut__in=['ACTIF', 'INSCRIT'])[:10]
    for e in sample:
        print(f"   • {e.matricule} - {e.nom} {e.prenom} ({e.classe.nom})")
    
    sys.exit(1)

print(f"👥 Élèves trouvés : {eleves.count()}")

# Afficher les premiers élèves
print("\nÉlèves concernés:")
for e in eleves[:5]:
    print(f"   • {e.matricule} - {e.nom} {e.prenom}")
if eleves.count() > 5:
    print(f"   ... et {eleves.count() - 5} autres")

# Demander le mois
print("\n📅 Sélection du mois:")
print("1. OCTOBRE")
print("2. NOVEMBRE")
print("3. DÉCEMBRE")
print("4. Mois actuel")

choix_mois = input("\nVotre choix (1-4, défaut=1) : ").strip() or "1"

mois_map = {
    "1": "OCTOBRE",
    "2": "NOVEMBRE", 
    "3": "DÉCEMBRE",
    "4": ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN",
          "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"][
              __import__('datetime').datetime.now().month - 1
          ]
}

mois = mois_map.get(choix_mois, "OCTOBRE")
print(f"\n✅ Mois sélectionné : {mois}")

# Création des notes
print("\n⏳ Création des notes en cours...")

notes_creees = 0
notes_existantes = 0

with transaction.atomic():
    for eleve in eleves:
        for matiere in matieres:
            # Vérifier si la note existe
            exists = NoteMensuelle.objects.filter(
                eleve=eleve,
                matiere=matiere,
                mois=mois,
                annee_scolaire=classe_note.annee_scolaire
            ).exists()
            
            if exists:
                notes_existantes += 1
            else:
                # Générer une note aléatoire
                # Notes plus élevées pour le français (matière principale)
                if "français" in matiere.nom.lower():
                    note = Decimal(str(random.uniform(12, 18))).quantize(Decimal('0.1'))
                else:
                    note = Decimal(str(random.uniform(10, 17))).quantize(Decimal('0.1'))
                
                # 5% de chance d'absence
                absent = random.random() < 0.05
                
                NoteMensuelle.objects.create(
                    eleve=eleve,
                    matiere=matiere,
                    mois=mois,
                    annee_scolaire=classe_note.annee_scolaire,
                    note=None if absent else note,
                    absent=absent,
                    observations="Note de test" if not absent else "Absent"
                )
                notes_creees += 1
                
                # Afficher la progression
                if notes_creees % 50 == 0:
                    print(f"   ... {notes_creees} notes créées")

print(f"\n✅ TERMINÉ !")
print(f"   • Notes créées : {notes_creees}")
print(f"   • Notes existantes : {notes_existantes}")
print(f"   • Total : {notes_creees + notes_existantes}")

# Afficher un échantillon
print("\n📊 Échantillon des notes créées:")
sample_notes = NoteMensuelle.objects.filter(
    matiere__classe=classe_note,
    mois=mois,
    annee_scolaire=classe_note.annee_scolaire
).order_by('-date_creation')[:10]

for n in sample_notes:
    status = "ABSENT" if n.absent else f"{n.note}/20"
    print(f"   • {n.eleve.matricule} - {n.matiere.nom}: {status}")

# Calculer quelques moyennes
print("\n📈 Moyennes par matière:")
for matiere in matieres[:5]:
    notes = NoteMensuelle.objects.filter(
        matiere=matiere,
        mois=mois,
        annee_scolaire=classe_note.annee_scolaire,
        absent=False,
        note__isnull=False
    )
    
    if notes.exists():
        notes_list = [float(n.note) for n in notes]
        moyenne = sum(notes_list) / len(notes_list) if notes_list else 0
        print(f"   • {matiere.nom}: {moyenne:.2f}/20")

print("\n" + "="*80)
print("✅ Les notes sont maintenant disponibles !")
print(f"   URL: https://www.myschoolgn.space/notes/consulter/")
print(f"   Classe: {classe_note.nom}")
print(f"   Mois: {mois}")
print("="*80)
