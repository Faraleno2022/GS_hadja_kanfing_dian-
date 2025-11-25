#!/usr/bin/env python
"""
Test pour vérifier la génération PDF du bulletin dynamique
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_bulletin_pdf():
    """Test pour vérifier la génération PDF du bulletin dynamique"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        # Test avec les mêmes paramètres que l'affichage
        url = '/notes/bulletins/pdf/?classe_id=74&eleve_id=947&periode=OCTOBRE&system_type=mensuel'
        
        print(f'Test de l\'URL: {url}')
        
        response = client.get(url)
        
        print(f'Status code: {response.status_code}')
        
        if response.status_code == 200:
            # Vérifier si c'est bien un PDF
            content_type = response.get('Content-Type', '')
            print(f'Content-Type: {content_type}')
            
            if 'application/pdf' in content_type:
                print('✅ PDF généré avec succès!')
                
                # Vérifier le nom du fichier
                content_disposition = response.get('Content-Disposition', '')
                print(f'Content-Disposition: {content_disposition}')
                
                # Vérifier la taille du PDF
                pdf_size = len(response.content)
                print(f'Taille du PDF: {pdf_size} octets')
                
                if pdf_size > 1000:  # Plus d'1KB, semble valide
                    print('✅ PDF semble valide (taille suffisante)')
                else:
                    print('⚠️ PDF semble trop petit, possible erreur')
                    
            else:
                print('❌ Réponse n\'est pas un PDF')
                print('Contenu de la réponse (premiers 500 caractères):')
                print(response.content.decode('utf-8')[:500])
                
        elif response.status_code == 302:
            # Redirection - probablement une erreur
            redirect_url = response.get('Location', '')
            print(f'Redirection vers: {redirect_url}')
            
            # Suivre la redirection pour voir le message d'erreur
            follow_response = client.get(redirect_url, follow=True)
            print(f'Status après redirection: {follow_response.status_code}')
            
            if follow_response.status_code == 200:
                # Chercher des messages d'erreur dans la page
                content = follow_response.content.decode('utf-8')
                if '❌' in content or 'error' in content.lower():
                    print('Messages d\'erreur trouvés:')
                    import re
                    errors = re.findall(r'❌[^<]*', content)
                    for error in errors[:3]:  # Limiter à 3 erreurs
                        print(f'  {error}')
                        
        else:
            print(f'❌ Erreur HTTP: {response.status_code}')
            print('Contenu de la réponse:')
            print(response.content.decode('utf-8')[:500])
            
    except Exception as e:
        print(f'❌ Erreur: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bulletin_pdf()
