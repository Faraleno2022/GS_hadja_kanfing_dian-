#!/usr/bin/env python
"""
Diagnostic détaillé pour identifier pourquoi certaines matières
n'affichent pas de notes sur le bulletin.
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereNote, Evaluation, NoteEleve, ClasseNote
from eleves.models import Eleve, Classe as ClasseEleve
from django.db.models import Q

def diagnostic_detaille():
    """Analyse détaillée du problème des notes manquantes"""
    
    print("\n" + "="*80)
    print("DIAGNOSTIC DÉTAILLÉ - NOTES MANQUANTES SUR LE BULLETIN")
    print("="*80)
    
    # Rechercher la classe 11 SÉRIE SCIENTIFIQUE
    print("\n1. RECHERCHE DE LA CLASSE")
    print("-" * 40)
    
    # Dans ClasseNote (utilisé pour le bulletin)
    try:
        classes_notes = ClasseNote.objects.filter(
            Q(nom__icontains='11') & Q(nom__icontains='SCIENT')
        )
        print(f"Classes trouvées dans ClasseNote: {classes_notes.count()}")
        for cn in classes_notes:
            print(f"  - {cn.nom} (ID: {cn.id}) - Année: {cn.annee_scolaire}")
            classe_note = cn
            break
    except:
        print("❌ Aucune classe trouvée dans ClasseNote")
        return
    
    # Dans ClasseEleve (utilisé pour les élèves)
    try:
        classes_eleves = ClasseEleve.objects.filter(
            Q(nom__icontains='11') & Q(nom__icontains='SCIENT')
        )
        print(f"Classes trouvées dans ClasseEleve: {classes_eleves.count()}")
        for ce in classes_eleves:
            print(f"  - {ce.nom} (ID: {ce.id}) - Année: {ce.annee_scolaire}")
            classe_eleve = ce
            break
    except:
        print("❌ Aucune classe trouvée dans ClasseEleve")
    
    # Analyser les matières
    print("\n2. ANALYSE DES MATIÈRES ET NOTES")
    print("-" * 40)
    
    # Liste des matières du bulletin avec leur statut
    matieres_bulletin = [
        ('Anglais', True, 13.00),
        ('Biologie', False, None),
        ('Chimie', True, 16.90),
        ('Economie', False, None),
        ('Français', False, None),
        ('Géographie', True, 14.00),
        ('Histoire', True, 9.00),
        ('Mathématique', True, 14.00),
        ('Philosophie', False, None),
        ('Physique', True, 2.00),
    ]
    
    periode = 'OCTOBRE'
    
    for nom_matiere, a_note, note_affichee in matieres_bulletin:
        print(f"\n📖 {nom_matiere}")
        print(f"   Statut bulletin: {'✅ Note affichée' if a_note else '❌ Pas de note'}")
        if a_note:
            print(f"   Note: {note_affichee}")
        
        # Rechercher la matière dans MatiereNote
        try:
            # Recherche flexible par nom
            matieres = MatiereNote.objects.filter(
                Q(nom__icontains=nom_matiere.lower()) | 
                Q(nom__icontains=nom_matiere.upper()) |
                Q(nom__iexact=nom_matiere),
                classe=classe_note
            )
            
            if matieres.exists():
                for mat in matieres:
                    print(f"   ✓ Matière trouvée: {mat.nom} (ID: {mat.id}, Actif: {mat.actif})")
                    
                    # Chercher les évaluations pour cette matière et période
                    evaluations = Evaluation.objects.filter(
                        matiere=mat,
                        periode=periode
                    )
                    print(f"   📊 Évaluations (période {periode}): {evaluations.count()}")
                    
                    if evaluations.exists():
                        # Vérifier s'il y a des notes
                        notes_count = NoteEleve.objects.filter(
                            evaluation__in=evaluations
                        ).count()
                        print(f"   📝 Notes totales: {notes_count}")
                        
                        # Rechercher un élève spécifique pour tester
                        try:
                            # Chercher un élève de cette classe
                            eleve_test = Eleve.objects.filter(classe=classe_eleve).first()
                            if eleve_test:
                                notes_eleve = NoteEleve.objects.filter(
                                    eleve=eleve_test,
                                    evaluation__in=evaluations
                                )
                                if notes_eleve.exists():
                                    for ne in notes_eleve:
                                        print(f"      Élève {eleve_test.prenom}: {ne.note}/20")
                        except:
                            pass
                    else:
                        # Chercher des évaluations dans d'autres périodes
                        all_evals = Evaluation.objects.filter(matiere=mat)
                        if all_evals.exists():
                            periodes = set(all_evals.values_list('periode', flat=True))
                            print(f"   ⚠️ Pas d'évaluation pour {periode}")
                            print(f"      Mais évaluations trouvées pour: {', '.join(periodes)}")
            else:
                print(f"   ❌ Matière '{nom_matiere}' non trouvée dans MatiereNote")
                
                # Chercher si la matière existe avec un nom légèrement différent
                matieres_similaires = MatiereNote.objects.filter(
                    classe=classe_note
                )
                for mat in matieres_similaires:
                    if nom_matiere.lower()[:4] in mat.nom.lower():
                        print(f"   💡 Matière similaire trouvée: {mat.nom} (ID: {mat.id})")
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    # Vérifier la cohérence entre modèles
    print("\n3. VÉRIFICATION DE COHÉRENCE")
    print("-" * 40)
    
    # Compter toutes les évaluations pour la classe et période
    all_evals = Evaluation.objects.filter(
        matiere__classe=classe_note,
        periode=periode
    )
    print(f"Total évaluations pour {classe_note.nom} en {periode}: {all_evals.count()}")
    
    # Lister les matières qui ont des évaluations
    matieres_avec_eval = set()
    for eval in all_evals:
        matieres_avec_eval.add(eval.matiere.nom)
    
    print(f"Matières avec évaluations: {', '.join(sorted(matieres_avec_eval))}")
    
    # Vérifier s'il y a des évaluations orphelines
    print("\n4. RECHERCHE D'ÉVALUATIONS ORPHELINES")
    print("-" * 40)
    
    # Rechercher toutes les évaluations pour octobre peu importe la classe
    evals_octobre = Evaluation.objects.filter(periode='OCTOBRE')
    print(f"Total évaluations en OCTOBRE (toutes classes): {evals_octobre.count()}")
    
    # Grouper par matière
    matieres_octobre = {}
    for eval in evals_octobre:
        if eval.matiere:
            nom = eval.matiere.nom
            if nom not in matieres_octobre:
                matieres_octobre[nom] = []
            matieres_octobre[nom].append(eval.matiere.classe.nom if eval.matiere.classe else "Sans classe")
    
    for nom, classes in matieres_octobre.items():
        if any(nom_recherche.lower() in nom.lower() for nom_recherche, _, _ in matieres_bulletin):
            print(f"  - {nom}: {', '.join(set(classes))}")

if __name__ == '__main__':
    diagnostic_detaille()
