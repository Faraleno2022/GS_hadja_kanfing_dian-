"""
Script pour créer des données de test complètes pour le bulletin
"""

import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe
from django.contrib.auth.models import User
from decimal import Decimal
import random

def creer_notes_test():
    """Créer des notes de test pour vérifier les calculs"""
    print("\n" + "="*70)
    print("   📝 CRÉATION DE NOTES DE TEST")
    print("="*70)
    
    # Récupérer une classe
    classe_note = ClasseNote.objects.filter(actif=True).first()
    if not classe_note:
        print("❌ Aucune classe active")
        return
    
    print(f"\n✅ Classe: {classe_note.nom}")
    
    # Récupérer les élèves
    try:
        classe_eleve = Classe.objects.get(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire
        )
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:3]
        print(f"✅ Élèves trouvés: {eleves.count()}")
        
    except Classe.DoesNotExist:
        print("❌ Classe élève non trouvée")
        return
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)[:3]
    print(f"✅ Matières: {matieres.count()}")
    
    # Récupérer un utilisateur pour créer les notes
    user = User.objects.first()
    
    periode = 'TRIMESTRE_1'
    notes_creees = 0
    
    for matiere in matieres:
        print(f"\n📖 Matière: {matiere.nom}")
        
        # Vérifier les évaluations existantes
        evals = Evaluation.objects.filter(matiere=matiere, periode=periode)
        
        if not evals.exists():
            # Créer des évaluations de test
            print(f"   Création d'évaluations...")
            
            # Créer 2 devoirs
            for i in range(2):
                eval_devoir = Evaluation.objects.create(
                    matiere=matiere,
                    titre=f"Devoir {i+1} - {periode}",
                    type_evaluation='DEVOIR',
                    periode=periode,
                    date_evaluation=date(2024, 10, 10+i*7),
                    note_sur=20,
                    coefficient=1,
                    cree_par=user
                )
                print(f"   ✅ {eval_devoir.titre}")
            
            # Créer 1 composition
            eval_compo = Evaluation.objects.create(
                matiere=matiere,
                titre=f"Composition - {periode}",
                type_evaluation='COMPOSITION',
                periode=periode,
                date_evaluation=date(2024, 11, 15),
                note_sur=20,
                coefficient=2,
                cree_par=user
            )
            print(f"   ✅ {eval_compo.titre}")
            
            evals = Evaluation.objects.filter(matiere=matiere, periode=periode)
        
        # Créer des notes pour chaque élève
        for eleve in eleves:
            for evaluation in evals:
                # Vérifier si la note existe déjà
                note_existe = NoteEleve.objects.filter(
                    eleve=eleve,
                    evaluation=evaluation
                ).exists()
                
                if not note_existe:
                    # Générer une note aléatoire entre 10 et 20
                    if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                        # Les compositions sont généralement un peu plus hautes
                        note_value = Decimal(str(random.uniform(12, 19)))
                    else:
                        # Les devoirs varient plus
                        note_value = Decimal(str(random.uniform(10, 18)))
                    
                    note_value = round(note_value, 2)
                    
                    NoteEleve.objects.create(
                        evaluation=evaluation,
                        eleve=eleve,
                        note=note_value,
                        absent=False,
                        cree_par=user
                    )
                    notes_creees += 1
    
    print(f"\n✅ {notes_creees} notes créées")
    
    # Afficher un exemple de calcul
    if eleves.exists():
        eleve_test = eleves.first()
        print(f"\n" + "="*70)
        print(f"   📊 EXEMPLE DE CALCUL POUR: {eleve_test.nom} {eleve_test.prenom}")
        print("="*70)
        
        total_points = Decimal('0')
        total_coef = Decimal('0')
        
        for matiere in matieres:
            evals = Evaluation.objects.filter(matiere=matiere, periode=periode)
            
            # Séparer devoirs et compositions
            total_dev = Decimal('0')
            count_dev = 0
            total_comp = Decimal('0')
            count_comp = 0
            
            for ev in evals:
                try:
                    n = NoteEleve.objects.get(eleve=eleve_test, evaluation=ev)
                    if n.note is not None and not n.absent:
                        if ev.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                            total_comp += n.note
                            count_comp += 1
                        else:
                            total_dev += n.note
                            count_dev += 1
                except NoteEleve.DoesNotExist:
                    pass
            
            moy_cont = round(float(total_dev / count_dev), 2) if count_dev > 0 else None
            moy_comp = round(float(total_comp / count_comp), 2) if count_comp > 0 else None
            
            # Formule guinéenne
            moy_mat = None
            if moy_cont and moy_comp:
                moy_mat = round((moy_cont + moy_comp * 2) / 3, 2)
            elif moy_comp:
                moy_mat = moy_comp
            elif moy_cont:
                moy_mat = moy_cont
            
            if moy_mat:
                points = Decimal(str(moy_mat)) * matiere.coefficient
                total_points += points
                total_coef += matiere.coefficient
                
                print(f"{matiere.nom[:25]:25} | MC:{moy_cont or 0:5.2f} | Comp:{moy_comp or 0:5.2f} | Moy:{moy_mat:5.2f} | Coef:{float(matiere.coefficient):3} | Pts:{float(points):6.2f}")
        
        if total_coef > 0:
            moy_gen = round(float(total_points / total_coef), 2)
            print("─" * 70)
            print(f"{'TOTAL':25} | Points: {float(total_points):6.2f} | Coef: {float(total_coef):3} | Moyenne: {moy_gen:5.2f}/20")
            
            # Mention
            if moy_gen >= 16:
                mention = "Très Bien"
            elif moy_gen >= 14:
                mention = "Bien"
            elif moy_gen >= 12:
                mention = "Assez Bien"
            elif moy_gen >= 10:
                mention = "Passable"
            else:
                mention = "Insuffisant"
            
            print(f"\n✅ MENTION: {mention}")
            
            # URL de test
            url = f"http://127.0.0.1:8001/notes/bulletins/?classe_id={classe_note.id}&system_type=trimestre&periode={periode}&eleve_id={eleve_test.id}"
            print(f"\n🔗 URL DE TEST:")
            print(f"   {url}")

def main():
    print("\n" + "="*70)
    print("   🧪 CRÉATION DE DONNÉES DE TEST POUR LE BULLETIN")
    print("="*70)
    
    try:
        creer_notes_test()
        
        print("\n" + "="*70)
        print("   ✅ DONNÉES DE TEST CRÉÉES AVEC SUCCÈS")
        print("="*70)
        print("\n💡 Utilisez l'URL affichée ci-dessus pour tester le bulletin")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
