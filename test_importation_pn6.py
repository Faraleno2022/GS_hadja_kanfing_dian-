#!/usr/bin/env python
"""
Script de test pour simuler l'importation des notes PN6
"""

import os
import sys
import django
import random

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve
from notes.models import ClasseNote, Evaluation, NoteEleve
from decimal import Decimal

def test_importation_notes():
    """Teste l'importation des notes pour la classe PN6"""
    
    print("🧪 TEST D'IMPORTATION - CLASSE PN6")
    print("=" * 50)
    
    # 1. Récupérer la classe PN6
    classe_note = ClasseNote.objects.filter(nom="PN6").first()
    if not classe_note:
        print("❌ Classe PN6 non trouvée")
        return
    
    print(f"✅ Classe: {classe_note.nom} (ID: {classe_note.id})")
    
    # 2. Récupérer les élèves PN6
    eleves_pn6 = Eleve.objects.filter(matricule__startswith="PN6")
    print(f"✅ Élèves PN6: {eleves_pn6.count()}")
    
    # 3. Récupérer les évaluations OCTOBRE
    evaluations_octobre = Evaluation.objects.filter(
        matiere__classe=classe_note,
        periode='OCTOBRE'
    )
    print(f"✅ Évaluations OCTOBRE: {evaluations_octobre.count()}")
    
    # 4. Simuler l'importation de notes
    print(f"\n📝 SIMULATION D'IMPORTATION")
    print("-" * 30)
    
    notes_creees = 0
    notes_mises_a_jour = 0
    absents = 0
    erreurs = 0
    
    for eleve in eleves_pn6:
        print(f"📚 {eleve.matricule}: {eleve.prenom} {eleve.nom}")
        
        for evaluation in evaluations_octobre:
            try:
                # Vérifier si la note existe déjà
                note_existante = NoteEleve.objects.filter(
                    eleve=eleve,
                    evaluation=evaluation
                ).first()
                
                # Générer une note aléatoire (simulation)
                if random.random() < 0.05:  # 5% d'absents
                    note_valeur = None
                    absent = True
                    absents += 1
                else:
                    note_valeur = Decimal(str(round(random.uniform(8.0, 18.0), 2)))
                    absent = False
                
                if note_existante:
                    # Mettre à jour
                    note_existante.note = note_valeur
                    note_existante.absent = absent
                    note_existante.save()
                    notes_mises_a_jour += 1
                    action = "MAJ"
                else:
                    # Créer
                    NoteEleve.objects.create(
                        eleve=eleve,
                        evaluation=evaluation,
                        note=note_valeur,
                        absent=absent
                    )
                    notes_creees += 1
                    action = "NEW"
                
                status = "ABS" if absent else f"{note_valeur}"
                print(f"  ✅ {evaluation.matiere.nom}: {status} ({action})")
                
            except Exception as e:
                print(f"  ❌ {evaluation.matiere.nom}: Erreur - {e}")
                erreurs += 1
    
    # 5. Résumé de l'importation
    print(f"\n📊 RÉSUMÉ DE L'IMPORTATION")
    print("=" * 40)
    print(f"✅ Notes créées: {notes_creees}")
    print(f"🔄 Notes mises à jour: {notes_mises_a_jour}")
    print(f"⚠️  Absents: {absents}")
    print(f"❌ Erreurs: {erreurs}")
    
    total_notes = notes_creees + notes_mises_a_jour
    print(f"📈 Total notes traitées: {total_notes}")
    
    # 6. Test de consultation
    print(f"\n🔍 TEST DE CONSULTATION")
    print("-" * 25)
    
    # Prendre quelques élèves pour tester le calcul des moyennes
    eleves_test = eleves_pn6[:5]
    
    for eleve in eleves_test:
        notes_eleve = NoteEleve.objects.filter(
            eleve=eleve,
            evaluation__periode='OCTOBRE'
        )
        
        # Calculer la moyenne
        total_pondere = Decimal('0')
        total_coef = Decimal('0')
        nb_notes = 0
        nb_absents = 0
        
        for note in notes_eleve:
            coef = Decimal(str(note.evaluation.coefficient or 1))
            if note.absent or note.note is None:
                # Absence = 0
                total_pondere += Decimal('0') * coef
                nb_absents += 1
            else:
                total_pondere += note.note * coef
                nb_notes += 1
            total_coef += coef
        
        if total_coef > 0:
            moyenne = total_pondere / total_coef
            print(f"📊 {eleve.matricule}: Moyenne = {moyenne:.2f}/20 ({nb_notes} notes, {nb_absents} absents)")
        else:
            print(f"📊 {eleve.matricule}: Aucune note")
    
    # 7. Instructions pour la consultation web
    print(f"\n🌐 CONSULTATION WEB")
    print("=" * 25)
    print("Pour voir les résultats dans l'interface web :")
    print(f"1. Allez sur: /notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")
    print("2. Vous devriez voir toutes les moyennes et rangs")
    print("3. Les tirets (-) ont disparu !")
    
    # 8. Vérification des données
    print(f"\n✅ VÉRIFICATION FINALE")
    print("-" * 25)
    
    total_notes_db = NoteEleve.objects.filter(
        evaluation__matiere__classe=classe_note,
        evaluation__periode='OCTOBRE'
    ).count()
    
    eleves_avec_notes = NoteEleve.objects.filter(
        evaluation__matiere__classe=classe_note,
        evaluation__periode='OCTOBRE'
    ).values('eleve').distinct().count()
    
    print(f"📈 Total notes en base: {total_notes_db}")
    print(f"👥 Élèves avec notes: {eleves_avec_notes}/{eleves_pn6.count()}")
    print(f"📚 Matières par élève: {evaluations_octobre.count()}")
    
    if total_notes_db > 0:
        print(f"\n🎉 SUCCÈS ! L'importation a fonctionné.")
        print(f"🔗 Lien direct: /notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")
    else:
        print(f"\n❌ ÉCHEC ! Aucune note n'a été créée.")

if __name__ == "__main__":
    try:
        test_importation_notes()
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
