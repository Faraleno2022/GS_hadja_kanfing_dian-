#!/usr/bin/env python
"""
Vérification des évaluations existantes et création si nécessaire
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def verifier_et_creer_evaluations():
    """Vérifier les évaluations existantes et créer celles d'OCTOBRE si nécessaire"""
    
    try:
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        from decimal import Decimal
        import random
        
        print("🔍 VÉRIFICATION DES ÉVALUATIONS EXISTANTES")
        
        # Prendre une classe test
        classe_note = ClasseNote.objects.first()
        if not classe_note:
            print("❌ Aucune classe trouvée")
            return
        
        print(f"📚 Classe: {classe_note.nom}")
        
        # Trouver la classe élève
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if not classe_eleve:
            print("❌ Classe élève non trouvée")
            return
        
        # Prendre quelques matières
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)[:3]
        print(f"✅ {len(matieres)} matières analysées")
        
        # Vérifier toutes les périodes
        periodes = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'TRIMESTRE_1', 'TRIMESTRE_2']
        
        print("\n📊 Évaluations par période:")
        for periode in periodes:
            total_eval = Evaluation.objects.filter(periode=periode).count()
            print(f"  {periode}: {total_eval} évaluations")
        
        # Vérifier spécifiquement pour nos matières
        print("\n📋 Évaluations par matière et période:")
        for matiere in matieres:
            print(f"\n📖 {matiere.nom}:")
            for periode in ['OCTOBRE', 'TRIMESTRE_1']:
                evals = Evaluation.objects.filter(matiere=matiere, periode=periode)
                print(f"  {periode}: {evals.count()} évaluation(s)")
                for eval in evals:
                    print(f"    • {eval.titre} (ID: {eval.id})")
        
        # Créer les évaluations manquantes pour OCTOBRE
        print("\n🔧 CRÉATION DES ÉVALUATIONS MANQUANTES POUR OCTOBRE")
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"✅ {len(eleves)} élèves dans la classe")
        
        evaluations_crees = 0
        notes_crees = 0
        
        for matiere in matieres:
            # Vérifier si une évaluation OCTOBRE existe pour cette matière
            eval_octobre = Evaluation.objects.filter(
                matiere=matiere,
                periode='OCTOBRE'
            ).first()
            
            if not eval_octobre:
                # Créer l'évaluation
                eval_octobre = Evaluation.objects.create(
                    matiere=matiere,
                    periode='OCTOBRE',
                    titre=f'Devoir Octobre {matiere.nom}',
                    type_evaluation='DEVOIR',
                    date_evaluation='2024-10-15',
                    coefficient=matiere.coefficient
                )
                evaluations_crees += 1
                print(f"  ✅ Évaluation créée: {eval_octobre.titre}")
            else:
                print(f"  ℹ️ Évaluation existante: {eval_octobre.titre}")
            
            # Créer des notes pour les élèves
            for eleve in eleves:
                # Vérifier si la note existe déjà
                note_existante = NoteEleve.objects.filter(
                    eleve=eleve,
                    evaluation=eval_octobre
                ).first()
                
                if not note_existante:
                    # Créer une note aléatoire
                    note_aleatoire = Decimal(str(random.uniform(8, 18)))
                    note = NoteEleve.objects.create(
                        eleve=eleve,
                        evaluation=eval_octobre,
                        note=note_aleatoire
                    )
                    notes_crees += 1
                    print(f"    📝 Note créée: {eleve.nom_complet[:20]} = {note_aleatoire}")
        
        print(f"\n📈 RÉSUMÉ:")
        print(f"  • Évaluations créées: {evaluations_crees}")
        print(f"  • Notes créées: {notes_crees}")
        
        # Tester la vue après création
        print("\n🌐 TEST APRÈS CRÉATION:")
        from django.test import Client
        from django.contrib.auth.models import User
        
        client = Client()
        user = User.objects.first()
        client.force_login(user)
        
        url = f'/notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE'
        response = client.get(url)
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            import re
            
            # Compter les notes numériques
            notes_pattern = r'<td[^>]*class="note-cell[^>]*>(\d+[.,]\d+|\d+)</td>'
            notes_trouvees = re.findall(notes_pattern, content)
            
            print(f"  ✅ Notes trouvées dans le HTML: {len(notes_trouvees)}")
            
            if len(notes_trouvees) > 0:
                print("  🎉 SUCCÈS ! Les notes s'affichent maintenant")
                print("  📋 Exemples de notes:")
                for i, note in enumerate(notes_trouvees[:5]):
                    print(f"    {i+1}. {note}")
            else:
                print("  ❌ Les notes ne s'affichent toujours pas")
        else:
            print(f"  ❌ Erreur HTTP: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verifier_et_creer_evaluations()
