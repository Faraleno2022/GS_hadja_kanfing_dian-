#!/usr/bin/env python
"""
Script de test pour vérifier la fonctionnalité des détails des notes par élève
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import Note
from eleves.models import Eleve
from django.db.models import Count

def main():
    print("🧪 TEST DES DÉTAILS DES NOTES PAR ÉLÈVE")
    print("=" * 45)
    
    # Récupération des élèves avec des notes
    eleves_avec_notes = Eleve.objects.annotate(
        nb_notes=Count('notes')
    ).filter(nb_notes__gt=0).order_by('-nb_notes')[:10]
    
    print(f"📊 {eleves_avec_notes.count()} élèves trouvés avec des notes")
    
    if not eleves_avec_notes:
        print("❌ Aucun élève avec des notes trouvé")
        return
    
    print("\n🎯 TOP 10 ÉLÈVES AVEC LE PLUS DE NOTES:")
    print("-" * 45)
    
    for i, eleve in enumerate(eleves_avec_notes, 1):
        notes_eleve = Note.objects.filter(eleve=eleve)
        
        if notes_eleve.exists():
            # Calcul de la moyenne
            total_points = sum(
                float(note.note) * note.evaluation.coefficient * note.matiere.coefficient
                for note in notes_eleve
            )
            total_coeffs = sum(
                note.evaluation.coefficient * note.matiere.coefficient 
                for note in notes_eleve
            )
            moyenne = round(total_points / total_coeffs, 2) if total_coeffs > 0 else 0
            
            print(f"{i:2d}. {eleve.nom} {eleve.prenom}")
            print(f"    📚 Classe: {eleve.classe.nom}")
            print(f"    🎯 Notes: {eleve.nb_notes}")
            print(f"    📊 Moyenne: {moyenne}/20")
            print(f"    🔗 URL: /notes/eleves/{eleve.id}/notes/")
            print()
    
    # Test d'un élève spécifique
    eleve_test = eleves_avec_notes.first()
    print(f"🔍 DÉTAIL POUR: {eleve_test.nom} {eleve_test.prenom}")
    print("-" * 45)
    
    notes_test = Note.objects.filter(eleve=eleve_test).select_related('evaluation', 'matiere')
    
    # Groupement par matière
    matieres_notes = {}
    for note in notes_test:
        matiere_nom = note.matiere.nom
        if matiere_nom not in matieres_notes:
            matieres_notes[matiere_nom] = []
        matieres_notes[matiere_nom].append(note)
    
    for matiere, notes in matieres_notes.items():
        print(f"\n📖 {matiere}:")
        for note in notes[:3]:  # Afficher les 3 premières notes
            print(f"   • {note.evaluation.titre}: {note.note}/20 ({note.evaluation.date})")
        
        if len(notes) > 3:
            print(f"   ... et {len(notes) - 3} autres notes")
    
    print(f"\n✅ FONCTIONNALITÉ PRÊTE!")
    print("🌐 Accédez au classement pour tester les liens:")
    print("   http://127.0.0.1:8001/notes/classes/{classe_id}/classement-moderne/")
    print("\n🔗 Ou directement aux détails d'un élève:")
    print(f"   http://127.0.0.1:8001/notes/eleves/{eleve_test.id}/notes/")


if __name__ == '__main__':
    main()
