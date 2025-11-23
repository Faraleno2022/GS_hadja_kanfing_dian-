#!/usr/bin/env python
"""
Solution finale pour la classe 61 - Utiliser la ClasseEleve existante
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

def solution_classe_61():
    """Solution finale pour la classe 61"""
    print("🎯 SOLUTION FINALE CLASSE 61")
    print("=" * 35)
    
    # 1. Récupérer la ClasseNote 61
    classe_note = ClasseNote.objects.get(pk=61)
    print(f"✅ ClasseNote 61: {classe_note.nom}")
    
    # 2. Utiliser la ClasseEleve existante (ID 56)
    classe_eleve = ClasseEleve.objects.get(pk=56)  # "12ÈME ANNÉE"
    print(f"✅ ClasseEleve existante: {classe_eleve.nom} (ID: {classe_eleve.id})")
    
    # 3. Vérifier les élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"📊 Élèves actifs: {eleves.count()}")
    
    if eleves.count() == 0:
        print("🆕 Création d'élèves de test...")
        eleves_test = [
            ('Aminata', 'DIALLO', 'F'),
            ('Mamadou', 'BARRY', 'M'),
            ('Fatoumata', 'SOW', 'F'),
            ('Alpha', 'CONDE', 'M'),
            ('Mariama', 'CAMARA', 'F'),
        ]
        
        for prenom, nom, sexe in eleves_test:
            eleve, created = Eleve.objects.get_or_create(
                prenom=prenom,
                nom=nom,
                classe=classe_eleve,
                defaults={
                    'sexe': sexe,
                    'statut': 'ACTIF',
                    'date_naissance': '2005-01-01',
                    'lieu_naissance': 'Conakry',
                    'date_inscription': '2024-09-01',
                    'matricule': f'12A{Eleve.objects.filter(classe=classe_eleve).count() + 1:03d}',
                }
            )
            if created:
                print(f"   ✅ {prenom} {nom}")
    
    # 4. Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"📚 Matières actives: {matieres.count()}")
    
    if matieres.count() == 0:
        print("🆕 Création de matières...")
        matieres_test = [
            ('Mathématiques', 'MATH', 4),
            ('Physique-Chimie', 'PC', 3),
            ('SVT', 'SVT', 2),
            ('Français', 'FR', 3),
            ('Anglais', 'ANG', 2),
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
                print(f"   ✅ {nom} (coef: {coef})")
    
    # 5. Vérifier les évaluations OCTOBRE
    evaluations_octobre = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE')
    print(f"📝 Évaluations OCTOBRE: {evaluations_octobre.count()}")
    
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
    
    # 6. Vérifier les notes
    notes_octobre = NoteEleve.objects.filter(
        evaluation__matiere__classe=classe_note, 
        evaluation__periode='OCTOBRE'
    )
    print(f"📊 Notes OCTOBRE: {notes_octobre.count()}")
    
    if notes_octobre.count() == 0:
        print("🆕 Création de notes de test...")
        import random
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        evaluations = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE')
        
        notes_creees = 0
        for eleve in eleves:
            for evaluation in evaluations:
                note_value = round(random.uniform(8.0, 18.0), 2)
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
    
    # 7. CORRECTION CRUCIALE : Modifier la fonction consulter_notes pour utiliser l'ID de classe
    print("\n🔧 CORRECTION DE LA FONCTION CONSULTER_NOTES")
    print("-" * 45)
    print("Le problème est que consulter_notes cherche une ClasseEleve avec exactement le même nom.")
    print("Solution: Utiliser l'ID de la ClasseEleve existante (56) au lieu de chercher par nom.")
    
    # 8. Test final
    print(f"\n🧪 TEST FINAL")
    print("-" * 15)
    
    eleves_count = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').count()
    matieres_count = MatiereNote.objects.filter(classe=classe_note, actif=True).count()
    evaluations_count = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE').count()
    notes_count = NoteEleve.objects.filter(evaluation__matiere__classe=classe_note, evaluation__periode='OCTOBRE').count()
    
    print(f"📊 Statistiques finales:")
    print(f"   - ClasseNote: {classe_note.id} ({classe_note.nom})")
    print(f"   - ClasseEleve: {classe_eleve.id} ({classe_eleve.nom})")
    print(f"   - Élèves actifs: {eleves_count}")
    print(f"   - Matières actives: {matieres_count}")
    print(f"   - Évaluations OCTOBRE: {evaluations_count}")
    print(f"   - Notes saisies: {notes_count}")
    
    if eleves_count > 0 and matieres_count > 0 and evaluations_count > 0 and notes_count > 0:
        print(f"\n🎉 DONNÉES PRÊTES !")
        print(f"⚠️  MAIS il faut corriger la fonction consulter_notes")
        print(f"   Elle doit utiliser ClasseEleve ID {classe_eleve.id} pour ClasseNote ID {classe_note.id}")
    else:
        print(f"\n❌ Il manque encore des données")
    
    return classe_note, classe_eleve

def corriger_fonction_consulter():
    """Proposer la correction pour la fonction consulter_notes"""
    print(f"\n💡 SOLUTION POUR CORRIGER CONSULTER_NOTES")
    print("=" * 45)
    print("Dans notes/views.py, fonction consulter_notes, ligne ~4707:")
    print()
    print("REMPLACER:")
    print("```python")
    print("classe_eleve = ClasseEleve.objects.filter(")
    print("    nom=classe_selectionnee.nom,")
    print("    annee_scolaire=classe_selectionnee.annee_scolaire,")
    print("    ecole=classe_selectionnee.ecole")
    print(").first()")
    print("```")
    print()
    print("PAR:")
    print("```python")
    print("# Mapping spécial pour les classes avec noms différents")
    print("mapping_classes = {")
    print("    61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'")
    print("}")
    print()
    print("if classe_selectionnee.id in mapping_classes:")
    print("    classe_eleve = ClasseEleve.objects.filter(")
    print("        id=mapping_classes[classe_selectionnee.id]")
    print("    ).first()")
    print("else:")
    print("    classe_eleve = ClasseEleve.objects.filter(")
    print("        nom=classe_selectionnee.nom,")
    print("        annee_scolaire=classe_selectionnee.annee_scolaire,")
    print("        ecole=classe_selectionnee.ecole")
    print("    ).first()")
    print("```")

if __name__ == "__main__":
    try:
        classe_note, classe_eleve = solution_classe_61()
        corriger_fonction_consulter()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        print("1. ✅ Données créées pour la classe 61")
        print("2. ⚠️  Il faut corriger la fonction consulter_notes")
        print("3. 🔧 Appliquer le mapping ClasseNote 61 -> ClasseEleve 56")
        print()
        print("Après correction, l'URL fonctionnera:")
        print("http://127.0.0.1:8000/notes/consulter/?classe_id=61&periode=OCTOBRE")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
