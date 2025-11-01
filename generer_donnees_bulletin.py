#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour générer des données de test pour les bulletins
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve

def generer_donnees_bulletin(classe_id=None, periode='TRIMESTRE_1'):
    """Génère des évaluations et notes pour un bulletin"""
    
    print("\n" + "="*80)
    print(" "*20 + "📝 GÉNÉRATION DE DONNÉES POUR BULLETIN")
    print("="*80)
    
    # 1. Sélectionner la classe
    if classe_id:
        try:
            classe = ClasseNote.objects.get(id=classe_id, actif=True)
        except ClasseNote.DoesNotExist:
            print(f"❌ Classe ID {classe_id} introuvable")
            return
    else:
        classes = ClasseNote.objects.filter(actif=True)
        if not classes.exists():
            print("❌ Aucune classe active. Créez d'abord une classe.")
            return
        
        print("\n📚 Classes disponibles :")
        for i, c in enumerate(classes, 1):
            print(f"   {i}. {c.nom} ({c.niveau_enseignement}) - {c.annee_scolaire}")
        
        choix = input("\nChoisissez une classe (numéro) : ").strip()
        try:
            classe = classes[int(choix) - 1]
        except (ValueError, IndexError):
            print("❌ Choix invalide")
            return
    
    print(f"\n✅ Classe sélectionnée : {classe.nom}")
    
    # 2. Vérifier les matières
    matieres = MatiereNote.objects.filter(classe=classe, actif=True)
    if not matieres.exists():
        print(f"❌ Aucune matière pour la classe '{classe.nom}'")
        print("   Créez d'abord des matières pour cette classe")
        return
    
    print(f"   Matières : {matieres.count()}")
    for m in matieres:
        print(f"   - {m.nom} (Coef: {m.coefficient})")
    
    # 3. Vérifier les élèves
    try:
        classe_eleve = ClasseEleve.objects.get(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire
        )
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    except ClasseEleve.DoesNotExist:
        print(f"❌ Classe '{classe.nom}' introuvable dans le module Élèves")
        print("   Créez cette classe dans Élèves > Gestion des Classes")
        return
    
    if not eleves.exists():
        print(f"❌ Aucun élève dans la classe '{classe.nom}'")
        print("   Ajoutez des élèves à cette classe")
        return
    
    print(f"   Élèves : {eleves.count()}")
    for e in eleves[:3]:
        print(f"   - {e.prenom} {e.nom}")
    if eleves.count() > 3:
        print(f"   ... et {eleves.count() - 3} autre(s)")
    
    # 4. Générer les évaluations
    print(f"\n📋 Génération des évaluations pour {periode}...")
    
    evaluations_creees = 0
    evaluations_existantes = 0
    
    # Déterminer les dates selon la période
    if periode == 'TRIMESTRE_1':
        date_debut = datetime(2024, 10, 1)
        date_fin = datetime(2024, 12, 20)
    elif periode == 'TRIMESTRE_2':
        date_debut = datetime(2025, 1, 10)
        date_fin = datetime(2025, 3, 20)
    elif periode == 'TRIMESTRE_3':
        date_debut = datetime(2025, 4, 1)
        date_fin = datetime(2025, 6, 20)
    elif periode == 'OCTOBRE':
        date_debut = datetime(2024, 10, 1)
        date_fin = datetime(2024, 10, 31)
    elif periode == 'NOVEMBRE':
        date_debut = datetime(2024, 11, 1)
        date_fin = datetime(2024, 11, 30)
    else:
        date_debut = datetime.now() - timedelta(days=30)
        date_fin = datetime.now()
    
    for matiere in matieres:
        # Créer 2 devoirs + 1 composition par matière
        
        # Devoir 1
        date_dev1 = date_debut + timedelta(days=random.randint(5, 15))
        eval1, created = Evaluation.objects.get_or_create(
            matiere=matiere,
            nom=f"Devoir 1 - {matiere.nom}",
            type_evaluation='DEVOIR',
            periode=periode,
            date_evaluation=date_dev1,
            defaults={
                'note_sur': 20,
                'coefficient': 1,
                'description': 'Premier devoir du trimestre'
            }
        )
        if created:
            evaluations_creees += 1
        else:
            evaluations_existantes += 1
        
        # Contrôle
        date_ctrl = date_debut + timedelta(days=random.randint(20, 35))
        eval2, created = Evaluation.objects.get_or_create(
            matiere=matiere,
            nom=f"Contrôle - {matiere.nom}",
            type_evaluation='CONTROLE',
            periode=periode,
            date_evaluation=date_ctrl,
            defaults={
                'note_sur': 20,
                'coefficient': 1,
                'description': 'Contrôle de connaissances'
            }
        )
        if created:
            evaluations_creees += 1
        else:
            evaluations_existantes += 1
        
        # Composition
        date_compo = date_fin - timedelta(days=random.randint(1, 5))
        eval3, created = Evaluation.objects.get_or_create(
            matiere=matiere,
            nom=f"Composition - {matiere.nom}",
            type_evaluation='COMPOSITION',
            periode=periode,
            date_evaluation=date_compo,
            defaults={
                'note_sur': 20,
                'coefficient': 1,
                'description': 'Composition de fin de période'
            }
        )
        if created:
            evaluations_creees += 1
        else:
            evaluations_existantes += 1
    
    print(f"   ✅ {evaluations_creees} évaluation(s) créée(s)")
    print(f"   ℹ️  {evaluations_existantes} évaluation(s) existante(s)")
    
    # 5. Générer les notes pour chaque élève
    print(f"\n📊 Génération des notes pour {eleves.count()} élève(s)...")
    
    evaluations = Evaluation.objects.filter(
        matiere__classe=classe,
        periode=periode
    )
    
    notes_creees = 0
    notes_existantes = 0
    
    for eleve in eleves:
        for evaluation in evaluations:
            # Vérifier si la note existe déjà
            note_existe = NoteEleve.objects.filter(
                eleve=eleve,
                evaluation=evaluation
            ).exists()
            
            if not note_existe:
                # Générer une note aléatoire entre 8 et 18
                note_aleatoire = round(random.uniform(8.0, 18.0), 2)
                
                # 5% de chance d'être absent
                absent = random.random() < 0.05
                
                NoteEleve.objects.create(
                    eleve=eleve,
                    evaluation=evaluation,
                    note=note_aleatoire if not absent else None,
                    absent=absent,
                    commentaire='' if not absent else 'Absent'
                )
                notes_creees += 1
            else:
                notes_existantes += 1
    
    print(f"   ✅ {notes_creees} note(s) créée(s)")
    print(f"   ℹ️  {notes_existantes} note(s) existante(s)")
    
    # 6. Résumé et URL de test
    print("\n" + "="*80)
    print(" "*25 + "✅ GÉNÉRATION TERMINÉE")
    print("="*80)
    
    print(f"\n📋 Résumé :")
    print(f"   Classe : {classe.nom}")
    print(f"   Période : {periode}")
    print(f"   Matières : {matieres.count()}")
    print(f"   Élèves : {eleves.count()}")
    print(f"   Évaluations : {evaluations.count()}")
    print(f"   Notes générées : {notes_creees}")
    
    print(f"\n🔗 URL pour tester le bulletin :")
    premier_eleve = eleves.first()
    print(f"   http://127.0.0.1:8000/notes/bulletin-dynamique/?classe_id={classe.id}&eleve_id={premier_eleve.id}&periode={periode}&system_type=trimestre")
    
    print("\n💡 Prochaines étapes :")
    print("   1. Aller sur Notes > Bulletin Dynamique")
    print(f"   2. Sélectionner la classe '{classe.nom}'")
    print(f"   3. Sélectionner la période '{periode}'")
    print(f"   4. Sélectionner un élève")
    print("   5. Le bulletin devrait afficher toutes les notes")
    
    print("\n" + "="*80 + "\n")

