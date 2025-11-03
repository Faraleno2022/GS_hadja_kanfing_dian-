#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour la fonctionnalité d'export des classements
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, NoteMensuelle
from eleves.models import Eleve, Classe as ClasseEleve

def tester_export_classement():
    """Tester la disponibilité des données pour l'export"""
    
    print("="*80)
    print(" "*20 + "TEST EXPORT CLASSEMENT")
    print("="*80)
    
    # Vérifier les classes
    classes = ClasseNote.objects.filter(actif=True)
    print(f"\n📚 Classes disponibles: {classes.count()}")
    
    if classes.exists():
        for classe in classes[:5]:  # Afficher les 5 premières
            print(f"   - {classe.nom} ({classe.annee_scolaire})")
            
            # Vérifier les matières
            matieres = MatiereNote.objects.filter(classe=classe, actif=True)
            print(f"     Matières: {matieres.count()}")
            
            # Vérifier les élèves
            try:
                classe_eleve = ClasseEleve.objects.filter(
                    nom=classe.nom,
                    annee_scolaire=classe.annee_scolaire,
                    ecole=classe.ecole
                ).first()
                
                if classe_eleve:
                    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
                    print(f"     Élèves actifs: {eleves.count()}")
                    
                    # Vérifier les notes mensuelles
                    if matieres.exists() and eleves.exists():
                        matiere = matieres.first()
                        eleve = eleves.first()
                        
                        notes = NoteMensuelle.objects.filter(
                            eleve=eleve,
                            matiere=matiere,
                            annee_scolaire=classe.annee_scolaire
                        )
                        print(f"     Notes mensuelles (exemple): {notes.count()}")
                        
                        if notes.exists():
                            note = notes.first()
                            print(f"     ✅ Exemple: {eleve.nom} {eleve.prenom} - {matiere.nom} - {note.get_mois_display()}: {note.note}/20")
                else:
                    print(f"     ⚠️  Classe élève non trouvée")
            except Exception as e:
                print(f"     ❌ Erreur: {str(e)}")
            
            print()
    else:
        print("   ⚠️  Aucune classe trouvée")
    
    # Vérifier l'URL
    print("\n🔗 URL d'export:")
    print("   /notes/exporter-classement/")
    
    # Vérifier le module
    print("\n📦 Module d'export:")
    try:
        from notes.export_classement import exporter_classement_classe
        print("   ✅ Module importé avec succès")
        print(f"   Fonction: {exporter_classement_classe.__name__}")
    except ImportError as e:
        print(f"   ❌ Erreur d'import: {str(e)}")
    
    # Vérifier openpyxl
    print("\n📊 Dépendance openpyxl:")
    try:
        import openpyxl
        print(f"   ✅ openpyxl version {openpyxl.__version__}")
    except ImportError:
        print("   ❌ openpyxl non installé")
        print("   Installation: pip install openpyxl")
    
    print("\n" + "="*80)
    print(" "*25 + "✅ TEST TERMINÉ")
    print("="*80)
    
    # Instructions
    print("\n📋 INSTRUCTIONS D'UTILISATION:")
    print("   1. Accéder à: http://127.0.0.1:8000/notes/consulter/")
    print("   2. Sélectionner une classe")
    print("   3. (Optionnel) Filtrer par matière/période")
    print("   4. Cliquer sur 'Exporter Classement' (bouton jaune 🏆)")
    print("   5. Choisir 'Classement Général' ou 'Par Matière'")
    print("   6. Le fichier Excel sera téléchargé automatiquement")
    print("\n" + "="*80)

if __name__ == "__main__":
    tester_export_classement()
