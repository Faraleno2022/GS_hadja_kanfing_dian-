#!/usr/bin/env python
"""
Test pour vérifier que l'export de classement récupère bien les notes mensuelles
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def test_export_classement_octobre():
    """Test l'export de classement pour OCTOBRE"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        print("🔍 Test de l'export de classement pour OCTOBRE")
        
        # Trouver une classe avec des données
        classe = ClasseNote.objects.first()
        if not classe:
            print("❌ Aucune classe trouvée")
            return
        
        print(f"✅ Classe utilisée: {classe.nom} (ID: {classe.id})")
        
        # Trouver la classe élève
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        if not classe_eleve:
            print("❌ Classe élève non trouvée")
            return
        
        # Prendre une matière
        matiere = MatiereNote.objects.filter(classe=classe, actif=True).first()
        if not matiere:
            print("❌ Aucune matière trouvée")
            return
        
        print(f"✅ Matière utilisée: {matiere.nom} (ID: {matiere.id})")
        
        # Vérifier les notes existantes
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')[:3]
        notes_count = 0
        
        for eleve in eleves:
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode='OCTOBRE'
            )
            if evaluations:
                eval_mois = evaluations.first()
                try:
                    note = NoteEleve.objects.get(eleve=eleve, evaluation=eval_mois)
                    notes_count += 1
                    print(f"  📝 Note trouvée: {eleve.nom_complet[:20]} = {note.note}")
                except NoteEleve.DoesNotExist:
                    print(f"  ❌ Note manquante: {eleve.nom_complet[:20]}")
        
        print(f"\n📈 Total de notes trouvées: {notes_count}")
        
        # Tester l'export de classement
        print("\n🌐 Test de l'export de classement:")
        url = f'/notes/exporter-classement/?classe_id={classe.id}&matiere_id={matiere.id}&periode=OCTOBRE'
        print(f"URL: {url}")
        
        response = client.get(url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Vérifier que c'est bien un fichier Excel
            content_type = response.get('Content-Type', '')
            if 'excel' in content_type or 'xlsx' in content_type or 'vnd.openxmlformats' in content_type:
                print("✅ Fichier Excel généré avec succès")
                
                # Vérifier la taille du fichier
                file_size = len(response.content)
                print(f"Taille du fichier: {file_size} octets")
                
                if file_size > 1000:  # Fichier significatif
                    print("✅ Fichier Excel semble contenir des données")
                else:
                    print("⚠️ Fichier Excel très petit, possible problème")
                
                # Vérifier le nom du fichier
                content_disposition = response.get('Content-Disposition', '')
                if '.xlsx' in content_disposition:
                    print(f"✅ Nom de fichier Excel: {content_disposition}")
                
            else:
                print(f"❌ Pas un fichier Excel: {content_type}")
                print("Contenu de la réponse:")
                print(response.content.decode('utf-8')[:500])
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(response.content.decode('utf-8')[:300])
            
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_export_classement_octobre()
