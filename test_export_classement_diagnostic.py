"""
Script de diagnostic pour l'export de classement
Ce script vérifie les notes disponibles dans la base de données
"""
import os
import django
import sys

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote, NoteEleve, Evaluation
from eleves.models import Eleve, Classe as ClasseEleve

def diagnostiquer_notes(nom_classe):
    """Diagnostiquer les notes disponibles pour une classe"""
    
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC DES NOTES POUR LA CLASSE: {nom_classe}")
    print(f"{'='*80}\n")
    
    # 1. Trouver la classe dans le système de notes
    try:
        classe_note = ClasseNote.objects.filter(nom__icontains=nom_classe).first()
        if not classe_note:
            print(f"❌ ClasseNote non trouvée pour '{nom_classe}'")
            print("\nClasses disponibles dans le système de notes:")
            for cn in ClasseNote.objects.all()[:10]:
                print(f"   - {cn.nom} ({cn.annee_scolaire})")
            return
        
        print(f"✅ ClasseNote trouvée: {classe_note.nom}")
        print(f"   - ID: {classe_note.id}")
        print(f"   - Année scolaire: {classe_note.annee_scolaire}")
        print(f"   - École: {classe_note.ecole.nom}")
    except Exception as e:
        print(f"❌ Erreur lors de la recherche de ClasseNote: {e}")
        return
    
    # 2. Trouver la classe élève correspondante
    try:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if not classe_eleve:
            print(f"❌ ClasseEleve non trouvée")
            print("\nClasses élèves disponibles:")
            for ce in ClasseEleve.objects.filter(ecole=classe_note.ecole)[:10]:
                print(f"   - {ce.nom} ({ce.annee_scolaire})")
            return
        
        print(f"✅ ClasseEleve trouvée: {classe_eleve.nom}")
        print(f"   - ID: {classe_eleve.id}")
    except Exception as e:
        print(f"❌ Erreur lors de la recherche de ClasseEleve: {e}")
        return
    
    # 3. Compter les élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"\n📊 Nombre d'élèves actifs: {eleves.count()}")
    
    if eleves.count() > 0:
        print(f"\nPremiers élèves:")
        for eleve in eleves[:5]:
            print(f"   - {eleve.matricule}: {eleve.nom} {eleve.prenom}")
    
    # 4. Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"\n📚 Nombre de matières actives: {matieres.count()}")
    
    if matieres.count() > 0:
        print(f"\nMatières:")
        for matiere in matieres:
            print(f"   - {matiere.nom} ({matiere.code}) - Coef: {matiere.coefficient}")
    
    # 5. Vérifier les évaluations (système moderne)
    evaluations = Evaluation.objects.filter(matiere__classe=classe_note)
    print(f"\n📝 Nombre d'évaluations: {evaluations.count()}")
    
    if evaluations.count() > 0:
        print(f"\nDernières évaluations:")
        periodes_evaluations = set()
        for evaluation in evaluations[:10]:
            periodes_evaluations.add(evaluation.periode)
            print(f"   - {evaluation.titre} ({evaluation.matiere.nom})")
            print(f"     Type: {evaluation.type_evaluation}, Période: {evaluation.periode}")
        
        print(f"\nPériodes disponibles dans les évaluations: {', '.join(sorted(periodes_evaluations))}")
    
    # 6. Vérifier les notes élèves (système moderne)
    if eleves.count() > 0 and evaluations.count() > 0:
        premier_eleve = eleves.first()
        notes_eleve = NoteEleve.objects.filter(
            eleve=premier_eleve,
            evaluation__matiere__classe=classe_note
        )
        print(f"\n📋 Nombre de notes pour {premier_eleve.prenom} {premier_eleve.nom}: {notes_eleve.count()}")
        
        if notes_eleve.count() > 0:
            print(f"\nDétail des notes:")
            for note in notes_eleve[:5]:
                status = "Absent" if note.absent else f"{note.note}/{note.evaluation.note_sur}"
                print(f"   - {note.evaluation.matiere.nom}: {status}")
    
    # 7. Vérifier les notes mensuelles (ancien système)
    notes_mensuelles = NoteMensuelle.objects.filter(
        eleve__classe=classe_eleve,
        matiere__classe=classe_note
    )
    print(f"\n📅 Nombre de notes mensuelles: {notes_mensuelles.count()}")
    
    if notes_mensuelles.count() > 0:
        mois_disponibles = set()
        annees_disponibles = set()
        for note in notes_mensuelles:
            mois_disponibles.add(note.mois)
            annees_disponibles.add(note.annee_scolaire)
        
        print(f"\nMois disponibles: {', '.join(sorted(mois_disponibles))}")
        print(f"Années scolaires: {', '.join(sorted(annees_disponibles))}")
    
    # 8. Vérifier les notes de composition (ancien système)
    notes_composition = CompositionNote.objects.filter(
        eleve__classe=classe_eleve,
        matiere__classe=classe_note
    )
    print(f"\n🏆 Nombre de notes de composition: {notes_composition.count()}")
    
    if notes_composition.count() > 0:
        periodes_disponibles = set()
        annees_disponibles = set()
        for note in notes_composition:
            periodes_disponibles.add(note.periode)
            annees_disponibles.add(note.annee_scolaire)
        
        print(f"\nPériodes disponibles: {', '.join(sorted(periodes_disponibles))}")
        print(f"Années scolaires: {', '.join(sorted(annees_disponibles))}")
    
    # 9. Résumé et recommandations
    print(f"\n{'='*80}")
    print("RÉSUMÉ ET RECOMMANDATIONS")
    print(f"{'='*80}\n")
    
    if eleves.count() == 0:
        print("❌ PROBLÈME: Aucun élève actif dans la classe")
        print("   → Vérifier que des élèves sont bien inscrits dans cette classe")
    
    if matieres.count() == 0:
        print("❌ PROBLÈME: Aucune matière active pour cette classe")
        print("   → Créer des matières pour cette classe dans le système de notes")
    
    total_notes = notes_eleve.count() + notes_mensuelles.count() + notes_composition.count()
    
    if total_notes == 0:
        print("❌ PROBLÈME: Aucune note saisie")
        print("   → Les notes doivent être saisies avant de pouvoir exporter le classement")
    elif notes_eleve.count() > 0:
        print(f"✅ Système moderne utilisé ({notes_eleve.count()} notes)")
        print(f"   → Utiliser les périodes: {', '.join(sorted(periodes_evaluations))}")
    elif notes_mensuelles.count() > 0 or notes_composition.count() > 0:
        print(f"✅ Ancien système utilisé")
        if notes_mensuelles.count() > 0:
            print(f"   → Notes mensuelles disponibles pour: {', '.join(sorted(mois_disponibles))}")
        if notes_composition.count() > 0:
            print(f"   → Notes de composition disponibles pour: {', '.join(sorted(periodes_disponibles))}")
    
    print()


if __name__ == '__main__':
    # Liste des classes à diagnostiquer
    classes_a_tester = [
        "12 SÉRIE SCIENTIFIQUE",
        "12 SERIE SCIENTIFIQUE",
        "12ème",
        "Terminale",
    ]
    
    # Chercher la première classe qui existe
    for nom_classe in classes_a_tester:
        classe_note = ClasseNote.objects.filter(nom__icontains=nom_classe).first()
        if classe_note:
            diagnostiquer_notes(classe_note.nom)
            break
    else:
        print("\n❌ Aucune classe trouvée dans les noms testés")
        print("\nVoici toutes les classes disponibles:")
        for cn in ClasseNote.objects.all():
            print(f"   - {cn.nom} ({cn.annee_scolaire})")
