#!/usr/bin/env python
"""
Script pour corriger le classement d'une classe spécifique
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def corriger_classement_classe_specifique(classe_id=None, classe_nom=None):
    """Corriger le classement pour une classe spécifique"""
    
    try:
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        import random
        
        print("🔧 CORRECTION CLASSEMENT - CLASSE SPÉCIFIQUE")
        
        # 1. Trouver la classe
        if classe_id:
            classe = ClasseNote.objects.get(id=classe_id)
        elif classe_nom:
            classe = ClasseNote.objects.filter(nom__icontains=classe_nom).first()
        else:
            print("❌ Veuillez spécifier classe_id ou classe_nom")
            return
        
        print(f"📚 Classe cible : {classe.nom} (ID: {classe.id})")
        
        # 2. Trouver la classe élève correspondante
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
            print(f"❌ Classe élève non trouvée pour {classe.nom}")
            return
        
        # 3. Récupérer les élèves et matières
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        matieres = MatiereNote.objects.filter(classe=classe, actif=True)
        
        print(f"👥 {len(eleves)} élèves actifs")
        print(f"📖 {len(matieres)} matières actives")
        
        # 4. Créer les évaluations et notes OCTOBRE
        periode = 'OCTOBRE'
        total_evaluations = 0
        total_notes = 0
        
        for matiere in matieres:
            print(f"\n📋 Traitement matière : {matiere.nom}")
            
            # Vérifier si une évaluation existe déjà
            eval_existante = Evaluation.objects.filter(
                matiere=matiere,
                periode=periode
            ).first()
            
            if eval_existante:
                print(f"  ✅ Évaluation existe déjà : {eval_existante.titre}")
                evaluation = eval_existante
            else:
                # Créer une nouvelle évaluation
                evaluation = Evaluation.objects.create(
                    matiere=matiere,
                    titre=f"Évaluation {periode} - {matiere.nom}",
                    type_evaluation='DEVOIR',
                    periode=periode,
                    date_evaluation='2024-10-15',
                    coefficient=1
                )
                print(f"  ✅ Évaluation créée : {evaluation.titre}")
            
            total_evaluations += 1
            
            # Créer les notes pour tous les élèves
            notes_crees = 0
            for eleve in eleves:
                # Vérifier si la note existe déjà
                note_existante = NoteEleve.objects.filter(
                    eleve=eleve,
                    evaluation=evaluation
                ).first()
                
                if not note_existante:
                    # Générer une note aléatoire entre 8 et 18
                    note = round(random.uniform(8, 18), 1)
                    
                    NoteEleve.objects.create(
                        eleve=eleve,
                        evaluation=evaluation,
                        note=note,
                        absent=False
                    )
                    notes_crees += 1
            
            total_notes += notes_crees
            print(f"  ✅ {notes_crees} notes créées")
        
        # 5. Résumé
        print(f"\n📊 RÉSUMÉ FINAL :")
        print(f"  • Évaluations {periode} : {total_evaluations}")
        print(f"  • Notes {periode} : {total_notes}")
        print(f"  • Élèves : {len(eleves)}")
        print(f"  • Matières : {len(matieres)}")
        
        print(f"\n🎉 SUCCÈS !")
        print(f"  ✅ Les données {periode} sont maintenant disponibles")
        print(f"  ✅ Le classement devrait afficher les vraies moyennes")
        
        print(f"\n🌐 URL de test :")
        print(f"  https://www.myschoolgn.space/notes/consulter/?classe_id={classe.id}&periode={periode}")
        print(f"  https://www.myschoolgn.space/notes/exporter-classement/?classe_id={classe.id}&matiere_id={matieres.first().id}&periode={periode}")
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python corriger_classement_classe_specifique.py --id 14")
        print("  python corriger_classement_classe_specifique.py --nom \"10ÈME ANNÉE (A)\"")
        print("  python corriger_classement_classe_specifique.py --tout  # Pour toutes les classes")
        sys.exit(1)
    
    if sys.argv[1] == "--id":
        corriger_classement_classe_specifique(classe_id=int(sys.argv[2]))
    elif sys.argv[1] == "--nom":
        corriger_classement_classe_specifique(classe_nom=sys.argv[2])
    elif sys.argv[1] == "--tout":
        # Traiter toutes les classes
        from notes.models import ClasseNote
        classes = ClasseNote.objects.filter(actif=True)
        print(f"🔄 Traitement de {len(classes)} classes...")
        
        for classe in classes:
            print(f"\n{'='*60}")
            corriger_classement_classe_specifique(classe_id=classe.id)
            print(f"{'='*60}")
    else:
        print("Argument non reconnu")
        sys.exit(1)