def afficher_menu():
    """Affiche le menu interactif"""
    print("\n" + "="*80)
    print(" "*15 + "🎓 GÉNÉRATEUR DE DONNÉES POUR BULLETINS")
    print("="*80)
    
    print("\n📋 Que voulez-vous faire ?")
    print("   1. Générer des données pour TRIMESTRE 1")
    print("   2. Générer des données pour TRIMESTRE 2")
    print("   3. Générer des données pour TRIMESTRE 3")
    print("   4. Générer des données pour un MOIS (Octobre)")
    print("   5. Diagnostiquer les problèmes")
    print("   0. Quitter")
    
    choix = input("\nVotre choix : ").strip()
    
    if choix == '1':
        generer_donnees_bulletin(periode='TRIMESTRE_1')
    elif choix == '2':
        generer_donnees_bulletin(periode='TRIMESTRE_2')
    elif choix == '3':
        generer_donnees_bulletin(periode='TRIMESTRE_3')
    elif choix == '4':
        generer_donnees_bulletin(periode='OCTOBRE')
    elif choix == '5':
        os.system('python diagnostiquer_bulletin.py')
    elif choix == '0':
        print("\nAu revoir ! 👋\n")
    else:
        print("\n❌ Choix invalide")

if __name__ == '__main__':
    try:
        if '--auto' in sys.argv:
            # Mode automatique : génère pour la première classe et TRIMESTRE_1
            generer_donnees_bulletin(periode='TRIMESTRE_1')
        else:
            # Mode interactif
            afficher_menu()
    except KeyboardInterrupt:
        print("\n\n⚠️  Opération annulée par l'utilisateur\n")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
