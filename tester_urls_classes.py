#!/usr/bin/env python
"""
Tester les URLs de consultation pour les classes 59 et 61
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Classe as ClasseEleve, Eleve

def tester_classe(classe_id, nom_classe):
    """Tester une classe spécifique"""
    print(f"\n🧪 TEST CLASSE {classe_id} - {nom_classe}")
    print("=" * 50)
    
    try:
        # 1. Vérifier ClasseNote
        classe_note = ClasseNote.objects.get(pk=classe_id)
        print(f"✅ ClasseNote: {classe_note.nom}")
        
        # 2. Vérifier le mapping
        mapping_classes = {
            61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'
            59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
        }
        
        if classe_id in mapping_classes:
            classe_eleve_id = mapping_classes[classe_id]
            classe_eleve = ClasseEleve.objects.get(pk=classe_eleve_id)
            print(f"✅ Mapping: ClasseEleve {classe_eleve_id} ({classe_eleve.nom})")
        else:
            print("⚠️  Pas de mapping spécial")
        
        # 3. Vérifier les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"👥 Élèves actifs: {eleves.count()}")
        
        # 4. Vérifier les matières
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        print(f"📚 Matières actives: {matieres.count()}")
        
        # 5. Vérifier les évaluations OCTOBRE
        evaluations_octobre = Evaluation.objects.filter(
            matiere__classe=classe_note,
            periode='OCTOBRE'
        )
        print(f"📝 Évaluations OCTOBRE: {evaluations_octobre.count()}")
        
        # 6. Vérifier les notes OCTOBRE
        notes_octobre = NoteEleve.objects.filter(
            evaluation__matiere__classe=classe_note,
            evaluation__periode='OCTOBRE'
        )
        print(f"📊 Notes OCTOBRE: {notes_octobre.count()}")
        
        # 7. Résultat du test
        if eleves.count() > 0 and matieres.count() > 0 and evaluations_octobre.count() > 0:
            print(f"🎉 CLASSE PRÊTE !")
            print(f"🔗 URL: http://127.0.0.1:8000/notes/consulter/?classe_id={classe_id}&periode=OCTOBRE")
            
            if notes_octobre.count() > 0:
                print(f"✅ {notes_octobre.count()} notes disponibles")
            else:
                print(f"⚠️  Aucune note - Les élèves apparaîtront sans notes")
        else:
            print(f"❌ CLASSE PAS PRÊTE")
            if eleves.count() == 0:
                print(f"   - Manque des élèves")
            if matieres.count() == 0:
                print(f"   - Manque des matières")
            if evaluations_octobre.count() == 0:
                print(f"   - Manque des évaluations OCTOBRE")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

def tester_toutes_classes():
    """Tester toutes les classes importantes"""
    print("🧪 TEST COMPLET DES CLASSES")
    print("=" * 40)
    
    classes_a_tester = [
        (59, "11ème Série littéraire"),
        (61, "12ème Année"),
    ]
    
    for classe_id, nom in classes_a_tester:
        tester_classe(classe_id, nom)
    
    print(f"\n📊 RÉSUMÉ GLOBAL")
    print("=" * 20)
    
    # Statistiques globales
    total_classes_notes = ClasseNote.objects.filter(actif=True).count()
    total_classes_eleves = ClasseEleve.objects.count()
    total_evaluations = Evaluation.objects.count()
    total_notes = NoteEleve.objects.count()
    
    print(f"📚 Classes Notes actives: {total_classes_notes}")
    print(f"👥 Classes Élèves: {total_classes_eleves}")
    print(f"📝 Total évaluations: {total_evaluations}")
    print(f"📊 Total notes: {total_notes}")
    
    print(f"\n🎯 URLS DE TEST PRINCIPALES:")
    print(f"   - 11ème Littéraire: http://127.0.0.1:8000/notes/consulter/?classe_id=59&periode=OCTOBRE")
    print(f"   - 12ème Année: http://127.0.0.1:8000/notes/consulter/?classe_id=61&periode=OCTOBRE")

if __name__ == "__main__":
    try:
        tester_toutes_classes()
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
