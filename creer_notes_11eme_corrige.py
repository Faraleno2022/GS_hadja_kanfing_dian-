"""
Script CORRIGÉ pour créer les notes de la classe 11ème Série littéraire
SANS le champ 'observations' qui n'existe pas dans le modèle
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
print("🎲 CRÉATION CORRIGÉE DE NOTES - 11ÈME SÉRIE LITTÉRAIRE")
print("="*80)

# Trouver la ClasseNote
classe_note = ClasseNote.objects.filter(nom__icontains='11').first()

if not classe_note:
    print("\n❌ Aucune ClasseNote pour 11ème trouvée")
    sys.exit(1)

print(f"\n✅ ClasseNote : {classe_note.nom} (ID: {classe_note.id})")

# Récupérer les matières
matieres = MatiereNote.objects.filter(classe=classe_note)
print(f"📚 Matières : {matieres.count()}")

if not matieres.exists():
    print("❌ Aucune matière configurée")
    sys.exit(1)

# Trouver les élèves
# Utiliser les élèves trouvés précédemment (matricules L11xxx)
eleves = Eleve.objects.filter(
    matricule__startswith='L11',
    statut__in=['ACTIF', 'INSCRIT']
)

if not eleves.exists():
    # Fallback: chercher par nom de classe
    eleves = Eleve.objects.filter(
        classe__nom__icontains='11',
        statut__in=['ACTIF', 'INSCRIT']
    )

print(f"👥 Élèves trouvés : {eleves.count()}")

if not eleves.exists():
    print("❌ Aucun élève trouvé")
    sys.exit(1)

# Afficher les premiers élèves
print("\nÉlèves concernés:")
for e in eleves[:5]:
    print(f"   • {e.matricule} - {e.nom} {e.prenom}")
if eleves.count() > 5:
    print(f"   ... et {eleves.count() - 5} autres")

# Sélection du mois
print("\n📅 Sélection du mois:")
print("1. OCTOBRE")
print("2. NOVEMBRE") 
print("3. DECEMBRE")

choix_mois = input("\nVotre choix (1-3, défaut=1) : ").strip() or "1"

mois_map = {
    "1": "OCTOBRE",
    "2": "NOVEMBRE",
    "3": "DECEMBRE"
}

mois = mois_map.get(choix_mois, "OCTOBRE")
print(f"\n✅ Mois sélectionné : {mois}")

# Création des notes
print("\n⏳ Création des notes en cours...")

notes_creees = 0
notes_existantes = 0

try:
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
                    # Notes plus élevées pour certaines matières
                    if any(mot in matiere.nom.lower() for mot in ['français', 'littérature']):
                        note = Decimal(str(random.uniform(12, 18))).quantize(Decimal('0.1'))
                    else:
                        note = Decimal(str(random.uniform(10, 17))).quantize(Decimal('0.1'))
                    
                    # 5% de chance d'absence
                    absent = random.random() < 0.05
                    
                    # CORRECTION: Retirer le champ 'observations'
                    NoteMensuelle.objects.create(
                        eleve=eleve,
                        matiere=matiere,
                        mois=mois,
                        annee_scolaire=classe_note.annee_scolaire,
                        note=None if absent else note,
                        absent=absent
                        # observations supprimé car le champ n'existe pas
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

except Exception as e:
    print(f"\n❌ Erreur lors de la création : {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
