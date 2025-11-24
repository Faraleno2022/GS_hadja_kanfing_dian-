"""
Diagnostic spécifique pour la classe ID 13 (9ÈME ANNÉE 2025-2026)
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import NoteMensuelle, ClasseNote, MatiereNote
from eleves.models import Eleve, Classe

def diagnostic_classe_13():
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC CLASSE ID 13 - ANNÉE SCOLAIRE 2025-2026")
    print("="*80)
    
    # Rechercher la classe ID 13
    try:
        classe_note = ClasseNote.objects.get(id=13)
        print(f"\n✅ ClasseNote trouvée :")
        print(f"   • ID : {classe_note.id}")
        print(f"   • Nom : {classe_note.nom}")
        print(f"   • Année scolaire : {classe_note.annee_scolaire}")
        print(f"   • École : {classe_note.ecole}")
    except ClasseNote.DoesNotExist:
        print("❌ ClasseNote ID 13 non trouvée")
        return
    
    # Rechercher la classe Eleve correspondante
    print("\n📚 Recherche de la Classe (modèle Eleve) correspondante...")
    classes_eleve = Classe.objects.filter(nom__icontains=classe_note.nom)
    
    for classe_eleve in classes_eleve:
        print(f"\n   Classe trouvée : {classe_eleve.nom}")
        print(f"   • ID : {classe_eleve.id}")
        print(f"   • Année scolaire : {classe_eleve.annee_scolaire}")
        print(f"   • École : {classe_eleve.ecole}")
        
        # Compter les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='INSCRIT')
        print(f"\n👥 ÉLÈVES INSCRITS : {eleves.count()}")
        
        if eleves.exists():
            print("\n   Exemples d'élèves :")
            for eleve in eleves[:5]:
                print(f"   • {eleve.matricule} - {eleve.nom} {eleve.prenom}")
        else:
            print("   ❌ Aucun élève inscrit")
    
    # Lister les matières
    matieres = MatiereNote.objects.filter(classe=classe_note)
    print(f"\n📖 MATIÈRES CONFIGURÉES : {matieres.count()}")
    
    if matieres.exists():
        print("\n   Liste des matières :")
        for matiere in matieres:
            print(f"   • {matiere.nom:30} (Code: {matiere.code}, Coef: {matiere.coefficient})")
    else:
        print("   ❌ Aucune matière configurée pour cette classe")
    
    # Vérifier les notes mensuelles d'OCTOBRE
    print("\n" + "-"*80)
    print("📊 NOTES MENSUELLES D'OCTOBRE 2025-2026")
    print("-"*80)
    
    # Rechercher toutes les notes pour octobre de cette année scolaire
    notes_octobre = NoteMensuelle.objects.filter(
        mois='OCTOBRE',
        annee_scolaire='2025-2026'
    )
    
    print(f"\nTotal notes trouvées (toute l'école) : {notes_octobre.count()}")
    
    # Filtrer pour les matières de cette classe
    if matieres.exists():
        notes_classe = notes_octobre.filter(matiere__in=matieres)
        print(f"Notes pour cette classe : {notes_classe.count()}")
        
        if notes_classe.exists():
            # Compter par matière
            print("\n📈 Répartition par matière :")
            for matiere in matieres:
                notes_matiere = notes_classe.filter(matiere=matiere)
                if notes_matiere.exists():
                    print(f"   • {matiere.nom:30} : {notes_matiere.count()} notes")
                    # Afficher quelques notes
                    for note in notes_matiere[:3]:
                        if note.absent:
                            print(f"      - {note.eleve.matricule} : ABSENT")
                        else:
                            print(f"      - {note.eleve.matricule} : {note.note}/20")
        else:
            print("\n❌ AUCUNE NOTE MENSUELLE pour cette classe en OCTOBRE")
    
    # Diagnostic final
    print("\n" + "="*80)
    print("📋 DIAGNOSTIC FINAL")
    print("="*80)
    
    if not matieres.exists():
        print("\n❌ PROBLÈME 1 : Aucune matière configurée pour cette classe")
        print("   SOLUTION : Configurer les matières dans Notes → Matières")
    
    if not eleves.exists():
        print("\n❌ PROBLÈME 2 : Aucun élève inscrit dans cette classe")
        print("   SOLUTION : Vérifier l'année scolaire et les inscriptions")
    
    if matieres.exists() and not notes_classe.exists():
        print("\n❌ PROBLÈME 3 : Les notes mensuelles ne sont pas saisies")
        print("\n   SOLUTIONS :")
        print("   1. Via l'interface web :")
        print("      • Aller dans Notes → Notes Mensuelles")
        print("      • Sélectionner la classe 9ÈME ANNÉE")
        print("      • Sélectionner OCTOBRE")
        print("      • Saisir les notes")
        print("\n   2. Via import Excel :")
        print("      • Notes → Importer Notes")
        print("      • Type : Notes Mensuelles")
        print("      • Télécharger le template")
        print("      • Remplir et importer")
    
    if matieres.exists() and notes_classe.exists():
        print("\n✅ Des notes existent pour cette classe")
        print("   Si elles ne s'affichent pas :")
        print("   • Vérifier que le code a été déployé")
        print("   • Redémarrer Django")
        print("   • Vider le cache du navigateur")

if __name__ == "__main__":
    diagnostic_classe_13()
