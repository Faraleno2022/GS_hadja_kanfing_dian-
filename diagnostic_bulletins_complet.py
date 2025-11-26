#!/usr/bin/env python
"""
Diagnostic complet pour trouver pourquoi les notes ne s'affichent pas dans les bulletins
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def diagnostic_complet_bulletins():
    """Diagnostic complet du problème de notes dans les bulletins"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        print("🔍 DIAGNOSTIC COMPLET : Pourquoi les notes ne s'affichent pas ?")
        
        # 1. Trouver une classe avec des élèves
        classe_note = ClasseNote.objects.first()
        if not classe_note:
            print("❌ Aucune classe trouvée")
            return
        
        print(f"\n📚 Classe analysée: {classe_note.nom} (ID: {classe_note.id})")
        
        # 2. Trouver la classe élève correspondante
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if not classe_eleve:
            print("❌ Classe élève non trouvée")
            return
        
        print(f"✅ Classe élève trouvée: {classe_eleve.nom}")
        
        # 3. Prendre quelques élèves et matières
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:3]
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)[:3]
        
        print(f"✅ {len(eleves)} élèves et {len(matieres)} matières analysés")
        
        # 4. Vérifier les évaluations pour OCTOBRE
        print("\n📋 Vérification des évaluations pour OCTOBRE:")
        total_evaluations = 0
        total_notes = 0
        
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode='OCTOBRE'
            )
            total_evaluations += evaluations.count()
            
            print(f"\n📖 {matiere.nom}:")
            print(f"  Évaluations OCTOBRE: {evaluations.count()}")
            
            for eval_octobre in evaluations:
                print(f"    • {eval_octobre.titre} (ID: {eval_octobre.id})")
                
                # Vérifier les notes pour cette évaluation
                notes_eval = NoteEleve.objects.filter(evaluation=eval_octobre)
                total_notes += notes_eval.count()
                print(f"      Notes: {notes_eval.count()}")
                
                # Afficher quelques notes
                for note in notes_eval[:2]:
                    print(f"        - {note.eleve.nom_complet[:25]}: {note.note}")
        
        print(f"\n📊 Résumé:")
        print(f"  • Évaluations OCTOBRE totales: {total_evaluations}")
        print(f"  • Notes OCTOBRE totales: {total_notes}")
        
        # 5. Tester la vue consulter_notes
        print("\n🌐 Test de la vue consulter_notes:")
        url = f'/notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE'
        print(f"URL: {url}")
        
        response = client.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Compter les notes non vides
            import re
            
            # Pattern pour les notes numériques
            notes_pattern = r'<td[^>]*class="note-cell[^>]*>(\d+[.,]\d+|\d+)</td>'
            notes_trouvees = re.findall(notes_pattern, content)
            
            # Pattern pour les cellules vides
            vide_pattern = r'<td[^>]*class="note-cell[^>]*>-</td>'
            vides = re.findall(vide_pattern, content)
            
            print(f"  ✅ Notes numériques trouvées: {len(notes_trouvees)}")
            print(f"  ❌ Cellules vides (-): {len(vides)}")
            
            if len(notes_trouvees) > 0:
                print("  📋 Exemples de notes trouvées:")
                for i, note in enumerate(notes_trouvees[:5]):
                    print(f"    {i+1}. {note}")
                print("  ✅ Les notes s'affichent !")
            else:
                print("  ❌ Aucune note numérique trouvée")
                
                # Chercher les erreurs dans le contenu
                if 'error' in content.lower() or 'erreur' in content.lower():
                    print("  ⚠️ Erreurs détectées dans la page")
                    # Afficher les erreurs
                    error_lines = [line for line in content.split('\n') if 'error' in line.lower() or 'erreur' in line.lower()]
                    for error_line in error_lines[:3]:
                        print(f"    {error_line.strip()[:100]}")
                
                # Afficher un extrait du HTML autour des notes
                print("\n  📄 Extrait du HTML (recherche de note-cell):")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'note-cell' in line and i < 200:
                        print(f"    {i+1}: {line.strip()[:100]}")
                        if i > 160:  # Limiter l'affichage
                            break
        else:
            print(f"  ❌ Erreur HTTP: {response.status_code}")
            print(response.content.decode('utf-8')[:300])
        
        # 6. Diagnostic spécifique du code
        print("\n🔧 Diagnostic du code:")
        
        # Vérifier si la correction consulter_notes est bien appliquée
        try:
            with open('notes/views.py', 'r', encoding='utf-8') as f:
                content_views = f.read()
            
            # Chercher la ligne corrigée
            if 'evaluations_mois = Evaluation.objects.filter(' in content_views:
                print("  ✅ Correction consulter_notes présente dans views.py")
            else:
                print("  ❌ Correction consulter_notes NON trouvée dans views.py")
            
            # Chercher NoteMensuelle
            if 'NoteMensuelle' in content_views:
                print("  ⚠️ NoteMensuelle encore présente dans le code")
                # Trouver les lignes
                lines = content_views.split('\n')
                for i, line in enumerate(lines):
                    if 'NoteMensuelle' in line:
                        print(f"    Ligne {i+1}: {line.strip()}")
            else:
                print("  ✅ NoteMensuelle supprimée du code")
                
        except Exception as e:
            print(f"  ❌ Erreur lecture views.py: {e}")
        
    except Exception as e:
        print(f"❌ Erreur générale: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostic_complet_bulletins()
