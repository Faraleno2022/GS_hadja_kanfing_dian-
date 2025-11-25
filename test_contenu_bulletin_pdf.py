#!/usr/bin/env python
"""
Test pour vérifier que le bulletin PDF contient bien les bonnes données
"""

import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_bulletin_pdf_contenu():
    """Test pour vérifier le contenu du bulletin PDF"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        # Test avec l'élève spécifique et les données attendues
        url = '/notes/bulletins/pdf/?classe_id=74&eleve_id=923&periode=TRIMESTRE_1&system_type=trimestre'
        print(f'Test de contenu: {url}')
        
        # D'abord, tester l'affichage web pour voir les données attendues
        web_url = '/notes/bulletins/?classe_id=74&eleve_id=923&periode=TRIMESTRE_1&system_type=trimestre'
        web_response = client.get(web_url)
        
        if web_response.status_code == 200:
            web_content = web_response.content.decode('utf-8')
            
            # Extraire les données du web
            import re
            
            # Chercher la moyenne générale
            moyenne_match = re.search(r'Moyenne générale[^:]*:\s*(\d+\.\d+)', web_content)
            if moyenne_match:
                moyenne_web = float(moyenne_match.group(1))
                print(f'Moyenne générale (web): {moyenne_web}')
            
            # Chercher les totaux
            totaux_match = re.search(r'TOTAUX.*?(\d+\.\d+).*?(\d+\.\d+)', web_content, re.DOTALL)
            if totaux_match:
                total_coeff_web = float(totaux_match.group(1))
                total_points_web = float(totaux_match.group(2))
                print(f'Totaux (web): coeff={total_coeff_web}, points={total_points_web}')
            
            # Compter les matières
            matieres_matches = re.findall(r'<tr[^>]*class="matiere-row"', web_content)
            print(f'Nombre de matières (web): {len(matieres_matches)}')
        
        # Maintenant tester le PDF
        pdf_response = client.get(url)
        
        if pdf_response.status_code == 200:
            content_type = pdf_response.get('Content-Type', '')
            if 'application/pdf' in content_type:
                print('✅ PDF généré avec succès!')
                pdf_size = len(pdf_response.content)
                print(f'Taille du PDF: {pdf_size} octets')
                
                # Extraire le texte du PDF (simple vérification)
                try:
                    import PyPDF2
                    import io
                    
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_response.content))
                    pdf_text = ""
                    for page in pdf_reader.pages:
                        pdf_text += page.extract_text() + "\n"
                    
                    print('\n--- Contenu du PDF ---')
                    
                    # Vérifier la présence des éléments attendus
                    if 'BULLETIN SCOLAIRE' in pdf_text:
                        print('✅ En-tête "BULLETIN SCOLAIRE" trouvé')
                    
                    if 'ZOUMANIGUI' in pdf_text and 'BAKARY GOYO' in pdf_text:
                        print('✅ Nom de l\'élève trouvé')
                    
                    if '10ÈME ANNÉE' in pdf_text:
                        print('✅ Nom de la classe trouvé')
                    
                    if 'TRIMESTRE_1' in pdf_text or '1er Trimestre' in pdf_text:
                        print('✅ Période trouvée')
                    
                    # Chercher la moyenne générale dans le PDF
                    if 'Moyenne générale:' in pdf_text:
                        moyenne_pdf_match = re.search(r'Moyenne générale:\s*(\d+\.\d+)', pdf_text)
                        if moyenne_pdf_match:
                            moyenne_pdf = float(moyenne_pdf_match.group(1))
                            print(f'✅ Moyenne générale (PDF): {moyenne_pdf}')
                            
                            # Comparer avec le web
                            if 'moyenne_web' in locals() and abs(moyenne_pdf - moyenne_web) < 0.01:
                                print('✅ Moyenne générale identique entre web et PDF!')
                            else:
                                print('⚠️ Différence de moyenne entre web et PDF')
                    
                    # Chercher les totaux dans le PDF
                    if 'TOTAUX' in pdf_text:
                        print('✅ Ligne TOTAUX trouvée')
                    
                    # Compter les matières dans le PDF
                    matieres_pdf = pdf_text.count('Anglais') + pdf_text.count('Biologie') + pdf_text.count('Mathématique')
                    if matieres_pdf > 0:
                        print(f'✅ Matières détectées dans le PDF: {matieres_pdf}')
                    
                    # Afficher un extrait du texte
                    print('\n--- Extrait du texte PDF ---')
                    lines = pdf_text.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip() and i < 20:  # Premières 20 lignes utiles
                            print(f'{i+1:2d}: {line.strip()}')
                    
                except ImportError:
                    print('⚠️ PyPDF2 non disponible pour analyser le contenu du PDF')
                except Exception as e:
                    print(f'⚠️ Erreur lors de l\'analyse du PDF: {e}')
                
            else:
                print('❌ Réponse n\'est pas un PDF')
        else:
            print(f'❌ Erreur HTTP: {pdf_response.status_code}')
            
    except Exception as e:
        print(f'❌ Erreur: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bulletin_pdf_contenu()
