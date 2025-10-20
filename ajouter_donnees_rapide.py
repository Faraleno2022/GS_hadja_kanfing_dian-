#!/usr/bin/env python
"""
Script rapide pour ajouter des données de test au module notes
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
    print("🚀 Ajout rapide des données de test...")
    
    # 1. Récupération des classes existantes
    classes = Classe.objects.all()[:10]  # Prendre les 10 premières classes
    
    if not classes:
        print("❌ Aucune classe trouvée. Veuillez d'abord créer des classes.")
        return
    
    print(f"📚 {len(classes)} classes trouvées")
    
    # 2. Ajout des matières
    matieres_base = [
        ("Mathématiques", 4),
        ("Français", 4),
        ("Anglais", 3),
        ("Sciences Physiques", 3),
        ("Histoire-Géographie", 3),
        ("Éducation Physique", 2),
    ]
    
    print("📖 Ajout des matières...")
    matieres_creees = []
    
    for classe in classes:
        print(f"   📝 Classe: {classe.nom}")
        
        for nom_matiere, coefficient in matieres_base:
            matiere, created = MatiereClasse.objects.get_or_create(
                nom=nom_matiere,
                classe=classe,
                defaults={
                    'coefficient': coefficient,
                    'ecole': classe.ecole,
                    'actif': True
                }
            )
            
            if created:
                matieres_creees.append(matiere)
                print(f"      ✅ {nom_matiere} (coeff. {coefficient})")
    
    # 3. Création des évaluations
    print("📝 Création des évaluations...")
    evaluations_creees = []
    
    evaluations_types = [
        ("Devoir n°1", "COURS", 1),
        ("Devoir n°2", "COURS", 1),
        ("Composition 1er trimestre", "COMPOSITION", 2),
        ("Devoir n°3", "COURS", 1),
        ("Devoir n°4", "COURS", 1),
        ("Composition 2ème trimestre", "COMPOSITION", 2),
    ]
    
    for matiere in matieres_creees:
        for i, (titre, categorie, coeff) in enumerate(evaluations_types):
            date_eval = date.today() - timedelta(days=30*i)
            if i < 3:
                trimestre = "T1"
            elif i < 5:
                trimestre = "T2"
            else:
                trimestre = "T3"
            
            evaluation, created = Evaluation.objects.get_or_create(
                titre=f"{titre} - {matiere.nom}",
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
                evaluations_creees.append(evaluation)
                print(f"      ✅ {titre}")
    
    # 4. Génération des notes
    print("🎯 Génération des notes...")
    notes_creees = 0
    
    user = User.objects.first()
    if not user:
        print("❌ Aucun utilisateur trouvé pour la saisie des notes")
        return
    
    for evaluation in evaluations_creees:
        eleves = Eleve.objects.filter(classe=evaluation.classe, statut='ACTIF')[:15]  # Max 15 élèves par classe
        
        for eleve in eleves:
            # Note réaliste entre 8 et 18
            note_value = round(random.uniform(8.0, 18.0) * 4) / 4  # Arrondi à 0.25
            
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
    
    # 5. Statistiques finales
    print("\n📊 STATISTIQUES:")
    print(f"📚 Classes: {len(classes)}")
    print(f"📖 Matières créées: {len(matieres_creees)}")
    print(f"📝 Évaluations créées: {len(evaluations_creees)}")
    print(f"🎯 Notes créées: {notes_creees}")
    
    # Totaux dans la base
    total_matieres = MatiereClasse.objects.count()
    total_evaluations = Evaluation.objects.count()
    total_notes = Note.objects.count()
    
    print(f"\n📈 TOTAUX EN BASE:")
    print(f"📖 Total matières: {total_matieres}")
    print(f"📝 Total évaluations: {total_evaluations}")
    print(f"🎯 Total notes: {total_notes}")
    
    if total_notes > 0:
        from django.db.models import Avg
        moyenne = Note.objects.aggregate(avg=Avg('note'))['avg']
        print(f"📊 Moyenne générale: {moyenne:.2f}/20")
    
    print("\n🎉 DONNÉES AJOUTÉES AVEC SUCCÈS!")
    print("Vous pouvez maintenant tester les interfaces modernes:")
    print("• Dashboard: http://127.0.0.1:8001/notes/")
    print("• Saisie moderne: Sélectionnez une évaluation depuis le dashboard")
    print("• Classements: Sélectionnez une classe depuis le dashboard")


if __name__ == '__main__':
    main()
