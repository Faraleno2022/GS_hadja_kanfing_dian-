#!/usr/bin/env python
"""
Script pour diagnostiquer et corriger les problèmes de notes manquantes sur le bulletin
après suppression/recréation de matières.

Problème : Quand une matière est supprimée puis recréée avec le même nom,
elle obtient un nouvel ID. Les évaluations restent liées à l'ancien ID.
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereNote, Evaluation, NoteEleve, ClasseNote
from django.db.models import Count

def diagnostiquer_probleme(classe_id=None):
    """Diagnostique les incohérences entre matières et évaluations"""
    print("\n" + "="*80)
    print("DIAGNOSTIC DES MATIÈRES ET ÉVALUATIONS")
    print("="*80)
    
    # Filtrer par classe si spécifiée
    if classe_id:
        classes = ClasseNote.objects.filter(id=classe_id)
        if not classes.exists():
            print(f"❌ Classe avec ID {classe_id} non trouvée")
            return
    else:
        classes = ClasseNote.objects.filter(actif=True).order_by('niveau', 'nom')
    
    problemes_trouves = False
    
    for classe in classes:
        print(f"\n📚 Classe: {classe.nom} ({classe.annee_scolaire})")
        print("-" * 60)
        
        # Récupérer toutes les matières de la classe
        matieres = MatiereNote.objects.filter(classe=classe, actif=True).order_by('nom')
        
        if not matieres:
            print("   ⚠️ Aucune matière active trouvée pour cette classe")
            continue
            
        for matiere in matieres:
            evaluations = Evaluation.objects.filter(matiere=matiere)
            notes_count = NoteEleve.objects.filter(evaluation__matiere=matiere).count()
            
            print(f"\n   📖 {matiere.nom} (ID: {matiere.id})")
            print(f"      - Coefficient: {matiere.coefficient}")
            print(f"      - Évaluations: {evaluations.count()}")
            print(f"      - Notes totales: {notes_count}")
            
            # Vérifier les évaluations orphelines (avec matière supprimée)
            # Ces évaluations existent mais leur matière a été supprimée
            evaluations_orphelines = Evaluation.objects.filter(
                matiere__isnull=True,
                matiere__classe=classe
            ).count()
            
            if evaluations.count() == 0 and notes_count == 0:
                # Chercher si des évaluations existent avec un nom similaire
                # mais un ID différent (matière recréée)
                from django.db.models import Q
                evaluations_similaires = Evaluation.objects.filter(
                    Q(matiere__nom=matiere.nom) & 
                    Q(matiere__classe=classe) &
                    ~Q(matiere=matiere)
                )
                
                if evaluations_similaires.exists():
                    print(f"      ⚠️ PROBLÈME DÉTECTÉ: {evaluations_similaires.count()} évaluations trouvées")
                    print(f"         pour une matière '{matiere.nom}' avec un ID différent!")
                    print(f"         Ces évaluations sont probablement liées à une ancienne")
                    print(f"         version supprimée de cette matière.")
                    problemes_trouves = True
                    
                    # Afficher les détails
                    for eval in evaluations_similaires[:3]:  # Limiter l'affichage
                        print(f"         - Évaluation '{eval.titre}' (ID: {eval.id})")
                        print(f"           Matière ID: {eval.matiere_id}")
                        notes = NoteEleve.objects.filter(evaluation=eval).count()
                        print(f"           Notes: {notes}")
    
    if not problemes_trouves:
        print("\n✅ Aucun problème détecté")
    else:
        print("\n" + "="*80)
        print("⚠️ PROBLÈMES DÉTECTÉS - Actions recommandées:")
        print("-" * 80)
        print("1. Utilisez --fix-auto pour réassocier automatiquement les évaluations")
        print("2. Ou utilisez --fix-manuel pour choisir matière par matière")
        print("="*80)

def corriger_associations(classe_id=None, mode='manuel'):
    """Corrige les associations entre matières et évaluations"""
    print("\n" + "="*80)
    print("CORRECTION DES ASSOCIATIONS MATIÈRES-ÉVALUATIONS")
    print("="*80)
    
    if classe_id:
        classes = ClasseNote.objects.filter(id=classe_id)
    else:
        classes = ClasseNote.objects.filter(actif=True).order_by('niveau', 'nom')
    
    corrections_effectuees = 0
    
    for classe in classes:
        print(f"\n📚 Classe: {classe.nom}")
        
        # Pour chaque matière active de la classe
        matieres = MatiereNote.objects.filter(classe=classe, actif=True).order_by('nom')
        
        for matiere in matieres:
            # Chercher des évaluations avec le même nom de matière mais ID différent
            from django.db.models import Q
            evaluations_orphelines = Evaluation.objects.filter(
                Q(matiere__nom=matiere.nom) & 
                Q(matiere__classe=classe) &
                ~Q(matiere=matiere)
            )
            
            if evaluations_orphelines.exists():
                print(f"\n   📖 {matiere.nom} (ID actuel: {matiere.id})")
                print(f"      {evaluations_orphelines.count()} évaluations à réassocier")
                
                if mode == 'auto':
                    # Mode automatique : réassocier directement
                    for eval in evaluations_orphelines:
                        ancien_id = eval.matiere_id
                        eval.matiere = matiere
                        eval.save()
                        corrections_effectuees += 1
                        print(f"      ✅ Évaluation '{eval.titre}' réassociée")
                        print(f"         (ancien ID matière: {ancien_id} → nouveau: {matiere.id})")
                
                elif mode == 'manuel':
                    # Mode manuel : demander confirmation
                    print(f"      Voulez-vous réassocier ces évaluations à cette matière?")
                    for eval in evaluations_orphelines[:5]:  # Afficher max 5
                        notes_count = NoteEleve.objects.filter(evaluation=eval).count()
                        print(f"      - '{eval.titre}' ({notes_count} notes)")
                    
                    reponse = input(f"      Réassocier? (o/n) : ").lower()
                    if reponse == 'o':
                        for eval in evaluations_orphelines:
                            ancien_id = eval.matiere_id
                            eval.matiere = matiere
                            eval.save()
                            corrections_effectuees += 1
                        print(f"      ✅ {evaluations_orphelines.count()} évaluations réassociées")
    
    print("\n" + "="*80)
    print(f"✅ TERMINÉ: {corrections_effectuees} corrections effectuées")
    print("="*80)
    print("\n💡 Conseil: Relancez le diagnostic pour vérifier que tout est corrigé")

def verifier_integrite():
    """Vérifie l'intégrité globale des données"""
    print("\n" + "="*80)
    print("VÉRIFICATION D'INTÉGRITÉ")
    print("="*80)
    
    # Évaluations sans matière
    evals_sans_matiere = Evaluation.objects.filter(matiere__isnull=True)
    if evals_sans_matiere.exists():
        print(f"\n⚠️ {evals_sans_matiere.count()} évaluations sans matière trouvées!")
        for eval in evals_sans_matiere[:5]:
            print(f"   - '{eval.titre}' (ID: {eval.id})")
    
    # Notes sans évaluation valide
    notes_orphelines = NoteEleve.objects.filter(evaluation__isnull=True)
    if notes_orphelines.exists():
        print(f"\n⚠️ {notes_orphelines.count()} notes sans évaluation trouvées!")
    
    # Matières inactives avec évaluations
    matieres_inactives = MatiereNote.objects.filter(actif=False)
    for mat in matieres_inactives:
        eval_count = Evaluation.objects.filter(matiere=mat).count()
        if eval_count > 0:
            print(f"\n⚠️ Matière inactive '{mat.nom}' a encore {eval_count} évaluations")
    
    print("\n✅ Vérification terminée")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnostiquer et corriger les problèmes de bulletin")
    parser.add_argument('--classe-id', type=int, help="ID de la classe à analyser (optionnel)")
    parser.add_argument('--diagnostic', action='store_true', help="Lancer le diagnostic")
    parser.add_argument('--fix-auto', action='store_true', help="Correction automatique")
    parser.add_argument('--fix-manuel', action='store_true', help="Correction manuelle avec confirmation")
    parser.add_argument('--check', action='store_true', help="Vérifier l'intégrité des données")
    
    args = parser.parse_args()
    
    if not any([args.diagnostic, args.fix_auto, args.fix_manuel, args.check]):
        print("\n⚠️ Aucune action spécifiée. Utilisez --help pour voir les options.")
        print("\nExemples d'utilisation:")
        print("  python fix_matieres_bulletin.py --diagnostic")
        print("  python fix_matieres_bulletin.py --diagnostic --classe-id 5")
        print("  python fix_matieres_bulletin.py --fix-auto")
        print("  python fix_matieres_bulletin.py --fix-manuel")
        print("  python fix_matieres_bulletin.py --check")
        return
    
    if args.diagnostic:
        diagnostiquer_probleme(args.classe_id)
    
    if args.fix_auto:
        corriger_associations(args.classe_id, mode='auto')
    
    if args.fix_manuel:
        corriger_associations(args.classe_id, mode='manuel')
    
    if args.check:
        verifier_integrite()

if __name__ == '__main__':
    main()
