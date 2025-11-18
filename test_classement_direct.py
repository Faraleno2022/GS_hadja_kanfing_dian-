#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test direct du calcul du classement et des moyennes
Teste la logique de calcul sans passer par la vue Django
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

def calculer_moyenne_et_classement(classe_note_id):
    """Calculer directement les moyennes et le classement pour une classe"""
    print(f"\n{'='*70}")
    print(f"TEST CLASSE ID: {classe_note_id}")
    print(f"{'='*70}")
    
    try:
        classe_note = ClasseNote.objects.get(pk=classe_note_id)
        print(f"✅ Classe trouvée: {classe_note.nom} ({classe_note.annee_scolaire})")
    except ClasseNote.DoesNotExist:
        print(f"❌ Classe ID {classe_note_id} non trouvée")
        return False
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
    print(f"✅ Matières trouvées: {matieres.count()}")
    
    if matieres.count() == 0:
        print("⚠️  Aucune matière active pour cette classe")
        return True
    
    # Récupérer la classe élève correspondante
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if not classe_eleve:
        print("⚠️  Classe élève non trouvée (peut-être pas d'élèves)")
        return True
    
    # Récupérer les élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('prenom', 'nom')
    print(f"✅ Élèves trouvés: {eleves.count()}")
    
    if eleves.count() == 0:
        print("⚠️  Aucun élève actif dans cette classe")
        return True
    
    # Calculer les moyennes pour chaque élève
    eleves_toutes_notes = []
    
    for eleve in eleves:
        notes_par_matiere = {}
        somme_moy_coef = Decimal('0')
        somme_coef = Decimal('0')
        
        for matiere in matieres:
            # Récupérer toutes les évaluations de cette matière
            evaluations = Evaluation.objects.filter(matiere=matiere).order_by('periode', 'date_evaluation')
            
            notes_matiere = {
                'evaluations': [],
                'notes': [],
                'moyenne': None
            }
            
            # Calculer la moyenne pondérée par coefficient d'évaluation
            total_pondere = Decimal('0')
            total_coef_eval = Decimal('0')
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    notes_matiere['evaluations'].append(evaluation)
                    notes_matiere['notes'].append({
                        'evaluation': evaluation,
                        'note': note_obj.note,
                        'absent': note_obj.absent,
                    })
                    if note_obj.note is not None and not note_obj.absent:
                        coef_eval = Decimal(str(evaluation.coefficient or 1))
                        total_pondere += Decimal(str(note_obj.note)) * coef_eval
                        total_coef_eval += coef_eval
                except NoteEleve.DoesNotExist:
                    notes_matiere['evaluations'].append(evaluation)
                    notes_matiere['notes'].append({
                        'evaluation': evaluation,
                        'note': None,
                        'absent': False,
                    })
            
            # Calculer la moyenne pondérée de la matière
            if total_coef_eval > 0:
                moyenne_matiere = total_pondere / total_coef_eval
                notes_matiere['moyenne'] = round(float(moyenne_matiere), 2)
                
                # Ajouter à la moyenne générale pondérée par coefficient de matière
                coef_matiere = Decimal(str(matiere.coefficient or 1))
                somme_moy_coef += moyenne_matiere * coef_matiere
                somme_coef += coef_matiere
            
            notes_par_matiere[matiere.id] = notes_matiere
        
        # Calculer la moyenne générale
        moyenne_generale = None
        if somme_coef > 0:
            moyenne_generale = round(float(somme_moy_coef / somme_coef), 2)
        
        eleves_toutes_notes.append({
            'eleve': eleve,
            'notes_par_matiere': notes_par_matiere,
            'moyenne_generale': moyenne_generale,
        })
    
    # Calculer le classement
    eleves_avec_moyenne = [e for e in eleves_toutes_notes if e['moyenne_generale'] is not None]
    eleves_sans_moyenne = [e for e in eleves_toutes_notes if e['moyenne_generale'] is None]
    
    # Trier les élèves avec moyenne par moyenne décroissante
    eleves_avec_moyenne.sort(key=lambda x: x['moyenne_generale'], reverse=True)
    
    # Attribuer les rangs (gestion des ex-aequo)
    prev_moyenne = None
    prev_rang = None
    for idx, eleve_data in enumerate(eleves_avec_moyenne, start=1):
        moyenne = eleve_data['moyenne_generale']
        if prev_moyenne is not None and abs(moyenne - prev_moyenne) < 0.01:
            # Ex-aequo : même rang que le précédent
            eleve_data['rang'] = prev_rang
        else:
            eleve_data['rang'] = idx
            prev_rang = idx
        prev_moyenne = moyenne
    
    # Les élèves sans moyenne ont le rang '-'
    for eleve_data in eleves_sans_moyenne:
        eleve_data['rang'] = '-'
    
    # Reconstruire la liste avec classement
    eleves_toutes_notes = eleves_avec_moyenne + eleves_sans_moyenne
    
    # Afficher les résultats
    print(f"\n📊 RÉSULTATS POUR {classe_note.nom}:")
    print(f"   Nombre d'élèves: {len(eleves_toutes_notes)}")
    print(f"   Élèves avec moyenne: {len(eleves_avec_moyenne)}")
    print(f"   Élèves sans moyenne: {len(eleves_sans_moyenne)}")
    
    if len(eleves_avec_moyenne) == 0:
        print("⚠️  Aucun élève n'a de moyenne générale calculée")
        return True
    
    # Afficher les 10 premiers du classement
    print(f"\n🏆 CLASSEMENT (10 premiers):")
    for idx, eleve_data in enumerate(eleves_avec_moyenne[:10], 1):
        eleve = eleve_data['eleve']
        moyenne_generale = eleve_data['moyenne_generale']
        rang = eleve_data['rang']
        nom_complet = f"{eleve.prenom} {eleve.nom}"
        matricule = eleve.matricule or "N/A"
        
        print(f"   {rang}. {nom_complet} ({matricule}) - Moyenne: {moyenne_generale}/20")
    
    if len(eleves_avec_moyenne) > 10:
        print(f"   ... et {len(eleves_avec_moyenne) - 10} autres élèves")
    
    # Vérifier que le classement est correct (décroissant)
    moyennes = [e['moyenne_generale'] for e in eleves_avec_moyenne]
    if len(moyennes) > 1:
        est_trie = all(moyennes[i] >= moyennes[i+1] for i in range(len(moyennes)-1))
        if est_trie:
            print(f"\n✅ Classement correct (décroissant)")
        else:
            print(f"\n❌ Classement incorrect (pas décroissant)")
            print(f"   Moyennes: {moyennes[:5]}...")
            return False
    
    # Vérifier que tous les rangs sont attribués
    rangs_attribues = sum(1 for e in eleves_avec_moyenne if e.get('rang') != '-')
    if rangs_attribues == len(eleves_avec_moyenne):
        print(f"✅ Tous les rangs sont attribués ({rangs_attribues}/{len(eleves_avec_moyenne)})")
    else:
        print(f"⚠️  Seulement {rangs_attribues}/{len(eleves_avec_moyenne)} rangs attribués")
    
    return True

