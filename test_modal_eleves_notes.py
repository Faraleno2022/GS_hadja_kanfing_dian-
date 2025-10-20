#!/usr/bin/env python
"""
Script de test pour la nouvelle fonctionnalité de fenêtre modale
Liste des élèves avec notes par classe et période avec classement
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import Note, Evaluation
from eleves.models import Eleve, Classe
from django.db.models import Count
import requests
import json

def main():
    print("🧪 TEST DE LA FENÊTRE MODALE ÉLÈVES & NOTES")
    print("=" * 50)
    
    # 1. Vérification des données disponibles
    print("📊 VÉRIFICATION DES DONNÉES:")
    
    classes = list(Classe.objects.all()[:5])
    print(f"   📚 Classes disponibles: {len(classes)}")
    
    for classe in classes:
        eleves = Eleve.objects.filter(classe=classe, statut='ACTIF')
        notes = Note.objects.filter(classe=classe)
        print(f"      • {classe.nom}: {eleves.count()} élèves, {notes.count()} notes")
    
    # 2. Test des périodes disponibles
    print(f"\n📅 PÉRIODES DISPONIBLES:")
    
    # Trimestres
    trimestres = Evaluation.objects.values_list('trimestre', flat=True).distinct()
    print(f"   📝 Trimestres: {list(trimestres)}")
    
    # Mois (basé sur les dates d'évaluations)
    evaluations_avec_dates = Evaluation.objects.filter(date__isnull=False)
    mois_disponibles = set()
    for eval in evaluations_avec_dates[:20]:  # Échantillon
        if eval.date:
            mois_disponibles.add(f"{eval.date.year}-{eval.date.month:02d}")
    
    print(f"   📅 Mois avec évaluations: {sorted(list(mois_disponibles))[:6]}...")
    
    # 3. Test de l'API
    print(f"\n🔗 TEST DE L'API:")
    
    if classes:
        classe_test = classes[0]
        
        # Test des différents types de périodes
        tests_api = [
            ('trimestre', 'T1', '1er Trimestre'),
            ('trimestre', 'T2', '2ème Trimestre'),
            ('semestre', 'S1', '1er Semestre'),
            ('mois', '2024-09', 'Septembre 2024'),
        ]
        
        print(f"   🎯 Classe de test: {classe_test.nom}")
        
        for periode_type, periode_value, periode_label in tests_api:
            # Simulation d'une requête à l'API
            eleves = Eleve.objects.filter(classe=classe_test, statut='ACTIF')
            
            # Comptage des notes selon la période
            notes_count = 0
            if periode_type == 'trimestre':
                notes_count = Note.objects.filter(
                    classe=classe_test,
                    evaluation__trimestre=periode_value
                ).count()
            elif periode_type == 'semestre':
                if periode_value == 'S1':
                    notes_count = Note.objects.filter(
                        classe=classe_test,
                        evaluation__trimestre__in=['T1', 'T2']
                    ).count()
                else:
                    notes_count = Note.objects.filter(
                        classe=classe_test,
                        evaluation__trimestre='T3'
                    ).count()
            elif periode_type == 'mois':
                try:
                    year, month = periode_value.split('-')
                    notes_count = Note.objects.filter(
                        classe=classe_test,
                        evaluation__date__year=int(year),
                        evaluation__date__month=int(month)
                    ).count()
                except:
                    notes_count = 0
            
            print(f"      ✅ {periode_label}: {eleves.count()} élèves, {notes_count} notes")
    
    # 4. Simulation du calcul de moyennes
    print(f"\n📊 SIMULATION CALCUL DE MOYENNES:")
    
    if classes and Eleve.objects.filter(classe=classes[0]).exists():
        eleve_test = Eleve.objects.filter(classe=classes[0]).first()
        
        # Notes de l'élève pour T1
        notes_t1 = Note.objects.filter(
            eleve=eleve_test,
            evaluation__trimestre='T1'
        ).select_related('evaluation', 'matiere')
        
        if notes_t1.exists():
            print(f"   👨‍🎓 Élève test: {eleve_test.nom} {eleve_test.prenom}")
            print(f"   📝 Notes T1: {notes_t1.count()}")
            
            # Calcul de la moyenne T1
            total_points = 0
            total_coeffs = 0
            notes_par_matiere = {}
            
            for note in notes_t1:
                matiere_nom = note.matiere.nom
                if matiere_nom not in notes_par_matiere:
                    notes_par_matiere[matiere_nom] = {
                        'notes': [],
                        'coefficient_matiere': note.matiere.coefficient
                    }
                
                notes_par_matiere[matiere_nom]['notes'].append({
                    'note': float(note.note),
                    'coefficient': note.evaluation.coefficient
                })
            
            # Calcul de la moyenne générale
            for matiere_nom, data in notes_par_matiere.items():
                total_points_matiere = sum(
                    n['note'] * n['coefficient'] for n in data['notes']
                )
                total_coeffs_matiere = sum(n['coefficient'] for n in data['notes'])
                
                if total_coeffs_matiere > 0:
                    moyenne_matiere = total_points_matiere / total_coeffs_matiere
                    total_points += moyenne_matiere * data['coefficient_matiere']
                    total_coeffs += data['coefficient_matiere']
            
            moyenne_generale = round(total_points / total_coeffs, 2) if total_coeffs > 0 else 0
            
            print(f"   📊 Moyenne T1 calculée: {moyenne_generale}/20")
            print(f"   📚 Matières: {list(notes_par_matiere.keys())[:3]}...")
        else:
            print(f"   ⚠️  Aucune note T1 pour l'élève test")
    
    # 5. URLs de test
    print(f"\n🌐 URLS DE TEST:")
    print(f"   📋 Dashboard ancien: http://127.0.0.1:8001/notes/ancien/")
    print(f"   🔗 API Modal: http://127.0.0.1:8001/notes/api/eleves-notes-modal/")
    
    # Exemples d'URLs avec paramètres
    if classes:
        classe_id = classes[0].id
        print(f"\n📝 EXEMPLES D'URLS API:")
        print(f"   • Trimestre T1: /notes/api/eleves-notes-modal/?classe_id={classe_id}&periode_type=trimestre&periode_value=T1")
        print(f"   • Semestre S1: /notes/api/eleves-notes-modal/?classe_id={classe_id}&periode_type=semestre&periode_value=S1")
        print(f"   • Mois Sept 2024: /notes/api/eleves-notes-modal/?classe_id={classe_id}&periode_type=mois&periode_value=2024-09")
    
    print(f"\n🎉 FONCTIONNALITÉ PRÊTE POUR LES TESTS!")
    print("=" * 50)
    print("📋 INSTRUCTIONS D'UTILISATION:")
    print("1. Accédez à l'ancien dashboard: /notes/ancien/")
    print("2. Cliquez sur le bouton 'Liste Élèves & Notes'")
    print("3. Sélectionnez une classe dans la fenêtre modale")
    print("4. Choisissez le type de période (Trimestre/Semestre/Mois)")
    print("5. Sélectionnez la période spécifique")
    print("6. Cliquez sur 'Charger les Données'")
    print("7. Consultez le classement avec moyennes et statistiques")
    print("8. Cliquez sur l'œil pour voir les détails d'un élève")


if __name__ == '__main__':
    main()
