"""
Trouver la vraie classe 9ÈME ANNÉE de l'année 2025-2026
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe

def trouver_classe_9eme():
    print("\n" + "="*80)
    print("🔍 RECHERCHE DE LA CLASSE 9ÈME ANNÉE - ANNÉE 2025-2026")
    print("="*80)
    
    # Rechercher toutes les classes avec "9" dans le nom
    print("\n📚 Classes contenant '9' :")
    classes_9 = ClasseNote.objects.filter(nom__icontains='9').order_by('-annee_scolaire', 'nom')
    
    for classe in classes_9:
        print(f"\n✅ ID: {classe.id:3} | {classe.nom:30} | Année: {classe.annee_scolaire}")
        
        # Compter les matières
        nb_matieres = MatiereNote.objects.filter(classe=classe).count()
        print(f"   Matières : {nb_matieres}")
        
        # Chercher la classe Eleve correspondante
        classe_eleve = Classe.objects.filter(
            nom__icontains=classe.nom.replace('è', 'e').replace('È', 'E'),
            annee_scolaire=classe.annee_scolaire
        ).first()
        
        if classe_eleve:
            nb_eleves = Eleve.objects.filter(classe=classe_eleve, statut='INSCRIT').count()
            print(f"   Élèves : {nb_eleves}")
        else:
            print(f"   Élèves : Classe non trouvée")
    
    # Rechercher spécifiquement pour 2025-2026
    print("\n" + "-"*80)
    print("🎯 RECHERCHE SPÉCIFIQUE ANNÉE 2025-2026")
    print("-"*80)
    
    classes_2025 = ClasseNote.objects.filter(annee_scolaire='2025-2026').order_by('nom')
    
    print(f"\nTOTAL CLASSES 2025-2026 : {classes_2025.count()}")
    
    if classes_2025.exists():
        print("\n📋 LISTE COMPLÈTE DES CLASSES 2025-2026 :")
        
        for classe in classes_2025:
            nb_matieres = MatiereNote.objects.filter(classe=classe).count()
            
            # Chercher les élèves
            classe_eleve = Classe.objects.filter(
                nom__iexact=classe.nom,
                annee_scolaire='2025-2026'
            ).first()
            
            nb_eleves = 0
            if classe_eleve:
                nb_eleves = Eleve.objects.filter(classe=classe_eleve, statut='INSCRIT').count()
            
            # Marquer la classe 9ème
            marker = " ⭐" if '9' in classe.nom.upper() else ""
            
            print(f"\nID: {classe.id:3} | {classe.nom:30}{marker}")
            print(f"   • Matières : {nb_matieres}")
            print(f"   • Élèves : {nb_eleves}")
    
    # Diagnostic de l'élève mentionné
    print("\n" + "-"*80)
    print("🔍 RECHERCHE DE L'ÉLÈVE CL9-011 (ABDOUL GOUDOUSSY DIALLO)")
    print("-"*80)
    
    try:
        eleve = Eleve.objects.get(matricule='CL9-011')
        print(f"\n✅ Élève trouvé :")
        print(f"   • Nom : {eleve.nom} {eleve.prenom}")
        print(f"   • Matricule : {eleve.matricule}")
        print(f"   • Classe : {eleve.classe.nom}")
        print(f"   • Classe ID : {eleve.classe.id}")
        print(f"   • Année scolaire : {eleve.classe.annee_scolaire}")
        
        # Chercher la ClasseNote correspondante
        classe_note = ClasseNote.objects.filter(
            nom__iexact=eleve.classe.nom,
            annee_scolaire=eleve.classe.annee_scolaire
        ).first()
        
        if classe_note:
            print(f"\n✅ ClasseNote correspondante trouvée :")
            print(f"   • ID : {classe_note.id}")
            print(f"   • Nom : {classe_note.nom}")
            print(f"   • URL correcte : /notes/bulletins/?classe_id={classe_note.id}&eleve_id={eleve.id}&periode=OCTOBRE&system_type=mensuel")
            
            # Vérifier les notes
            notes = NoteMensuelle.objects.filter(
                eleve=eleve,
                mois='OCTOBRE',
                annee_scolaire=eleve.classe.annee_scolaire
            ).count()
            
            print(f"\n📊 Notes mensuelles OCTOBRE : {notes}")
            
            if notes == 0:
                print("\n❌ AUCUNE NOTE pour cet élève en OCTOBRE")
        else:
            print("\n❌ ClasseNote non trouvée pour cette classe")
            
    except Eleve.DoesNotExist:
        print("\n❌ Élève CL9-011 non trouvé")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    trouver_classe_9eme()
