#!/usr/bin/env python
"""
Diagnostiquer pourquoi les notes ne sont pas récupérées
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

def diagnostiquer():
    """Trouver où sont les notes"""
    print("🔍 DIAGNOSTIC NOTES MANQUANTES")
    print("=" * 35)
    
    # ClasseEleve 8
    classe_eleve = ClasseEleve.objects.get(pk=8)
    print(f"ClasseEleve: {classe_eleve.nom} (ID: {classe_eleve.id})")
    
    # Tous les ClasseNote qui pourraient correspondre
    print(f"\n📚 ClasseNote candidats:")
    classes_note = ClasseNote.objects.all()
    for cn in classes_note:
        print(f"   - ID {cn.id}: {cn.nom}")
        matieres_count = MatiereNote.objects.filter(classe=cn).count()
        print(f"      Matières: {matieres_count}")
        
        # Pour chaque matière, compter les évaluations
        for mat in MatiereNote.objects.filter(classe=cn, actif=True)[:3]:
            evals_count = Evaluation.objects.filter(matiere=mat).count()
            print(f"         - {mat.nom}: {evals_count} évaluations")
            
            # Compter les notes pour cette matière
            notes_count = NoteEleve.objects.filter(evaluation__matiere=mat).count()
            print(f"            Notes dans cette matière: {notes_count}")
    
    # Élève test
    print(f"\n👤 Élève test:")
    eleve = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').first()
    print(f"   - {eleve.prenom} {eleve.nom} (ID: {eleve.id})")
    
    # Toutes les notes de cet élève
    notes_eleve = NoteEleve.objects.filter(eleve=eleve).select_related('evaluation', 'evaluation__matiere')
    print(f"   - Notes totales: {notes_eleve.count()}")
    
    if notes_eleve.exists():
        print(f"\n📝 Échantillon de notes:")
        for note in notes_eleve[:10]:
            print(f"      • {note.evaluation.matiere.nom} - {note.evaluation.titre}")
            print(f"        Période: {note.evaluation.periode}, Note: {note.note if note.note else 'ABS'}")
            print(f"        ClasseNote ID de la matière: {note.evaluation.matiere.classe.id}")
    else:
        print(f"   ❌ Aucune note trouvée pour cet élève !")
        
        # Chercher des notes pour d'autres élèves
        print(f"\n🔍 Chercher des notes dans le système:")
        toutes_notes = NoteEleve.objects.all()[:20]
        if toutes_notes.exists():
            print(f"   ✅ {NoteEleve.objects.count()} notes totales dans le système")
            print(f"\n   Échantillon:")
            for note in toutes_notes:
                print(f"      • Élève ID {note.eleve.id}: {note.evaluation.matiere.nom}")
                print(f"        ClasseEleve: {note.eleve.classe.nom} (ID: {note.eleve.classe.id})")
                print(f"        ClasseNote de la matière: {note.evaluation.matiere.classe.nom} (ID: {note.evaluation.matiere.classe.id})")
        else:
            print(f"   ❌ Aucune note dans tout le système !")

if __name__ == "__main__":
    try:
        diagnostiquer()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
