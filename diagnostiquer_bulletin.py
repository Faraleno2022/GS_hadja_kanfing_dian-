#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnostic pour identifier pourquoi les notes ne s'affichent pas sur le bulletin
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

def diagnostiquer_bulletin():
    print("\n" + "="*80)
    print(" "*20 + "🔍 DIAGNOSTIC DU BULLETIN - NOTES MANQUANTES")
    print("="*80)
    
    # 1. Vérifier les classes
    print("\n1️⃣  VÉRIFICATION DES CLASSES")
    print("-" * 80)
    
    classes_note = ClasseNote.objects.filter(actif=True)
    print(f"   Classes (Notes) actives : {classes_note.count()}")
    
    if classes_note.exists():
        for classe in classes_note[:5]:
            print(f"   - {classe.nom} ({classe.niveau_enseignement}) - {classe.annee_scolaire}")
    else:
        print("   ❌ AUCUNE CLASSE TROUVÉE dans ClasseNote")
        print("   → Créez d'abord des classes dans Notes > Gestion des Classes")
        return
    
    # 2. Vérifier les matières
    print("\n2️⃣  VÉRIFICATION DES MATIÈRES")
    print("-" * 80)
    
    premiere_classe = classes_note.first()
    matieres = MatiereNote.objects.filter(classe=premiere_classe, actif=True)
    
    print(f"   Matières pour '{premiere_classe.nom}' : {matieres.count()}")
    
    if matieres.exists():
        for matiere in matieres:
            print(f"   - {matiere.nom} (Coef: {matiere.coefficient})")
    else:
        print(f"   ❌ AUCUNE MATIÈRE TROUVÉE pour la classe '{premiere_classe.nom}'")
        print("   → Ajoutez des matières à cette classe")
        return
    
    # 3. Vérifier les élèves
    print("\n3️⃣  VÉRIFICATION DES ÉLÈVES")
    print("-" * 80)
    
    try:
        classe_eleve = ClasseEleve.objects.get(
            nom=premiere_classe.nom,
            annee_scolaire=premiere_classe.annee_scolaire
        )
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"   Élèves actifs dans '{premiere_classe.nom}' : {eleves.count()}")
        
        if eleves.exists():
            for eleve in eleves[:3]:
                print(f"   - {eleve.prenom} {eleve.nom} (Matricule: {eleve.matricule})")
        else:
            print(f"   ❌ AUCUN ÉLÈVE ACTIF dans la classe '{premiere_classe.nom}'")
            print("   → Ajoutez des élèves à cette classe")
            return
            
    except ClasseEleve.DoesNotExist:
        print(f"   ❌ Classe '{premiere_classe.nom}' introuvable dans le module Élèves")
        print(f"   → Créez une classe '{premiere_classe.nom}' dans Élèves > Gestion des Classes")
        print(f"   → Année scolaire : {premiere_classe.annee_scolaire}")
        return
    
    # 4. Vérifier les évaluations
    print("\n4️⃣  VÉRIFICATION DES ÉVALUATIONS")
    print("-" * 80)
    
    periodes_a_verifier = ['TRIMESTRE_1', 'TRIMESTRE_2', 'TRIMESTRE_3', 'OCTOBRE', 'NOVEMBRE']
    
    evaluations_totales = Evaluation.objects.filter(matiere__classe=premiere_classe)
    print(f"   Évaluations totales pour '{premiere_classe.nom}' : {evaluations_totales.count()}")
    
    if evaluations_totales.exists():
        print("\n   Détail par période :")
        for periode in periodes_a_verifier:
            evals_periode = evaluations_totales.filter(periode=periode)
            if evals_periode.exists():
                print(f"   ✅ {periode} : {evals_periode.count()} évaluation(s)")
                # Afficher les types
                for eval in evals_periode[:2]:
                    print(f"      - {eval.matiere.nom} : {eval.type_evaluation} ({eval.date_evaluation})")
            else:
                print(f"   ⚠️  {periode} : 0 évaluation")
    else:
        print("   ❌ AUCUNE ÉVALUATION TROUVÉE")
        print(f"   → Créez des évaluations pour la classe '{premiere_classe.nom}'")
        print("   → Menu : Notes > Gestion des Évaluations")
        return
    
    # 5. Vérifier les notes des élèves
    print("\n5️⃣  VÉRIFICATION DES NOTES DES ÉLÈVES")
    print("-" * 80)
    
    if eleves.exists() and evaluations_totales.exists():
        premier_eleve = eleves.first()
        notes_eleve = NoteEleve.objects.filter(
            eleve=premier_eleve,
            evaluation__in=evaluations_totales
        )
        
        print(f"   Notes pour '{premier_eleve.prenom} {premier_eleve.nom}' :")
        print(f"   Total : {notes_eleve.count()} note(s)")
        
        if notes_eleve.exists():
            for note in notes_eleve[:5]:
                absent = "ABSENT" if note.absent else f"{note.note}/20"
                print(f"   - {note.evaluation.matiere.nom} ({note.evaluation.type_evaluation}) : {absent}")
        else:
            print(f"   ❌ AUCUNE NOTE TROUVÉE pour cet élève")
            print("   → Saisissez les notes pour cet élève")
            print("   → Menu : Notes > Saisie des Notes")
    
    # 6. Diagnostic final et recommandations
    print("\n" + "="*80)
    print(" "*25 + "📋 DIAGNOSTIC FINAL")
    print("="*80)
    
    problemes = []
    solutions = []
    
    if not classes_note.exists():
        problemes.append("❌ Aucune classe active")
        solutions.append("→ Créer des classes dans Notes > Gestion des Classes")
    
    if classes_note.exists() and not matieres.exists():
        problemes.append("❌ Aucune matière dans la classe")
        solutions.append(f"→ Ajouter des matières à '{premiere_classe.nom}'")
    
    try:
        if not eleves.exists():
            problemes.append("❌ Aucun élève dans la classe")
            solutions.append(f"→ Ajouter des élèves à la classe '{premiere_classe.nom}'")
    except:
        problemes.append("❌ Classe inexistante dans le module Élèves")
        solutions.append(f"→ Créer la classe '{premiere_classe.nom}' dans Élèves")
    
    if classes_note.exists() and matieres.exists() and not evaluations_totales.exists():
        problemes.append("❌ Aucune évaluation créée")
        solutions.append("→ Créer des évaluations dans Notes > Gestion des Évaluations")
    
    if evaluations_totales.exists() and eleves.exists() and not notes_eleve.exists():
        problemes.append("❌ Aucune note saisie pour les élèves")
        solutions.append("→ Saisir les notes dans Notes > Saisie des Notes")
    
    if problemes:
        print("\n🔴 PROBLÈMES IDENTIFIÉS :")
        for p in problemes:
            print(f"   {p}")
        
        print("\n💡 SOLUTIONS RECOMMANDÉES :")
        for s in solutions:
            print(f"   {s}")
        
        print("\n📝 ORDRE DES ÉTAPES À SUIVRE :")
        print("   1. Créer une classe dans Notes > Gestion des Classes")
        print("   2. Ajouter des matières à cette classe")
        print("   3. Créer la même classe dans Élèves > Gestion des Classes")
        print("   4. Ajouter des élèves à cette classe")
        print("   5. Créer des évaluations pour chaque matière")
        print("   6. Saisir les notes pour chaque élève")
        print("   7. Générer le bulletin")
    else:
        print("\n✅ SYSTÈME OPÉRATIONNEL")
        print("   Toutes les données nécessaires sont présentes.")
        print("   Si le bulletin reste vide, vérifiez :")
        print("   - La période sélectionnée correspond aux évaluations")
        print("   - L'élève sélectionné a bien des notes")
        print("   - Les évaluations ont le bon type (DEVOIR, COMPOSITION, etc.)")
    
    # 7. Script de génération rapide
    print("\n" + "="*80)
    print(" "*25 + "🚀 GÉNÉRATION RAPIDE DE DONNÉES")
    print("="*80)
    
    print("\nPour générer rapidement des données de test, utilisez :")
    print("   python gerer_notes_mensuelles.py --auto")
    print("\nOu pour un bulletin trimestriel :")
    print("   python generer_donnees_bulletin.py")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    try:
        diagnostiquer_bulletin()
    except Exception as e:
        print(f"\n❌ Erreur lors du diagnostic : {e}")
        import traceback
        traceback.print_exc()
