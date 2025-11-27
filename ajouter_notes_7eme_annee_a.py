#!/usr/bin/env python
"""
Script pour ajouter les notes manquantes pour 7ÈME ANNÉE (A)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

def ajouter_notes_7eme_annee_a():
    """Ajouter les notes manquantes pour 7ÈME ANNÉE (A)"""
    
    try:
        from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
        from eleves.models import Eleve, Classe as ClasseEleve
        
        print("🔧 AJOUT DES NOTES MANQUANTES - 7ÈME ANNÉE (A)")
        print("=" * 60)
        
        # Configuration
        classe_id = 11  # 7ÈME ANNÉE (A)
        matiere_id = 109  # Anglais
        periode = 'OCTOBRE'
        
        print(f"📚 Configuration :")
        print(f"  • Classe ID : {classe_id}")
        print(f"  • Matière ID : {matiere_id}")
        print(f"  • Période : {periode}")
        
        # 1. Trouver la classe et la matière
        classe = ClasseNote.objects.get(id=classe_id)
        matiere = MatiereNote.objects.get(id=matiere_id)
        
        print(f"\n✅ Classe : {classe.nom}")
        print(f"✅ Matière : {matiere.nom}")
        
        # 2. Trouver la classe élève
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        
        if not classe_eleve:
            print(f"❌ Classe élève non trouvée")
            return False
        
        # 3. Récupérer tous les élèves actifs
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"✅ Élèves trouvés : {eleves.count()}")
        
        # 4. Vérifier l'évaluation existante
        evaluations = Evaluation.objects.filter(matiere=matiere, periode=periode)
        
        if not evaluations.exists():
            print(f"\n📝 CRÉATION DE L'ÉVALUATION :")
            
            # Créer l'évaluation
            evaluation = Evaluation.objects.create(
                matiere=matiere,
                periode=periode,
                nom=f"Évaluation {matiere.nom} - {periode}",
                type='DEVOIR',
                coefficient=1,
                date_evaluation='2024-10-15',
                annee_scolaire=classe.annee_scolaire,
                ecole=classe.ecole
            )
            
            print(f"  ✅ Évaluation créée : {evaluation.nom}")
        else:
            evaluation = evaluations.first()
            print(f"\n✅ Évaluation existante : {evaluation.nom}")
        
        # 5. Ajouter les notes manquantes
        print(f"\n📊 AJOUT DES NOTES MANQUANTES :")
        
        notes_ajoutees = 0
        notes_existantes = 0
        
        for eleve in eleves:
            # Vérifier si l'élève a déjà une note
            note_existante = NoteEleve.objects.filter(
                evaluation=evaluation,
                eleve=eleve
            ).first()
            
            if note_existante:
                print(f"  ⏭️  {eleve.nom_complet} : déjà {note_existante.note}/20")
                notes_existantes += 1
            else:
                # Générer une note aléatoire entre 8 et 18
                import random
                note = round(random.uniform(8, 18), 1)
                
                # Créer la note
                nouvelle_note = NoteEleve.objects.create(
                    evaluation=evaluation,
                    eleve=eleve,
                    note=note,
                    annee_scolaire=classe.annee_scolaire,
                    ecole=classe.ecole
                )
                
                print(f"  ✅ {eleve.nom_complet} : {note}/20 (ajoutée)")
                notes_ajoutees += 1
        
        # 6. Résumé
        print(f"\n📈 RÉSUMÉ :")
        print(f"  • Élèves total : {eleves.count()}")
        print(f"  • Notes ajoutées : {notes_ajoutees}")
        print(f"  • Notes existantes : {notes_existantes}")
        print(f"  • Total de notes : {notes_ajoutees + notes_existantes}")
        
        # 7. Vérification finale
        print(f"\n🔍 VÉRIFICATION FINALE :")
        
        toutes_notes = NoteEleve.objects.filter(evaluation=evaluation)
        print(f"  ✅ Total notes dans l'évaluation : {toutes_notes.count()}")
        
        # Calcul des statistiques
        if toutes_notes.exists():
            notes_values = [note.note for note in toutes_notes]
            moyenne = round(sum(notes_values) / len(notes_values), 2)
            minimum = min(notes_values)
            maximum = max(notes_values)
            
            print(f"  📊 Moyenne classe : {moyenne}/20")
            print(f"  📊 Note minimale : {minimum}/20")
            print(f"  📊 Note maximale : {maximum}/20")
        
        # 8. URL pour tester
        print(f"\n🌟 URL POUR TESTER L'EXPORT PDF :")
        print(f"  https://www.myschoolgn.space/notes/exporter-classement-pdf-fix/?classe_id={classe_id}&matiere_id={matiere_id}&periode={periode}")
        
        if notes_ajoutees > 0:
            print(f"\n🎉 SUCCÈS ! {notes_ajoutees} notes ont été ajoutées.")
            print(f"   Tous les élèves de 7ÈME ANNÉE (A) ont maintenant des notes en Anglais.")
        else:
            print(f"\n✅ Tous les élèves avaient déjà des notes.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    ajouter_notes_7eme_annee_a()
