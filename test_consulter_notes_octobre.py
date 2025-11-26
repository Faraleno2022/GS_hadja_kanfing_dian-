#!/usr/bin/env python
"""
Test pour vérifier que la vue consulter_notes récupère bien les notes mensuelles
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_consulter_notes_octobre():
    """Test la vue consulter_notes pour OCTOBRE"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        print("🔍 Test de la vue consulter_notes pour OCTOBRE")
        
        # URL de test
        url = '/notes/consulter/?classe_id=6&periode=OCTOBRE'
        print(f"URL: {url}")
        
        # Vérifier que les données existent en base
        print("\n📊 Vérification des données en base:")
        
        # Chercher une classe existante
        try:
            classe = ClasseNote.objects.get(id=6)
        except ClasseNote.DoesNotExist:
            # Prendre la première classe disponible
            classe = ClasseNote.objects.first()
            if not classe:
                print("❌ Aucune classe trouvée en base")
                return
        
        print(f"✅ Classe utilisée: {classe.nom} (ID: {classe.id})")
        
        # Mettre à jour l'URL avec la bonne classe
        url = f'/notes/consulter/?classe_id={classe.id}&periode=OCTOBRE'
        print(f"URL mise à jour: {url}")
        
        # Trouver la classe élève
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        if classe_eleve:
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:3]  # Limiter à 3 pour le test
            print(f"✅ {len(eleves)} élèves trouvés")
            
            matieres = MatiereNote.objects.filter(classe=classe, actif=True)[:3]  # Limiter à 3 pour le test
            print(f"✅ {len(matieres)} matières trouvées")
            
            # Vérifier les notes pour OCTOBRE
            notes_count = 0
            for eleve in eleves:
                for matiere in matieres:
                    evaluations = Evaluation.objects.filter(
                        matiere=matiere,
                        periode='OCTOBRE'
                    )
                    if evaluations:
                        eval_mois = evaluations.first()
                        try:
                            note = NoteEleve.objects.get(eleve=eleve, evaluation=eval_mois)
                            notes_count += 1
                            print(f"  📝 Note trouvée: {eleve.nom_complet[:20]} - {matiere.nom[:15]} = {note.note}")
                        except NoteEleve.DoesNotExist:
                            print(f"  ❌ Note manquante: {eleve.nom_complet[:20]} - {matiere.nom[:15]}")
            
            print(f"\n📈 Total de notes trouvées: {notes_count}")
        
        # Tester la vue
        print("\n🌐 Test de la vue:")
        response = client.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Vérifier si les notes apparaissent dans le HTML
            import re
            
            # Compter les notes non vides
            notes_pattern = r'<td[^>]*class="note-cell[^>]*>(\d+,\d+|\d+\.\d+)</td>'
            notes_trouvees = re.findall(notes_pattern, content)
            
            print(f"✅ Notes trouvées dans le HTML: {len(notes_trouvees)}")
            
            if len(notes_trouvees) > 0:
                print("📋 Exemples de notes trouvées:")
                for i, note in enumerate(notes_trouvees[:5]):
                    print(f"  {i+1}. {note}")
                
                print("\n🎉 SUCCÈS ! Les notes s'affichent correctement")
            else:
                print("\n❌ Les notes ne s'affichent pas encore")
                
                # Chercher les cellules vides
                vide_pattern = r'<td[^>]*class="note-cell[^>]*>-</td>'
                vides = re.findall(vide_pattern, content)
                print(f"Cellules vides trouvées: {len(vides)}")
                
                # Afficher un extrait du HTML pour déboguer
                print("\n📄 Extrait du HTML:")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'note-cell' in line and i < 100:  # Premières 100 lignes
                        print(f"  {i+1}: {line.strip()[:80]}")
                        if i > 10:  # Limiter l'affichage
                            break
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_consulter_notes_octobre()
