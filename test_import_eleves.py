#!/usr/bin/env python
"""
Test de la fonctionnalité d'importation d'élèves
"""
import os
import sys
import django
import pandas as pd
import tempfile
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe, Ecole, Responsable
from eleves.import_eleves import (
    generer_matricule,
    lire_fichier_eleves,
    generer_template_eleves,
    ImportElevesValidator,
    ImportElevesProcessor,
    ImportElevesError
)

class TestImportEleves:
    """Tests pour l'importation d'élèves"""
    
    def __init__(self):
        self.tests_reussis = 0
        self.tests_echoues = 0
        self.resultats = []
        
    def test_ok(self, message):
        self.tests_reussis += 1
        self.resultats.append(f"✅ {message}")
        print(f"✅ {message}")
        
    def test_echec(self, message):
        self.tests_echoues += 1
        self.resultats.append(f"❌ {message}")
        print(f"❌ {message}")
        
    def preparer_donnees(self):
        """Prépare les données de test"""
        print("\n" + "="*60)
        print("  PRÉPARATION DES DONNÉES")
        print("="*60)
        
        try:
            # Créer une école test
            self.ecole, _ = Ecole.objects.get_or_create(
                nom="École Test Import Élèves",
                defaults={
                    'adresse': 'Conakry Test',
                    'telephone': '622111111',
                    'email': 'test.eleves@ecole.gn'
                }
            )
            self.test_ok("École test créée")
            
            # Créer une classe test
            self.classe, _ = Classe.objects.get_or_create(
                nom="6ème Test Import",
                ecole=self.ecole,
                annee_scolaire="2024-2025",
                defaults={
                    'niveau': 'PRIMAIRE',
                    'capacite_max': 40,
                    'code_matricule': '6T'
                }
            )
            self.test_ok("Classe test créée")
            
            return True
            
        except Exception as e:
            self.test_echec(f"Erreur préparation: {e}")
            return False
            
    def test_generation_matricule(self):
        """Test la génération automatique de matricules"""
        print("\n" + "="*60)
        print("  TEST GÉNÉRATION MATRICULE")
        print("="*60)
        
        try:
            # Test génération simple
            matricule1 = generer_matricule(self.classe, 1, "2024-2025")
            if "6T-2024-001" in matricule1:
                self.test_ok(f"Génération matricule: {matricule1}")
            else:
                self.test_echec(f"Format matricule incorrect: {matricule1}")
            
            # Test incrémentation
            matricule2 = generer_matricule(self.classe, 2, "2024-2025")
            if "6T-2024-002" in matricule2:
                self.test_ok(f"Incrémentation OK: {matricule2}")
            else:
                self.test_echec(f"Incrémentation incorrecte: {matricule2}")
            
            # Test unicité
            matricule3 = generer_matricule(self.classe, 1, "2024-2025")
            if matricule3 != matricule1:
                self.test_ok(f"Unicité assurée: {matricule3} != {matricule1}")
            else:
                self.test_echec("Matricule dupliqué généré")
                
        except Exception as e:
            self.test_echec(f"Erreur génération matricule: {e}")
            
    def test_generation_template(self):
        """Test la génération du template Excel"""
        print("\n" + "="*60)
        print("  TEST GÉNÉRATION TEMPLATE")
        print("="*60)
        
        try:
            # Générer le template
            df = generer_template_eleves(self.classe.id)
            
            # Vérifier les colonnes
            colonnes_attendues = [
                'Matricule', 'Prénom', 'Nom', 'Sexe', 'Date de Naissance',
                'Lieu de Naissance', 'Nom du Père/Tuteur', 'Prénom du Père/Tuteur',
                'Téléphone Principal', 'Adresse'
            ]
            
            colonnes_manquantes = []
            for col in colonnes_attendues:
                if col not in df.columns:
                    colonnes_manquantes.append(col)
            
            if not colonnes_manquantes:
                self.test_ok(f"Template avec {len(df.columns)} colonnes correctes")
            else:
                self.test_echec(f"Colonnes manquantes: {colonnes_manquantes}")
            
            # Vérifier qu'il y a des exemples
            if len(df) >= 3:
                self.test_ok(f"Template avec {len(df)} lignes d'exemple")
            else:
                self.test_echec(f"Pas assez d'exemples: {len(df)} lignes")
                
        except Exception as e:
            self.test_echec(f"Erreur génération template: {e}")
            
    def test_lecture_fichier(self):
        """Test la lecture de fichiers Excel/CSV"""
        print("\n" + "="*60)
        print("  TEST LECTURE FICHIERS")
        print("="*60)
        
        # Test CSV
        try:
            data = {
                'Matricule': ['', '', ''],
                'Prénom': ['Amadou', 'Binta', 'Moussa'],
                'Nom': ['DIALLO', 'SOW', 'BARRY'],
                'Sexe': ['M', 'F', 'M'],
                'Date de Naissance': ['15/01/2010', '23/05/2010', '10/09/2010'],
                'Lieu de Naissance': ['Conakry', 'Kindia', 'Labé'],
                'Nom du Père/Tuteur': ['DIALLO', 'SOW', 'BARRY'],
                'Prénom du Père/Tuteur': ['Ibrahim', 'Ousmane', 'Sekou'],
                'Téléphone Principal': ['622000001', '622000002', '622000003'],
                'Adresse': ['Ratoma', 'Matoto', 'Dixinn']
            }
            
            df_test = pd.DataFrame(data)
            
            # Sauvegarder en CSV
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df_test.to_csv(f, index=False)
                csv_path = f.name
            
            # Lire le CSV
            with open(csv_path, 'r') as f:
                df_lu = pd.read_csv(f)
            
            if len(df_lu) == 3:
                self.test_ok(f"CSV lu: {len(df_lu)} élèves")
            else:
                self.test_echec(f"Lecture CSV incorrecte: {len(df_lu)} lignes")
            
            os.unlink(csv_path)
            
        except Exception as e:
            self.test_echec(f"Erreur lecture CSV: {e}")
        
        # Test Excel
        try:
            # Sauvegarder en Excel
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                df_test.to_excel(f.name, index=False, engine='openpyxl')
                excel_path = f.name
            
            # Lire l'Excel
            df_excel = lire_fichier_eleves(excel_path)
            
            if len(df_excel) == 3:
                self.test_ok(f"Excel lu: {len(df_excel)} élèves")
            else:
                self.test_echec(f"Lecture Excel incorrecte: {len(df_excel)} lignes")
            
            os.unlink(excel_path)
            
        except Exception as e:
            self.test_echec(f"Erreur lecture Excel: {e}")
            
    def test_validation(self):
        """Test la validation des données"""
        print("\n" + "="*60)
        print("  TEST VALIDATION")
        print("="*60)
        
        # Données valides
        try:
            data_valide = pd.DataFrame({
                'Matricule': [''],
                'Prénom': ['Fatou'],
                'Nom': ['KANTE'],
                'Sexe': ['F'],
                'Date de Naissance': ['15/01/2010'],
                'Lieu de Naissance': ['Conakry'],
                'Nom du Père/Tuteur': ['KANTE'],
                'Prénom du Père/Tuteur': ['Mamadou'],
                'Téléphone Principal': ['622000001'],
                'Adresse': ['Kaloum']
            })
            
            validator = ImportElevesValidator(data_valide, self.classe.id)
            if validator.valider():
                self.test_ok("Données valides acceptées")
            else:
                self.test_echec("Données valides rejetées")
                
        except Exception as e:
            self.test_echec(f"Erreur validation données valides: {e}")
        
        # Données invalides - sexe incorrect
        try:
            data_invalide = pd.DataFrame({
                'Matricule': [''],
                'Prénom': ['Test'],
                'Nom': ['TEST'],
                'Sexe': ['X'],  # Invalide
                'Date de Naissance': ['15/01/2010'],
                'Lieu de Naissance': ['Conakry'],
                'Nom du Père/Tuteur': ['TEST'],
                'Prénom du Père/Tuteur': ['Test'],
                'Téléphone Principal': ['622000001'],
                'Adresse': ['Test']
            })
            
            validator = ImportElevesValidator(data_invalide, self.classe.id)
            validator.valider()
            
            if len(validator.erreurs) > 0:
                self.test_ok("Sexe invalide détecté")
            else:
                self.test_echec("Sexe invalide non détecté")
                
        except Exception as e:
            self.test_echec(f"Erreur validation sexe: {e}")
        
        # Données invalides - téléphone court
        try:
            data_invalide = pd.DataFrame({
                'Matricule': [''],
                'Prénom': ['Test'],
                'Nom': ['TEST'],
                'Sexe': ['M'],
                'Date de Naissance': ['15/01/2010'],
                'Lieu de Naissance': ['Conakry'],
                'Nom du Père/Tuteur': ['TEST'],
                'Prénom du Père/Tuteur': ['Test'],
                'Téléphone Principal': ['123'],  # Trop court
                'Adresse': ['Test']
            })
            
            validator = ImportElevesValidator(data_invalide, self.classe.id)
            validator.valider()
            
            if len(validator.erreurs) > 0:
                self.test_ok("Téléphone invalide détecté")
            else:
                self.test_echec("Téléphone invalide non détecté")
                
        except Exception as e:
            self.test_echec(f"Erreur validation téléphone: {e}")
            
    def test_import_complet(self):
        """Test l'importation complète d'élèves"""
        print("\n" + "="*60)
        print("  TEST IMPORT COMPLET")
        print("="*60)
        
        try:
            # Préparer les données
            data = pd.DataFrame({
                'Matricule': ['', '', 'TEST-MANUEL-001'],
                'Prénom': ['Aminata', 'Boubacar', 'Kadiatou'],
                'Nom': ['TOURE', 'CONDE', 'DIOP'],
                'Sexe': ['F', 'M', 'F'],
                'Date de Naissance': ['12/03/2011', '05/07/2011', '18/11/2011'],
                'Lieu de Naissance': ['Conakry', 'Boké', 'Mamou'],
                'Nom du Père/Tuteur': ['TOURE', 'CONDE', 'DIOP'],
                'Prénom du Père/Tuteur': ['Lansana', 'Alpha', 'Ibrahima'],
                'Téléphone Principal': ['622111111', '622222222', '622333333'],
                'Adresse': ['Cosa', 'Tombolia', 'Madina'],
                'Nom de la Mère': ['CAMARA', 'BARRY', 'SYLLA'],
                'Prénom de la Mère': ['Mariama', 'Hadja', 'Fatoumata']
            })
            
            # Valider
            validator = ImportElevesValidator(data, self.classe.id)
            if not validator.valider():
                self.test_echec(f"Validation échouée: {validator.erreurs}")
                return
            
            # Importer
            processor = ImportElevesProcessor(
                df=data,
                classe_id=self.classe.id,
                generer_matricules=True
            )
            
            stats = processor.importer()
            
            # Vérifier les statistiques
            if stats['total'] == 3:
                self.test_ok(f"Import: {stats['total']} élèves traités")
            else:
                self.test_echec(f"Nombre incorrect: {stats['total']}")
            
            if stats['matricules_generes'] == 2:
                self.test_ok(f"Matricules générés: {stats['matricules_generes']}")
            else:
                self.test_echec(f"Génération incorrecte: {stats['matricules_generes']}")
            
            # Vérifier en base
            eleves = Eleve.objects.filter(classe=self.classe)
            if eleves.count() >= 3:
                self.test_ok(f"Base de données: {eleves.count()} élèves")
                
                # Vérifier les matricules générés
                for eleve in eleves:
                    if eleve.matricule:
                        print(f"   📝 {eleve.prenom} {eleve.nom}: {eleve.matricule}")
            else:
                self.test_echec(f"Élèves manquants: {eleves.count()}")
            
            # Vérifier les responsables
            responsables = Responsable.objects.filter(
                telephone__in=['622111111', '622222222', '622333333']
            )
            if responsables.count() == 3:
                self.test_ok(f"Responsables créés: {responsables.count()}")
            else:
                self.test_echec(f"Responsables manquants: {responsables.count()}")
                
        except Exception as e:
            self.test_echec(f"Erreur import complet: {e}")
            
    def nettoyer(self):
        """Nettoie les données de test"""
        print("\n" + "="*60)
        print("  NETTOYAGE")
        print("="*60)
        
        try:
            # Supprimer les élèves de test
            if hasattr(self, 'classe'):
                Eleve.objects.filter(classe=self.classe).delete()
                
            # Supprimer la classe et l'école
            if hasattr(self, 'classe'):
                self.classe.delete()
            if hasattr(self, 'ecole'):
                self.ecole.delete()
                
            # Supprimer les responsables de test
            Responsable.objects.filter(
                telephone__in=['622111111', '622222222', '622333333']
            ).delete()
            
            self.test_ok("Données de test nettoyées")
            
        except Exception as e:
            self.test_echec(f"Erreur nettoyage: {e}")
            
    def afficher_resume(self):
        """Affiche le résumé des tests"""
        print("\n" + "="*60)
        print("  RÉSUMÉ DES TESTS")
        print("="*60)
        
        total = self.tests_reussis + self.tests_echoues
        print(f"\n📊 Tests exécutés: {total}")
        print(f"✅ Réussis: {self.tests_reussis}")
        print(f"❌ Échoués: {self.tests_echoues}")
        
        if self.tests_echoues == 0:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
        else:
            print(f"\n⚠️ {self.tests_echoues} test(s) ont échoué")
        
        print("\n" + "="*60)
        print("  DÉTAIL DES RÉSULTATS")
        print("="*60)
        for resultat in self.resultats:
            print(resultat)
            
    def executer(self):
        """Exécute tous les tests"""
        print("\n" + "🚀"*30)
        print("  TESTS D'IMPORTATION D'ÉLÈVES")
        print("🚀"*30)
        
        if self.preparer_donnees():
            self.test_generation_matricule()
            self.test_generation_template()
            self.test_lecture_fichier()
            self.test_validation()
            self.test_import_complet()
            self.nettoyer()
        
        self.afficher_resume()


if __name__ == "__main__":
    print("Démarrage des tests d'importation d'élèves...")
    print("="*60)
    
    # Vérifier pandas et openpyxl
    try:
        import pandas
        print(f"✅ pandas installé - Version: {pandas.__version__}")
    except ImportError:
        print("❌ pandas n'est pas installé!")
        print("   Installer avec: pip install pandas")
        sys.exit(1)
    
    try:
        import openpyxl
        print(f"✅ openpyxl installé - Version: {openpyxl.__version__}")
    except ImportError:
        print("❌ openpyxl n'est pas installé!")
        print("   Installer avec: pip install openpyxl")
        sys.exit(1)
    
    # Exécuter les tests
    test = TestImportEleves()
    test.executer()
