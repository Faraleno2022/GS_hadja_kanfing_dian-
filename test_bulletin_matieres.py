#!/usr/bin/env python
"""
Test rapide pour vérifier le problème des matières sans notes sur le bulletin
pour l'élève Fatoumata Djiba (L11SC-013).
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereNote, Evaluation, NoteEleve, ClasseNote
from eleves.models import Eleve

def analyser_bulletin_eleve():
    """Analyse le problème pour l'élève spécifique"""
    
    print("\n" + "="*80)
    print("ANALYSE DU BULLETIN - Fatoumata Djiba (L11SC-013)")
    print("="*80)
    
    # Rechercher l'élève
    try:
        eleve = Eleve.objects.get(matricule='L11SC-013')
        print(f"\n✅ Élève trouvé: {eleve.prenom} {eleve.nom}")
        print(f"   Classe: {eleve.classe.nom}")
    except Eleve.DoesNotExist:
        print("❌ Élève avec matricule L11SC-013 non trouvé")
        return
    
    # Rechercher la classe dans ClasseNote
    try:
        classe_note = ClasseNote.objects.get(
            nom__icontains='11 SÉRIE SCIENTIFIQUE',
            annee_scolaire=eleve.classe.annee_scolaire
        )
        print(f"✅ Classe trouvée dans ClasseNote: {classe_note.nom}")
    except ClasseNote.DoesNotExist:
        print("❌ Classe '11 SÉRIE SCIENTIFIQUE' non trouvée dans ClasseNote")
        return
    
    # Analyser les matières et leurs notes pour Octobre
    periode = 'OCTOBRE'
    print(f"\n📅 Période analysée: {periode}")
    print("-" * 60)
    
    # Liste des matières du bulletin avec leurs statuts
    matieres_bulletin = {
        'Anglais': {'coef': 1.00, 'note': 13.00},
        'Biologie': {'coef': 1.00, 'note': None},
        'Chimie': {'coef': 1.00, 'note': 16.90},
        'Economie': {'coef': 1.00, 'note': None},
        'Français': {'coef': 2.00, 'note': None},
        'Géographie': {'coef': 1.00, 'note': 14.00},
        'Histoire': {'coef': 1.00, 'note': 9.00},
        'Mathématique': {'coef': 2.00, 'note': 14.00},
        'Philosophie': {'coef': 1.00, 'note': None},
        'Physique': {'coef': 1.00, 'note': 2.00},
    }
    
    # Analyser chaque matière
    for nom_matiere, info_bulletin in matieres_bulletin.items():
        print(f"\n📖 {nom_matiere}")
        print(f"   Coefficient: {info_bulletin['coef']}")
        print(f"   Note affichée sur bulletin: {info_bulletin['note'] if info_bulletin['note'] else '❌ MANQUANTE'}")
        
        # Rechercher la matière actuelle
        try:
            matiere = MatiereNote.objects.get(
                nom__icontains=nom_matiere.split()[0],  # Prendre le premier mot
                classe=classe_note,
                actif=True
            )
            print(f"   ✅ Matière active trouvée (ID: {matiere.id})")
            
            # Rechercher les évaluations
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode=periode
            )
            print(f"   📊 Évaluations trouvées: {evaluations.count()}")
            
            # Rechercher les notes de l'élève
            for eval in evaluations:
                try:
                    note = NoteEleve.objects.get(eleve=eleve, evaluation=eval)
                    print(f"      - {eval.titre}: {note.note}/20")
                except NoteEleve.DoesNotExist:
                    print(f"      - {eval.titre}: Pas de note")
            
            # Si pas d'évaluation, chercher avec un ID différent
            if evaluations.count() == 0:
                # Rechercher des évaluations orphelines
                from django.db.models import Q
                evaluations_autres = Evaluation.objects.filter(
                    Q(matiere__nom__icontains=nom_matiere.split()[0]) &
                    Q(matiere__classe=classe_note) &
                    Q(periode=periode) &
                    ~Q(matiere=matiere)
                )
                
                if evaluations_autres.exists():
                    print(f"   ⚠️ PROBLÈME: {evaluations_autres.count()} évaluations trouvées")
                    print(f"      avec un autre ID de matière!")
                    for eval in evaluations_autres:
                        print(f"      - {eval.titre} (Matière ID: {eval.matiere_id})")
                        try:
                            note = NoteEleve.objects.get(eleve=eleve, evaluation=eval)
                            print(f"        Note existante: {note.note}/20")
                            print(f"        ⚠️ Cette note n'apparaît pas sur le bulletin!")
                        except NoteEleve.DoesNotExist:
                            print(f"        Pas de note")
                
        except MatiereNote.DoesNotExist:
            print(f"   ❌ Matière '{nom_matiere}' non trouvée ou inactive")
        except MatiereNote.MultipleObjectsReturned:
            print(f"   ⚠️ Plusieurs matières '{nom_matiere}' trouvées!")
            matieres_multiples = MatiereNote.objects.filter(
                nom__icontains=nom_matiere.split()[0],
                classe=classe_note
            )
            for mat in matieres_multiples:
                print(f"      - ID: {mat.id}, Actif: {mat.actif}")
    
    print("\n" + "="*80)
    print("RÉSUMÉ DU DIAGNOSTIC")
    print("="*80)
    print("\n💡 Si des matières ont été supprimées puis recréées, les évaluations")
    print("   restent liées aux anciens IDs des matières supprimées.")
    print("\n📌 Solution: Exécuter le script de correction:")
    print("   python fix_matieres_bulletin.py --fix-auto")

if __name__ == '__main__':
    analyser_bulletin_eleve()
