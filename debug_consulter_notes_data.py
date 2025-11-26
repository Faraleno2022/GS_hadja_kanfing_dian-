#!/usr/bin/env python
"""
Debug direct de la vue consulter_notes pour voir les données passées au template
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def debug_consulter_notes_data():
    """Debug des données de la vue consulter_notes"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        
        print("🔍 Debug direct de consulter_notes")
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        # Appeler la vue via le client
        print("Appel de la vue...")
        response = client.get('/notes/consulter/?classe_id=74&periode=OCTOBRE')
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Type de réponse: {type(response)}")
            
            # Le contexte est dans response.context
            context = response.context
            print(f"Type du contexte: {type(context)}")
            
            if context is None:
                print("❌ Contexte est None")
                print("Contenu de la réponse:")
                print(response.content.decode('utf-8')[:500])
                return
            
            print("\n📋 Contexte disponible:")
            for key in context.keys():
                value = context[key]
                if hasattr(value, '__len__') and len(value) > 0:
                    print(f"  {key}: {type(value)} (len={len(value)})")
                else:
                    print(f"  {key}: {type(value)}")
            
            # Vérifier spécifiquement les données importantes
            if 'eleves_toutes_notes' in context:
                eleves_data = context['eleves_toutes_notes']
                print(f"\n👥 Élèves avec notes: {len(eleves_data)}")
                
                if len(eleves_data) > 0:
                    premier_eleve = eleves_data[0]
                    print(f"Premier élève: {premier_eleve}")
                    
                    if 'notes_par_matiere' in premier_eleve:
                        notes_par_matiere = premier_eleve['notes_par_matiere']
                        print(f"Notes par matière: {len(notes_par_matiere)}")
                        
                        for matiere_id, notes_data in notes_par_matiere.items():
                            print(f"  Matière {matiere_id}:")
                            print(f"    Évaluations: {len(notes_data.get('evaluations', []))}")
                            print(f"    Notes: {len(notes_data.get('notes', []))}")
                            
                            if notes_data.get('notes'):
                                for note_info in notes_data['notes'][:2]:
                                    note = note_info.get('note', 'N/A')
                                    print(f"      - Note: {note}")
                    else:
                        print("❌ Pas de 'notes_par_matiere' dans l'élève")
                else:
                    print("❌ Aucun élève dans eleves_toutes_notes")
            else:
                print("❌ 'eleves_toutes_notes' pas dans le contexte")
            
            # Vérifier les autres clés importantes
            important_keys = ['classe_selectionnee', 'matieres', 'periode_classement']
            for key in important_keys:
                if key in context:
                    value = context[key]
                    if hasattr(value, '__len__') and hasattr(value, 'count'):
                        print(f"{key}: {value.count()} éléments")
                    else:
                        print(f"{key}: {value}")
                else:
                    print(f"❌ {key} manquant")
            
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(response.content.decode('utf-8')[:500])
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_consulter_notes_data()
