#!/usr/bin/env python
"""
Test spécifique pour la vue consulter_notes sur le serveur de production
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_consulter_notes_debug():
    """Test détaillé de consulter_notes pour trouver pourquoi les élèves ne sont pas passés"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 TEST SPÉCIFIQUE - consulter_notes")
        
        # 1. Configuration du test
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        periode = 'OCTOBRE'
        url = f'/notes/consulter/?classe_id={classe_id}&periode={periode}'
        
        print(f"URL test : {url}")
        
        # 2. Vérifier les données avant l'appel
        print(f"\n📊 VÉRIFICATION DES DONNÉES AVANT L'APPEL :")
        
        classe = ClasseNote.objects.get(id=classe_id)
        print(f"  ✅ Classe : {classe.nom}")
        
        # Vérifier le mapping
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
            print(f"  ❌ Classe élève non trouvée")
            return
        
        print(f"  ✅ Classe élève : {classe_eleve.nom}")
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"  ✅ Élèves actifs : {len(eleves)}")
        
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        print(f"  ✅ Matières : {len(matieres)}")
        
        # Vérifier les évaluations OCTOBRE
        evaluations_octobre = Evaluation.objects.filter(periode='OCTOBRE')
        print(f"  ✅ Évaluations OCTOBRE : {evaluations_octobre.count()}")
        
        notes_octobre = NoteEleve.objects.filter(evaluation__periode='OCTOBRE')
        print(f"  ✅ Notes OCTOBRE : {notes_octobre.count()}")
        
        # 3. Appeler la vue
        print(f"\n🌐 APPEL DE LA VUE :")
        
        response = client.get(url)
        print(f"  Status : {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ❌ Erreur HTTP : {response.status_code}")
            print(f"  Contenu : {response.content.decode('utf-8')[:500]}")
            return
        
        # 4. Analyser le contexte
        print(f"\n📋 ANALYSE DU CONTEXTE :")
        
        # Le template est chargé, vérifier le contenu
        content = response.content.decode('utf-8')
        
        # Compter les occurrences d'élèves dans le HTML
        eleve_names = []
        for eleve in eleves:
            if eleve.nom.upper() in content.upper():
                eleve_names.append(eleve.nom)
        
        print(f"  📊 Élèves trouvés dans le HTML : {len(eleve_names)}/{len(eleves)}")
        if len(eleve_names) > 0:
            print(f"    Exemples : {', '.join(eleve_names[:3])}")
        
        # Chercher les patterns de notes
        import re
        
        # Pattern pour les notes dans les cellules
        notes_pattern = r'<td[^>]*class="[^"]*note[^"]*"[^>]*>(\d+[.,]\d+|\d+)</td>'
        notes_trouvees = re.findall(notes_pattern, content)
        
        # Pattern pour tous les nombres dans les TD
        all_numbers_pattern = r'<td[^>]*>(\d+[.,]\d+|\d+)</td>'
        all_numbers = re.findall(all_numbers_pattern, content)
        
        print(f"  📊 Notes dans cellules 'note' : {len(notes_trouvees)}")
        print(f"  📊 Tous les nombres dans TD : {len(all_numbers)}")
        
        # Vérifier la structure du tableau
        table_count = content.count('<table')
        tr_count = content.count('<tr')
        td_count = content.count('<td')
        
        print(f"  📊 Structure HTML : {table_count} tableaux, {tr_count} lignes, {td_count} cellules")
        
        # 5. Diagnostic du problème
        print(f"\n🔍 DIAGNOSTIC DU PROBLÈME :")
        
        if len(eleve_names) == 0:
            print(f"  ❌ PROBLÈME CONFIRMÉ : Les élèves ne sont pas dans le template")
            print(f"  🔍 CAUSE POSSIBLE :")
            print(f"     • La variable 'eleves_toutes_notes' est vide")
            print(f"     • Le template n'itère pas correctement")
            print(f"     • Problème dans la vue consulter_notes")
        
        if len(notes_trouvees) == 0 and len(all_numbers) > 0:
            print(f"  ❌ PROBLÈME : Les notes existent mais ne sont pas dans les bonnes cellules")
            print(f"  🔍 Le template affiche des nombres mais pas dans les cellules 'note'")
        
        if len(all_numbers) == 0:
            print(f"  ❌ PROBLÈME : Aucune donnée numérique dans le template")
            print(f"  🔍 Le template est complètement vide de données")
        
        # 6. Vérifier spécifiquement le contexte de la vue
        print(f"\n🔧 VÉRIFICATION SPÉCIFIQUE :")
        
        # Simuler l'appel direct à la vue pour déboguer
        from django.test import RequestFactory
        from notes.views import consulter_notes
        
        factory = RequestFactory()
        request = factory.get(url)
        request.user = user
        
        try:
            # Appeler la vue directement
            response_direct = consulter_notes(request)
            
            if hasattr(response_direct, 'context_data'):
                context = response_direct.context_data
                print(f"  ✅ Contexte disponible")
                
                if 'eleves_toutes_notes' in context:
                    eleves_context = context['eleves_toutes_notes']
                    print(f"  📊 eleves_toutes_notes dans contexte : {len(eleves_context)}")
                    
                    if len(eleves_context) > 0:
                        premier_eleve = eleves_context[0]
                        print(f"    Premier élève : {premier_eleve.get('eleve', 'Non trouvé')}")
                        
                        notes_premier = premier_eleve.get('notes_par_matiere', {})
                        print(f"    Notes par matière : {len(notes_premier)}")
                    else:
                        print(f"    ❌ eleves_toutes_notes est vide")
                else:
                    print(f"    ❌ 'eleves_toutes_notes' pas dans le contexte")
                
                # Afficher toutes les clés du contexte
                print(f"    Clés du contexte : {list(context.keys())}")
                
            else:
                print(f"  ❌ Pas de context_data disponible")
                
        except Exception as e:
            print(f"  ❌ Erreur lors de l'appel direct : {str(e)}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_consulter_notes_debug()
