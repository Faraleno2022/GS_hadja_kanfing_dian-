#!/usr/bin/env python
"""
Tester l'URL directement avec le client de test Django
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
from django.urls import reverse

def tester_url_avec_client():
    """Tester l'URL avec le client de test Django"""
    print("🌐 TEST URL AVEC CLIENT DJANGO")
    print("=" * 35)
    
    # Créer un client de test
    client = Client()
    
    # Se connecter avec un utilisateur admin
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ Aucun superuser trouvé")
            return
        
        login_success = client.login(username=user.username, password='admin123')  # Mot de passe par défaut
        if not login_success:
            print(f"⚠️  Échec de connexion avec {user.username}")
            # Essayer de créer une session manuellement
            client.force_login(user)
            print(f"✅ Connexion forcée avec {user.username}")
        else:
            print(f"✅ Connexion réussie avec {user.username}")
            
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return
    
    # URL problématique
    url = '/notes/bulletins/classe/pdf/'
    params = {
        'classe_id': '59',
        'periode': 'OCTOBRE',
        'system_type': 'mensuel'
    }
    
    print(f"\n📋 Test URL: {url}")
    print(f"📋 Paramètres: {params}")
    
    # Faire la requête
    try:
        response = client.get(url, params)
        print(f"\n📊 Résultat:")
        print(f"   - Status code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Succès ! PDF généré")
            print(f"   - Content-Type: {response.get('Content-Type', 'N/A')}")
            print(f"   - Taille: {len(response.content)} bytes")
            
        elif response.status_code == 302:
            print(f"🔄 Redirection vers: {response.get('Location', 'N/A')}")
            
        elif response.status_code == 404:
            print(f"❌ Erreur 404 confirmée")
            print(f"   - Contenu: {response.content.decode('utf-8')[:500]}...")
            
        else:
            print(f"⚠️  Status inattendu: {response.status_code}")
            print(f"   - Contenu: {response.content.decode('utf-8')[:500]}...")
            
    except Exception as e:
        print(f"❌ Erreur requête: {e}")
        import traceback
        traceback.print_exc()

def tester_urls_alternatives():
    """Tester des URLs alternatives pour comparaison"""
    print(f"\n🔗 TEST URLS ALTERNATIVES")
    print("=" * 30)
    
    client = Client()
    
    # Se connecter
    try:
        user = User.objects.filter(is_superuser=True).first()
        client.force_login(user)
        print(f"✅ Connecté avec {user.username}")
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return
    
    # URLs à tester
    urls_test = [
        ('/notes/consulter/', {'classe_id': '59', 'periode': 'OCTOBRE'}),
        ('/notes/bulletins/pdf/', {'classe_id': '59', 'eleve_id': '422', 'periode': 'OCTOBRE', 'system_type': 'mensuel'}),
        ('/notes/exporter-classement/', {'classe_id': '59', 'type_note': 'mensuelle', 'periode': 'OCTOBRE'}),
    ]
    
    for url, params in urls_test:
        try:
            response = client.get(url, params)
            status_icon = "✅" if response.status_code == 200 else "🔄" if response.status_code == 302 else "❌"
            print(f"{status_icon} {url} - Status: {response.status_code}")
            
            if response.status_code == 302:
                print(f"   → Redirection: {response.get('Location', 'N/A')}")
                
        except Exception as e:
            print(f"❌ {url} - Erreur: {e}")

def verifier_urls_patterns():
    """Vérifier les patterns d'URL"""
    print(f"\n🗺️  VÉRIFICATION PATTERNS URL")
    print("=" * 35)
    
    try:
        # Essayer de résoudre l'URL
        from django.urls import resolve
        
        url_path = '/notes/bulletins/classe/pdf/'
        resolved = resolve(url_path)
        
        print(f"✅ URL résolue:")
        print(f"   - View: {resolved.func.__name__}")
        print(f"   - Module: {resolved.func.__module__}")
        print(f"   - Args: {resolved.args}")
        print(f"   - Kwargs: {resolved.kwargs}")
        
    except Exception as e:
        print(f"❌ Erreur résolution URL: {e}")
    
    # Vérifier le reverse
    try:
        reversed_url = reverse('notes:bulletins_dynamiques_classe_pdf')
        print(f"✅ Reverse URL: {reversed_url}")
    except Exception as e:
        print(f"❌ Erreur reverse: {e}")

if __name__ == "__main__":
    try:
        tester_url_avec_client()
        tester_urls_alternatives()
        verifier_urls_patterns()
        
        print(f"\n🎯 RECOMMANDATIONS")
        print("=" * 20)
        print("1. Redémarrer le serveur Django")
        print("2. Vider le cache Django")
        print("3. Vérifier les logs du serveur")
        print("4. Tester avec un autre utilisateur")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
