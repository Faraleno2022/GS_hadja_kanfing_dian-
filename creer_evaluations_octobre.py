#!/usr/bin/env python
"""
Script pour créer les évaluations OCTOBRE pour la classe PN6
"""

import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation
from datetime import date

def creer_evaluations_octobre():
    """Crée les évaluations OCTOBRE pour la classe PN6"""
    
    print("📝 CRÉATION DES ÉVALUATIONS OCTOBRE")
    print("=" * 50)
    
    # Récupérer la classe PN6
    classe_note = ClasseNote.objects.filter(nom="PN6").first()
    
    if not classe_note:
        print("❌ Classe PN6 non trouvée")
        return
    
    print(f"✅ Classe: {classe_note.nom} (ID: {classe_note.id})")
    
    # Récupérer toutes les matières de la classe
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    print(f"📚 {matieres.count()} matière(s) trouvée(s)")
    
    evaluations_creees = 0
    evaluations_existantes = 0
    
    for matiere in matieres:
        # Vérifier si l'évaluation OCTOBRE existe déjà
        evaluation_existante = Evaluation.objects.filter(
            matiere=matiere,
            periode='OCTOBRE'
        ).first()
        
        if evaluation_existante:
            print(f"⚠️  {matiere.nom}: Évaluation OCTOBRE déjà existante")
            evaluations_existantes += 1
            continue
        
        # Créer l'évaluation OCTOBRE
        try:
            evaluation = Evaluation.objects.create(
                matiere=matiere,
                titre=f"Évaluation Octobre - {matiere.nom}",
                type_evaluation='DEVOIR',
                periode='OCTOBRE',
                date_evaluation=date(2024, 10, 15),  # Date au milieu d'octobre
                coefficient=1.0,
                note_sur=20.0,
                description=f"Évaluation mensuelle d'octobre pour {matiere.nom}"
            )
            
            print(f"✅ {matiere.nom}: Évaluation créée (ID: {evaluation.id})")
            evaluations_creees += 1
            
        except Exception as e:
            print(f"❌ {matiere.nom}: Erreur - {e}")
    
    # Résumé
    print(f"\n📊 RÉSUMÉ")
    print("=" * 30)
    print(f"✅ Évaluations créées: {evaluations_creees}")
    print(f"⚠️  Évaluations déjà existantes: {evaluations_existantes}")
    
    # Vérification finale
    print(f"\n🔍 VÉRIFICATION")
    print("-" * 20)
    
    evaluations_octobre = Evaluation.objects.filter(
        matiere__classe=classe_note,
        periode='OCTOBRE'
    )
    
    print(f"Total évaluations OCTOBRE: {evaluations_octobre.count()}")
    
    if evaluations_octobre.exists():
        print("Liste des évaluations:")
        for eval in evaluations_octobre:
            print(f"  - {eval.matiere.nom}: {eval.titre} (ID: {eval.id})")
    
    print(f"\n🎯 PROCHAINES ÉTAPES")
    print("=" * 30)
    print("1. Importer les notes avec les matricules PN6-xxx")
    print("2. Les notes seront automatiquement liées aux évaluations OCTOBRE")
    print("3. Consulter les résultats via:")
    print(f"   /notes/consulter/?classe_id={classe_note.id}&periode=OCTOBRE")

if __name__ == "__main__":
    try:
        creer_evaluations_octobre()
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
