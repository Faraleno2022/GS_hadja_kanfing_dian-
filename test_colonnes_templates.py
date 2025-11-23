#!/usr/bin/env python
"""
Test de cohérence des colonnes entre templates et import
Vérifie que les templates générés ont exactement les colonnes attendues
"""
import os
import sys
import django
import pandas as pd
from io import BytesIO

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.import_notes import generer_template_excel, ImportNotesValidator, ImportNotesError
from eleves.import_eleves import generer_template_eleves, ImportElevesValidator, ImportElevesError
from notes.models import ClasseNote, MatiereNote
from eleves.models import Classe


class TestColonnesTemplates:
    """Teste la cohérence des colonnes"""
    
    def __init__(self):
        self.resultats = {}
        
    def test_colonnes_notes(self):
        """Teste les colonnes du template notes"""
        print("\n" + "="*60)
        print("📝 TEST 1 : COLONNES TEMPLATE NOTES")
        print("="*60)
        
        try:
            # Récupérer une classe et matière
            classe_note = ClasseNote.objects.first()
            matiere = MatiereNote.objects.filter(classe=classe_note).first()
            
            if not classe_note or not matiere:
                print("❌ Aucune classe ou matière trouvée")
                return False
            
            print(f"\n📚 Classe : {classe_note.nom}")
            print(f"📖 Matière : {matiere.nom}")
            
            # Générer le template
            print(f"\n🔄 Génération du template...")
            df_template = generer_template_excel(
                classe_id=classe_note.id,
                matiere_id=matiere.id,
                type_import='MENSUELLE'
            )
            
            # Colonnes du template
            colonnes_template = list(df_template.columns)
            print(f"\n📋 Colonnes dans le template :")
            for col in colonnes_template:
                print(f"   ✓ {col}")
            
            # Colonnes attendues par le validateur
            colonnes_attendues = ['Matricule', 'Prénom', 'Nom', 'Note', 'Absent']
            print(f"\n📋 Colonnes attendues par le validateur :")
            for col in colonnes_attendues:
                print(f"   ✓ {col}")
            
            # Vérifier la correspondance
            colonnes_manquantes = set(colonnes_attendues) - set(colonnes_template)
            colonnes_extra = set(colonnes_template) - set(colonnes_attendues)
            
            if colonnes_manquantes:
                print(f"\n❌ COLONNES MANQUANTES dans le template :")
                for col in colonnes_manquantes:
                    print(f"   ✗ {col}")
                return False
            
            if colonnes_extra:
                print(f"\n⚠️  COLONNES EN TROP dans le template :")
                for col in colonnes_extra:
                    print(f"   • {col}")
            
            # Tester avec le validateur
            print(f"\n🔍 Validation avec le validateur...")
            validator = ImportNotesValidator(
                df=df_template,
                classe_id=classe_note.id,
                matiere_id=matiere.id,
                type_import='MENSUELLE'
            )
            
            try:
                validator.valider()
                print(f"   ✅ Validation réussie")
            except ImportNotesError as e:
                print(f"   ❌ Erreur de validation : {e}")
                return False
            
            print(f"\n✅ TOUTES LES COLONNES CORRESPONDENT PARFAITEMENT")
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_colonnes_eleves(self):
        """Teste les colonnes du template élèves"""
        print("\n" + "="*60)
        print("👥 TEST 2 : COLONNES TEMPLATE ÉLÈVES")
        print("="*60)
        
        try:
            # Récupérer une classe
            classe = Classe.objects.first()
            
            if not classe:
                print("❌ Aucune classe trouvée")
                return False
            
            print(f"\n📚 Classe : {classe.nom}")
            
            # Générer le template
            print(f"\n🔄 Génération du template...")
            df_template = generer_template_eleves(classe_id=classe.id)
            
            # Colonnes du template
            colonnes_template = list(df_template.columns)
            print(f"\n📋 Colonnes dans le template :")
            for col in colonnes_template:
                print(f"   ✓ {col}")
            
            # Colonnes obligatoires attendues par le validateur
            colonnes_obligatoires = [
                'Prénom', 'Nom', 'Sexe', 'Date de Naissance', 
                'Lieu de Naissance', 'Nom du Père/Tuteur', 
                'Prénom du Père/Tuteur', 'Téléphone Principal', 'Adresse'
            ]
            
            # Colonnes optionnelles
            colonnes_optionnelles = [
                'Matricule', 'Nom de la Mère', 'Prénom de la Mère', 
                'Téléphone Secondaire', 'Email'
            ]
            
            print(f"\n📋 Colonnes OBLIGATOIRES attendues :")
            for col in colonnes_obligatoires:
                present = "✓" if col in colonnes_template else "✗"
                print(f"   {present} {col}")
            
            print(f"\n📋 Colonnes OPTIONNELLES attendues :")
            for col in colonnes_optionnelles:
                present = "✓" if col in colonnes_template else "✗"
                print(f"   {present} {col}")
            
            # Vérifier la correspondance
            colonnes_manquantes = set(colonnes_obligatoires) - set(colonnes_template)
            colonnes_extra = set(colonnes_template) - set(colonnes_obligatoires + colonnes_optionnelles)
            
            if colonnes_manquantes:
                print(f"\n❌ COLONNES OBLIGATOIRES MANQUANTES dans le template :")
                for col in colonnes_manquantes:
                    print(f"   ✗ {col}")
                return False
            
            if colonnes_extra:
                print(f"\n⚠️  COLONNES INCONNUES dans le template :")
                for col in colonnes_extra:
                    print(f"   • {col}")
            
            # Tester avec le validateur
            print(f"\n🔍 Validation avec le validateur...")
            validator = ImportElevesValidator(
                df=df_template,
                classe_id=classe.id
            )
            
            try:
                validator.valider()
                print(f"   ✅ Validation réussie")
            except ImportElevesError as e:
                print(f"   ❌ Erreur de validation : {e}")
                return False
            
            print(f"\n✅ TOUTES LES COLONNES CORRESPONDENT PARFAITEMENT")
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_import_avec_template(self):
        """Teste l'import réel avec un template généré"""
        print("\n" + "="*60)
        print("🔄 TEST 3 : IMPORT RÉEL AVEC TEMPLATE GÉNÉRÉ")
        print("="*60)
        
        try:
            from notes.import_notes import ImportNotesProcessor, lire_fichier_import
            from eleves.models import Eleve
            
            # Récupérer une classe et matière
            classe_note = ClasseNote.objects.first()
            matiere = MatiereNote.objects.filter(classe=classe_note).first()
            
            if not classe_note or not matiere:
                print("❌ Aucune classe ou matière trouvée")
                return False
            
            # Générer le template
            print(f"\n🔄 Génération du template pour {classe_note.nom} - {matiere.nom}...")
            df_template = generer_template_excel(
                classe_id=classe_note.id,
                matiere_id=matiere.id,
                type_import='MENSUELLE'
            )
            
            print(f"   ✓ Template généré avec {len(df_template)} ligne(s)")
            
            # Vérifier qu'il y a des élèves
            if len(df_template) == 0 or 'ERREUR' in str(df_template.iloc[0]['Matricule']):
                print(f"   ⚠️  Pas d'élèves dans la classe")
                return True  # Ce n'est pas une erreur de colonnes
            
            # Remplir quelques notes de test
            nb_lignes = min(5, len(df_template))
            df_test = df_template.head(nb_lignes).copy()
            df_test['Note'] = [15.0, 16.0, 14.0, 17.0, 13.0][:nb_lignes]
            df_test['Absent'] = ['NON'] * nb_lignes
            
            print(f"\n📝 Préparation de {nb_lignes} notes de test...")
            print(f"\n📋 Aperçu des données :")
            print(df_test[['Matricule', 'Prénom', 'Nom', 'Note', 'Absent']].to_string(index=False))
            
            # Tenter l'import
            print(f"\n🔄 Tentative d'import...")
            processor = ImportNotesProcessor(
                df=df_test,
                classe_id=classe_note.id,
                matiere_id=matiere.id,
                periode='FEVRIER',
                annee_scolaire='2024-2025',
                type_import='MENSUELLE'
            )
            
            stats = processor.importer()
            
            print(f"\n📊 Résultats de l'import :")
            print(f"   - Total : {stats['total']}")
            print(f"   - Importées : {stats['importees']}")
            print(f"   - Modifiées : {stats['modifiees']}")
            print(f"   - Erreurs : {stats['erreurs']}")
            
            if stats['erreurs'] == 0:
                print(f"\n✅ IMPORT RÉUSSI AVEC LE TEMPLATE GÉNÉRÉ")
                
                # Nettoyer les données de test
                from notes.models import NoteMensuelle
                NoteMensuelle.objects.filter(
                    matiere=matiere,
                    mois='FEVRIER',
                    annee_scolaire='2024-2025'
                ).delete()
                print(f"   🧹 Données de test nettoyées")
                
                return True
            else:
                print(f"\n❌ {stats['erreurs']} ERREUR(S) LORS DE L'IMPORT")
                return False
            
        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def executer(self):
        """Execute tous les tests"""
        print("\n" + "="*70)
        print("🔬 TEST DE COHÉRENCE DES COLONNES TEMPLATES")
        print("="*70)
        
        # Exécuter les tests
        self.resultats['Colonnes template notes'] = self.test_colonnes_notes()
        self.resultats['Colonnes template élèves'] = self.test_colonnes_eleves()
        self.resultats['Import avec template'] = self.test_import_avec_template()
        
        # Rapport final
        self.generer_rapport()
    
    def generer_rapport(self):
        """Génère le rapport final"""
        print("\n" + "="*70)
        print("📊 RAPPORT FINAL")
        print("="*70)
        
        total_tests = len(self.resultats)
        tests_reussis = sum(1 for r in self.resultats.values() if r)
        
        print(f"\n✅ Tests réussis : {tests_reussis}/{total_tests}")
        
        print(f"\n📋 Détails :")
        for nom_test, resultat in self.resultats.items():
            statut = "✅ RÉUSSI" if resultat else "❌ ÉCHOUÉ"
            print(f"   {statut} - {nom_test}")
        
        if tests_reussis == total_tests:
            print(f"\n🎉 TOUS LES TESTS ONT RÉUSSI !")
            print(f"\n✅ Les colonnes des templates correspondent parfaitement")
            print(f"✅ Les imports fonctionnent avec les templates générés")
            print(f"✅ Aucun problème de colonnes détecté")
        else:
            print(f"\n⚠️  {total_tests - tests_reussis} test(s) ont échoué")
            print(f"\n❌ PROBLÈME DE COLONNES DÉTECTÉ")
            print(f"\nℹ️  Actions requises :")
            print(f"   1. Vérifier les noms exacts des colonnes")
            print(f"   2. Corriger generer_template_excel() ou generer_template_eleves()")
            print(f"   3. Assurer cohérence avec ImportNotesValidator/ImportElevesValidator")


if __name__ == "__main__":
    tester = TestColonnesTemplates()
    tester.executer()
    
    print("\n" + "="*70 + "\n")
