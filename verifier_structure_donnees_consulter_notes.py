#!/usr/bin/env python
"""
Vérification de la structure des données dans consulter_notes
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def verifier_structure_donnees_consulter_notes():
    """Vérifier la structure exacte des données passées au template"""
    
    try:
        from django.test import Client, RequestFactory
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from notes.views import consulter_notes
        from eleves.models import Eleve, Classe as ClasseEleve
        from django.template import Context, Template
        
        print("🔧 VÉRIFICATION STRUCTURE DONNÉES - consulter_notes")
        
        # 1. Configuration
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        periode = 'OCTOBRE'
        
        # 2. Créer une requête factice
        factory = RequestFactory()
        request = factory.get(f'/notes/consulter/?classe_id={classe_id}&periode={periode}')
        
        user = User.objects.first()
        request.user = user
        
        print(f"URL : {request.get_full_path()}")
        
        # 3. Appeler la vue
        response = consulter_notes(request)
        
        if response.status_code != 200:
            print(f"❌ Erreur HTTP : {response.status_code}")
            return
        
        # 4. Analyser le contexte
        print(f"\n📋 ANALYSE DU CONTEXTE :")
        
        # Le template est rendu directement, on ne peut pas accéder au contexte
        # On va simuler la logique de la vue pour vérifier
        
        # Récupérer les données manuellement
        classe = ClasseNote.objects.get(id=classe_id)
        print(f"✅ Classe : {classe.nom}")
        
        # Mapping des classes
        mapping_classes = {
            59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
        }
        
        classe_eleve = None
        if classe.id in mapping_classes:
            classe_eleve = ClasseEleve.objects.filter(id=mapping_classes[classe.id]).first()
        
        if not classe_eleve:
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe.nom,
                annee_scolaire=classe.annee_scolaire,
                ecole=classe.ecole
            ).first()
        
        if not classe_eleve:
            print("❌ Classe élève non trouvée")
            return
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        
        print(f"✅ Élèves : {len(eleves)}")
        print(f"✅ Matières : {len(matieres)}")
        
        # 5. Simuler la logique de calcul des notes
        print(f"\n🔍 SIMULATION CALCUL NOTES :")
        
        eleves_toutes_notes = []
        
        for i, eleve in enumerate(eleves):
            if i >= 3:  # Limiter à 3 élèves pour le debug
                break
                
            print(f"\n  📝 Élève {i+1} : {eleve.nom_complet}")
            
            notes_par_matiere = {}
            
            for matiere in matieres:
                if i >= 2:  # Limiter à 2 matières pour le debug
                    break
                    
                print(f"    📖 Matière : {matiere.nom}")
                
                # Logique pour OCTOBRE (période mensuelle)
                evaluations_mois = Evaluation.objects.filter(
                    matiere=matiere,
                    periode=periode
                )
                
                evaluation_mois = evaluations_mois.first()
                
                notes_matiere = {
                    'evaluations': [],
                    'notes': [],
                    'moyenne': None
                }
                
                if evaluation_mois:
                    print(f"      ✅ Évaluation trouvée : {evaluation_mois.titre}")
                    
                    try:
                        note_obj = NoteEleve.objects.get(
                            eleve=eleve,
                            evaluation=evaluation_mois
                        )
                        
                        print(f"      ✅ Note trouvée : {note_obj.note}")
                        
                        notes_matiere['notes'].append({
                            'evaluation': evaluation_mois,
                            'note': note_obj.note,
                            'absent': note_obj.absent if hasattr(note_obj, 'absent') else False,
                        })
                        
                        if note_obj.note is not None and not (hasattr(note_obj, 'absent') and note_obj.absent):
                            notes_matiere['moyenne'] = float(note_obj.note)
                            print(f"      ✅ Moyenne : {notes_matiere['moyenne']}")
                        else:
                            notes_matiere['moyenne'] = 0.0
                            print(f"      ❌ Moyenne : 0.0 (absent ou None)")
                            
                    except NoteEleve.DoesNotExist:
                        print(f"      ❌ Note non trouvée pour cet élève")
                        notes_matiere['notes'].append({
                            'evaluation': evaluation_mois,
                            'note': None,
                            'absent': False,
                        })
                        notes_matiere['moyenne'] = 0.0
                else:
                    print(f"      ❌ Pas d'évaluation pour {matiere.nom} en {periode}")
                    notes_matiere['moyenne'] = 0.0
                
                notes_par_matiere[matiere.id] = notes_matiere
                
                # Vérifier la structure pour le template
                print(f"        📊 notes_matiere.notes : {len(notes_matiere['notes'])}")
                if notes_matiere['notes']:
                    for j, note_info in enumerate(notes_matiere['notes']):
                        print(f"          {j+1}. note : {note_info.get('note')}, absent : {note_info.get('absent')}")
            
            eleves_toutes_notes.append({
                'eleve': eleve,
                'notes_par_matiere': notes_par_matiere,
                'moyenne_generale': None,
                'rang': '-',
            })
        
        # 6. Vérifier la structure finale
        print(f"\n🎯 VÉRIFICATION STRUCTURE FINALE :")
        print(f"  • eleves_toutes_notes : {len(eleves_toutes_notes)}")
        
        for i, eleve_data in enumerate(eleves_toutes_notes):
            print(f"    Élève {i+1} : {eleve_data['eleve'].nom_complet}")
            notes_par_matiere = eleve_data['notes_par_matiere']
            print(f"      notes_par_matiere : {len(notes_par_matiere)}")
            
            for matiere_id, notes_matiere in notes_par_matiere.items():
                print(f"        Matière {matiere_id} :")
                print(f"          evaluations : {len(notes_matiere.get('evaluations', []))}")
                print(f"          notes : {len(notes_matiere.get('notes', []))}")
                print(f"          moyenne : {notes_matiere.get('moyenne')}")
                
                # Vérifier si les notes sont accessibles comme dans le template
                notes = notes_matiere.get('notes', [])
                for j, note_info in enumerate(notes):
                    note = note_info.get('note')
                    absent = note_info.get('absent')
                    print(f"            Note {j+1} : {note} (absent: {absent})")
        
        # 7. Diagnostic du problème template
        print(f"\n🔍 DIAGNOSTIC TEMPLATE :")
        print(f"  Le template utilise :")
        print(f"    {% for note_info in notes_matiere.notes %}")
        print(f"      {{ note_info.note }}")
        print(f"      {{ note_info.absent }}")
        print(f"")
        print(f"  Si notes_matiere.notes est vide, rien ne s'affiche.")
        print(f"  Si note_info.note est None, '-' s'affiche.")
        
        # 8. Solution proposée
        print(f"\n🔧 SOLUTION PROPOSÉE :")
        print(f"  1. Vérifier que notes_matiere.notes n'est pas vide")
        print(f"  2. Vérifier que note_info.note n'est pas None")
        print(f"  3. Ajouter du debug dans le template")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verifier_structure_donnees_consulter_notes()
