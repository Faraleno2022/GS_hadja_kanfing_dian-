"""
Test simple du système d'export corrigé
"""
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Eleve, Classe as ClasseEleve
import re

def trouver_classe_eleve(classe_note):
    """Reproduire exactement la logique de export_classement.py"""
    
    # Essai 1: Correspondance exacte
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    print(f"Essai 1 (exacte): {classe_eleve.nom if classe_eleve else 'Aucune'}")
    
    # Essai 2: Correspondance insensible à la casse
    if not classe_eleve:
        classe_eleve = ClasseEleve.objects.filter(
            nom__iexact=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        print(f"Essai 2 (iexact): {classe_eleve.nom if classe_eleve else 'Aucune'}")
    
    # Essai 3: Recherche par mots-clés
    if not classe_eleve:
        match = re.search(r'(\d+)', classe_note.nom)
        if match:
            niveau_num = match.group(1)
            print(f"Niveau extrait: {niveau_num}")
            
            # Chercher d'abord avec l'école
            classes_possibles = ClasseEleve.objects.filter(
                nom__icontains=niveau_num,
                annee_scolaire=classe_note.annee_scolaire,
                ecole=classe_note.ecole
            )
            
            print(f"Classes avec école ID {classe_note.ecole.id}: {classes_possibles.count()}")
            
            # Si aucune classe trouvée avec l'école, chercher sans filtrer par école
            if not classes_possibles.exists():
                classes_possibles = ClasseEleve.objects.filter(
                    nom__icontains=niveau_num,
                    annee_scolaire=classe_note.annee_scolaire
                )
                print(f"Classes sans filtre école: {classes_possibles.count()}")
                for c in classes_possibles:
                    print(f"  - {c.nom} (école ID: {c.ecole.id})")
            
            classe_eleve = classes_possibles.first()
            
            # Si plusieurs classes trouvées, essayer d'affiner avec les mots-clés
            if classe_eleve and classes_possibles.count() > 1:
                print(f"Affinement nécessaire ({classes_possibles.count()} classes)")
                
                # Chercher des mots-clés spécifiques dans le nom de la classe
                if 'scientifique' in classe_note.nom.lower() or 'science' in classe_note.nom.lower():
                    print("Recherche SCIENCE...")
                    for c in classes_possibles:
                        if 'SCIENCE' in c.nom.upper():
                            classe_eleve = c
                            print(f"  Trouvé: {c.nom}")
                            break
                elif 'littéraire' in classe_note.nom.lower() or 'lettre' in classe_note.nom.lower():
                    print("Recherche LETTRE...")
                    for c in classes_possibles:
                        if 'LETTRE' in c.nom.upper():
                            classe_eleve = c
                            print(f"  Trouvé: {c.nom}")
                            break
    
    return classe_eleve


# Test
classe_note = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='scien').first()

if classe_note:
    print(f"\n{'='*80}")
    print(f"ClasseNote: {classe_note.nom}")
    print(f"Année: {classe_note.annee_scolaire}")
    print(f"École: {classe_note.ecole.nom} (ID: {classe_note.ecole.id})")
    print(f"{'='*80}\n")
    
    classe_eleve = trouver_classe_eleve(classe_note)
    
    if classe_eleve:
        print(f"\n✅ CLASSE ÉLÈVE TROUVÉE: {classe_eleve.nom}")
        print(f"   École: {classe_eleve.ecole.nom} (ID: {classe_eleve.ecole.id})")
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"   Élèves actifs: {eleves.count()}")
        
        if eleves.count() > 0:
            print(f"\n   Premiers élèves:")
            for e in eleves[:5]:
                print(f"      - {e.matricule}: {e.nom} {e.prenom}")
    else:
        print("\n❌ AUCUNE CLASSE ÉLÈVE TROUVÉE")
else:
    print("❌ ClasseNote non trouvée")
