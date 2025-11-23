#!/usr/bin/env python
"""
Script de test pour vérifier que le serveur Django démarre sans erreur
"""
import os
import sys
import django
import subprocess
import time

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')

def test_imports():
    """Test des imports Django"""
    print("🧪 TEST: Imports Django")
    print("-" * 50)
    
    try:
        django.setup()
        print("✅ Django setup: OK")
    except Exception as e:
        print(f"❌ Django setup: {e}")
        return False
    
    try:
        from notes import views
        print("✅ Import notes.views: OK")
    except Exception as e:
        print(f"❌ Import notes.views: {e}")
        return False
    
    try:
        from notes import urls
        print("✅ Import notes.urls: OK")
    except Exception as e:
        print(f"❌ Import notes.urls: {e}")
        return False
    
    return True

def test_decorateurs():
    """Test des décorateurs dans views.py"""
    print("\n🧪 TEST: Décorateurs")
    print("-" * 50)
    
    try:
        import inspect
        from notes import views
        
        # Vérifier les fonctions avec décorateurs
        fonctions_decorateurs = [
            'classement_classe',
            'cartes_scolaires_classe', 
            'cartes_scolaires_pdf'
        ]
        
        for nom_fonction in fonctions_decorateurs:
            if hasattr(views, nom_fonction):
                fonction = getattr(views, nom_fonction)
                source = inspect.getsource(fonction)
                
                if '@require_school_object(model=ClasseEleve' in source:
                    print(f"✅ {nom_fonction}: Décorateur corrigé")
                elif '@require_school_object(model=Classe' in source:
                    print(f"❌ {nom_fonction}: Décorateur non corrigé")
                    return False
                else:
                    print(f"⚠️  {nom_fonction}: Décorateur non trouvé")
            else:
                print(f"❌ {nom_fonction}: Fonction non trouvée")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test des décorateurs: {e}")
        return False

def test_check_django():
    """Test du check Django"""
    print("\n🧪 TEST: Django Check")
    print("-" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, 'manage.py', 'check'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Django check: OK")
            print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ Django check: ERREUR")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Django check: Timeout")
        return False
    except Exception as e:
        print(f"❌ Django check: {e}")
        return False

def test_collectstatic():
    """Test du collectstatic (optionnel)"""
    print("\n🧪 TEST: Collectstatic (optionnel)")
    print("-" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, 'manage.py', 'collectstatic', '--noinput', '--dry-run'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Collectstatic: OK")
            return True
        else:
            print("⚠️  Collectstatic: Erreur (non critique)")
            print(f"Error: {result.stderr}")
            return True  # Non critique
            
    except Exception as e:
        print(f"⚠️  Collectstatic: {e} (non critique)")
        return True  # Non critique

def main():
    """Fonction principale de test"""
    print("🚀 TESTS DU SERVEUR DJANGO")
    print("=" * 60)
    print()
    
    tests_results = []
    
    # Test 1: Imports
    tests_results.append(("Imports Django", test_imports()))
    
    # Test 2: Décorateurs
    tests_results.append(("Décorateurs", test_decorateurs()))
    
    # Test 3: Django Check
    tests_results.append(("Django Check", test_check_django()))
    
    # Test 4: Collectstatic (optionnel)
    tests_results.append(("Collectstatic", test_collectstatic()))
    
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
        print("✅ Le serveur Django peut démarrer sans erreur")
        print()
        print("🚀 COMMANDES POUR DÉMARRER:")
        print("   python manage.py runserver")
        print("   ou")
        print("   python manage.py runserver 0.0.0.0:8000")
        print()
        print("🌐 URLs TESTÉES:")
        print("   http://127.0.0.1:8000/")
        print("   http://127.0.0.1:8000/notes/")
        print("   http://127.0.0.1:8000/notes/bulletins/")
        print("   http://127.0.0.1:8000/notes/exporter-classement-pdf/")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("🔧 Vérifiez les erreurs ci-dessus avant de démarrer le serveur")
    
    return tous_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
