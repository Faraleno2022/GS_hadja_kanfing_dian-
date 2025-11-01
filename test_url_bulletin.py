"""
Test pour simuler une requête complète à la vue bulletin_dynamique
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from notes.views import bulletin_dynamique
from django.contrib.auth.models import User

def tester_url():
    print("\n" + "="*80)
    print("   🧪 TEST DE LA REQUÊTE COMPLÈTE")
    print("="*80)
    
    # Créer une factory de requêtes
    factory = RequestFactory()
    
    # Paramètres de l'URL
    url = "/notes/bulletins/?classe_id=6&system_type=trimestre&periode=TRIMESTRE_1&eleve_id=805"
    
    print(f"\n🔗 URL testée:")
    print(f"   {url}")
    
    # Créer la requête GET
    request = factory.get(url)
    
    # Ajouter un utilisateur authentifié
    try:
        user = User.objects.first()
        if not user:
            print("\n❌ Aucun utilisateur trouvé dans la base")
            return
        request.user = user
    except:
        request.user = AnonymousUser()
    
    print(f"\n👤 Utilisateur: {request.user}")
    
    # Exécuter la vue
    print(f"\n⚙️  Exécution de la vue bulletin_dynamique...")
    
    try:
        response = bulletin_dynamique(request)
        
        print(f"\n✅ Réponse reçue:")
        print(f"   - Status Code: {response.status_code}")
        print(f"   - Content Type: {response.get('Content-Type', 'N/A')}")
        
        # Si c'est un TemplateResponse, on peut accéder au context
        if hasattr(response, 'context_data'):
            context = response.context_data
            print(f"\n📦 Données du contexte:")
            print(f"   - classes: {'Oui' if 'classes' in context else 'Non'}")
            print(f"   - classe_selectionnee: {'Oui' if 'classe_selectionnee' in context else 'Non'}")
            print(f"   - eleve_selectionne: {'Oui' if 'eleve_selectionne' in context else 'Non'}")
            print(f"   - bulletin_data: {'Oui' if 'bulletin_data' in context else 'Non'}")
            
            if 'bulletin_data' in context and context['bulletin_data']:
                bd = context['bulletin_data']
                print(f"\n📊 Contenu de bulletin_data:")
                print(f"   - eleve: {bd.get('eleve', 'Non')}")
                print(f"   - classe: {bd.get('classe', 'Non')}")
                print(f"   - periode: {bd.get('periode', 'Non')}")
                print(f"   - matieres_notes: {len(bd.get('matieres_notes', []))} matière(s)")
                
                if bd.get('matieres_notes'):
                    print(f"\n   Détail des matières:")
                    for i, mat in enumerate(bd['matieres_notes'][:5], 1):
                        matiere_nom = mat['matiere'].nom if hasattr(mat['matiere'], 'nom') else 'N/A'
                        notes = mat.get('notes', [])
                        moyenne = mat.get('moyenne', 'N/A')
                        print(f"      {i}. {matiere_nom}")
                        print(f"         Notes: {len(notes)} valeur(s)")
                        if notes:
                            for j, n in enumerate(notes):
                                note_val = n.get('note', 'None')
                                print(f"            - Note {j+1}: {note_val}")
                        print(f"         Moyenne: {moyenne}")
                else:
                    print(f"   ⚠️  Liste matieres_notes vide!")
                    
                print(f"\n   - moyenne_generale: {bd.get('moyenne_generale', 'N/A')}")
                print(f"   - mention: {bd.get('mention', 'N/A')}")
                print(f"   - rang: {bd.get('rang', 'N/A')}")
            else:
                print(f"\n   ❌ bulletin_data est None ou absent!")
        else:
            print(f"\n   ℹ️  Pas de context_data disponible (réponse non-template)")
        
        # Vérifier le contenu HTML rendu
        if hasattr(response, 'render'):
            response.render()
            content = response.content.decode('utf-8')
            
            # Chercher des indicateurs dans le HTML
            has_bulletin = 'bulletin-container' in content
            has_notes_table = 'notes-table' in content
            has_matiere = 'ANGLAIS' in content or 'ECM' in content
            
            print(f"\n🔍 Analyse du HTML rendu:")
            print(f"   - Contient 'bulletin-container': {'Oui' if has_bulletin else 'Non'}")
            print(f"   - Contient 'notes-table': {'Oui' if has_notes_table else 'Non'}")
            print(f"   - Contient noms de matières: {'Oui' if has_matiere else 'Non'}")
            
            # Chercher les notes dans le HTML
            import re
            # Pattern pour détecter les nombres qui pourraient être des notes
            note_pattern = r'<td[^>]*>\s*(\d+\.\d{2})\s*</td>'
            notes_found = re.findall(note_pattern, content)
            
            if notes_found:
                print(f"   - Notes trouvées dans le HTML: {len(notes_found)}")
                print(f"     Exemples: {', '.join(notes_found[:5])}")
            else:
                print(f"   - ❌ Aucune note trouvée dans le HTML!")
                
                # Chercher si des tirets sont affichés
                dash_pattern = r'<td[^>]*>\s*-\s*</td>'
                dashes = re.findall(dash_pattern, content)
                if dashes:
                    print(f"   - {len(dashes)} cellules avec '-' trouvées")
        
        print(f"\n✅ Test terminé")
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de l'exécution de la vue:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    tester_url()
