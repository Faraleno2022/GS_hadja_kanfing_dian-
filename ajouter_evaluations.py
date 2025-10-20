#!/usr/bin/env python
"""
Script pour ajouter des évaluations variées au module notes
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta
import random

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import MatiereClasse, Evaluation, Note
from eleves.models import Classe, Eleve
from django.contrib.auth.models import User


def main():
    print("📝 Ajout d'évaluations variées...")
    
    # Récupération des matières existantes
    matieres = MatiereClasse.objects.filter(actif=True)
    
    if not matieres:
        print("❌ Aucune matière trouvée. Veuillez d'abord créer des matières.")
        return
    
    print(f"📖 {matieres.count()} matières trouvées")
    
    # Types d'évaluations variées
    evaluations_types = [
        # Premier trimestre
        ("Devoir de rentrée", "COURS", 1, "T1", -150),
        ("Interrogation n°1", "COURS", 1, "T1", -140),
        ("Devoir surveillé n°1", "COURS", 2, "T1", -130),
        ("Test de connaissances", "COURS", 1, "T1", -120),
        ("Devoir maison n°1", "COURS", 1, "T1", -110),
        ("Interrogation n°2", "COURS", 1, "T1", -100),
        ("Devoir surveillé n°2", "COURS", 2, "T1", -90),
        ("Composition 1er trimestre", "COMPOSITION", 3, "T1", -80),
        
        # Deuxième trimestre
        ("Devoir de reprise", "COURS", 1, "T2", -70),
        ("Interrogation n°3", "COURS", 1, "T2", -60),
        ("Devoir surveillé n°3", "COURS", 2, "T2", -50),
        ("Test pratique", "COURS", 1, "T2", -40),
        ("Devoir maison n°2", "COURS", 1, "T2", -30),
        ("Interrogation n°4", "COURS", 1, "T2", -20),
        ("Devoir surveillé n°4", "COURS", 2, "T2", -10),
        ("Composition 2ème trimestre", "COMPOSITION", 3, "T2", 0),
        
        # Troisième trimestre
        ("Devoir de révision", "COURS", 1, "T3", 10),
        ("Interrogation n°5", "COURS", 1, "T3", 20),
        ("Devoir surveillé n°5", "COURS", 2, "T3", 30),
        ("Évaluation finale", "COURS", 2, "T3", 40),
        ("Composition 3ème trimestre", "COMPOSITION", 3, "T3", 50),
    ]
    
    evaluations_creees = 0
    
    # Création des évaluations pour chaque matière
    for matiere in matieres:
        print(f"   📚 {matiere.nom} - {matiere.classe.nom}")
        
        for titre, categorie, coeff, trimestre, jours_offset in evaluations_types:
            # Date d'évaluation
            date_eval = date.today() + timedelta(days=jours_offset)
            
            # Titre personnalisé selon la matière
            titre_complet = f"{titre} - {matiere.nom}"
            
            evaluation, created = Evaluation.objects.get_or_create(
                titre=titre_complet,
                classe=matiere.classe,
                matiere=matiere,
                defaults={
                    'ecole': matiere.ecole,
                    'date': date_eval,
                    'categorie': categorie,
                    'coefficient': coeff,
                    'trimestre': trimestre,
                    'annee_scolaire': '2024-2025'
                }
            )
            
            if created:
                evaluations_creees += 1
                print(f"      ✅ {titre}")
    
    print(f"\n🎯 {evaluations_creees} nouvelles évaluations créées")
    
    # Génération de notes pour les nouvelles évaluations
    generer_notes_evaluations()
    
    # Statistiques finales
    afficher_statistiques()


def generer_notes_evaluations():
    """Génère des notes pour toutes les évaluations sans notes"""
    print("\n🎯 Génération des notes pour les évaluations...")
    
    user = User.objects.first()
    if not user:
        print("❌ Aucun utilisateur trouvé pour la saisie des notes")
        return
    
    # Évaluations sans notes
    evaluations_sans_notes = Evaluation.objects.filter(notes__isnull=True).distinct()
    notes_creees = 0
    
    for evaluation in evaluations_sans_notes:
        # Élèves de la classe
        eleves = Eleve.objects.filter(classe=evaluation.classe, statut='ACTIF')[:20]  # Max 20 élèves
        
        for eleve in eleves:
            # Note réaliste selon le type d'évaluation et la matière
            note_value = generer_note_realiste(evaluation)
            
            note, created = Note.objects.get_or_create(
                evaluation=evaluation,
                eleve=eleve,
                defaults={
                    'ecole': evaluation.ecole,
                    'classe': evaluation.classe,
                    'matiere': evaluation.matiere,
                    'matricule': eleve.matricule,
                    'note': Decimal(str(note_value)),
                    'saisie_par': user
                }
            )
            
            if created:
                notes_creees += 1
    
    print(f"   📊 {notes_creees} nouvelles notes générées")


def generer_note_realiste(evaluation):
    """Génère une note réaliste selon l'évaluation"""
    # Moyennes de base selon la matière
    moyennes_matieres = {
        'Mathématiques': 11.5,
        'Français': 12.0,
        'Anglais': 11.8,
        'Sciences Physiques': 11.2,
        'Sciences Naturelles': 12.5,
        'Histoire-Géographie': 12.8,
        'Philosophie': 11.0,
        'Éducation Physique': 14.0,
        'Arts Plastiques': 13.5,
        'Musique': 13.2,
        'Physique-Chimie': 11.0,
        'SVT': 12.3,
    }
    
    # Moyenne de base selon la matière
    moyenne_base = moyennes_matieres.get(evaluation.matiere.nom, 12.0)
    
    # Ajustement selon le type d'évaluation
    if evaluation.categorie == "COMPOSITION":
        # Les compositions sont généralement plus difficiles
        moyenne_base -= 1.0
    elif "Interrogation" in evaluation.titre:
        # Les interrogations sont souvent plus faciles
        moyenne_base += 0.5
    elif "Devoir maison" in evaluation.titre:
        # Les devoirs maison ont de meilleures notes
        moyenne_base += 1.5
    
    # Ajustement selon le trimestre
    if evaluation.trimestre == "T1":
        # Premier trimestre : notes plus faibles (adaptation)
        moyenne_base -= 0.5
    elif evaluation.trimestre == "T3":
        # Troisième trimestre : notes meilleures (progression)
        moyenne_base += 0.5
    
    # Distribution normale avec écart-type variable
    ecart_type = 3.0
    if evaluation.categorie == "COMPOSITION":
        ecart_type = 3.5  # Plus de dispersion pour les compositions
    
    note = random.normalvariate(moyenne_base, ecart_type)
    
    # Contraintes entre 0 et 20
    note = max(0, min(20, note))
    
    # Arrondi à 0.25 près
    note = round(note * 4) / 4
    
    return note


