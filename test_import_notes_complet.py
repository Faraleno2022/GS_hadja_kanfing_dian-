#!/usr/bin/env python
"""
Script de test complet pour la fonctionnalité d'importation de notes
Date: 15 novembre 2024
"""

import os
import sys
import django
import pandas as pd
from decimal import Decimal
from io import BytesIO
import tempfile

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from notes.import_notes import (
    ImportNotesValidator,
    ImportNotesProcessor,
    ImportNotesError,
    lire_fichier_import,
    generer_template_excel
)
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe as ClasseEleve, Ecole

User = get_user_model()

class TestImportNotes:
    """Tests complets pour l'importation de notes"""
    
    def __init__(self):
        self.tests_reussis = 0
        self.tests_echoues = 0
        self.resultats = []
        
    def afficher_titre(self, titre):
        """Affiche un titre de section"""
        print("\n" + "=" * 60)
        print(f"  {titre}")
        print("=" * 60)
        
    def test_ok(self, description):
        """Marque un test comme réussi"""
        self.tests_reussis += 1
        self.resultats.append(f"✅ {description}")
        print(f"✅ {description}")
        
    def test_echec(self, description, erreur=None):
        """Marque un test comme échoué"""
        self.tests_echoues += 1
        msg = f"❌ {description}"
        if erreur:
            msg += f" - Erreur: {erreur}"
        self.resultats.append(msg)
        print(msg)
        
    def preparer_donnees_test(self):
        """Prépare les données de test"""
        self.afficher_titre("PRÉPARATION DES DONNÉES")
        
        try:
            # Créer ou récupérer l'école
            self.ecole, _ = Ecole.objects.get_or_create(
                nom="École Test Import",
                defaults={
                    'adresse': 'Conakry',
                    'telephone': '622000000',
                    'email': 'test@ecole.gn'
                }
            )
            self.test_ok("École créée/récupérée")
            
            # Définir l'année scolaire
            self.annee_scolaire = "2024-2025"
            self.test_ok("Année scolaire définie")
            
            # Créer un utilisateur test
            self.user, _ = User.objects.get_or_create(
                username="test_import",
                defaults={
                    'email': 'test@import.com',
                    'first_name': 'Test',
                    'last_name': 'Import'
                }
            )
            self.test_ok("Utilisateur test créé/récupéré")
            
            # Créer une classe d'élèves
            self.classe_eleve, _ = ClasseEleve.objects.get_or_create(
                nom="6ème A Test",
                ecole=self.ecole,
                annee_scolaire=self.annee_scolaire,
                defaults={
                    'niveau': 'PRIMAIRE',
                    'capacite_max': 35
                }
            )
            self.test_ok("Classe d'élèves créée/récupérée")
            
            # Créer une classe de notes
            self.classe_note, _ = ClasseNote.objects.get_or_create(
                nom="6ème A Test",
                niveau='6EME',
                annee_scolaire="2024-2025",
                ecole=self.ecole,
                defaults={
                    'actif': True,
                    'cree_par': self.user
                }
            )
            self.test_ok("Classe de notes créée/récupérée")
            
            # Créer une matière
            self.matiere, _ = MatiereNote.objects.get_or_create(
                nom="Mathématiques Test",
                code="MATH-TEST",
                classe=self.classe_note,
                defaults={
                    'coefficient': 3,
                    'actif': True,
                    'cree_par': self.user
                }
            )
            self.test_ok("Matière créée/récupérée")
            
            # Créer un responsable test
            from eleves.models import Responsable
            self.responsable, _ = Responsable.objects.get_or_create(
                telephone="600000000",
                defaults={
                    'nom': 'ResponsableTest',
                    'prenom': 'Parent',
                    'adresse': 'Conakry'
                }
            )
            
            # Créer des élèves tests
            self.eleves = []
            for i in range(1, 6):
                eleve, _ = Eleve.objects.get_or_create(
                    matricule=f"TEST-{i:03d}",
                    defaults={
                        'prenom': f'Élève{i}',
                        'nom': f'TEST{i}',
                        'date_naissance': '2010-01-01',
                        'lieu_naissance': 'Conakry',
                        'sexe': 'M' if i % 2 == 0 else 'F',
                        'classe': self.classe_eleve,
                        'date_inscription': '2024-09-01',
                        'responsable_principal': self.responsable,
                        'statut': 'ACTIF'
                    }
                )
                self.eleves.append(eleve)
            self.test_ok(f"{len(self.eleves)} élèves créés/récupérés")
            
            # Créer une évaluation
            self.evaluation, _ = Evaluation.objects.get_or_create(
                titre="Devoir Test Import",
                matiere=self.matiere,
                defaults={
                    'type_evaluation': 'DEVOIR',
                    'periode': 'NOVEMBRE',
                    'coefficient': 1,
                    'date_evaluation': '2024-11-15',
                    'cree_par': self.user
                }
            )
            self.test_ok("Évaluation créée/récupérée")
            
        except Exception as e:
            self.test_echec("Erreur lors de la préparation des données", str(e))
            
    def test_lecture_fichier_csv(self):
        """Test de lecture d'un fichier CSV"""
        self.afficher_titre("TEST LECTURE FICHIER CSV")
        
        try:
            # Créer un fichier CSV temporaire
            data = {
                'Matricule': ['TEST-001', 'TEST-002', 'TEST-003'],
                'Prénom': ['Mamadou', 'Fatoumata', 'Ibrahim'],
                'Nom': ['DIALLO', 'BAH', 'CAMARA'],
                'Note': [15.5, 18, 12.25],
                'Absent': ['NON', 'NON', 'NON']
            }
            df_test = pd.DataFrame(data)
            
            # Sauvegarder en CSV
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df_test.to_csv(f, index=False)
                csv_path = f.name
            
            # Lire le fichier
            with open(csv_path, 'r') as f:
                df_lu = pd.read_csv(f)
            
            # Vérifications
            if len(df_lu) == 3:
                self.test_ok(f"Lecture CSV réussie - {len(df_lu)} lignes lues")
            else:
                self.test_echec(f"Nombre de lignes incorrect: {len(df_lu)} au lieu de 3")
                
            if list(df_lu.columns) == ['Matricule', 'Prénom', 'Nom', 'Note', 'Absent']:
                self.test_ok("Colonnes CSV correctement lues")
            else:
                self.test_echec(f"Colonnes incorrectes: {list(df_lu.columns)}")
                
            # Nettoyer
            os.unlink(csv_path)
            
        except Exception as e:
            self.test_echec("Erreur lecture CSV", str(e))
            
    def test_lecture_fichier_excel(self):
        """Test de lecture d'un fichier Excel"""
        self.afficher_titre("TEST LECTURE FICHIER EXCEL")
        
        try:
            # Créer un fichier Excel temporaire
            data = {
                'Matricule': ['TEST-001', 'TEST-002', 'TEST-003', 'TEST-004', 'TEST-005'],
                'Prénom': ['Ali', 'Binta', 'Moussa', 'Aissatou', 'Sekou'],
                'Nom': ['KEITA', 'SOW', 'TOURE', 'FOFANA', 'CONDE'],
                'Note': [14, 16.75, '', 19, 13.5],
                'Absent': ['NON', 'NON', 'OUI', 'NON', 'NON']
            }
            df_test = pd.DataFrame(data)
            
            # Sauvegarder en Excel
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
                df_test.to_excel(f.name, index=False, engine='openpyxl')
                excel_path = f.name
            
            # Lire le fichier
            df_lu = lire_fichier_import(excel_path)
            
            # Vérifications
            if len(df_lu) == 5:
                self.test_ok(f"Lecture Excel réussie - {len(df_lu)} lignes lues")
            else:
                self.test_echec(f"Nombre de lignes incorrect: {len(df_lu)} au lieu de 5")
                
            # Vérifier gestion des absents
            ligne_absent = df_lu.iloc[2]
            if ligne_absent['Absent'].upper() == 'OUI':
                self.test_ok("Gestion des absents dans Excel OK")
            else:
                self.test_echec("Problème avec la gestion des absents")
                
            # Nettoyer
            os.unlink(excel_path)
            
        except Exception as e:
            self.test_echec("Erreur lecture Excel", str(e))
            
    def test_validation_donnees(self):
        """Test de validation des données"""
        self.afficher_titre("TEST VALIDATION DES DONNÉES")
        
        try:
            # Test 1: Données valides
            data_valide = pd.DataFrame({
                'Matricule': ['TEST-001', 'TEST-002'],
                'Prénom': ['Test1', 'Test2'],
                'Nom': ['NOM1', 'NOM2'],
                'Note': [15, 18.5],
                'Absent': ['NON', 'NON']
            })
            
            validator = ImportNotesValidator(
                data_valide,
                classe_id=self.classe_note.id,
                matiere_id=self.matiere.id,
                type_import='MENSUELLE'
            )
            
            if validator.valider():
                self.test_ok("Validation de données correctes")
            else:
                self.test_echec("Données valides rejetées")
                
            # Test 2: Note invalide (> 20)
            data_invalide = pd.DataFrame({
                'Matricule': ['TEST-001'],
                'Prénom': ['Test'],
                'Nom': ['NOM'],
                'Note': [25],  # Note invalide
                'Absent': ['NON']
            })
            
            validator_invalide = ImportNotesValidator(
                data_invalide,
                classe_id=self.classe_note.id,
                matiere_id=self.matiere.id,
                type_import='MENSUELLE'
            )
            
            validator_invalide.valider()
            if len(validator_invalide.erreurs) > 0:
                self.test_ok("Détection de note invalide (>20)")
            else:
                self.test_echec("Note invalide non détectée")
                
            # Test 3: Matricule manquant
            data_sans_matricule = pd.DataFrame({
                'Matricule': [''],  # Matricule vide
                'Prénom': ['Test'],
                'Nom': ['NOM'],
                'Note': [15],
                'Absent': ['NON']
            })
            
            validator_sans_mat = ImportNotesValidator(
                data_sans_matricule,
                classe_id=self.classe_note.id,
                matiere_id=self.matiere.id,
                type_import='MENSUELLE'
            )
            
            validator_sans_mat.valider()
            if len(validator_sans_mat.erreurs) > 0:
                self.test_ok("Détection de matricule manquant")
            else:
                self.test_echec("Matricule manquant non détecté")
                
        except Exception as e:
            self.test_echec("Erreur validation", str(e))
            
    def test_import_notes_mensuelles(self):
        """Test d'importation de notes mensuelles"""
        self.afficher_titre("TEST IMPORT NOTES MENSUELLES")
        
        try:
            # Préparer les données
            data = pd.DataFrame({
                'Matricule': [e.matricule for e in self.eleves],
                'Prénom': [e.prenom for e in self.eleves],
                'Nom': [e.nom for e in self.eleves],
                'Note': [15.5, 18, 12, 14.75, 16],
                'Absent': ['NON', 'NON', 'OUI', 'NON', 'NON']
            })
            
            # Importer
            processor = ImportNotesProcessor(
                data,
                classe_id=self.classe_note.id,
                matiere_id=self.matiere.id,
                periode='NOVEMBRE',
                annee_scolaire='2024-2025',
                type_import='MENSUELLE',
                user=self.user
            )
            
            stats = processor.importer()
            
            # Vérifications
            if stats['total'] == 5:
                self.test_ok(f"Import mensuel: {stats['total']} notes traitées")
            else:
                self.test_echec(f"Nombre incorrect: {stats['total']}")
                
            if stats['absents'] == 1:
                self.test_ok("Gestion des absents OK")
            else:
                self.test_echec(f"Absents incorrects: {stats['absents']}")
                
            # Vérifier en base
            notes_db = NoteMensuelle.objects.filter(
                matiere=self.matiere,
                mois='NOVEMBRE',
                annee_scolaire='2024-2025'
            ).count()
            
            if notes_db >= 4:  # Au moins 4 notes (5 - 1 absent possible)
                self.test_ok(f"Notes mensuelles en base: {notes_db}")
            else:
                self.test_echec(f"Notes en base insuffisantes: {notes_db}")
                
        except Exception as e:
            self.test_echec("Erreur import mensuel", str(e))
            
    def test_import_notes_composition(self):
        """Test d'importation de notes de composition"""
        self.afficher_titre("TEST IMPORT NOTES COMPOSITION")
        
        try:
            # Préparer les données
            data = pd.DataFrame({
                'Matricule': [self.eleves[0].matricule, self.eleves[1].matricule],
                'Prénom': [self.eleves[0].prenom, self.eleves[1].prenom],
                'Nom': [self.eleves[0].nom, self.eleves[1].nom],
                'Note': [17.5, 19],
                'Absent': ['NON', 'NON']
            })
            
            # Importer
            processor = ImportNotesProcessor(
                data,
                classe_id=self.classe_note.id,
                matiere_id=self.matiere.id,
                periode='TRIMESTRE_1',
                annee_scolaire='2024-2025',
                type_import='COMPOSITION',
                user=self.user
            )
            
            stats = processor.importer()
            
            if stats['total'] == 2:
                self.test_ok(f"Import composition: {stats['total']} notes traitées")
            else:
                self.test_echec(f"Nombre incorrect: {stats['total']}")
                
            # Vérifier en base
            notes_db = CompositionNote.objects.filter(
                matiere=self.matiere,
                periode='TRIMESTRE_1',
                annee_scolaire='2024-2025'
            ).count()
            
            if notes_db >= 2:
                self.test_ok(f"Notes composition en base: {notes_db}")
            else:
                self.test_echec(f"Notes composition insuffisantes: {notes_db}")
                
        except Exception as e:
            self.test_echec("Erreur import composition", str(e))
            
    def test_generation_template(self):
        """Test de génération de template Excel"""
        self.afficher_titre("TEST GÉNÉRATION TEMPLATE")
        
        try:
            # Générer un template
            df_template = generer_template_excel(
                classe_id=self.classe_note.id,
                matiere_id=self.matiere.id,
                type_import='MENSUELLE'
            )
            
            # Vérifications
            colonnes_attendues = ['Matricule', 'Prénom', 'Nom', 'Note', 'Absent']
            if list(df_template.columns) == colonnes_attendues:
                self.test_ok("Template avec colonnes correctes")
            else:
                self.test_echec(f"Colonnes incorrectes: {list(df_template.columns)}")
                
            # Vérifier que les colonnes 'Absent' sont pré-remplies
            if all(df_template['Absent'] == 'NON'):
                self.test_ok("Valeurs par défaut 'Absent' = NON")
            else:
                self.test_echec("Valeurs par défaut incorrectes")
                
            # Sauvegarder le template en Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_template.to_excel(writer, index=False, sheet_name='Notes')
            
            output.seek(0)
            if len(output.getvalue()) > 0:
                self.test_ok("Template Excel généré avec succès")
            else:
                self.test_echec("Template vide")
                
        except Exception as e:
            self.test_echec("Erreur génération template", str(e))
            
    def nettoyer_donnees_test(self):
        """Nettoie les données de test"""
        self.afficher_titre("NETTOYAGE")
        
        try:
            # Supprimer les notes créées
            NoteMensuelle.objects.filter(matiere=self.matiere).delete()
            CompositionNote.objects.filter(matiere=self.matiere).delete()
            NoteEleve.objects.filter(evaluation=self.evaluation).delete()
            
            # Supprimer l'évaluation
            self.evaluation.delete()
            
            # Supprimer la matière
            self.matiere.delete()
            
            # Supprimer les élèves test
            Eleve.objects.filter(matricule__startswith='TEST-').delete()
            
            # Supprimer les classes
            self.classe_note.delete()
            self.classe_eleve.delete()
            
            self.test_ok("Données de test nettoyées")
            
        except Exception as e:
            self.test_echec("Erreur nettoyage", str(e))
            
    def afficher_resume(self):
        """Affiche le résumé des tests"""
        self.afficher_titre("RÉSUMÉ DES TESTS")
        
        total = self.tests_reussis + self.tests_echoues
        
        print(f"\n📊 Tests exécutés: {total}")
        print(f"✅ Réussis: {self.tests_reussis}")
        print(f"❌ Échoués: {self.tests_echoues}")
        
        if self.tests_echoues == 0:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
        else:
            print(f"\n⚠️ {self.tests_echoues} test(s) ont échoué")
            
        print("\n" + "=" * 60)
        print("  DÉTAIL DES RÉSULTATS")
        print("=" * 60)
        for resultat in self.resultats:
            print(resultat)
            
    def executer_tous_les_tests(self):
        """Exécute tous les tests"""
        print("\n" + "🚀" * 30)
        print("  TESTS COMPLETS - IMPORTATION DE NOTES")
        print("🚀" * 30)
        
        # Préparer les données
        self.preparer_donnees_test()
        
        # Exécuter les tests
        self.test_lecture_fichier_csv()
        self.test_lecture_fichier_excel()
        self.test_validation_donnees()
        self.test_import_notes_mensuelles()
        self.test_import_notes_composition()
        self.test_generation_template()
        
        # Nettoyer
        self.nettoyer_donnees_test()
        
        # Afficher le résumé
        self.afficher_resume()


if __name__ == "__main__":
    print("Démarrage des tests d'importation de notes...")
    print("=" * 60)
    
    # Vérifier les dépendances
    try:
        import pandas
        print("✅ pandas installé - Version:", pandas.__version__)
    except ImportError:
        print("❌ pandas NON installé - Installation requise: pip install pandas")
        sys.exit(1)
        
    try:
        import openpyxl
        print("✅ openpyxl installé - Version:", openpyxl.__version__)
    except ImportError:
        print("❌ openpyxl NON installé - Installation requise: pip install openpyxl")
        sys.exit(1)
    
    # Exécuter les tests
    testeur = TestImportNotes()
    testeur.executer_tous_les_tests()
