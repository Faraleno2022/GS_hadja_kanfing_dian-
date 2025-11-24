#!/usr/bin/env python
"""
Script de test pour vérifier que la colonne NOTE s'affiche correctement
dans les bulletins mensuels
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle
from eleves.models import Eleve
from notes.calculs_moyennes import calculer_moyenne_matiere


def test_notes_mensuelles_existence():
    """Test 1: Vérifier que des NoteMensuelle existent"""
    print("\n" + "="*60)
    print("TEST 1 : EXISTENCE DES NOTES MENSUELLES")
    print("="*60)
    
    notes = NoteMensuelle.objects.filter(mois='OCTOBRE')
    print(f"\n📊 Notes mensuelles pour OCTOBRE : {notes.count()}")
    
    if notes.exists():
        print(f"   ✅ {notes.count()} notes mensuelles trouvées")
        
        # Afficher quelques exemples
        print(f"\n📋 Exemples de notes (5 premières) :")
        for note in notes[:5]:
            absent_str = "ABS" if note.absent else f"{note.note}/20"
            print(f"   • {note.eleve.matricule} - {note.matiere.nom} : {absent_str}")
        
        return True
    else:
        print(f"   ❌ Aucune note mensuelle trouvée pour OCTOBRE")
        return False


def test_calcul_moyenne_matiere():
    """Test 2: Vérifier que calculer_moyenne_matiere() récupère les NoteMensuelle"""
    print("\n" + "="*60)
    print("TEST 2 : CALCUL MOYENNE AVEC NoteMensuelle")
    print("="*60)
    
    # Chercher un élève avec des notes mensuelles
    note_test = NoteMensuelle.objects.filter(
        mois='OCTOBRE',
        note__isnull=False,
        absent=False
    ).first()
    
    if not note_test:
        print("   ❌ Aucune note mensuelle disponible pour tester")
        return False
    
    eleve = note_test.eleve
    matiere = note_test.matiere
    
    print(f"\n🧪 Test avec :")
    print(f"   - Élève : {eleve.prenom} {eleve.nom} ({eleve.matricule})")
    print(f"   - Matière : {matiere.nom}")
    print(f"   - Période : OCTOBRE")
    print(f"   - Note attendue : {note_test.note}/20")
    
    # Appeler la fonction corrigée
    result = calculer_moyenne_matiere(
        eleve=eleve,
        matiere=matiere,
        periode='OCTOBRE',
        system_type='mensuel'
    )
    
    print(f"\n📊 Résultat du calcul :")
    print(f"   - moyenne_continue : {result['moyenne_continue']}")
    print(f"   - note_composition : {result['note_composition']}")
    print(f"   - moyenne_matiere : {result['moyenne_matiere']}")
    print(f"   - points : {result['points']}")
    
    # Vérifier que la moyenne_continue correspond à la note
    if result['moyenne_continue'] == float(note_test.note):
        print(f"\n   ✅ SUCCÈS : La note est correctement récupérée")
        return True
    else:
        print(f"\n   ❌ ERREUR : Note attendue {note_test.note}, obtenue {result['moyenne_continue']}")
        return False


def test_multiple_eleves():
    """Test 3: Tester avec plusieurs élèves"""
    print("\n" + "="*60)
    print("TEST 3 : PLUSIEURS ÉLÈVES")
    print("="*60)
    
    # Récupérer 5 élèves avec des notes
    notes_test = NoteMensuelle.objects.filter(
        mois='OCTOBRE',
        note__isnull=False,
        absent=False
    ).select_related('eleve', 'matiere')[:5]
    
    if not notes_test:
        print("   ❌ Aucune note disponible")
        return False
    
    succes = 0
    erreurs = 0
    
    print(f"\n🧪 Test de {len(notes_test)} notes...")
    
    for note_test in notes_test:
        result = calculer_moyenne_matiere(
            eleve=note_test.eleve,
            matiere=note_test.matiere,
            periode='OCTOBRE',
            system_type='mensuel'
        )
        
        if result['moyenne_continue'] == float(note_test.note):
            succes += 1
            statut = "✅"
        else:
            erreurs += 1
            statut = "❌"
        
        print(f"   {statut} {note_test.eleve.matricule} - {note_test.matiere.nom}")
    
    print(f"\n📊 Résultat :")
    print(f"   - Succès : {succes}/{len(notes_test)}")
    print(f"   - Erreurs : {erreurs}/{len(notes_test)}")
    
    if erreurs == 0:
        print(f"   ✅ TOUS LES TESTS RÉUSSIS")
        return True
    else:
        print(f"   ⚠️  {erreurs} test(s) échoué(s)")
        return False


def test_bulletin_complet():
    """Test 4: Simuler un bulletin complet"""
    print("\n" + "="*60)
    print("TEST 4 : SIMULATION BULLETIN COMPLET")
    print("="*60)
    
    # Chercher un élève avec plusieurs notes
    from django.db.models import Count
    
    eleve_test = Eleve.objects.annotate(
        nb_notes=Count('notes_mensuelles')
    ).filter(
        nb_notes__gte=3,
        notes_mensuelles__mois='OCTOBRE'
    ).first()
    
    if not eleve_test:
        print("   ❌ Aucun élève avec suffisamment de notes")
        return False
    
    print(f"\n🧪 Élève : {eleve_test.prenom} {eleve_test.nom} ({eleve_test.matricule})")
    
    # Récupérer ses notes
    notes = NoteMensuelle.objects.filter(
        eleve=eleve_test,
        mois='OCTOBRE'
    ).select_related('matiere')
    
    print(f"\n📋 Notes du bulletin (système mensuel) :")
    print(f"{'MATIÈRE':<20} {'NOTE':>8} {'MOY':>8} {'STATUS':>10}")
    print("-" * 50)
    
    toutes_reussies = True
    
    for note in notes:
        result = calculer_moyenne_matiere(
            eleve=eleve_test,
            matiere=note.matiere,
            periode='OCTOBRE',
            system_type='mensuel'
        )
        
        note_affichee = result['moyenne_continue'] if result['moyenne_continue'] else '-'
        moy_affichee = result['moyenne_matiere'] if result['moyenne_matiere'] else '-'
        
        # Vérifier que NOTE et MOY sont identiques pour un bulletin mensuel
        if note_affichee != '-' and moy_affichee != '-':
            if note_affichee == moy_affichee:
                status = "✅ OK"
            else:
                status = "❌ DIFF"
                toutes_reussies = False
        else:
            status = "⚪ VIDE"
        
        print(f"{note.matiere.nom:<20} {str(note_affichee):>8} {str(moy_affichee):>8} {status:>10}")
    
    if toutes_reussies:
        print(f"\n   ✅ SUCCÈS : NOTE et MOY sont identiques partout")
        return True
    else:
        print(f"\n   ❌ ERREUR : Différences détectées entre NOTE et MOY")
        return False


def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("🔬 TEST CORRECTION COLONNE NOTE - BULLETIN MENSUEL")
    print("="*70)
    
    resultats = {}
    
    try:
        resultats['Existence notes'] = test_notes_mensuelles_existence()
        resultats['Calcul moyenne'] = test_calcul_moyenne_matiere()
        resultats['Plusieurs élèves'] = test_multiple_eleves()
        resultats['Bulletin complet'] = test_bulletin_complet()
        
        # Rapport final
        print("\n" + "="*70)
        print("📊 RAPPORT FINAL")
        print("="*70)
        
        total_tests = len(resultats)
        tests_reussis = sum(1 for r in resultats.values() if r)
        
        print(f"\n✅ Tests réussis : {tests_reussis}/{total_tests}")
        
        print(f"\n📋 Détails :")
        for nom_test, resultat in resultats.items():
            statut = "✅ RÉUSSI" if resultat else "❌ ÉCHOUÉ"
            print(f"   {statut} - {nom_test}")
        
        if tests_reussis == total_tests:
            print(f"\n🎉 TOUS LES TESTS ONT RÉUSSI !")
            print(f"\n✅ La correction fonctionne correctement")
            print(f"✅ La colonne NOTE s'affiche dans les bulletins mensuels")
            return True
        else:
            print(f"\n⚠️  {total_tests - tests_reussis} test(s) ont échoué")
            print(f"\nℹ️  Vérifiez les détails ci-dessus")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur pendant les tests : {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    print("\n" + "="*70 + "\n")
    sys.exit(0 if success else 1)
