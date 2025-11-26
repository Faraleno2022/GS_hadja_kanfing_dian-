#!/usr/bin/env python
"""
Diagnostic spécifique pour les bulletins PDF sur le serveur de production
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def diagnostic_bulletin_pdf_production():
    """Diagnostic pour les bulletins PDF sur le serveur de production"""
    
    try:
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        from django.test import Client
        from django.contrib.auth.models import User
        
        print("🔧 DIAGNOSTIC BULLETIN PDF - SERVEUR PRODUCTION")
        print("🎯 Problème : Les notes ne s'affichent pas dans les bulletins PDF")
        
        # 1. Lister toutes les classes
        print("\n📚 Classes disponibles :")
        classes = ClasseNote.objects.all().order_by('nom')
        
        if classes.count() == 0:
            print("❌ Aucune classe trouvée")
            return
        
        # Chercher la classe "11 SÉRIE LITTÉRAIRE"
        classe_cible = None
        for classe in classes:
            if '11' in classe.nom.upper() and ('LITT' in classe.nom.upper() or 'LITER' in classe.nom.upper()):
                classe_cible = classe
                print(f"  ✅ {classe.nom} (ID: {classe.id}) ← CLASSE CIBLE")
                break
            else:
                print(f"  • {classe.nom} (ID: {classe.id})")
        
        if not classe_cible:
            print("❌ Classe '11 SÉRIE LITTÉRAIRE' non trouvée")
            classe_cible = classes.first()
            print(f"  🔄 Utilisation : {classe_cible.nom} (ID: {classe_cible.id})")
        
        # 2. Trouver la classe élève
        print(f"\n🔍 Recherche classe élève pour : {classe_cible.nom}")
        
        mapping_classes = {
            59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
        }
        
        classe_eleve = None
        if classe_cible.id in mapping_classes:
            classe_eleve = ClasseEleve.objects.filter(id=mapping_classes[classe_cible.id]).first()
            if classe_eleve:
                print(f"  ✅ Trouvée via mapping : {classe_eleve.nom}")
        
        if not classe_eleve:
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe_cible.nom,
                annee_scolaire=classe_cible.annee_scolaire,
                ecole=classe_cible.ecole
            ).first()
            if classe_eleve:
                print(f"  ✅ Trouvée par nom : {classe_eleve.nom}")
        
        if not classe_eleve:
            print("❌ Classe élève non trouvée")
            return
        
        # 3. Prendre un élève
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        if len(eleves) == 0:
            print("❌ Aucun élève trouvé")
            return
        
        eleve_test = eleves.first()
        print(f"\n👥 Élève test : {eleve_test.matricule} - {eleve_test.nom_complet}")
        print(f"   Total élèves : {len(eleves)}")
        
        # 4. Vérifier les matières
        matieres = MatiereNote.objects.filter(classe=classe_cible, actif=True)
        if len(matieres) == 0:
            print("❌ Aucune matière trouvée")
            return
        
        print(f"\n📖 {len(matières)} matières trouvées")
        for matiere in matieres[:3]:
            print(f"  • {matiere.nom} (ID: {matiere.id})")
        
        # 5. Vérifier les évaluations pour différentes périodes
        periodes_a_tester = ['OCTOBRE', 'TRIMESTRE_1', 'TRIMESTRE_2']
        
        print(f"\n📋 Vérification des évaluations par période :")
        
        for periode in periodes_a_tester:
            print(f"\n  📅 Période : {periode}")
            
            total_evals = 0
            total_notes = 0
            matieres_avec_eval = []
            
            for matiere in matieres:
                evals = Evaluation.objects.filter(matiere=matiere, periode=periode)
                total_evals += evals.count()
                
                if evals.exists():
                    matieres_avec_eval.append(matiere)
                    notes_count = 0
                    for eval in evals:
                        notes = NoteEleve.objects.filter(evaluation=eval, eleve=eleve_test)
                        total_notes += notes.count()
                        notes_count += notes.count()
                    
                    print(f"    ✅ {matiere.nom[:20]:20} : {evals.count()} eval, {notes_count} notes")
                else:
                    print(f"    ❌ {matiere.nom[:20]:20} : 0 évaluation")
            
            print(f"    📊 Total : {total_evals} évaluations, {total_notes} notes pour l'élève")
        
        # 6. Tester la vue bulletin_dynamique
        print(f"\n🌐 Test de la vue bulletin_dynamique :")
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        # Tester avec OCTOBRE
        url = f'/notes/bulletins/?classe_id={classe_cible.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel'
        print(f"URL test : {url}")
        
        response = client.get(url)
        print(f"Status : {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            
            # Chercher les notes dans le HTML
            import re
            
            # Pattern pour les notes numériques
            notes_pattern = r'<td[^>]*>(\d+[.,]\d+|\d+)</td>'
            notes_trouvees = re.findall(notes_pattern, content)
            
            # Pattern pour "Non saisi" ou "-"
            non_saisi_pattern = r'<td[^>]*>(Non saisi|-|N/A)</td>'
            non_saisi_trouvees = re.findall(non_saisi_pattern, content)
            
            print(f"  Notes numériques trouvées : {len(notes_trouvees)}")
            print(f"  'Non saisi' trouvés : {len(non_saisi_trouvees)}")
            
            if len(notes_trouvees) > 0:
                print("  ✅ Des notes sont présentes dans le bulletin HTML")
                print("  📋 Exemples de notes :")
                for note in notes_trouvees[:5]:
                    print(f"    • {note}")
            else:
                print("  ❌ Aucune note numérique trouvée")
                print("  🔍 Le problème vient des données manquantes")
        
        # 7. Diagnostic du problème
        print(f"\n🔍 DIAGNOSTIC DU PROBLÈME :")
        
        # Vérifier OCTOBRE spécifiquement
        evals_octobre = Evaluation.objects.filter(periode='OCTOBRE')
        notes_octobre = NoteEleve.objects.filter(evaluation__periode='OCTOBRE')
        
        print(f"  Évaluations OCTOBRE totales : {evals_octobre.count()}")
        print(f"  Notes OCTOBRE totales : {notes_octobre.count()}")
        
        if evals_octobre.count() == 0:
            print(f"\n❌ PROBLÈME IDENTIFIÉ :")
            print(f"   • Aucune évaluation OCTOBRE dans la base")
            print(f"   • Le bulletin mensuel ne peut pas trouver de notes")
            print(f"   • Solution : Créer les évaluations OCTOBRE")
            
            print(f"\n🔧 SOLUTION :")
            print(f"   1. Exécuter : python corriger_classement_production.py")
            print(f"   2. Cela créera les évaluations et notes manquantes")
            print(f"   3. Les bulletins PDF afficheront alors les notes")
        
        elif notes_octobre.count() == 0:
            print(f"\n❌ PROBLÈME IDENTIFIÉ :")
            print(f"   • Évaluations OCTOBRE existent mais pas de notes")
            print(f"   • Solution : Créer les notes pour les élèves")
        
        else:
            print(f"\n✅ Les données OCTOBRE existent")
            print(f"   Le problème pourrait être dans le template PDF")
            print(f"   Vérifier que WeasyPrint est installé sur le serveur")
        
        # 8. Instructions
        print(f"\n📋 INSTRUCTIONS COMPLÈTES :")
        print(f"1. Mettre à jour le code :")
        print(f"   git reset --hard origin/main")
        print(f"")
        print(f"2. Créer les données manquantes :")
        print(f"   python corriger_classement_production.py")
        print(f"")
        print(f"3. Tester le bulletin PDF :")
        print(f"   https://www.myschoolgn.space/notes/bulletins/pdf/?classe_id={classe_cible.id}&eleve_id={eleve_test.id}&periode=OCTOBRE&system_type=mensuel")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostic_bulletin_pdf_production()
