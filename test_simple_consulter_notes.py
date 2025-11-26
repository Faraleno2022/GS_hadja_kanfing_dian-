#!/usr/bin/env python
"""
Test simple pour vérifier que consulter_notes récupère bien les notes
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_simple_consulter_notes():
    """Test simple de la vue consulter_notes"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, Evaluation, NoteEleve
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        print("🔍 Test simple de consulter_notes")
        
        # Prendre la classe 74 (10ÈME ANNÉE A)
        classe_id = 74
        url = f'/notes/consulter/?classe_id={classe_id}&periode=OCTOBRE'
        
        print(f"URL: {url}")
        
        # Vérifier qu'il y a bien des évaluations et notes
        evaluations = Evaluation.objects.filter(periode='OCTOBRE').count()
        notes = NoteEleve.objects.filter(evaluation__periode='OCTOBRE').count()
        
        print(f"Évaluations OCTOBRE: {evaluations}")
        print(f"Notes OCTOBRE: {notes}")
        
        # Tester la vue
        response = client.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Chercher les patterns de notes dans le HTML
            import re
            
            # Pattern 1: Notes dans les cellules du tableau
            notes_pattern = r'<td[^>]*class="note-cell[^"]*"[^>]*>(\d+[.,]\d+|\d+)</td>'
            notes_trouvees = re.findall(notes_pattern, content)
            
            # Pattern 2: Toutes les valeurs numériques dans les TD
            all_numbers_pattern = r'<td[^>]*>(\d+[.,]\d+|\d+)</td>'
            all_numbers = re.findall(all_numbers_pattern, content)
            
            # Pattern 3: Recherche de "note" dans le HTML
            note_occurrences = content.lower().count('note')
            
            print(f"Notes dans note-cell: {len(notes_trouvees)}")
            print(f"Tous les nombres dans TD: {len(all_numbers)}")
            print(f"Occurrences de 'note': {note_occurrences}")
            
            # Afficher quelques nombres trouvés
            if all_numbers:
                print("Nombres trouvés dans les TD:")
                for i, num in enumerate(all_numbers[:10]):
                    print(f"  {i+1}. {num}")
            
            # Chercher les erreurs JavaScript
            if 'error' in content.lower():
                print("⚠️ Erreurs JavaScript détectées")
                error_lines = [line for line in content.split('\n') if 'error' in line.lower()]
                for error_line in error_lines[:3]:
                    print(f"  {error_line.strip()[:100]}")
            
            # Vérifier s'il y a un tableau
            if '<table' in content:
                print("✅ Tableau HTML trouvé")
                table_count = content.count('<table')
                print(f"  Nombre de tableaux: {table_count}")
            else:
                print("❌ Aucun tableau HTML trouvé")
            
            # Vérifier les élèves
            if 'AMADOU LAMARANA BAH' in content:
                print("✅ Élève trouvé dans le HTML")
            else:
                print("❌ Élève non trouvé dans le HTML")
                
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(response.content.decode('utf-8')[:300])
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_consulter_notes()
