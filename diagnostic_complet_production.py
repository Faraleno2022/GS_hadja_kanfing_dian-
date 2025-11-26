#!/usr/bin/env python
"""
Diagnostic complet pour le serveur de production
Problèmes : 
1. Template ne vient pas avec la liste des élèves
2. Notes importées non visibles
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def diagnostic_complet_production():
    """Diagnostic complet pour identifier tous les problèmes sur le serveur"""
    
    try:
        from django.test import Client
        from django.contrib.auth.models import User
        from django.template.loader import render_to_string
        from django.urls import reverse
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 DIAGNOSTIC COMPLET - SERVEUR PRODUCTION")
        print("🎯 Problèmes signalés :")
        print("   1. Template ne vient pas avec la liste des élèves")
        print("   2. Notes importées non visibles")
        
        # 1. Vérifier l'état de la base de données
        print(f"\n📊 ÉTAT DE LA BASE DE DONNÉES :")
        
        classes_count = ClasseNote.objects.count()
        eleves_count = Eleve.objects.count()
        matieres_count = MatiereNote.objects.count()
        evaluations_count = Evaluation.objects.count()
        notes_count = NoteEleve.objects.count()
        
        print(f"  • Classes : {classes_count}")
        print(f"  • Élèves : {eleves_count}")
        print(f"  • Matières : {matieres_count}")
        print(f"  • Évaluations : {evaluations_count}")
        print(f"  • Notes : {notes_count}")
        
        if classes_count == 0:
            print("❌ Aucune classe dans la base - problème majeur")
            return
        
        # 2. Trouver une classe test
        print(f"\n📚 RECHERCHE D'UNE CLASSE TEST :")
        
        # Chercher la classe "11 SÉRIE LITTÉRAIRE"
        classe_test = None
        classes = ClasseNote.objects.all()
        
        for classe in classes:
            if '11' in classe.nom.upper() and ('LITT' in classe.nom.upper() or 'LITER' in classe.nom.upper()):
                classe_test = classe
                print(f"  ✅ {classe.nom} (ID: {classe.id}) ← CLASSE TEST")
                break
        
        if not classe_test:
            classe_test = classes.first()
            print(f"  🔄 Utilisation : {classe_test.nom} (ID: {classe_test.id})")
        
        # 3. Vérifier les élèves de cette classe
        print(f"\n👥 VÉRIFICATION DES ÉLÈVES :")
        
        # Trouver la classe élève correspondante
        mapping_classes = {
            59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
        }
        
        classe_eleve = None
        if classe_test.id in mapping_classes:
            classe_eleve = ClasseEleve.objects.filter(id=mapping_classes[classe_test.id]).first()
        
        if not classe_eleve:
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe_test.nom,
                annee_scolaire=classe_test.annee_scolaire,
                ecole=classe_test.ecole
            ).first()
        
        if classe_eleve:
            eleves_classe = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            print(f"  ✅ {len(eleves_classe)} élèves actifs trouvés")
            
            if len(eleves_classe) > 0:
                print(f"  📋 5 premiers élèves :")
                for i, eleve in enumerate(eleves_classe[:5]):
                    print(f"    {i+1}. {eleve.matricule} - {eleve.nom_complet}")
            else:
                print(f"  ❌ Aucun élève actif trouvé")
        else:
            print(f"  ❌ Classe élève non trouvée")
            eleves_classe = []
        
        # 4. Vérifier les matières
        matieres = MatiereNote.objects.filter(classe=classe_test, actif=True)
        print(f"\n📖 {len(matieres)} matières actives")
        for matiere in matieres[:3]:
            print(f"  • {matiere.nom} (ID: {matiere.id})")
        
        # 5. Vérifier les notes existantes
        print(f"\n📋 VÉRIFICATION DES NOTES EXISTANTES :")
        
        total_notes_classe = 0
        for matiere in matieres:
            notes_matiere = NoteEleve.objects.filter(evaluation__matiere=matiere)
            total_notes_classe += notes_matiere.count()
            print(f"  • {matiere.nom}: {notes_matiere.count()} notes")
        
        print(f"  📊 Total notes pour la classe : {total_notes_classe}")
        
        # 6. Tester les différentes vues
        print(f"\n🌐 TEST DES VUES :")
        
        client = Client()
        user = User.objects.first()
        if not user:
            print("❌ Aucun utilisateur trouvé pour les tests")
            return
        
        client.force_login(user)
        
        # Test 1: Vue consulter_notes
        print(f"\n  📋 Test 1 : consulter_notes")
        url_consulter = f'/notes/consulter/?classe_id={classe_test.id}&periode=OCTOBRE'
        print(f"    URL : {url_consulter}")
        
        try:
            response = client.get(url_consulter)
            print(f"    Status : {response.status_code}")
            
            if response.status_code == 200:
                content = response.content.decode('utf-8')
                
                # Vérifier si les élèves sont dans le template
                eleves_dans_template = content.count('eleve') > 10  # Approximation
                tableau_present = '<table' in content
                notes_presentes = any(note in content for note in ['10.5', '12.0', '15.5', '8.5'])
                
                print(f"    ✅ Template chargé")
                print(f"    📊 Élèves dans template : {'Oui' if eleves_dans_template else 'Non'}")
                print(f"    📊 Tableau présent : {'Oui' if tableau_present else 'Non'}")
                print(f"    📊 Notes visibles : {'Oui' if notes_presentes else 'Non'}")
                
                if not eleves_dans_template:
                    print(f"    ❌ PROBLÈME : Les élèves ne sont pas passés au template")
                
                if not notes_presentes and total_notes_classe > 0:
                    print(f"    ❌ PROBLÈME : Les notes existent mais ne s'affichent pas")
                
            else:
                print(f"    ❌ Erreur HTTP : {response.status_code}")
                print(f"    Contenu : {response.content.decode('utf-8')[:200]}")
                
        except Exception as e:
            print(f"    ❌ Erreur : {str(e)}")
        
        # Test 2: Vue bulletin_dynamique
        if len(eleves_classe) > 0:
            print(f"\n  📋 Test 2 : bulletin_dynamique")
            eleve_test = eleves_classe.first()
            url_bulletin = f'/notes/bulletins/?classe_id={classe_test.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel'
            print(f"    URL : {url_bulletin}")
            
            try:
                response = client.get(url_bulletin)
                print(f"    Status : {response.status_code}")
                
                if response.status_code == 200:
                    content = response.content.decode('utf-8')
                    
                    # Vérifier les éléments du bulletin
                    eleve_nom_present = eleve_test.nom.upper() in content.upper()
                    notes_bulletin = any(note in content for note in ['10.5', '12.0', '15.5', '8.5'])
                    
                    print(f"    ✅ Bulletin chargé")
                    print(f"    📊 Nom élève présent : {'Oui' if eleve_nom_present else 'Non'}")
                    print(f"    📊 Notes dans bulletin : {'Oui' if notes_bulletin else 'Non'}")
                    
                else:
                    print(f"    ❌ Erreur HTTP : {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Erreur : {str(e)}")
        
        # 7. Diagnostic des problèmes possibles
        print(f"\n🔍 DIAGNOSTIC DES PROBLÈMES :")
        
        if len(eleves_classe) == 0:
            print(f"❌ Problème 1 : Aucun élève trouvé pour la classe")
            print(f"   → Vérifier le mapping entre ClasseNote et ClasseEleve")
        
        if total_notes_classe == 0:
            print(f"❌ Problème 2 : Aucune note dans la base")
            print(f"   → Exécuter : python corriger_classement_production.py")
        
        if evaluations_count == 0:
            print(f"❌ Problème 3 : Aucune évaluation dans la base")
            print(f"   → Les notes importées ne peuvent pas être associées")
        
        # 8. Vérifier les imports récents
        print(f"\n📥 VÉRIFICATION DES IMPORTS RÉCENTS :")
        
        # Chercher des notes récentes (dernières 24h)
        from django.utils import timezone
        from datetime import timedelta
        
        hier = timezone.now() - timedelta(hours=24)
        notes_recentes = NoteEleve.objects.filter(date_creation__gte=hier) if hasattr(NoteEleve._meta.get_field('date_creation'), 'auto_now_add') else NoteEleve.objects.all()[:10]
        
        print(f"  • Notes récentes : {notes_recentes.count()}")
        
        if notes_recentes.count() > 0:
            print(f"  📋 Dernières notes importées :")
            for note in notes_recentes[:5]:
                print(f"    • {note.eleve.nom_complet[:25]} - {note.evaluation.matiere.nom} : {note.note}")
        else:
            print(f"  ℹ️ Aucune note récente détectée")
        
        # 9. Instructions de correction
        print(f"\n🔧 INSTRUCTIONS DE CORRECTION :")
        
        print(f"1. Mettre à jour le code :")
        print(f"   git reset --hard origin/main")
        print(f"   touch ecole_moderne/wsgi.py")
        print(f"")
        
        print(f"2. Diagnostiquer spécifiquement :")
        print(f"   python diagnostic_bulletin_pdf_production.py")
        print(f"")
        
        print(f"3. Créer les données manquantes :")
        print(f"   python corriger_classement_production.py")
        print(f"")
        
        print(f"4. Vérifier les imports :")
        print(f"   - Vérifier que les fichiers Excel/CSV contiennent bien les notes")
        print(f"   - Vérifier que les imports se terminent sans erreur")
        print(f"   - Vérifier que les évaluations sont créées pendant l'import")
        
        print(f"\n🌐 URLS de test après correction :")
        print(f"• Consultation notes : /notes/consulter/?classe_id={classe_test.id}&periode=OCTOBRE")
        if len(eleves_classe) > 0:
            print(f"• Bulletin élève : /notes/bulletins/?classe_id={classe_test.id}&eleve_id={eleves_classe.first().id}&periode=OCTOBRE&system_type=mensuel")
        
    except Exception as e:
        print(f"❌ Erreur générale : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostic_complet_production()
