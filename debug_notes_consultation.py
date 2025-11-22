#!/usr/bin/env python
"""
Script de diagnostic pour le problème de consultation des notes
"""

import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, Evaluation, NoteEleve, MatiereNote
from eleves.models import Classe as ClasseEleve, Eleve

def diagnostiquer_probleme():
    """Diagnostique le problème de consultation des notes"""
    
    print("🔍 DIAGNOSTIC - Problème consultation des notes")
    print("=" * 60)
    
    # 1. Trouver la classe PN6
    print("\n1. RECHERCHE DE LA CLASSE PN6")
    classes_pn6 = ClasseNote.objects.filter(nom__icontains='PN6')
    
    if not classes_pn6.exists():
        print("❌ Aucune classe PN6 trouvée dans ClasseNote")
        # Chercher dans ClasseEleve
        classes_eleve_pn6 = ClasseEleve.objects.filter(nom__icontains='PN6')
        if classes_eleve_pn6.exists():
            print(f"✅ Trouvé {classes_eleve_pn6.count()} classe(s) PN6 dans ClasseEleve:")
            for classe in classes_eleve_pn6:
                print(f"   - {classe.nom} (ID: {classe.id}) - École: {classe.ecole.nom}")
        return
    
    classe_note = classes_pn6.first()
    print(f"✅ Classe trouvée: {classe_note.nom} (ID: {classe_note.id})")
    
    # 2. Vérifier les matières
    print(f"\n2. MATIÈRES DE LA CLASSE")
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"✅ {matieres.count()} matière(s) trouvée(s):")
    for matiere in matieres:
        print(f"   - {matiere.nom} (Coef: {matiere.coefficient})")
    
    # 3. Vérifier les évaluations
    print(f"\n3. ÉVALUATIONS")
    toutes_evaluations = Evaluation.objects.filter(matiere__classe=classe_note)
    print(f"✅ {toutes_evaluations.count()} évaluation(s) au total")
    
    if toutes_evaluations.exists():
        periodes = {}
        for eval in toutes_evaluations:
            if eval.periode not in periodes:
                periodes[eval.periode] = 0
            periodes[eval.periode] += 1
        
        print("   Répartition par période:")
        for periode, count in periodes.items():
            print(f"   - {periode}: {count} évaluation(s)")
    
    # 4. Vérifier spécifiquement OCTOBRE
    print(f"\n4. ÉVALUATIONS OCTOBRE")
    evaluations_octobre = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE')
    print(f"✅ {evaluations_octobre.count()} évaluation(s) pour OCTOBRE")
    
    if evaluations_octobre.exists():
        for eval in evaluations_octobre:
            print(f"   - {eval.matiere.nom}: {eval.titre} (ID: {eval.id})")
    
    # 5. Vérifier les notes
    print(f"\n5. NOTES POUR OCTOBRE")
    notes_octobre = NoteEleve.objects.filter(evaluation__matiere__classe=classe_note, evaluation__periode='OCTOBRE')
    print(f"✅ {notes_octobre.count()} note(s) pour OCTOBRE")
    
    if notes_octobre.exists():
        # Grouper par élève
        notes_par_eleve = {}
        for note in notes_octobre:
            eleve_id = note.eleve.id
            if eleve_id not in notes_par_eleve:
                notes_par_eleve[eleve_id] = {
                    'eleve': note.eleve,
                    'notes': []
                }
            notes_par_eleve[eleve_id]['notes'].append(note)
        
        print(f"   Répartition par élève (premiers 5):")
        for i, (eleve_id, data) in enumerate(list(notes_par_eleve.items())[:5]):
            eleve = data['eleve']
            nb_notes = len(data['notes'])
            print(f"   - {eleve.prenom} {eleve.nom} ({eleve.matricule}): {nb_notes} note(s)")
    
    # 6. Vérifier les élèves
    print(f"\n6. ÉLÈVES DE LA CLASSE")
    try:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if classe_eleve:
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            print(f"✅ {eleves.count()} élève(s) actif(s)")
            
            # Vérifier quelques élèves spécifiques
            eleve_test = eleves.filter(matricule='PN6-031').first()  # DOUSOUBA CONDE
            if eleve_test:
                print(f"\n   Test élève: {eleve_test.prenom} {eleve_test.nom} ({eleve_test.matricule})")
                notes_eleve = NoteEleve.objects.filter(
                    eleve=eleve_test,
                    evaluation__periode='OCTOBRE'
                )
                print(f"   Notes OCTOBRE: {notes_eleve.count()}")
                for note in notes_eleve:
                    print(f"     - {note.evaluation.matiere.nom}: {note.note} (Absent: {note.absent})")
        else:
            print("❌ Classe élève correspondante non trouvée")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des élèves: {e}")
    
    # 7. Test de calcul de moyenne
    print(f"\n7. TEST CALCUL MOYENNE")
    if evaluations_octobre.exists() and notes_octobre.exists():
        # Prendre le premier élève avec des notes
        premier_eleve = notes_octobre.first().eleve
        print(f"   Test avec: {premier_eleve.prenom} {premier_eleve.nom}")
        
        # Calculer manuellement la moyenne
        notes_eleve = NoteEleve.objects.filter(
            eleve=premier_eleve,
            evaluation__periode='OCTOBRE'
        )
        
        total_pondere = 0
        total_coef = 0
        
        for note in notes_eleve:
            coef = float(note.evaluation.coefficient or 1)
            valeur = 0 if (note.absent or note.note is None) else float(note.note)
            total_pondere += valeur * coef
            total_coef += coef
            print(f"     - {note.evaluation.matiere.nom}: {valeur} × {coef} = {valeur * coef}")
        
        if total_coef > 0:
            moyenne = total_pondere / total_coef
            print(f"   Moyenne calculée: {moyenne:.2f}")
        else:
            print("   ❌ Impossible de calculer la moyenne (total_coef = 0)")
    
    print(f"\n🎯 CONCLUSION")
    print("=" * 60)
    
    if not evaluations_octobre.exists():
        print("❌ PROBLÈME IDENTIFIÉ: Aucune évaluation pour la période OCTOBRE")
        print("   SOLUTION: Créer les évaluations pour OCTOBRE ou modifier le filtre")
    elif not notes_octobre.exists():
        print("❌ PROBLÈME IDENTIFIÉ: Aucune note pour la période OCTOBRE")
        print("   SOLUTION: Vérifier l'importation des notes")
    else:
        print("✅ Données présentes, problème probablement dans la vue consulter_notes")

if __name__ == "__main__":
    try:
        diagnostiquer_probleme()
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()
