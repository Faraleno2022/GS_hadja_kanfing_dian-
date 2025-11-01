"""
Script de diagnostic pour vérifier pourquoi les notes ne s'affichent pas
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe

def diagnostiquer():
    print("\n" + "="*80)
    print("   🔍 DIAGNOSTIC - NOTES NON AFFICHÉES")
    print("="*80)
    
    # Paramètres de test
    classe_id = 6
    eleve_id = 805
    periode = 'TRIMESTRE_1'
    system_type = 'trimestre'
    
    print(f"\n📋 PARAMÈTRES DE TEST:")
    print(f"   - Classe ID: {classe_id}")
    print(f"   - Élève ID: {eleve_id}")
    print(f"   - Période: {periode}")
    print(f"   - Système: {system_type}")
    
    # 1. Vérifier la classe
    print(f"\n1️⃣ VÉRIFICATION DE LA CLASSE")
    print("─" * 80)
    try:
        classe = ClasseNote.objects.get(pk=classe_id)
        print(f"   ✅ Classe trouvée: {classe.nom}")
        print(f"      - Niveau: {classe.get_niveau_display()}")
        print(f"      - Année: {classe.annee_scolaire}")
        print(f"      - Active: {classe.actif}")
    except ClasseNote.DoesNotExist:
        print(f"   ❌ ERREUR: Classe {classe_id} introuvable!")
        return
    
    # 2. Vérifier les matières
    print(f"\n2️⃣ VÉRIFICATION DES MATIÈRES")
    print("─" * 80)
    matieres = MatiereNote.objects.filter(classe=classe, actif=True)
    print(f"   ✅ Matières trouvées: {matieres.count()}")
    for mat in matieres[:3]:
        print(f"      - {mat.nom} (Coef: {mat.coefficient})")
    
    # 3. Vérifier l'élève
    print(f"\n3️⃣ VÉRIFICATION DE L'ÉLÈVE")
    print("─" * 80)
    try:
        eleve = Eleve.objects.get(pk=eleve_id)
        print(f"   ✅ Élève trouvé: {eleve.nom} {eleve.prenom}")
        print(f"      - Matricule: {eleve.matricule}")
        print(f"      - Classe: {eleve.classe.nom}")
        print(f"      - Statut: {eleve.statut}")
    except Eleve.DoesNotExist:
        print(f"   ❌ ERREUR: Élève {eleve_id} introuvable!")
        return
    
    # 4. Vérifier les évaluations
    print(f"\n4️⃣ VÉRIFICATION DES ÉVALUATIONS")
    print("─" * 80)
    
    total_evals = 0
    for matiere in matieres:
        evals = Evaluation.objects.filter(
            matiere=matiere,
            matiere__classe=classe,
            periode=periode
        )
        
        if evals.exists():
            total_evals += evals.count()
            print(f"   ✅ {matiere.nom}: {evals.count()} évaluation(s)")
            for ev in evals[:2]:
                print(f"      - {ev.titre} ({ev.get_type_evaluation_display()})")
        else:
            print(f"   ⚠️  {matiere.nom}: Aucune évaluation pour {periode}")
    
    print(f"\n   Total évaluations: {total_evals}")
    
    # 5. Vérifier les notes de l'élève
    print(f"\n5️⃣ VÉRIFICATION DES NOTES DE L'ÉLÈVE")
    print("─" * 80)
    
    notes_trouvees = 0
    for matiere in matieres[:5]:
        evals = Evaluation.objects.filter(
            matiere=matiere,
            matiere__classe=classe,
            periode=periode
        )
        
        print(f"\n   📖 {matiere.nom}:")
        
        devoirs = []
        compositions = []
        
        for ev in evals:
            try:
                note = NoteEleve.objects.get(eleve=eleve, evaluation=ev)
                notes_trouvees += 1
                
                if ev.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                    compositions.append(note.note)
                    print(f"      ✅ {ev.titre}: {note.note}/20 (Composition)")
                else:
                    devoirs.append(note.note)
                    print(f"      ✅ {ev.titre}: {note.note}/20 (Devoir)")
                    
            except NoteEleve.DoesNotExist:
                print(f"      ❌ {ev.titre}: PAS DE NOTE")
        
        # Calculer les moyennes
        if devoirs:
            moy_dev = sum(devoirs) / len(devoirs)
            print(f"      → Moyenne Continue: {moy_dev:.2f}")
        else:
            print(f"      → Moyenne Continue: N/A")
        
        if compositions:
            moy_comp = sum(compositions) / len(compositions)
            print(f"      → Composition: {moy_comp:.2f}")
        else:
            print(f"      → Composition: N/A")
    
    print(f"\n   Total notes trouvées: {notes_trouvees}")
    
    # 6. Diagnostiquer le problème
    print(f"\n6️⃣ DIAGNOSTIC DU PROBLÈME")
    print("─" * 80)
    
    if total_evals == 0:
        print("   ❌ PROBLÈME IDENTIFIÉ: Aucune évaluation pour la période sélectionnée")
        print(f"      Solution: Créer des évaluations pour {periode}")
    elif notes_trouvees == 0:
        print("   ❌ PROBLÈME IDENTIFIÉ: Aucune note saisie pour cet élève")
        print("      Solution: Saisir des notes pour cet élève")
    else:
        print("   ✅ Les données sont présentes")
        print(f"      - {total_evals} évaluations trouvées")
        print(f"      - {notes_trouvees} notes trouvées")
        print("\n      Vérifiez:")
        print("      1. Que la période est bien sélectionnée dans l'URL")
        print("      2. Que l'élève est bien sélectionné")
        print("      3. Que le system_type correspond (trimestre/semestre/mensuel)")
    
    # 7. Tester les filtres de la vue
    print(f"\n7️⃣ TEST DES FILTRES DE LA VUE")
    print("─" * 80)
    
    print("\n   Test du filtre principal:")
    test_evals = Evaluation.objects.filter(
        matiere__in=matieres,
        matiere__classe=classe,
        periode=periode
    )
    print(f"   ✅ Évaluations filtrées: {test_evals.count()}")
    
    print("\n   Test des notes:")
    test_notes = NoteEleve.objects.filter(
        eleve=eleve,
        evaluation__in=test_evals
    )
    print(f"   ✅ Notes filtrées: {test_notes.count()}")
    
    if test_notes.exists():
        print("\n   Exemple de notes:")
        for n in test_notes[:3]:
            print(f"      - {n.evaluation.matiere.nom}: {n.note}/20")
    
    # 8. Générer l'URL de test
    print(f"\n8️⃣ URL DE TEST")
    print("─" * 80)
    url = f"http://127.0.0.1:8001/notes/bulletins/?classe_id={classe_id}&system_type={system_type}&periode={periode}&eleve_id={eleve_id}"
    print(f"   {url}")
    
    print("\n" + "="*80)
    print("   FIN DU DIAGNOSTIC")
    print("="*80 + "\n")

if __name__ == '__main__':
    diagnostiquer()
