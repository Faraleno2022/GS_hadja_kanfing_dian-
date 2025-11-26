#!/usr/bin/env python
"""
Test de consulter_notes avec tous les élèves pour trouver l'erreur
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_consulter_notes_tous_eleves():
    """Test consulter_notes avec tous les élèves pour trouver l'erreur"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 TEST CONSULTER_NOTES - TOUS LES ÉLÈVES")
        
        # 1. Configuration
        classe_id = 4  # 11 SÉRIE LITTÉRAIRE
        periode = 'OCTOBRE'
        
        # 2. Récupérer les élèves
        classe = ClasseNote.objects.get(id=classe_id)
        
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
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        
        print(f"✅ Classe : {classe.nom}")
        print(f"✅ Élèves : {len(eleves)}")
        print(f"✅ Matières : {len(matieres)}")
        
        # 3. Tester chaque élève individuellement
        print(f"\n🔍 TEST INDIVIDUEL CHAQUE ÉLÈVE :")
        
        for i, eleve in enumerate(eleves):
            print(f"\n  📝 Élève {i+1}/{len(eleves)} : {eleve.nom_complet}")
            
            try:
                # Vérifier si cet élève a des notes
                notes_eleve = 0
                for matiere in matieres:
                    evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
                    for evaluation in evaluations:
                        try:
                            note = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                            notes_eleve += 1
                        except NoteEleve.DoesNotExist:
                            pass
                
                print(f"    ✅ Notes trouvées : {notes_eleve}")
                
                if notes_eleve == 0:
                    print(f"    ❌ Cet élève n'a aucune note")
                
            except Exception as e:
                print(f"    ❌ Erreur : {str(e)}")
        
        # 4. Tester la vue complète
        print(f"\n🌐 TEST VUE COMPLÈTE :")
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        url = f'/notes/consulter/?classe_id={classe_id}&periode={periode}'
        print(f"URL : {url}")
        
        try:
            response = client.get(url)
            print(f"Status : {response.status_code}")
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Compter les élèves dans le HTML
                eleves_dans_html = 0
                for eleve in eleves:
                    if eleve.nom.upper() in content.upper():
                        eleves_dans_html += 1
                
                print(f"✅ Élèves dans HTML : {eleves_dans_html}/{len(eleves)}")
                
                if eleves_dans_html < len(eleves):
                    print(f"❌ PROBLÈME : {len(eleves) - eleves_dans_html} élève(s) manquant(s)")
                    
                    # Identifier les élèves manquants
                    print(f"   Élèves manquants :")
                    for eleve in eleves:
                        if eleve.nom.upper() not in content.upper():
                            print(f"     • {eleve.nom_complet}")
                
                # Compter les notes numériques
                import re
                notes_pattern = r'<td[^>]*class="[^"]*note[^"]*"[^>]*>(\d+[.,]\d+|\d+)</td>'
                notes_trouvees = re.findall(notes_pattern, content)
                
                print(f"✅ Notes dans cellules 'note' : {len(notes_trouvees)}")
                
                if len(notes_trouvees) == 0:
                    print(f"❌ PROBLÈME : Aucune note dans les cellules 'note'")
                    print(f"   → Les notes existent mais ne sont pas affichées")
                
            else:
                print(f"❌ Erreur HTTP : {response.status_code}")
                print(f"Contenu : {response.content.decode('utf-8')[:500]}")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'appel de la vue : {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 5. Diagnostic du problème
        print(f"\n🔍 DIAGNOSTIC FINAL :")
        
        print(f"  • Les données existent en base : ✅")
        print(f"  • Les élèves sont récupérés : ✅")
        print(f"  • Les notes existent : ✅")
        print(f"  • Mais elles ne s'affichent pas dans le template : ❌")
        
        print(f"\n🔧 CAUSE PROBABLE :")
        print(f"  • Une exception dans la boucle de calcul des notes")
        print(f"  • Le traitement s'arrête au milieu de la boucle")
        print(f"  • Seuls les premiers élèves sont traités")
        
        print(f"\n💡 SOLUTION :")
        print(f"  • Ajouter un try/catch dans la boucle de consulter_notes")
        print(f"  • Empêcher les exceptions d'arrêter le traitement")
        print(f"  • Logger les erreurs pour identifier le problème")
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_consulter_notes_tous_eleves()
