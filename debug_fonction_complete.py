#!/usr/bin/env python
"""
Debug complet de la fonction bulletins_dynamiques_classe_pdf
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage

def debug_fonction_complete():
    """Debug complet avec tous les détails"""
    print("🔍 DEBUG COMPLET FONCTION")
    print("=" * 30)
    
    # Créer une requête factice avec middleware messages
    factory = RequestFactory()
    request = factory.get('/notes/bulletins/classe/pdf/', {
        'classe_id': '59',
        'periode': 'TRIMESTRE_1',
        'system_type': 'trimestre'
    })
    
    # Ajouter un utilisateur
    user = User.objects.filter(is_superuser=True).first()
    request.user = user
    
    # Ajouter le middleware des messages
    setattr(request, 'session', {})
    messages_storage = FallbackStorage(request)
    setattr(request, '_messages', messages_storage)
    
    print(f"✅ Requête préparée avec utilisateur: {user.username}")
    
    # Importer et appeler la fonction
    try:
        from notes.views import bulletins_dynamiques_classe_pdf
        print(f"✅ Fonction importée")
        
        print(f"\n📋 Appel de la fonction...")
        response = bulletins_dynamiques_classe_pdf(request)
        
        print(f"✅ Fonction exécutée avec succès")
        print(f"   - Type de réponse: {type(response)}")
        print(f"   - Status code: {getattr(response, 'status_code', 'N/A')}")
        
        if hasattr(response, 'status_code'):
            if response.status_code == 302:
                print(f"   - Redirection vers: {response.get('Location', 'N/A')}")
            elif response.status_code == 200:
                print(f"   - Contenu généré: {len(response.content)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans la fonction: {e}")
        print(f"   - Type d'erreur: {type(e)}")
        
        import traceback
        print(f"\n📋 Traceback complet:")
        traceback.print_exc()
        
        return False

def tester_url_pattern():
    """Tester si l'URL pattern est correct"""
    print(f"\n🔗 TEST URL PATTERN")
    print("=" * 20)
    
    from django.urls import resolve, reverse
    
    # Test resolve
    try:
        resolved = resolve('/notes/bulletins/classe/pdf/')
        print(f"✅ URL résolue vers: {resolved.func.__name__}")
        print(f"   - Module: {resolved.func.__module__}")
        print(f"   - Args: {resolved.args}")
        print(f"   - Kwargs: {resolved.kwargs}")
    except Exception as e:
        print(f"❌ Erreur resolve: {e}")
        return False
    
    # Test reverse
    try:
        reversed_url = reverse('notes:bulletins_dynamiques_classe_pdf')
        print(f"✅ Reverse URL: {reversed_url}")
    except Exception as e:
        print(f"❌ Erreur reverse: {e}")
        return False
    
    return True

def verifier_imports():
    """Vérifier que tous les imports fonctionnent"""
    print(f"\n📦 VÉRIFICATION IMPORTS")
    print("=" * 25)
    
    imports_test = [
        ('django.http', 'HttpResponse'),
        ('django.template.loader', 'render_to_string'),
        ('decimal', 'Decimal'),
        ('django.contrib', 'messages'),
        ('django.shortcuts', 'redirect'),
        ('notes.models', 'ClasseNote'),
        ('notes.models', 'MatiereNote'),
        ('eleves.models', 'Classe'),
    ]
    
    for module_path, class_name in imports_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {class_name}")
        except Exception as e:
            print(f"❌ {class_name}: {e}")
            return False
    
    # Test modules simples
    try:
        import tempfile, os, sys
        print(f"✅ tempfile, os, sys")
    except Exception as e:
        print(f"❌ modules système: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 DEBUG COMPLET BULLETINS_DYNAMIQUES_CLASSE_PDF")
        print("=" * 55)
        
        # Vérifications préliminaires
        imports_ok = verifier_imports()
        url_ok = tester_url_pattern()
        
        if not imports_ok:
            print(f"\n❌ Problème d'imports - Arrêt du debug")
            exit(1)
        
        if not url_ok:
            print(f"\n❌ Problème d'URL pattern - Arrêt du debug")
            exit(1)
        
        # Test principal
        function_ok = debug_fonction_complete()
        
        print(f"\n🎯 RÉSUMÉ DEBUG")
        print("=" * 20)
        
        if function_ok:
            print("✅ La fonction fonctionne en isolation")
            print("❓ Le problème vient du serveur web ou middleware")
            print("\n💡 Solutions possibles:")
            print("1. Redémarrer le serveur Django")
            print("2. Vider le cache Django")
            print("3. Vérifier les middlewares")
        else:
            print("❌ La fonction a un problème interne")
            print("🔧 Corriger les erreurs identifiées")
        
        print(f"\n🔗 URL à tester après correction:")
        print("http://127.0.0.1:8000/notes/bulletins/classe/pdf/?classe_id=59&periode=TRIMESTRE_1&system_type=trimestre")
        
    except Exception as e:
        print(f"❌ Erreur globale debug: {e}")
        import traceback
        traceback.print_exc()
