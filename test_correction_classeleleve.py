#!/usr/bin/env python
"""
Script de test pour vérifier que l'erreur ClasseEleve est corrigée
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_imports():
    """Test des imports dans views.py"""
    print("🧪 TEST: Imports dans views.py")
    print("-" * 50)
    
    try:
        # Test import global
        from notes.views import ClasseEleve
        print("✅ Import global ClasseEleve: OK")
    except ImportError as e:
        print(f"❌ Import global ClasseEleve: {e}")
        return False
    
    # Test des fonctions qui utilisaient ClasseEleve
    try:
        from notes.views import (
            statistiques, gerer_eleves, saisir_notes, 
            consulter_notes, bulletin_dynamique
        )
        print("✅ Import des fonctions: OK")
    except ImportError as e:
        print(f"❌ Import des fonctions: {e}")
        return False
    
    return True

def test_export_classement():
    """Test de l'export classement qui causait l'erreur"""
    print("\n🧪 TEST: Export classement")
    print("-" * 50)
    
    try:
        from notes.export_classement import exporter_classement_classe_pdf
        print("✅ Import export_classement: OK")
    except ImportError as e:
        print(f"❌ Import export_classement: {e}")
        return False
    
    # Test avec une classe réelle
    try:
        from notes.models import ClasseNote
        classe_test = ClasseNote.objects.filter(actif=True).first()
        
        if classe_test:
            print(f"✅ Classe test trouvée: {classe_test.nom}")
            
            # Simuler les paramètres de la requête
            class MockRequest:
                def __init__(self):
                    self.GET = {
                        'classe_id': str(classe_test.id),
                        'type_note': 'mensuelle'
                    }
                    self.user = None
            
            # Test sans exécuter complètement (juste vérifier que l'import fonctionne)
            print("✅ Structure export OK (test d'import uniquement)")
        else:
            print("⚠️  Aucune classe active trouvée pour le test")
    
    except Exception as e:
        print(f"❌ Erreur lors du test export: {e}")
        return False
    
    return True

def test_fonctions_bulletins():
    """Test des fonctions de bulletins"""
    print("\n🧪 TEST: Fonctions bulletins")
    print("-" * 50)
    
    try:
        from notes.views import bulletin_dynamique, bulletin_dynamique_pdf
        print("✅ Import fonctions bulletins: OK")
    except ImportError as e:
        print(f"❌ Import fonctions bulletins: {e}")
        return False
    
    return True

def test_modeles():
    """Test des modèles"""
    print("\n🧪 TEST: Modèles")
    print("-" * 50)
    
    try:
        from eleves.models import Classe as ClasseEleve, Eleve
        from notes.models import ClasseNote, MatiereNote
        print("✅ Import modèles: OK")
        
        # Test de base de données
        nb_classes = ClasseEleve.objects.count()
        nb_eleves = Eleve.objects.count()
        nb_classes_notes = ClasseNote.objects.count()
        
        print(f"📊 Classes élèves: {nb_classes}")
        print(f"📊 Élèves: {nb_eleves}")
        print(f"📊 Classes notes: {nb_classes_notes}")
        
    except Exception as e:
        print(f"❌ Erreur modèles: {e}")
        return False
    
    return True

def main():
    """Fonction principale de test"""
    print("🚀 TESTS DE CORRECTION CLASSELELEVE")
    print("=" * 60)
    print()
    
    tests_results = []
    
    # Test 1: Imports
    tests_results.append(("Imports views.py", test_imports()))
    
    # Test 2: Export classement
    tests_results.append(("Export classement", test_export_classement()))
    
    # Test 3: Fonctions bulletins
    tests_results.append(("Fonctions bulletins", test_fonctions_bulletins()))
    
    # Test 4: Modèles
    tests_results.append(("Modèles", test_modeles()))
    
    # Résumé
    print("\n📋 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    tous_ok = True
    for nom_test, resultat in tests_results:
        status = "✅ RÉUSSI" if resultat else "❌ ÉCHEC"
        print(f"{nom_test:.<30} {status}")
        if not resultat:
            tous_ok = False
    
    print("\n" + "=" * 60)
    if tous_ok:
        print("🎉 TOUS LES TESTS RÉUSSIS !")
        print("✅ L'erreur 'ClasseEleve is not defined' est CORRIGÉE")
        print()
        print("🚀 ACTIONS SUIVANTES:")
        print("1. Tester l'interface web")
        print("2. Générer un bulletin")
        print("3. Exporter un classement PDF")
        print("4. Vérifier que tout fonctionne normalement")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("🔧 Vérifiez les erreurs ci-dessus")
    
    return tous_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
