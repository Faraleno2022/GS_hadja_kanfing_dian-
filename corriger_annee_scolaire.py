"""
Script pour corriger les années scolaires des notes mensuelles
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote
from eleves.models import Eleve
from django.db import transaction

def corriger_annees_scolaires():
    """Corriger les années scolaires des notes"""
    print("\n" + "="*80)
    print("🔧 CORRECTION ANNÉES SCOLAIRES")
    print("="*80)
    
    # Vérifier les incohérences
    print("\n1️⃣ DÉTECTION DES INCOHÉRENCES:")
    
    notes_problematiques = []
    
    for note in NoteMensuelle.objects.all():
        # Année de l'élève
        annee_eleve = note.eleve.classe.annee_scolaire
        
        # Année de la ClasseNote
        annee_classenote = note.matiere.classe.annee_scolaire
        
        # Année de la note
        annee_note = note.annee_scolaire
        
        if annee_eleve != annee_note or annee_classenote != annee_note:
            notes_problematiques.append({
                'note': note,
                'annee_eleve': annee_eleve,
                'annee_classenote': annee_classenote,
                'annee_note': annee_note
            })
    
    if not notes_problematiques:
        print("✅ Aucune incohérence détectée")
        return
    
    print(f"⚠️ {len(notes_problematiques)} notes avec incohérences détectées")
    
    # Afficher quelques exemples
    for i, prob in enumerate(notes_problematiques[:5]):
        print(f"\n   Exemple {i+1}:")
        print(f"   • Élève: {prob['note'].eleve.matricule} (classe: {prob['annee_eleve']})")
        print(f"   • ClasseNote: {prob['note'].matiere.classe.nom} ({prob['annee_classenote']})")
        print(f"   • Note: {prob['annee_note']}")
    
    # Demander confirmation
    print(f"\n2️⃣ CORRECTION:")
    print(f"   Corriger {len(notes_problematiques)} notes ?")
    reponse = input("   (oui/non) : ")
    
    if reponse.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Correction annulée")
        return
    
    # Appliquer les corrections
    corrections = 0
    
    with transaction.atomic():
        for prob in notes_problematiques:
            note = prob['note']
            
            # Utiliser l'année de la ClasseNote comme référence
            nouvelle_annee = prob['annee_classenote']
            
            note.annee_scolaire = nouvelle_annee
            note.save()
            corrections += 1
    
    print(f"\n✅ {corrections} notes corrigées")
    print("   Années scolaires harmonisées avec les ClasseNote")

if __name__ == "__main__":
    corriger_annees_scolaires()
    print("\n" + "="*80)
    print("✅ CORRECTION TERMINÉE")
    print("="*80)
