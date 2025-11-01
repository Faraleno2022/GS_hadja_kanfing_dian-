"""
Test pour voir exactement ce qui est envoyé au template
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve
from decimal import Decimal

def simuler_bulletin():
    print("\n" + "="*80)
    print("   🔍 SIMULATION DE CE QUI EST ENVOYÉ AU TEMPLATE")
    print("="*80)
    
    # Paramètres
    classe_id = 6
    eleve_id = 805
    periode = 'TRIMESTRE_1'
    system_type = 'trimestre'
    
    # Récupérer les données
    classe_selectionnee = ClasseNote.objects.get(pk=classe_id)
    eleve_selectionne = Eleve.objects.get(pk=eleve_id)
    matieres = MatiereNote.objects.filter(classe=classe_selectionnee, actif=True)
    
    print(f"\n📋 Classe: {classe_selectionnee.nom}")
    print(f"👤 Élève: {eleve_selectionne.nom} {eleve_selectionne.prenom}")
    print(f"📅 Période: {periode}")
    print(f"🔧 Système: {system_type}")
    
    print("\n" + "="*80)
    print("   DONNÉES ENVOYÉES AU TEMPLATE (bulletin_data['matieres_notes'])")
    print("="*80)
    
    matieres_notes = []
    total_points = Decimal('0')
    total_coefficients = Decimal('0')
    
    for matiere in matieres:
        # Simulation exacte du code de la vue
        moyenne_continue = None
        note_composition = None
        
        if periode and eleve_selectionne:
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                matiere__classe=classe_selectionnee,
                periode=periode
            ).order_by('date_evaluation')
            
            total_devoirs = Decimal('0')
            count_devoirs = 0
            total_compo = Decimal('0')
            count_compo = 0
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve_selectionne, evaluation=evaluation)
                    if note_obj.note is not None and not note_obj.absent:
                        if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                            total_compo += Decimal(str(note_obj.note))
                            count_compo += 1
                        else:
                            total_devoirs += Decimal(str(note_obj.note))
                            count_devoirs += 1
                except NoteEleve.DoesNotExist:
                    pass
            
            if count_devoirs > 0:
                moyenne_continue = round(float(total_devoirs / count_devoirs), 2)
            
            if count_compo > 0:
                note_composition = round(float(total_compo / count_compo), 2)
        
        # Calculer la moyenne matière
        moyenne_matiere = None
        if system_type == 'mensuel':
            moyenne_matiere = moyenne_continue
        elif moyenne_continue is not None and note_composition is not None:
            moyenne_matiere = round((moyenne_continue + note_composition * 2) / 3, 2)
        elif note_composition is not None:
            moyenne_matiere = note_composition
        elif moyenne_continue is not None:
            moyenne_matiere = moyenne_continue
        
        # Calculer les points
        points = None
        if moyenne_matiere is not None:
            points = round(moyenne_matiere * float(matiere.coefficient), 2)
            total_points += Decimal(str(moyenne_matiere)) * matiere.coefficient
            total_coefficients += matiere.coefficient
        
        # Préparer les notes pour l'affichage
        notes_matiere = []
        if system_type in ['trimestre', 'semestre']:
            notes_matiere = [
                {'note': moyenne_continue, 'absent': False},
                {'note': note_composition, 'absent': False}
            ]
        elif system_type == 'mensuel':
            notes_matiere = [
                {'note': moyenne_continue, 'absent': False}
            ]
        
        # Afficher ce qui sera dans le template
        print(f"\n📖 {matiere.nom}")
        print(f"   Coefficient: {matiere.coefficient}")
        print(f"   notes_matiere (ce qui va dans le template):")
        if notes_matiere:
            for i, n in enumerate(notes_matiere):
                col_name = "Moy. Continue" if i == 0 else "Composition"
                if n['note'] is not None:
                    print(f"      - {col_name}: {n['note']:.2f}")
                else:
                    print(f"      - {col_name}: None (affichera '-')")
        else:
            print(f"      - Liste vide (affichera '-')")
        
        print(f"   Moyenne matière: {moyenne_matiere if moyenne_matiere else '-'}")
        print(f"   Points: {points if points else '-'}")
        
        matieres_notes.append({
            'matiere': matiere,
            'notes': notes_matiere,
            'moyenne': moyenne_matiere,
            'coefficient': matiere.coefficient,
            'points': points,
        })
    
    # Résumé final
    print("\n" + "="*80)
    print("   RÉSUMÉ FINAL")
    print("="*80)
    
    matieres_avec_notes = sum(1 for m in matieres_notes if any(n['note'] is not None for n in m['notes']))
    matieres_sans_notes = len(matieres_notes) - matieres_avec_notes
    
    print(f"\n📊 Matières avec notes affichables: {matieres_avec_notes}/{len(matieres_notes)}")
    print(f"⚠️  Matières sans notes (afficheront '-'): {matieres_sans_notes}/{len(matieres_notes)}")
    
    if total_coefficients > 0:
        moyenne_generale = float(total_points / total_coefficients)
        print(f"\n✅ Total Points: {float(total_points):.2f}")
        print(f"✅ Total Coefficients: {float(total_coefficients)}")
        print(f"✅ Moyenne Générale: {moyenne_generale:.2f}/20")
    else:
        print(f"\n❌ Aucune moyenne calculable (total_coefficients = 0)")
    
    print("\n" + "="*80)
    print("   CONCLUSION")
    print("="*80)
    
    if matieres_avec_notes > 0:
        print(f"\n✅ {matieres_avec_notes} matière(s) devraient afficher des notes")
        print(f"⚠️  {matieres_sans_notes} matière(s) afficheront '-' (pas de notes saisies)")
        print("\nSi vous ne voyez AUCUNE note dans le bulletin:")
        print("   1. Vérifiez que l'URL contient bien tous les paramètres:")
        print("      - classe_id=6")
        print("      - system_type=trimestre")
        print("      - periode=TRIMESTRE_1")
        print("      - eleve_id=805")
        print("   2. Vérifiez la console du navigateur pour des erreurs JavaScript")
        print("   3. Vérifiez les logs du serveur Django")
    else:
        print("\n❌ PROBLÈME: Aucune matière n'a de notes à afficher")
        print("   Raison: Aucune note n'a été saisie pour cet élève/période")
        print("   Solution: Utiliser creer_donnees_test.py pour créer des notes")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    simuler_bulletin()
