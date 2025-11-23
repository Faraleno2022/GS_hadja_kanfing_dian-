#!/usr/bin/env python
"""
Créer des données minimales pour tester la classe 61
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

def creer_donnees_minimales():
    """Créer des données minimales pour la classe 61"""
    print("🎯 CRÉATION DONNÉES MINIMALES CLASSE 61")
    print("=" * 40)
    
    # 1. Récupérer les classes
    classe_note = ClasseNote.objects.get(pk=61)
    classe_eleve = ClasseEleve.objects.get(pk=56)
    
    print(f"✅ ClasseNote: {classe_note.nom}")
    print(f"✅ ClasseEleve: {classe_eleve.nom}")
    
    # 2. Vérifier s'il y a des élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"📊 Élèves existants: {eleves.count()}")
    
    if eleves.count() > 0:
        print("✅ Des élèves existent déjà")
        for eleve in eleves[:3]:
            print(f"   - {eleve.prenom} {eleve.nom}")
    else:
        print("⚠️  Aucun élève - Les notes ne s'afficheront pas")
    
    # 3. Créer des matières si nécessaire
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"📚 Matières existantes: {matieres.count()}")
    
    if matieres.count() == 0:
        print("🆕 Création de matières...")
        matieres_test = [
            ('Mathématiques', 'MATH', 4),
            ('Physique-Chimie', 'PC', 3),
            ('Français', 'FR', 3),
        ]
        
        for nom, code, coef in matieres_test:
            matiere, created = MatiereNote.objects.get_or_create(
                classe=classe_note,
                nom=nom,
                defaults={
                    'code': code,
                    'coefficient': coef,
                    'actif': True,
                }
            )
            if created:
                print(f"   ✅ {nom}")
    
    # 4. Créer des évaluations OCTOBRE si nécessaire
    evaluations_octobre = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE')
    print(f"📝 Évaluations OCTOBRE existantes: {evaluations_octobre.count()}")
    
    if evaluations_octobre.count() == 0:
        print("🆕 Création d'évaluations OCTOBRE...")
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        for matiere in matieres:
            evaluation, created = Evaluation.objects.get_or_create(
                matiere=matiere,
                titre=f"Devoir OCTOBRE - {matiere.nom}",
                periode='OCTOBRE',
                defaults={
                    'type_evaluation': 'DEVOIR',
                    'date_evaluation': '2024-10-15',
                    'note_sur': 20.0,
                    'coefficient': 1.0,
                }
            )
            if created:
                print(f"   ✅ {evaluation.titre}")
    
    # 5. Créer quelques notes si il y a des élèves
    if eleves.count() > 0:
        notes_octobre = NoteEleve.objects.filter(
            evaluation__matiere__classe=classe_note, 
            evaluation__periode='OCTOBRE'
        )
        print(f"📊 Notes OCTOBRE existantes: {notes_octobre.count()}")
        
        if notes_octobre.count() == 0:
            print("🆕 Création de notes de test...")
            import random
            evaluations = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE')
            
            notes_creees = 0
            for eleve in eleves[:3]:  # Seulement les 3 premiers élèves
                for evaluation in evaluations:
                    note_value = round(random.uniform(10.0, 18.0), 2)
                    note, created = NoteEleve.objects.get_or_create(
                        eleve=eleve,
                        evaluation=evaluation,
                        defaults={
                            'note': note_value,
                            'absent': False,
                        }
                    )
                    if created:
                        notes_creees += 1
            
            print(f"   ✅ {notes_creees} notes créées")
    
    # 6. Résumé final
    print(f"\n📊 RÉSUMÉ FINAL")
    print("-" * 20)
    
    eleves_count = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').count()
    matieres_count = MatiereNote.objects.filter(classe=classe_note, actif=True).count()
    evaluations_count = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE').count()
    notes_count = NoteEleve.objects.filter(evaluation__matiere__classe=classe_note, evaluation__periode='OCTOBRE').count()
    
    print(f"   - Élèves actifs: {eleves_count}")
    print(f"   - Matières actives: {matieres_count}")
    print(f"   - Évaluations OCTOBRE: {evaluations_count}")
    print(f"   - Notes OCTOBRE: {notes_count}")
    
    if matieres_count > 0 and evaluations_count > 0:
        print(f"\n🎉 PRÊT POUR LE TEST !")
        print(f"✅ URL: http://127.0.0.1:8000/notes/consulter/?classe_id=61&periode=OCTOBRE")
        
        if eleves_count == 0:
            print(f"⚠️  Aucun élève - La page sera vide mais ne plantera pas")
        elif notes_count == 0:
            print(f"⚠️  Aucune note - Les élèves apparaîtront sans notes")
        else:
            print(f"✅ Tout est prêt - Les notes devraient s'afficher !")
    else:
        print(f"\n❌ Pas encore prêt - Il manque des matières ou évaluations")

if __name__ == "__main__":
    try:
        creer_donnees_minimales()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
