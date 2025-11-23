#!/usr/bin/env python
"""
Script de diagnostic pour analyser pourquoi les notes de la classe 61 (12 SÉRIE SCIENTIFIQUE) 
ne sont pas trouvées pour la période OCTOBRE
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

def diagnostic_classe_61():
    """Diagnostic complet de la classe 61"""
    print("🔍 DIAGNOSTIC CLASSE 61 - PÉRIODE OCTOBRE")
    print("=" * 60)
    
    # 1. Vérifier l'existence de la classe 61
    print("\n1️⃣ VÉRIFICATION CLASSE 61")
    print("-" * 30)
    
    try:
        classe_note = ClasseNote.objects.get(pk=61)
        print(f"✅ ClasseNote trouvée: {classe_note}")
        print(f"   - ID: {classe_note.id}")
        print(f"   - Nom: {classe_note.nom}")
        print(f"   - Niveau: {classe_note.niveau}")
        print(f"   - Année scolaire: {classe_note.annee_scolaire}")
        print(f"   - École: {classe_note.ecole}")
        print(f"   - Active: {classe_note.actif}")
    except ClasseNote.DoesNotExist:
        print("❌ ClasseNote avec ID 61 n'existe pas")
        return
    
    # 2. Vérifier la classe élève correspondante
    print("\n2️⃣ VÉRIFICATION CLASSE ÉLÈVE CORRESPONDANTE")
    print("-" * 45)
    
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if classe_eleve:
        print(f"✅ ClasseEleve correspondante trouvée: {classe_eleve}")
        print(f"   - ID: {classe_eleve.id}")
        print(f"   - Nom: {classe_eleve.nom}")
        print(f"   - Année scolaire: {classe_eleve.annee_scolaire}")
        print(f"   - École: {classe_eleve.ecole}")
    else:
        print("❌ Aucune ClasseEleve correspondante trouvée")
        print("   Recherche avec critères:")
        print(f"   - nom='{classe_note.nom}'")
        print(f"   - annee_scolaire='{classe_note.annee_scolaire}'")
        print(f"   - ecole='{classe_note.ecole}'")
        
        # Chercher des classes similaires
        print("\n   🔍 Classes élèves similaires:")
        classes_similaires = ClasseEleve.objects.filter(
            nom__icontains="12"
        ).filter(
            nom__icontains="SCIENTIFIQUE"
        )
        for c in classes_similaires:
            print(f"   - {c.id}: {c.nom} ({c.annee_scolaire}) - {c.ecole}")
        
        return
    
    # 3. Vérifier les élèves
    print("\n3️⃣ VÉRIFICATION ÉLÈVES")
    print("-" * 25)
    
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"📊 Nombre d'élèves actifs: {eleves.count()}")
    
    if eleves.exists():
        print("✅ Élèves trouvés:")
        for i, eleve in enumerate(eleves[:5], 1):  # Afficher les 5 premiers
            print(f"   {i}. {eleve.prenom} {eleve.nom} (ID: {eleve.id})")
        if eleves.count() > 5:
            print(f"   ... et {eleves.count() - 5} autres")
    else:
        print("❌ Aucun élève actif trouvé")
        
        # Vérifier tous les statuts
        tous_eleves = Eleve.objects.filter(classe=classe_eleve)
        print(f"   Total élèves (tous statuts): {tous_eleves.count()}")
        for statut in ['ACTIF', 'INACTIF', 'SUSPENDU', 'EXCLU']:
            count = tous_eleves.filter(statut=statut).count()
            if count > 0:
                print(f"   - {statut}: {count}")
    
    # 4. Vérifier les matières
    print("\n4️⃣ VÉRIFICATION MATIÈRES")
    print("-" * 25)
    
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"📊 Nombre de matières actives: {matieres.count()}")
    
    if matieres.exists():
        print("✅ Matières trouvées:")
        for matiere in matieres:
            print(f"   - {matiere.nom} (Coef: {matiere.coefficient})")
    else:
        print("❌ Aucune matière active trouvée")
        
        # Vérifier toutes les matières
        toutes_matieres = MatiereNote.objects.filter(classe=classe_note)
        print(f"   Total matières (toutes): {toutes_matieres.count()}")
        for matiere in toutes_matieres:
            print(f"   - {matiere.nom} (Actif: {matiere.actif})")
    
    # 5. Vérifier les évaluations OCTOBRE
    print("\n5️⃣ VÉRIFICATION ÉVALUATIONS OCTOBRE")
    print("-" * 35)
    
    evaluations_octobre = Evaluation.objects.filter(
        matiere__classe=classe_note,
        periode='OCTOBRE'
    )
    
    print(f"📊 Nombre d'évaluations OCTOBRE: {evaluations_octobre.count()}")
    
    if evaluations_octobre.exists():
        print("✅ Évaluations OCTOBRE trouvées:")
        for eval in evaluations_octobre:
            print(f"   - {eval.titre} ({eval.matiere.nom}) - {eval.date_evaluation}")
            
            # Compter les notes pour cette évaluation
            notes_count = NoteEleve.objects.filter(evaluation=eval).count()
            print(f"     Notes saisies: {notes_count}")
    else:
        print("❌ Aucune évaluation OCTOBRE trouvée")
        
        # Vérifier toutes les périodes
        print("\n   🔍 Évaluations par période:")
        for periode in ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 'MARS', 'AVRIL', 'MAI']:
            count = Evaluation.objects.filter(
                matiere__classe=classe_note,
                periode=periode
            ).count()
            if count > 0:
                print(f"   - {periode}: {count} évaluations")
    
    # 6. Vérifier les notes des élèves pour OCTOBRE
    print("\n6️⃣ VÉRIFICATION NOTES ÉLÈVES OCTOBRE")
    print("-" * 40)
    
    if eleves.exists() and evaluations_octobre.exists():
        premier_eleve = eleves.first()
        print(f"🎯 Test avec élève: {premier_eleve.prenom} {premier_eleve.nom}")
        
        for eval in evaluations_octobre[:3]:  # Tester les 3 premières évaluations
            try:
                note = NoteEleve.objects.get(eleve=premier_eleve, evaluation=eval)
                print(f"   ✅ {eval.titre}: {note.note}/20 (Absent: {note.absent})")
            except NoteEleve.DoesNotExist:
                print(f"   ❌ {eval.titre}: Pas de note saisie")
    
    # 7. Résumé du diagnostic
    print("\n7️⃣ RÉSUMÉ DU DIAGNOSTIC")
    print("-" * 25)
    
    problemes = []
    
    if not classe_eleve:
        problemes.append("❌ Pas de ClasseEleve correspondante")
    
    if eleves.count() == 0:
        problemes.append("❌ Aucun élève actif")
    
    if matieres.count() == 0:
        problemes.append("❌ Aucune matière active")
    
    if evaluations_octobre.count() == 0:
        problemes.append("❌ Aucune évaluation OCTOBRE")
    
    if problemes:
        print("🚨 PROBLÈMES IDENTIFIÉS:")
        for probleme in problemes:
            print(f"   {probleme}")
    else:
        print("✅ Structure de base OK - Problème probablement dans la logique de consultation")
    
    return {
        'classe_note': classe_note,
        'classe_eleve': classe_eleve,
        'nb_eleves': eleves.count() if classe_eleve else 0,
        'nb_matieres': matieres.count(),
        'nb_evaluations_octobre': evaluations_octobre.count(),
        'problemes': problemes
    }

def solutions_recommandees(diagnostic_result):
    """Propose des solutions basées sur le diagnostic"""
    print("\n🔧 SOLUTIONS RECOMMANDÉES")
    print("=" * 30)
    
    if not diagnostic_result['classe_eleve']:
        print("1️⃣ CRÉER LA LIAISON CLASSE ÉLÈVE")
        print("   - Vérifier que la classe existe dans le module élèves")
        print("   - Créer la classe élève avec le même nom et année scolaire")
        print("   - Ou corriger les noms/années pour qu'ils correspondent")
    
    if diagnostic_result['nb_eleves'] == 0:
        print("2️⃣ AJOUTER DES ÉLÈVES")
        print("   - Inscrire des élèves dans la classe")
        print("   - Vérifier que le statut est 'ACTIF'")
    
    if diagnostic_result['nb_matieres'] == 0:
        print("3️⃣ AJOUTER DES MATIÈRES")
        print("   - Créer les matières pour cette classe")
        print("   - Vérifier que les matières sont actives")
    
    if diagnostic_result['nb_evaluations_octobre'] == 0:
        print("4️⃣ CRÉER DES ÉVALUATIONS OCTOBRE")
        print("   - Ajouter des évaluations avec période='OCTOBRE'")
        print("   - Saisir les notes pour ces évaluations")
    
    print("\n💡 COMMANDES UTILES:")
    print("   - Accéder à l'admin Django: /admin/")
    print("   - Créer des évaluations: /notes/saisir/")
    print("   - Gérer les élèves: /eleves/")

if __name__ == "__main__":
    try:
        result = diagnostic_classe_61()
        solutions_recommandees(result)
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        import traceback
        traceback.print_exc()
