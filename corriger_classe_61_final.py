#!/usr/bin/env python
"""
Script final pour corriger le problème de la classe 61
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Classe as ClasseEleve, Eleve, Ecole

def corriger_classe_61():
    """Correction complète pour la classe 61"""
    print("🔧 CORRECTION CLASSE 61 - SOLUTION COMPLÈTE")
    print("=" * 50)
    
    # 1. Récupérer la ClasseNote 61
    try:
        classe_note = ClasseNote.objects.get(pk=61)
        print(f"✅ ClasseNote 61: {classe_note.nom}")
    except ClasseNote.DoesNotExist:
        print("❌ ClasseNote 61 n'existe pas")
        return
    
    # 2. Créer la ClasseEleve correspondante avec les bons champs
    classe_eleve, created = ClasseEleve.objects.get_or_create(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole,
        defaults={
            'niveau': classe_note.niveau,
            'code_matricule': '12A',  # Code pour les matricules
            'capacite_max': 50,
        }
    )
    
    if created:
        print(f"✅ ClasseEleve créée: {classe_eleve}")
    else:
        print(f"✅ ClasseEleve existe: {classe_eleve}")
    
    # 3. Créer quelques élèves de test
    eleves_test = [
        ('Aminata', 'DIALLO', 'F'),
        ('Mamadou', 'BARRY', 'M'),
        ('Fatoumata', 'SOW', 'F'),
        ('Alpha', 'CONDE', 'M'),
        ('Mariama', 'CAMARA', 'F'),
    ]
    
    print(f"\n CRÉATION ÉLÈVES DE TEST")
    print("-" * 30)
    
    for prenom, nom, sexe in eleves_test:
        eleve, created = Eleve.objects.get_or_create(
            prenom=prenom,
            nom=nom,
            classe=classe_eleve,
            defaults={
                'sexe': sexe,
                'statut': 'ACTIF',
                'date_naissance': '2005-01-01',
                'lieu_naissance': 'Conakry',
                'date_inscription': '2024-09-01',  # Date d'inscription obligatoire
                'matricule': f'12A{len(Eleve.objects.filter(classe=classe_eleve)) + 1:03d}',
            }
        )
        if created:
            print(f"   {prenom} {nom}")
    
    # 4. Créer des matières
    matieres_test = [
        ('Mathématiques', 'MATH', 4),
        ('Physique-Chimie', 'PC', 3),
        ('SVT', 'SVT', 2),
        ('Français', 'FR', 3),
        ('Anglais', 'ANG', 2),
    ]
    
    print(f"\n📚 CRÉATION MATIÈRES")
    print("-" * 20)
    
    for nom, code, coef in matieres_test:
        matiere, created = MatiereNote.objects.get_or_create(
            classe=classe_note,
            nom=nom,
            defaults={
                'code': code,
                'coefficient': coef,
                'actif': True,
            }
        )
        if created:
            print(f"   ✅ {nom} (coef: {coef})")
    
    # 5. Créer des évaluations OCTOBRE
    print(f"\n📝 CRÉATION ÉVALUATIONS OCTOBRE")
    print("-" * 35)
    
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    for matiere in matieres:
        evaluation, created = Evaluation.objects.get_or_create(
            matiere=matiere,
            titre=f"Devoir OCTOBRE - {matiere.nom}",
            periode='OCTOBRE',
            defaults={
                'type_evaluation': 'DEVOIR',
                'date_evaluation': '2024-10-15',
                'note_sur': 20.0,
                'coefficient': 1.0,
            }
        )
        if created:
            print(f"   ✅ {evaluation.titre}")
    
    # 6. Créer quelques notes de test
    print(f"\n📊 CRÉATION NOTES DE TEST")
    print("-" * 25)
    
    import random
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    evaluations = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE')
    
    notes_creees = 0
    for eleve in eleves:
        for evaluation in evaluations:
            # Créer une note aléatoire entre 8 et 18
            note_value = round(random.uniform(8.0, 18.0), 2)
            
            note, created = NoteEleve.objects.get_or_create(
                eleve=eleve,
                evaluation=evaluation,
                defaults={
                    'note': note_value,
                    'absent': False,
                }
            )
            if created:
                notes_creees += 1
    
    print(f"   ✅ {notes_creees} notes créées")
    
    # 7. Test final
    print(f"\n🧪 TEST FINAL")
    print("-" * 15)
    
    # Vérifier la liaison
    classe_eleve_test = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if classe_eleve_test:
        print(f"✅ Liaison OK: ClasseNote 61 ↔ ClasseEleve {classe_eleve_test.id}")
        
        eleves_count = Eleve.objects.filter(classe=classe_eleve_test, statut='ACTIF').count()
        matieres_count = MatiereNote.objects.filter(classe=classe_note, actif=True).count()
        evaluations_count = Evaluation.objects.filter(matiere__classe=classe_note, periode='OCTOBRE').count()
        notes_count = NoteEleve.objects.filter(evaluation__matiere__classe=classe_note, evaluation__periode='OCTOBRE').count()
        
        print(f"📊 Statistiques:")
        print(f"   - Élèves actifs: {eleves_count}")
        print(f"   - Matières actives: {matieres_count}")
        print(f"   - Évaluations OCTOBRE: {evaluations_count}")
        print(f"   - Notes saisies: {notes_count}")
        
        if eleves_count > 0 and matieres_count > 0 and evaluations_count > 0 and notes_count > 0:
            print(f"\n🎉 SUCCÈS ! Tout est prêt pour la consultation")
            print(f"✅ URL de test: http://127.0.0.1:8000/notes/consulter/?classe_id=61&periode=OCTOBRE")
        else:
            print(f"\n⚠️  Il manque encore des éléments")
    else:
        print(f"❌ Liaison toujours manquante")

if __name__ == "__main__":
    try:
        corriger_classe_61()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
