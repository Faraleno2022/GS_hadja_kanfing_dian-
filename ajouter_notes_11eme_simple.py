#!/usr/bin/env python
"""
Script simplifié pour ajouter des notes à la classe 11ème série littéraire 2024-2025
"""
import os
import sys
import django
import random

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Classe as ClasseEleve, Eleve

def ajouter_notes_11eme_simple():
    """Ajouter des notes pour la 11ème série littéraire de façon simple"""
    print("🎯 AJOUT NOTES 11ÈME SÉRIE LITTÉRAIRE - VERSION SIMPLE")
    print("=" * 60)
    
    # 1. Identifier la classe
    print("🔍 RECHERCHE CLASSE 11ÈME LITTÉRAIRE...")
    
    # Chercher ClasseNote
    classe_note = ClasseNote.objects.filter(
        nom__icontains="11",
        annee_scolaire="2024-2025"
    ).filter(nom__icontains="littéraire").first()
    
    if not classe_note:
        print("❌ ClasseNote 11ème littéraire non trouvée")
        return
    
    print(f"✅ ClasseNote trouvée: {classe_note.nom} (ID: {classe_note.id})")
    
    # 2. Trouver la ClasseEleve correspondante
    classe_eleve = ClasseEleve.objects.filter(
        nom__icontains="11",
        annee_scolaire="2024-2025"
    ).filter(nom__icontains="littéraire").first()
    
    if not classe_eleve:
        # Essayer avec "LETTRES"
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains="11",
            annee_scolaire="2024-2025"
        ).filter(nom__icontains="LETTRES").first()
    
    if not classe_eleve:
        print("❌ ClasseEleve correspondante non trouvée")
        return
    
    print(f"✅ ClasseEleve trouvée: {classe_eleve.nom} (ID: {classe_eleve.id})")
    
    # 3. Vérifier les matières existantes
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"📚 Matières existantes: {matieres.count()}")
    
    if matieres.count() == 0:
        print("❌ Aucune matière trouvée pour cette classe")
        return
    
    for matiere in matieres:
        print(f"   - {matiere.nom} (coef: {matiere.coefficient})")
    
    # 4. Vérifier les élèves
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    print(f"👥 Élèves actifs: {eleves.count()}")
    
    if eleves.count() == 0:
        print("⚠️  Aucun élève actif - Création d'élèves de test...")
        
        # Créer un responsable de test
        from eleves.models import Responsable
        responsable, _ = Responsable.objects.get_or_create(
            nom='PARENT',
            prenom='Test',
            defaults={
                'telephone': '123456789',
                'profession': 'Test',
                'adresse': 'Adresse test'
            }
        )
        
        # Créer quelques élèves
        eleves_test = [
            ('Aissatou', 'DIALLO', 'F'),
            ('Mamadou', 'BARRY', 'M'),
            ('Fatoumata', 'SOW', 'F'),
            ('Alpha', 'CONDE', 'M'),
            ('Mariama', 'CAMARA', 'F'),
        ]
        
        eleves_crees = []
        for i, (prenom, nom, sexe) in enumerate(eleves_test, 1):
            try:
                eleve, created = Eleve.objects.get_or_create(
                    prenom=prenom,
                    nom=nom,
                    classe=classe_eleve,
                    defaults={
                        'sexe': sexe,
                        'statut': 'ACTIF',
                        'date_naissance': '2006-01-01',
                        'lieu_naissance': 'Conakry',
                        'date_inscription': '2024-09-01',
                        'matricule': f'11L{i:03d}',
                        'responsable_principal': responsable,
                    }
                )
                if created:
                    eleves_crees.append(eleve)
                    print(f"   ✅ {prenom} {nom}")
            except Exception as e:
                print(f"   ❌ Erreur pour {prenom} {nom}: {e}")
        
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    
    print(f"👥 Total élèves: {eleves.count()}")
    for eleve in eleves[:3]:
        print(f"   - {eleve.prenom} {eleve.nom}")
    
    # 5. Créer des évaluations pour différentes périodes
    periodes = [
        ('OCTOBRE', '2024-10-15'),
        ('NOVEMBRE', '2024-11-15'),
        ('DECEMBRE', '2024-12-15'),
        ('JANVIER', '2025-01-15'),
    ]
    
    print(f"\n📝 CRÉATION ÉVALUATIONS...")
    evaluations_creees = 0
    
    for periode, date in periodes:
        print(f"   📅 {periode}:")
        
        for matiere in matieres:
            evaluation, created = Evaluation.objects.get_or_create(
                matiere=matiere,
                titre=f"Devoir {periode} - {matiere.nom}",
                periode=periode,
                defaults={
                    'type_evaluation': 'DEVOIR',
                    'date_evaluation': date,
                    'note_sur': 20.0,
                    'coefficient': 1.0,
                }
            )
            if created:
                evaluations_creees += 1
                print(f"      ✅ {matiere.nom}")
    
    print(f"📊 Évaluations créées: {evaluations_creees}")
    
    # 6. Générer des notes réalistes
    print(f"\n📊 GÉNÉRATION NOTES...")
    
    evaluations = Evaluation.objects.filter(matiere__classe=classe_note)
    notes_creees = 0
    
    # Profils d'élèves pour des notes réalistes
    profils = ['excellent', 'bon', 'moyen', 'faible']
    ranges = {
        'excellent': (15, 19),
        'bon': (12, 16),
        'moyen': (8, 14),
        'faible': (5, 11),
    }
    
    for i, eleve in enumerate(eleves):
        # Assigner un profil
        profil = profils[i % len(profils)]
        min_note, max_note = ranges[profil]
        
        print(f"   👤 {eleve.prenom} {eleve.nom} ({profil})")
        
        for evaluation in evaluations:
            # Variation selon la matière
            matiere_nom = evaluation.matiere.nom.lower()
            bonus = 0
            
            if 'français' in matiere_nom or 'philosophie' in matiere_nom:
                bonus = 1  # Bonus pour matières littéraires
            elif 'mathématiques' in matiere_nom:
                bonus = -1  # Malus pour maths en série littéraire
            
            # Générer la note
            note_base = random.uniform(min_note, max_note)
            note_finale = max(0, min(20, note_base + bonus + random.uniform(-1, 1)))
            note_finale = round(note_finale, 2)
            
            # 5% de chance d'absence
            absent = random.random() < 0.05
            
            note_obj, created = NoteEleve.objects.get_or_create(
                eleve=eleve,
                evaluation=evaluation,
                defaults={
                    'note': None if absent else note_finale,
                    'absent': absent,
                }
            )
            
            if created:
                notes_creees += 1
    
    print(f"✅ Notes créées: {notes_creees}")
    
    # 7. Résumé final
    print(f"\n📊 RÉSUMÉ FINAL")
    print("=" * 20)
    
    total_evaluations = Evaluation.objects.filter(matiere__classe=classe_note).count()
    total_notes = NoteEleve.objects.filter(evaluation__matiere__classe=classe_note).count()
    
    print(f"✅ Classe: {classe_note.nom} (ID: {classe_note.id})")
    print(f"✅ Élèves: {eleves.count()}")
    print(f"✅ Matières: {matieres.count()}")
    print(f"✅ Évaluations: {total_evaluations}")
    print(f"✅ Notes: {total_notes}")
    
    if total_notes > 0:
        print(f"\n🎉 SUCCÈS ! Notes ajoutées pour la 11ème série littéraire")
        print(f"🔗 URL de consultation:")
        print(f"   http://127.0.0.1:8000/notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")
        print(f"   http://127.0.0.1:8000/notes/consulter/?classe_id={classe_note.id}&periode=NOVEMBRE")
        print(f"   http://127.0.0.1:8000/notes/consulter/?classe_id={classe_note.id}&periode=DECEMBRE")
    else:
        print(f"\n⚠️  Aucune note créée")

if __name__ == "__main__":
    try:
        ajouter_notes_11eme_simple()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