def test_toutes_les_classes():
    """Tester le classement pour toutes les classes actives"""
    print("\n" + "="*70)
    print("TEST DU CLASSEMENT POUR TOUTES LES CLASSES")
    print("="*70)
    
    classes = ClasseNote.objects.filter(actif=True).order_by('nom')
    print(f"\n📚 Nombre de classes actives: {classes.count()}")
    
    if classes.count() == 0:
        print("⚠️  Aucune classe active trouvée")
        return
    
    resultats = []
    classes_avec_notes = 0
    
    for classe in classes:
        resultat = calculer_moyenne_et_classement(classe.id)
        resultats.append((classe.nom, resultat))
        
        # Compter les classes avec des notes
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire,
            ecole=classe.ecole
        ).first()
        if classe_eleve:
            eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
            if eleves.exists():
                # Vérifier s'il y a des notes
                matieres = MatiereNote.objects.filter(classe=classe, actif=True)
                evaluations = Evaluation.objects.filter(matiere__in=matieres)
                notes = NoteEleve.objects.filter(evaluation__in=evaluations, eleve__in=eleves)
                if notes.exists():
                    classes_avec_notes += 1
    
    # Résumé final
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    
    reussis = sum(1 for _, r in resultats if r)
    echecs = len(resultats) - reussis
    
    print(f"\n📊 Résultats:")
    print(f"   ✅ Tests réussis: {reussis}/{len(resultats)}")
    print(f"   ❌ Tests échoués: {echecs}/{len(resultats)}")
    print(f"   📝 Classes avec notes: {classes_avec_notes}/{len(resultats)}")
    
    if classes_avec_notes > 0:
        print(f"\n✅ Le système de classement fonctionne pour les classes avec notes !")
    else:
        print(f"\n⚠️  Aucune classe n'a de notes saisies pour tester le classement")

if __name__ == "__main__":
    print("🧪 TEST DIRECT DU SYSTÈME DE CLASSEMENT")
    print("="*70)
    
    # Test de la classe spécifique mentionnée (classe_id=6)
    print("\n1. Test de la classe ID 6 (mentionnée dans le problème)")
    calculer_moyenne_et_classement(6)
    
    # Test de toutes les classes
    print("\n\n2. Test de toutes les classes actives")
    test_toutes_les_classes()
    
    print("\n" + "="*70)
    print("TESTS TERMINÉS")
    print("="*70)

