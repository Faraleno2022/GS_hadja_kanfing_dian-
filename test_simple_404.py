#!/usr/bin/env python
"""
Test simple pour isoler le problème 404
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve

def test_simple():
    print("🔍 TEST SIMPLE 404")
    print("=" * 20)
    
    # 1. Test résolution URL
    try:
        url_path = '/notes/bulletins/classe/pdf/'
        resolved = resolve(url_path)
        print(f"✅ URL résolue: {resolved.func.__name__}")
    except Exception as e:
        print(f"❌ Erreur résolution: {e}")
        return
    
    # 2. Test reverse
    try:
        reversed_url = reverse('notes:bulletins_dynamiques_classe_pdf')
        print(f"✅ Reverse: {reversed_url}")
    except Exception as e:
        print(f"❌ Erreur reverse: {e}")
        return
    
    # 3. Test avec client minimal
    client = Client()
    
    # Se connecter
    try:
        user = User.objects.filter(is_superuser=True).first()
        if user:
            client.force_login(user)
            print(f"✅ Connecté: {user.username}")
        else:
            print("❌ Pas d'utilisateur")
            return
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return
    
    # 4. Test GET simple sans paramètres
    print(f"\n📋 Test GET sans paramètres:")
    try:
        response = client.get('/notes/bulletins/classe/pdf/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 302:
            print(f"Redirection: {response.get('Location')}")
        elif response.status_code == 404:
            print("❌ 404 confirmé même sans paramètres")
        else:
            print(f"Autre status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur GET: {e}")
    
    # 5. Test avec paramètres minimaux
    print(f"\n📋 Test GET avec paramètres:")
    try:
        response = client.get('/notes/bulletins/classe/pdf/', {
            'classe_id': '59',
            'periode': 'OCTOBRE'
        })
        print(f"Status: {response.status_code}")
        
        if response.status_code == 302:
            print(f"Redirection: {response.get('Location')}")
        elif response.status_code == 404:
            print("❌ 404 avec paramètres")
        else:
            print(f"Autre status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur GET avec params: {e}")

def test_fonction_directe():
    """Tester la fonction directement"""
    print(f"\n🎯 TEST FONCTION DIRECTE")
    print("=" * 25)
    
    from django.test import RequestFactory
    from notes.views import bulletins_dynamiques_classe_pdf
    from django.contrib.auth.models import User
    
    # Créer une requête factice
    factory = RequestFactory()
    request = factory.get('/notes/bulletins/classe/pdf/', {
        'classe_id': '59',
        'periode': 'OCTOBRE',
        'system_type': 'mensuel'
    })
    
    # Ajouter un utilisateur
    try:
        user = User.objects.filter(is_superuser=True).first()
        request.user = user
        print(f"✅ Utilisateur: {user.username}")
    except Exception as e:
        print(f"❌ Erreur utilisateur: {e}")
        return
    
    # Appeler la fonction directement
    try:
        print("📋 Appel direct de la fonction...")
        response = bulletins_dynamiques_classe_pdf(request)
        print(f"✅ Fonction appelée avec succès")
        print(f"Status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
        print(f"Type: {type(response)}")
        
    except Exception as e:
        print(f"❌ Erreur fonction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        test_simple()
        test_fonction_directe()
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
