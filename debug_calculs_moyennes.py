"""
Script pour déboguer les calculs de moyennes
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve
from notes.calculs_moyennes import calculer_moyenne_matiere

def debug_calculs():
    """Debug des calculs de moyennes"""
    print("\n" + "="*80)
    print("🐛 DEBUG CALCULS MOYENNES")
    print("="*80)
    
    # Trouver un élève avec des notes
    eleve_test = Eleve.objects.filter(
        notes_mensuelles__isnull=False
    ).first()
    
    if not eleve_test:
        print("❌ Aucun élève avec notes")
        return
    
    print(f"🧪 Élève test : {eleve_test.matricule} - {eleve_test.nom}")
    
    # Ses notes
    notes = NoteMensuelle.objects.filter(eleve=eleve_test)
    print(f"📝 Total notes : {notes.count()}")
    
    # Test pour chaque note
    for note in notes[:3]:  # Tester 3 notes
        print(f"\n" + "-"*60)
        print(f"🔍 Test note : {note.matiere.nom} - {note.mois}")
        print(f"   • Note directe : {note.note} (absent: {note.absent})")
        print(f"   • Année note : {note.annee_scolaire}")
        print(f"   • Année matière : {note.matiere.classe.annee_scolaire}")
        print(f"   • Année élève : {eleve_test.classe.annee_scolaire}")
        
        # Test de recherche exacte
        try:
            note_recherche = NoteMensuelle.objects.get(
                eleve=eleve_test,
                matiere=note.matiere,
                mois=note.mois,
                annee_scolaire=note.matiere.classe.annee_scolaire
            )
            print(f"   ✅ Note trouvée par recherche exacte")
        except NoteMensuelle.DoesNotExist:
            print(f"   ❌ Note NON trouvée par recherche exacte")
            
            # Chercher avec l'année de la note
            try:
                note_recherche_alt = NoteMensuelle.objects.get(
                    eleve=eleve_test,
                    matiere=note.matiere,
                    mois=note.mois,
                    annee_scolaire=note.annee_scolaire
                )
                print(f"   ⚠️ Note trouvée avec année de la note : {note.annee_scolaire}")
            except NoteMensuelle.DoesNotExist:
                print(f"   ❌ Note introuvable même avec année de la note")
        except Exception as e:
            print(f"   ❌ Erreur recherche : {e}")
        
        # Test calcul fonction
        try:
            resultat = calculer_moyenne_matiere(
                eleve=eleve_test,
                matiere=note.matiere,
                periode=note.mois,
                system_type='mensuel'
            )
            print(f"   📊 Résultat calcul : {resultat}")
        except Exception as e:
            print(f"   ❌ Erreur calcul : {e}")
            import traceback
            traceback.print_exc()

def proposer_corrections():
    """Proposer des corrections"""
    print("\n" + "="*80)
    print("💡 CORRECTIONS PROPOSÉES")
    print("="*80)
    
    print("\n🔧 Si années scolaires incohérentes :")
    print("   python corriger_annee_scolaire.py")
    
    print("\n🔧 Si problème de correspondance classes :")
    print("   python reparer_lien_classe_notes.py")
    
    print("\n🔧 Si notes manquantes :")
    print("   python creer_notes_11eme_corrige.py")

if __name__ == "__main__":
    debug_calculs()
    proposer_corrections()
    print("\n" + "="*80)
    print("✅ DEBUG TERMINÉ")
    print("="*80)
