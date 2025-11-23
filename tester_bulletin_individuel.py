#!/usr/bin/env python
"""
Tester le bulletin individuel avec les paramètres exacts
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

def tester_bulletin_individuel():
    """Tester le bulletin individuel avec les paramètres de l'URL"""
    print("📋 TEST BULLETIN INDIVIDUEL")
    print("=" * 30)
    
    # Paramètres exacts de l'URL
    params = {
        'classe_id': '59',
        'system_type': 'mensuel',
        'periode': 'OCTOBRE',
        'eleve_id': '422'
    }
    
    print(f"📋 Paramètres:")
    for key, value in params.items():
        print(f"   - {key}: {value}")
    
    # Créer un client de test
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
    
    # Test 1: Page bulletin dynamique (GET)
    print(f"\n📋 Test 1: Page bulletin dynamique")
    try:
        response = client.get('/notes/bulletins/', params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Page chargée avec succès")
            # Vérifier le contenu pour les messages d'avertissement
            content = response.content.decode('utf-8')
            warning_count = content.count("WeasyPrint non disponible")
            if warning_count > 0:
                print(f"⚠️  Messages d'avertissement trouvés: {warning_count}")
            else:
                print("✅ Pas de messages d'avertissement")
                
        elif response.status_code == 302:
            print(f"🔄 Redirection: {response.get('Location')}")
        else:
            print(f"⚠️  Status inattendu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur GET: {e}")
    
    # Test 2: Génération PDF (bulletin individuel)
    print(f"\n📋 Test 2: Génération PDF bulletin individuel")
    try:
        response = client.get('/notes/bulletins/pdf/', params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ PDF généré avec succès")
            print(f"Content-Type: {response.get('Content-Type', 'N/A')}")
            print(f"Taille: {len(response.content)} bytes")
            
        elif response.status_code == 302:
            print(f"🔄 Redirection: {response.get('Location')}")
        else:
            print(f"⚠️  Status inattendu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur PDF: {e}")

def tester_alternatives():
    """Tester les alternatives disponibles"""
    print(f"\n🔗 ALTERNATIVES DISPONIBLES")
    print("=" * 30)
    
    client = Client()
    
    # Se connecter
    try:
        user = User.objects.filter(is_superuser=True).first()
        client.force_login(user)
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return
    
    # URLs alternatives
    alternatives = [
        ('/notes/consulter/', {'classe_id': '59', 'periode': 'OCTOBRE'}, "Consultation des notes"),
        ('/notes/exporter-classement/', {'classe_id': '59', 'type_note': 'mensuelle', 'periode': 'OCTOBRE'}, "Export classement Excel"),
        ('/notes/bulletins/classe/pdf/', {'classe_id': '59', 'periode': 'OCTOBRE', 'system_type': 'mensuel'}, "Bulletins de classe PDF"),
    ]
    
    for url, params, description in alternatives:
        try:
            response = client.get(url, params)
            status_icon = "✅" if response.status_code == 200 else "🔄" if response.status_code == 302 else "❌"
            print(f"{status_icon} {description}")
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 302:
                print(f"   → Redirection: {response.get('Location', 'N/A')}")
            elif response.status_code == 200 and 'pdf' in url:
                print(f"   → PDF généré: {len(response.content)} bytes")
                
        except Exception as e:
            print(f"❌ {description} - Erreur: {e}")
        print()

def verifier_eleve_422():
    """Vérifier que l'élève 422 existe"""
    print(f"\n👤 VÉRIFICATION ÉLÈVE 422")
    print("=" * 30)
    
    from eleves.models import Eleve
    from notes.models import ClasseNote
    
    try:
        # Vérifier l'élève
        eleve = Eleve.objects.get(pk=422)
        print(f"✅ Élève trouvé: {eleve.prenom} {eleve.nom}")
        print(f"   - Matricule: {eleve.matricule}")
        print(f"   - Classe: {eleve.classe.nom if eleve.classe else 'N/A'}")
        print(f"   - Statut: {eleve.statut}")
        
        # Vérifier la classe
        classe = ClasseNote.objects.get(pk=59)
        print(f"✅ Classe trouvée: {classe.nom}")
        
        # Vérifier si l'élève est dans la bonne classe
        if eleve.classe and eleve.classe.nom == classe.nom:
            print(f"✅ Élève dans la bonne classe")
        else:
            print(f"⚠️  Élève pas dans la classe attendue")
            print(f"   - Classe élève: {eleve.classe.nom if eleve.classe else 'N/A'}")
            print(f"   - Classe demandée: {classe.nom}")
            
    except Eleve.DoesNotExist:
        print(f"❌ Élève 422 non trouvé")
    except ClasseNote.DoesNotExist:
        print(f"❌ Classe 59 non trouvée")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    try:
        tester_bulletin_individuel()
        tester_alternatives()
        verifier_eleve_422()
        
        print(f"\n🎯 RECOMMANDATIONS")
        print("=" * 20)
        print("1. Utiliser la consultation des notes pour voir les résultats")
        print("2. Utiliser l'export classement Excel pour avoir un document")
        print("3. Les bulletins PDF individuels nécessitent WeasyPrint")
        print("4. Alternative: Bulletins de classe PDF (tous les élèves)")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
