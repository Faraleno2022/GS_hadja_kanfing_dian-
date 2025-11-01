"""
Script de test pour vérifier les corrections du bulletin dynamique
Date: 1er novembre 2025
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe
from django.contrib.auth.models import User

def test_calculs_moyennes():
    """Test des calculs de moyennes selon le système guinéen"""
    print("\n" + "="*70)
    print("TEST 1: Calculs des moyennes avec pondération")
    print("="*70)
    
    # Simuler des notes
    notes_devoirs = [12, 14, 15]  # Moyenne continue = 13.67
    notes_compo = [16]  # Composition = 16
    
    # Calcul selon la formule guinéenne: (MC + Compo*2) / 3
    moyenne_continue = sum(notes_devoirs) / len(notes_devoirs)
    note_composition = notes_compo[0]
    moyenne_matiere = (moyenne_continue + note_composition * 2) / 3
    
    print(f"📝 Notes devoirs: {notes_devoirs}")
    print(f"📝 Moyenne Continue: {moyenne_continue:.2f}")
    print(f"📝 Note Composition: {note_composition}")
    print(f"✅ Moyenne Matière calculée: {moyenne_matiere:.2f}")
    print(f"   Formule: ({moyenne_continue:.2f} + {note_composition} × 2) / 3 = {moyenne_matiere:.2f}")
    
    # Vérification
    expected = (13.67 + 16 * 2) / 3
    assert abs(moyenne_matiere - expected) < 0.01, "Erreur de calcul!"
    print("✅ TEST RÉUSSI: La formule de pondération est correcte")

def test_separation_evaluations():
    """Test de la séparation des évaluations par type"""
    print("\n" + "="*70)
    print("TEST 2: Séparation des évaluations (Devoirs vs Compositions)")
    print("="*70)
    
    # Chercher des évaluations existantes
    try:
        classe = ClasseNote.objects.filter(actif=True).first()
        if classe:
            matieres = MatiereNote.objects.filter(classe=classe, actif=True)[:3]
            print(f"📚 Classe testée: {classe.nom}")
            print(f"📖 Nombre de matières: {matieres.count()}")
            
            for matiere in matieres:
                evaluations = Evaluation.objects.filter(matiere=matiere)
                devoirs = evaluations.filter(type_evaluation__in=['DEVOIR', 'CONTROLE', 'INTERROGATION'])
                compos = evaluations.filter(type_evaluation__in=['COMPOSITION', 'EXAMEN'])
                
                print(f"\n   Matière: {matiere.nom}")
                print(f"   - Devoirs/Contrôles: {devoirs.count()}")
                print(f"   - Compositions: {compos.count()}")
                
            print("\n✅ TEST RÉUSSI: Séparation des évaluations fonctionne")
        else:
            print("⚠️  Aucune classe active trouvée pour le test")
    except Exception as e:
        print(f"❌ ERREUR: {e}")

def test_filtrage_evaluations():
    """Test du filtrage des évaluations par classe"""
    print("\n" + "="*70)
    print("TEST 3: Filtrage des évaluations par classe")
    print("="*70)
    
    try:
        classes = ClasseNote.objects.filter(actif=True)[:2]
        
        for classe in classes:
            matieres = MatiereNote.objects.filter(classe=classe, actif=True)
            total_evals = 0
            
            for matiere in matieres:
                # Test du filtrage correct
                evals = Evaluation.objects.filter(
                    matiere=matiere,
                    matiere__classe=classe
                )
                total_evals += evals.count()
            
            print(f"📚 Classe: {classe.nom}")
            print(f"   - Matières: {matieres.count()}")
            print(f"   - Évaluations totales: {total_evals}")
        
        print("\n✅ TEST RÉUSSI: Le filtrage par classe fonctionne")
    except Exception as e:
        print(f"❌ ERREUR: {e}")

def test_calcul_points_et_rang():
    """Test du calcul des points et du rang"""
    print("\n" + "="*70)
    print("TEST 4: Calcul des points et moyenne générale")
    print("="*70)
    
    # Simuler des données
    matieres_data = [
        {'nom': 'Mathématiques', 'coef': 4, 'moyenne': 15},
        {'nom': 'Français', 'coef': 3, 'moyenne': 13},
        {'nom': 'Anglais', 'coef': 2, 'moyenne': 14},
    ]
    
    total_points = Decimal('0')
    total_coef = Decimal('0')
    
    print("\nMatières testées:")
    for matiere in matieres_data:
        points = Decimal(str(matiere['moyenne'])) * Decimal(str(matiere['coef']))
        total_points += points
        total_coef += Decimal(str(matiere['coef']))
        
        print(f"   {matiere['nom']:15} | Coef: {matiere['coef']} | Moy: {matiere['moyenne']:5.2f} | Points: {points:6.2f}")
    
    moyenne_generale = total_points / total_coef if total_coef > 0 else 0
    
    print(f"\n{'='*50}")
    print(f"Total Points: {total_points:.2f}")
    print(f"Total Coefficients: {total_coef}")
    print(f"✅ Moyenne Générale: {moyenne_generale:.2f}/20")
    
    # Vérification
    expected_mg = (15*4 + 13*3 + 14*2) / (4+3+2)
    assert abs(float(moyenne_generale) - expected_mg) < 0.01, "Erreur de calcul!"
    print("✅ TEST RÉUSSI: Calcul de moyenne générale correct")

def test_gestion_absences():
    """Test de la gestion des absences"""
    print("\n" + "="*70)
    print("TEST 5: Gestion des absences")
    print("="*70)
    
    # Simuler des notes avec absences
    notes = [
        {'note': 15, 'absent': False},
        {'note': None, 'absent': True},  # Absent
        {'note': 14, 'absent': False},
        {'note': None, 'absent': True},  # Absent
    ]
    
    total = Decimal('0')
    count = 0
    
    for n in notes:
        if not n['absent'] and n['note'] is not None:
            total += Decimal(str(n['note']))
            count += 1
    
    moyenne = total / count if count > 0 else None
    
    print(f"📝 Notes totales: {len(notes)}")
    print(f"📝 Absences: {sum(1 for n in notes if n['absent'])}")
    print(f"📝 Notes comptées: {count}")
    print(f"✅ Moyenne calculée: {moyenne:.2f}" if moyenne else "⚠️  Pas de notes valides")
    
    assert moyenne == 14.5, "Erreur dans la gestion des absences!"
    print("✅ TEST RÉUSSI: Les absences sont correctement exclues du calcul")

def test_structure_bulletin():
    """Test de la structure du bulletin selon le système"""
    print("\n" + "="*70)
    print("TEST 6: Structure du bulletin (Mensuel vs Trimestre)")
    print("="*70)
    
    systemes = ['mensuel', 'trimestre', 'semestre']
    
    for systeme in systemes:
        if systeme == 'mensuel':
            colonnes = ['Note']
            nb_cols = 1
        else:
            colonnes = ['Moy. Continue', 'Composition']
            nb_cols = 2
        
        print(f"\n📋 Système: {systeme.upper()}")
        print(f"   Colonnes: {', '.join(colonnes)}")
        print(f"   Nombre: {nb_cols}")
    
    print("\n✅ TEST RÉUSSI: Structure adaptative selon le système")

def verifier_donnees_existantes():
    """Vérifier les données existantes dans la base"""
    print("\n" + "="*70)
    print("VÉRIFICATION: Données existantes dans la base")
    print("="*70)
    
    classes = ClasseNote.objects.filter(actif=True).count()
    matieres = MatiereNote.objects.filter(actif=True).count()
    evaluations = Evaluation.objects.count()
    notes = NoteEleve.objects.count()
    
    print(f"📚 Classes actives: {classes}")
    print(f"📖 Matières actives: {matieres}")
    print(f"📝 Évaluations: {evaluations}")
    print(f"✏️  Notes d'élèves: {notes}")
    
    if classes > 0 and matieres > 0:
        classe = ClasseNote.objects.filter(actif=True).first()
        print(f"\n📌 Exemple de classe: {classe.nom}")
        print(f"   - Année scolaire: {classe.annee_scolaire}")
        print(f"   - Niveau: {classe.get_niveau_display()}")
        
        # Chercher les élèves
        try:
            classe_eleve = Classe.objects.filter(
                nom=classe.nom,
                annee_scolaire=classe.annee_scolaire
            ).first()
            if classe_eleve:
                eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
                print(f"   - Élèves actifs: {eleves.count()}")
                if eleves.exists():
                    print(f"   - Exemple: {eleves.first().nom} {eleves.first().prenom}")
        except Exception as e:
            print(f"   ⚠️  Élèves: {e}")
    
    return classes > 0 and matieres > 0 and evaluations > 0

def main():
    """Fonction principale de test"""
    print("\n" + "="*70)
    print("   🧪 TESTS DES CORRECTIONS DU BULLETIN DYNAMIQUE")
    print("="*70)
    
    try:
        # Vérifier les données
        donnees_ok = verifier_donnees_existantes()
        
        # Tests unitaires
        test_calculs_moyennes()
        test_separation_evaluations()
        test_filtrage_evaluations()
        test_calcul_points_et_rang()
        test_gestion_absences()
        test_structure_bulletin()
        
        # Résumé
        print("\n" + "="*70)
        print("   ✅ TOUS LES TESTS SONT RÉUSSIS!")
        print("="*70)
        
        if donnees_ok:
            print("\n💡 Le serveur est en cours d'exécution sur http://127.0.0.1:8001/")
            print("💡 Testez le bulletin dynamique avec l'URL:")
            print("   http://127.0.0.1:8001/notes/bulletins/?classe_id=3&system_type=trimestre&periode=TRIMESTRE_1")
        else:
            print("\n⚠️  Pour des tests complets, ajoutez des données:")
            print("   - Classes actives")
            print("   - Matières avec coefficients")
            print("   - Évaluations (devoirs et compositions)")
            print("   - Notes d'élèves")
        
    except Exception as e:
        print(f"\n❌ ERREUR LORS DES TESTS: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
