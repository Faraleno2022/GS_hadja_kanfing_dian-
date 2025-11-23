#!/usr/bin/env python
"""
Diagnostiquer l'erreur 404 pour bulletins classe PDF
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
from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve

def diagnostiquer_404():
    """Diagnostiquer l'erreur 404"""
    print("🔍 DIAGNOSTIC ERREUR 404 BULLETINS CLASSE PDF")
    print("=" * 50)
    
    # Paramètres de l'URL qui échoue
    params = {
        'classe_id': '59',
        'periode': 'TRIMESTRE_1',
        'system_type': 'trimestre'
    }
    
    print(f"📋 Paramètres de l'URL qui échoue:")
    for key, value in params.items():
        print(f"   - {key}: {value}")
    
    # 1. Vérifier que ClasseNote 59 existe
    print(f"\n🔍 Vérification ClasseNote ID 59:")
    try:
        classe_note = ClasseNote.objects.get(pk=59)
        print(f"✅ ClasseNote trouvée: {classe_note.nom}")
        print(f"   - ID: {classe_note.id}")
        print(f"   - École: {classe_note.ecole}")
        print(f"   - Année: {classe_note.annee_scolaire}")
    except ClasseNote.DoesNotExist:
        print(f"❌ ClasseNote ID 59 n'existe pas !")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False
    
    # 2. Vérifier le mapping ClasseEleve
    print(f"\n🔍 Vérification mapping ClasseEleve:")
    mapping_classes = {59: 8, 61: 56}
    
    if 59 in mapping_classes:
        classe_eleve_id = mapping_classes[59]
        print(f"✅ Mapping trouvé: ClasseNote 59 → ClasseEleve {classe_eleve_id}")
        
        try:
            classe_eleve = ClasseEleve.objects.get(pk=classe_eleve_id)
            print(f"✅ ClasseEleve trouvée: {classe_eleve.nom}")
        except ClasseEleve.DoesNotExist:
            print(f"❌ ClasseEleve ID {classe_eleve_id} n'existe pas !")
        except Exception as e:
            print(f"❌ Erreur ClasseEleve: {e}")
    
    # 3. Test de la requête HTTP
    print(f"\n🔍 Test requête HTTP:")
    client = Client()
    
    # Se connecter
    try:
        user = User.objects.filter(is_superuser=True).first()
        if user:
            client.force_login(user)
            print(f"✅ Connecté: {user.username}")
        else:
            print("❌ Pas d'utilisateur admin")
            return False
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return False
    
    # Test de l'URL
    try:
        url = '/notes/bulletins/classe/pdf/'
        response = client.get(url, params)
        print(f"📋 URL testée: {url}")
        print(f"📋 Paramètres: {params}")
        print(f"📋 Status: {response.status_code}")
        
        if response.status_code == 404:
            print(f"❌ Erreur 404 confirmée")
            return False
        elif response.status_code == 302:
            print(f"🔄 Redirection: {response.get('Location')}")
            return True
        elif response.status_code == 200:
            print(f"✅ Succès")
            return True
        else:
            print(f"⚠️  Status inattendu: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur requête: {e}")
        import traceback
        traceback.print_exc()
        return False

def tester_url_alternative():
    """Tester une URL alternative qui fonctionne"""
    print(f"\n🔗 TEST URL ALTERNATIVE")
    print("=" * 25)
    
    client = Client()
    
    # Se connecter
    try:
        user = User.objects.filter(is_superuser=True).first()
        client.force_login(user)
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return False
    
    # Tester la consultation qui fonctionne
    try:
        response = client.get('/notes/consulter/', {
            'classe_id': '59',
            'periode': 'OCTOBRE'
        })
        print(f"📋 URL consultation: /notes/consulter/")
        print(f"📋 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ La consultation fonctionne")
            return True
        else:
            print(f"❌ Même la consultation échoue")
            return False
            
    except Exception as e:
        print(f"❌ Erreur consultation: {e}")
        return False

def proposer_solution():
    """Proposer une solution"""
    print(f"\n💡 SOLUTION PROPOSÉE")
    print("=" * 25)
    
    print("🔧 Actions à effectuer:")
    print("1. Vérifier que la fonction bulletins_dynamiques_classe_pdf")
    print("   convertit bien classe_id en entier")
    print("2. Vérifier que le get_object_or_404 ne lève pas d'erreur")
    print("3. Tester avec une période différente")
    print("4. Vérifier les logs Django pour plus de détails")
    
    print(f"\n🔗 URLs alternatives à tester:")
    print("- Consultation: /notes/consulter/?classe_id=59&periode=OCTOBRE")
    print("- Bulletin individuel: /notes/bulletins/?classe_id=59&eleve_id=420&periode=TRIMESTRE_1&system_type=trimestre")

if __name__ == "__main__":
    try:
        success = diagnostiquer_404()
        
        # Test URL alternative
        alt_success = tester_url_alternative()
        
        # Proposer solution
        proposer_solution()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        
        if success:
            print("✅ Le problème semble résolu")
        else:
            print("❌ Problème confirmé - Erreur 404")
        
        if alt_success:
            print("✅ Les URLs alternatives fonctionnent")
        else:
            print("❌ Problème plus large - Vérifier la base de données")
        
        print(f"\n🚨 RECOMMANDATION:")
        if not success:
            print("Utiliser la consultation des notes en attendant la correction")
            print("URL: http://127.0.0.1:8000/notes/consulter/?classe_id=59&periode=OCTOBRE")
        else:
            print("Le problème semble résolu, réessayer l'URL")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
