"""
Test pour vérifier le problème des matières sans notes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve
from decimal import Decimal

def test_eleve_matieres_sans_notes():
    """
    Teste un élève avec des matières sans notes
    """
    print("\n" + "="*80)
    print("TEST: Élève avec matières sans notes")
    print("="*80 + "\n")
    
    # Trouver une classe
    classe_note = ClasseNote.objects.first()
    if not classe_note:
        print("❌ Aucune classe trouvée")
        return
    
    print(f"📚 Classe: {classe_note.nom}")
    
    # Trouver la classe élève correspondante
    classe_eleve = ClasseEleve.objects.filter(
        nom__icontains=classe_note.nom.split()[0],
        annee_scolaire=classe_note.annee_scolaire
    ).first()
    
    if not classe_eleve:
        print("❌ Classe élève introuvable")
        return
    
    # Trouver un élève
    eleve = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').first()
    if not eleve:
        print("❌ Aucun élève trouvé")
        return
    
    print(f"👤 Élève: {eleve.prenom} {eleve.nom}\n")
    
    # Récupérer toutes les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"📖 Nombre de matières: {matieres.count()}\n")
    
    periode = 'OCTOBRE'
    
    # Analyser chaque matière
    print(f"{'Matière':<25} {'Coef':<6} {'Notes':<10} {'Moyenne':<10} {'Points'}")
    print("-" * 80)
    
    total_points_avec_notes = Decimal('0')
    total_coef_avec_notes = Decimal('0')
    
    total_points_toutes_matieres = Decimal('0')
    total_coef_toutes_matieres = Decimal('0')
    
    matieres_sans_notes = 0
    matieres_avec_notes = 0
    
    for matiere in matieres:
        # Récupérer les évaluations
        evaluations = Evaluation.objects.filter(
            matiere=matiere,
            periode=periode
        )
        
        # Calculer la moyenne
        total = Decimal('0')
        count = 0
        
        for evaluation in evaluations:
            try:
                note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                if note_obj.note is not None and not note_obj.absent:
                    total += Decimal(str(note_obj.note))
                    count += 1
            except NoteEleve.DoesNotExist:
                pass
        
        if count > 0:
            moyenne = total / count
            points = moyenne * matiere.coefficient
            
            # Méthode 1: Ne compter que les matières avec notes
            total_points_avec_notes += points
            total_coef_avec_notes += matiere.coefficient
            
            # Méthode 2: Compter toutes les matières
            total_points_toutes_matieres += points
            total_coef_toutes_matieres += matiere.coefficient
            
            print(f"{matiere.nom:<25} {matiere.coefficient:<6.1f} {count:<10} {float(moyenne):<10.2f} {float(points):.2f}")
            matieres_avec_notes += 1
        else:
            # Pas de notes
            # Méthode 2: Compter comme 0
            total_points_toutes_matieres += Decimal('0')
            total_coef_toutes_matieres += matiere.coefficient
            
            print(f"{matiere.nom:<25} {matiere.coefficient:<6.1f} {'0':<10} {'-':<10} {'0.00'}")
            matieres_sans_notes += 1
    
    print("-" * 80)
    print(f"\n📊 Résumé:")
    print(f"   Matières avec notes: {matieres_avec_notes}")
    print(f"   Matières sans notes: {matieres_sans_notes}")
    print(f"   Total matières: {matieres.count()}\n")
    
    # Calculer les deux moyennes
    if total_coef_avec_notes > 0:
        moyenne_methode1 = total_points_avec_notes / total_coef_avec_notes
        print(f"❌ MÉTHODE 1 (ne compte que les matières avec notes):")
        print(f"   Total points: {float(total_points_avec_notes):.2f}")
        print(f"   Total coefficients: {float(total_coef_avec_notes):.1f}")
        print(f"   Moyenne générale: {float(moyenne_methode1):.2f}/20")
        print(f"   → PROBLÈME: Moyenne artificiellement élevée!\n")
    
    if total_coef_toutes_matieres > 0:
        moyenne_methode2 = total_points_toutes_matieres / total_coef_toutes_matieres
        print(f"✅ MÉTHODE 2 (compte toutes les matières, sans notes = 0):")
        print(f"   Total points: {float(total_points_toutes_matieres):.2f}")
        print(f"   Total coefficients: {float(total_coef_toutes_matieres):.1f}")
        print(f"   Moyenne générale: {float(moyenne_methode2):.2f}/20")
        print(f"   → CORRECT: Reflète la réalité!\n")
    
    # Calculer la différence
    if total_coef_avec_notes > 0 and total_coef_toutes_matieres > 0:
        difference = float(moyenne_methode1 - moyenne_methode2)
        print(f"🔴 DIFFÉRENCE: {difference:.2f} points")
        print(f"   La moyenne augmente de {difference:.2f} points avec la méthode incorrecte!\n")
    
    print("="*80)
    print("CONCLUSION:")
    if matieres_sans_notes > 0:
        print(f"⚠️  Cet élève a {matieres_sans_notes} matière(s) sans notes")
        print(f"⚠️  Sa moyenne est GONFLÉE de {difference:.2f} points dans le bulletin")
        print(f"⚠️  Il faut corriger le code pour compter toutes les matières!")
    else:
        print(f"✅ Cet élève a des notes dans toutes les matières")
        print(f"✅ Pas de problème de cohérence")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_eleve_matieres_sans_notes()