def afficher_statistiques():
    """Affiche les statistiques finales"""
    print("\n📊 STATISTIQUES FINALES:")
    print("=" * 40)
    
    total_classes = Classe.objects.count()
    total_matieres = MatiereClasse.objects.count()
    total_evaluations = Evaluation.objects.count()
    total_notes = Note.objects.count()
    
    print(f"📚 Classes: {total_classes}")
    print(f"📖 Matières: {total_matieres}")
    print(f"📝 Évaluations: {total_evaluations}")
    print(f"🎯 Notes: {total_notes}")
    
    if total_notes > 0:
        from django.db.models import Avg, Count
        
        # Moyenne générale
        moyenne_generale = Note.objects.aggregate(avg=Avg('note'))['avg']
        print(f"📊 Moyenne générale: {moyenne_generale:.2f}/20")
        
        # Répartition par trimestre
        print(f"\n📅 RÉPARTITION PAR TRIMESTRE:")
        for trimestre in ['T1', 'T2', 'T3']:
            nb_eval = Evaluation.objects.filter(trimestre=trimestre).count()
            nb_notes = Note.objects.filter(evaluation__trimestre=trimestre).count()
            if nb_notes > 0:
                moy_trim = Note.objects.filter(evaluation__trimestre=trimestre).aggregate(avg=Avg('note'))['avg']
                print(f"   {trimestre}: {nb_eval} évaluations, {nb_notes} notes (moy: {moy_trim:.2f})")
        
        # Répartition par catégorie
        print(f"\n📋 RÉPARTITION PAR CATÉGORIE:")
        for categorie in ['COURS', 'COMPOSITION']:
            nb_eval = Evaluation.objects.filter(categorie=categorie).count()
            nb_notes = Note.objects.filter(evaluation__categorie=categorie).count()
            if nb_notes > 0:
                moy_cat = Note.objects.filter(evaluation__categorie=categorie).aggregate(avg=Avg('note'))['avg']
                print(f"   {categorie}: {nb_eval} évaluations, {nb_notes} notes (moy: {moy_cat:.2f})")
        
        # Top 5 des matières avec le plus d'évaluations
        print(f"\n🏆 TOP 5 MATIÈRES (nb évaluations):")
        top_matieres = MatiereClasse.objects.annotate(
            nb_eval=Count('evaluations')
        ).order_by('-nb_eval')[:5]
        
        for i, matiere in enumerate(top_matieres, 1):
            print(f"   {i}. {matiere.nom}: {matiere.nb_eval} évaluations")
    
    print(f"\n🎉 DONNÉES COMPLÈTES POUR LES TESTS!")
    print("Accédez au dashboard: http://127.0.0.1:8001/notes/")
    print("Les nouvelles interfaces modernes sont prêtes à être testées!")


if __name__ == '__main__':
    main()
