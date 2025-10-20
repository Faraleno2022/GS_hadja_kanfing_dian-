#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.urls import reverse

def test_eleves_soldes_view():
    print("=== TEST VUE ÉLÈVES SOLDÉS ===")
    
    # Créer un client de test
    client = Client()
    
    # Essayer d'accéder à la page sans authentification
    try:
        response = client.get('/paiements/eleves-soldes/')
        print(f"Réponse sans auth: status={response.status_code}")
        if response.status_code == 302:
            print(f"Redirection vers: {response.url}")
    except Exception as e:
        print(f"Erreur sans auth: {e}")
    
    # Créer un utilisateur de test
    try:
        user = User.objects.get(username='admin')
        print(f"Utilisateur trouvé: {user.username}")
    except User.DoesNotExist:
        # Créer un utilisateur admin de test
        user = User.objects.create_user(
            username='test_admin',
            password='test123',
            is_staff=True,
            is_superuser=True
        )
        print(f"Utilisateur créé: {user.username}")
    
    # Se connecter
    client.force_login(user)
    
    # Tester la vue
    try:
        response = client.get('/paiements/eleves-soldes/')
        print(f"Réponse avec auth: status={response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            print(f"Contenu reçu: {len(content)} caractères")
            
            # Chercher le debug dans le HTML
            if "DEBUG:" in content:
                lines = content.split('\n')
                for line in lines:
                    if "DEBUG:" in line:
                        print(f"Debug trouvé: {line.strip()}")
            
            # Vérifier si le tableau est présent
            if '<tbody>' in content:
                print("Tableau présent dans la réponse")
                # Compter les lignes de données
                tbody_start = content.find('<tbody>')
                tbody_end = content.find('</tbody>')
                if tbody_start != -1 and tbody_end != -1:
                    tbody_content = content[tbody_start:tbody_end]
                    tr_count = tbody_content.count('<tr>') - tbody_content.count('student-details')
                    print(f"Nombre de lignes d'élèves: {tr_count}")
            else:
                print("Tableau absent de la réponse")
                
        else:
            print(f"Erreur HTTP: {response.status_code}")
            if hasattr(response, 'content'):
                print(f"Contenu erreur: {response.content.decode('utf-8')[:500]}")
                
    except Exception as e:
        print(f"Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_eleves_soldes_view()
