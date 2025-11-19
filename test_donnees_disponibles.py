"""
Test pour voir les données disponibles dans la base
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve, Classe as ClasseEleve
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve

def lister_donnees():
    print("="*80)
    print("DONNÉES DISPONIBLES DANS LA BASE")
    print("="*80)
    
    # Lister les classes notes
    print("\n📚 CLASSES NOTES :")
    print("-"*40)
    classes_notes = ClasseNote.objects.all().order_by('nom')[:10]
    for cn in classes_notes:
        print(f"  - {cn.nom} ({cn.annee_scolaire}) - ID: {cn.id}")
    
    # Lister les classes élèves
    print("\n👥 CLASSES ÉLÈVES :")
    print("-"*40)
    classes_eleves = ClasseEleve.objects.all().order_by('nom')[:10]
    for ce in classes_eleves:
        print(f"  - {ce.nom} ({ce.annee_scolaire}) - École: {ce.ecole.nom if ce.ecole else 'N/A'}")
    
    # Lister quelques élèves
    print("\n🎓 ÉLÈVES (premiers 20) :")
    print("-"*40)
    eleves = Eleve.objects.all().order_by('matricule')[:20]
    for e in eleves:
        classe_nom = e.classe.nom if e.classe else "Sans classe"
        print(f"  - {e.matricule}: {e.nom} {e.prenom} - Classe: {classe_nom}")
    
    # Chercher spécifiquement les élèves de 12ème
    print("\n🔍 ÉLÈVES DE 12ème :")
    print("-"*40)
    eleves_12 = Eleve.objects.filter(classe__nom__icontains="12")[:20]
    if eleves_12:
        for e in eleves_12:
            print(f"  - {e.matricule}: {e.nom} {e.prenom} - Classe: {e.classe.nom}")
    else:
        print("  Aucun élève trouvé en 12ème")
    
    # Chercher spécifiquement L12SC
    print("\n🔍 ÉLÈVES AVEC MATRICULE L12SC :")
    print("-"*40)
    eleves_l12sc = Eleve.objects.filter(matricule__startswith="L12SC")
    if eleves_l12sc:
        for e in eleves_l12sc:
            classe_nom = e.classe.nom if e.classe else "Sans classe"
            print(f"  - {e.matricule}: {e.nom} {e.prenom} - Classe: {classe_nom}")
    else:
        print("  Aucun élève avec matricule L12SC trouvé")
    
    # Statistiques générales
    print("\n📊 STATISTIQUES :")
    print("-"*40)
    print(f"  Total classes notes : {ClasseNote.objects.count()}")
    print(f"  Total classes élèves : {ClasseEleve.objects.count()}")
    print(f"  Total élèves : {Eleve.objects.count()}")
    print(f"  Total matières : {MatiereNote.objects.count()}")
    print(f"  Total évaluations : {Evaluation.objects.count()}")
    print(f"  Total notes : {NoteEleve.objects.count()}")

if __name__ == "__main__":
    lister_donnees()
