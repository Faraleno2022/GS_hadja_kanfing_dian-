#!/usr/bin/env python
"""
Test complet : Import d'élèves et notes + Vérification affichage dans le système
Valide que les données importées sont correctement visibles
"""
import os
import sys
import django
import pandas as pd
from datetime import datetime
from decimal import Decimal

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db import transaction
from eleves.models import Eleve, Classe, Responsable
from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve, NoteMensuelle
from eleves.import_eleves import ImportElevesProcessor
from notes.import_notes import ImportNotesProcessor


class TestImportAffichage:
    """Teste l'import et l'affichage des données"""
    
    def __init__(self):
        self.eleves_importes = []
        self.notes_importees = []
        self.classe_test = None
        self.classe_note_test = None
        self.matiere_test = None
        
    def nettoyer_donnees_test(self):
        """Nettoie les données de test précédentes"""
        print("\n🧹 Nettoyage des données de test précédentes...")
        
        # Supprimer les élèves de test
        count_eleves = Eleve.objects.filter(nom__startswith='TEST_IMPORT').delete()[0]
        # Supprimer les responsables de test
        count_resp = Responsable.objects.filter(nom__startswith='TEST_IMPORT').delete()[0]
        # Supprimer les notes de test (si matricule commence par TEST)
        count_notes = NoteEleve.objects.filter(eleve__matricule__startswith='TEST').delete()[0]
        count_notes_mens = NoteMensuelle.objects.filter(eleve__matricule__startswith='TEST').delete()[0]
        
        print(f"   ✅ {count_eleves} élèves supprimés")
        print(f"   ✅ {count_resp} responsables supprimés")
        print(f"   ✅ {count_notes + count_notes_mens} notes supprimées")
    
    def preparer_classe_test(self):
        """Prépare une classe pour les tests"""
        print("\n📚 Préparation de la classe de test...")
        
        # Utiliser une classe existante ou en créer une
        self.classe_test = Classe.objects.first()
        
        if not self.classe_test:
            print("   ❌ Aucune classe trouvée dans le système!")
            return False
        
        print(f"   ✅ Classe : {self.classe_test.nom} (ID: {self.classe_test.id})")
        
        # Trouver ClasseNote correspondante
        self.classe_note_test = ClasseNote.objects.filter(
            nom__icontains=self.classe_test.nom.split()[0]
        ).first()
        
        if not self.classe_note_test:
            print(f"   ⚠️  Aucune ClasseNote trouvée pour '{self.classe_test.nom}'")
            # Prendre la première ClasseNote disponible
            self.classe_note_test = ClasseNote.objects.first()
        
        if not self.classe_note_test:
            print("   ❌ Aucune ClasseNote trouvée dans le système!")
            return False
        
        print(f"   ✅ ClasseNote : {self.classe_note_test.nom} (ID: {self.classe_note_test.id})")
        
        # Trouver une matière
        self.matiere_test = MatiereNote.objects.filter(classe=self.classe_note_test).first()
        
        if not self.matiere_test:
            print("   ❌ Aucune matière trouvée pour cette ClasseNote!")
            return False
        
        print(f"   ✅ Matière : {self.matiere_test.nom} (ID: {self.matiere_test.id})")
        
        return True
    
    def test_import_eleves(self):
        """Teste l'import d'élèves"""
        print("\n" + "="*60)
        print("👥 TEST 1 : IMPORT D'ÉLÈVES")
        print("="*60)
        
        # Créer un DataFrame avec 5 élèves de test
        nb_eleves = 5
        data = {
            'Matricule': [''] * nb_eleves,  # Génération auto
            'Prénom': [f'TestImport{i}' for i in range(1, nb_eleves+1)],
            'Nom': ['TEST_IMPORT'] * nb_eleves,
            'Sexe': ['M' if i % 2 == 0 else 'F' for i in range(nb_eleves)],
            'Date de Naissance': ['15/01/2010'] * nb_eleves,
            'Lieu de Naissance': ['Conakry'] * nb_eleves,
            'Nom du Père/Tuteur': ['TEST_IMPORT'] * nb_eleves,
            'Prénom du Père/Tuteur': [f'Pere{i}' for i in range(1, nb_eleves+1)],
            'Téléphone Principal': [f'62290{i:04d}' for i in range(1, nb_eleves+1)],
            'Adresse': ['Ratoma Test'] * nb_eleves,
            'Nom de la Mère': [''] * nb_eleves,
            'Prénom de la Mère': [''] * nb_eleves,
            'Téléphone Secondaire': [''] * nb_eleves,
            'Email': [''] * nb_eleves
        }
        
        df = pd.DataFrame(data)
        
        print(f"\n📝 Import de {nb_eleves} élèves de test...")
        
        # Créer le processeur
        processor = ImportElevesProcessor(
            df=df,
            classe_id=self.classe_test.id,
            generer_matricules=True
        )
        
        # Importer
        stats = processor.importer()
        
        print(f"\n📊 Résultats de l'import :")
        print(f"   - Total traité : {stats['total']}")
        print(f"   - Élèves créés : {stats['crees']}")
        print(f"   - Matricules générés : {stats['matricules_generes']}")
        print(f"   - Erreurs : {stats['erreurs']}")
        
        # Vérifier que les élèves sont bien dans la base
        self.eleves_importes = list(Eleve.objects.filter(
            nom='TEST_IMPORT',
            classe=self.classe_test
        ).order_by('matricule'))
        
        print(f"\n✅ Vérification dans la base de données :")
        print(f"   - Élèves trouvés : {len(self.eleves_importes)}")
        
        if len(self.eleves_importes) == nb_eleves:
            print(f"   ✅ TOUS LES ÉLÈVES SONT BIEN ENREGISTRÉS")
            
            print(f"\n📋 Liste des élèves importés :")
            for eleve in self.eleves_importes:
                print(f"      • {eleve.matricule} - {eleve.prenom} {eleve.nom}")
                print(f"        Classe: {eleve.classe.nom}")
                print(f"        Responsable: {eleve.responsable_principal.prenom if eleve.responsable_principal else 'N/A'}")
        else:
            print(f"   ❌ ERREUR : {nb_eleves} attendus, {len(self.eleves_importes)} trouvés")
            return False
        
        return True
    
    def test_import_notes(self):
        """Teste l'import de notes"""
        print("\n" + "="*60)
        print("📝 TEST 2 : IMPORT DE NOTES")
        print("="*60)
        
        if not self.eleves_importes:
            print("❌ Pas d'élèves importés pour tester les notes")
            return False
        
        # Créer un DataFrame avec les notes
        nb_notes = len(self.eleves_importes)
        data = {
            'Matricule': [e.matricule for e in self.eleves_importes],
            'Prénom': [e.prenom for e in self.eleves_importes],
            'Nom': [e.nom for e in self.eleves_importes],
            'Note': [float(12 + i) for i in range(nb_notes)],
            'Absent': ['NON'] * nb_notes
        }
        
        df = pd.DataFrame(data)
        
        print(f"\n📝 Import de {nb_notes} notes pour la matière {self.matiere_test.nom}...")
        
        # Créer le processeur
        processor = ImportNotesProcessor(
            df=df,
            classe_id=self.classe_note_test.id,
            matiere_id=self.matiere_test.id,
            periode='JANVIER',
            annee_scolaire='2024-2025',
            type_import='MENSUELLE'
        )
        
        # Importer
        stats = processor.importer()
        
        print(f"\n📊 Résultats de l'import :")
        print(f"   - Total traité : {stats['total']}")
        print(f"   - Notes créées : {stats['importees']}")
        print(f"   - Notes modifiées : {stats['modifiees']}")
        print(f"   - Absents : {stats['absents']}")
        print(f"   - Erreurs : {stats['erreurs']}")
        
        # Vérifier que les notes sont bien dans la base
        self.notes_importees = list(NoteMensuelle.objects.filter(
            eleve__in=self.eleves_importes,
            matiere=self.matiere_test,
            mois='JANVIER'
        ).select_related('eleve'))
        
        print(f"\n✅ Vérification dans la base de données :")
        print(f"   - Notes trouvées : {len(self.notes_importees)}")
        
        if len(self.notes_importees) == nb_notes:
            print(f"   ✅ TOUTES LES NOTES SONT BIEN ENREGISTRÉES")
            
            print(f"\n📋 Liste des notes importées :")
            for note in self.notes_importees:
                print(f"      • {note.eleve.matricule} - {note.eleve.prenom} : {note.note}/20")
        else:
            print(f"   ⚠️  ATTENTION : {nb_notes} attendues, {len(self.notes_importees)} trouvées")
            if stats['erreurs'] > 0:
                print(f"   ℹ️  {stats['erreurs']} erreur(s) lors de l'import")
        
        return len(self.notes_importees) > 0
    
    def verifier_affichage_liste_eleves(self):
        """Vérifie que les élèves s'affichent dans la liste"""
        print("\n" + "="*60)
        print("🔍 TEST 3 : AFFICHAGE DANS LA LISTE DES ÉLÈVES")
        print("="*60)
        
        # Simuler la requête de la vue liste_eleves
        eleves_affiches = Eleve.objects.filter(
            classe=self.classe_test,
            statut='ACTIF'
        ).select_related('classe', 'responsable_principal').order_by('nom', 'prenom')
        
        # Compter nos élèves de test
        eleves_test_affiches = [e for e in eleves_affiches if e.nom == 'TEST_IMPORT']
        
        print(f"\n📊 Résultats :")
        print(f"   - Total élèves dans la classe : {eleves_affiches.count()}")
        print(f"   - Élèves de test visibles : {len(eleves_test_affiches)}")
        
        if len(eleves_test_affiches) == len(self.eleves_importes):
            print(f"   ✅ TOUS LES ÉLÈVES IMPORTÉS SONT VISIBLES")
            
            print(f"\n📋 Élèves affichés :")
            for eleve in eleves_test_affiches:
                print(f"      • {eleve.matricule} - {eleve.prenom} {eleve.nom}")
                print(f"        Classe: {eleve.classe.nom}")
                print(f"        Statut: {eleve.statut}")
            return True
        else:
            print(f"   ❌ ERREUR : {len(self.eleves_importes)} importés, {len(eleves_test_affiches)} visibles")
            return False
    
    def verifier_affichage_notes(self):
        """Vérifie que les notes s'affichent dans la consultation"""
        print("\n" + "="*60)
        print("🔍 TEST 4 : AFFICHAGE DES NOTES DANS LA CONSULTATION")
        print("="*60)
        
        if not self.notes_importees:
            print("❌ Pas de notes à vérifier")
            return False
        
        # Simuler la requête de consultation des notes
        print(f"\n📝 Vérification pour la matière : {self.matiere_test.nom}")
        print(f"   Période : JANVIER")
        
        notes_visibles = NoteMensuelle.objects.filter(
            matiere=self.matiere_test,
            mois='JANVIER',
            annee_scolaire='2024-2025'
        ).select_related('eleve')
        
        # Filtrer nos notes de test
        notes_test_visibles = [n for n in notes_visibles if n.eleve.nom == 'TEST_IMPORT']
        
        print(f"\n📊 Résultats :")
        print(f"   - Total notes pour cette matière/période : {notes_visibles.count()}")
        print(f"   - Notes de test visibles : {len(notes_test_visibles)}")
        
        if len(notes_test_visibles) == len(self.notes_importees):
            print(f"   ✅ TOUTES LES NOTES IMPORTÉES SONT VISIBLES")
            
            print(f"\n📋 Notes affichées :")
            for note in notes_test_visibles:
                print(f"      • {note.eleve.matricule} - {note.eleve.prenom} : {note.note}/20")
                print(f"        Absent: {'Oui' if note.absent else 'Non'}")
            return True
        else:
            print(f"   ❌ ERREUR : {len(self.notes_importees)} importées, {len(notes_test_visibles)} visibles")
            return False
    
    def verifier_coherence_donnees(self):
        """Vérifie la cohérence des données importées"""
        print("\n" + "="*60)
        print("🔍 TEST 5 : COHÉRENCE DES DONNÉES")
        print("="*60)
        
        problemes = []
        
        # Vérifier les élèves
        print(f"\n👥 Vérification des élèves...")
        for eleve in self.eleves_importes:
            # Vérifier le matricule
            if not eleve.matricule:
                problemes.append(f"Élève {eleve.id} sans matricule")
            
            # Vérifier le responsable
            if not eleve.responsable_principal:
                problemes.append(f"Élève {eleve.matricule} sans responsable")
            
            # Vérifier la classe
            if eleve.classe != self.classe_test:
                problemes.append(f"Élève {eleve.matricule} dans la mauvaise classe")
            
            # Vérifier le statut
            if eleve.statut != 'ACTIF':
                problemes.append(f"Élève {eleve.matricule} statut {eleve.statut} au lieu de ACTIF")
        
        if not problemes:
            print(f"   ✅ Tous les élèves sont cohérents")
        else:
            print(f"   ❌ {len(problemes)} problème(s) trouvé(s)")
            for p in problemes:
                print(f"      - {p}")
        
        # Vérifier les notes
        print(f"\n📝 Vérification des notes...")
        for note in self.notes_importees:
            # Vérifier la note
            if note.note < 0 or note.note > 20:
                problemes.append(f"Note invalide pour {note.eleve.matricule}: {note.note}")
            
            # Vérifier la matière
            if note.matiere != self.matiere_test:
                problemes.append(f"Note de {note.eleve.matricule} dans la mauvaise matière")
            
            # Vérifier la période
            if note.mois != 'JANVIER':
                problemes.append(f"Note de {note.eleve.matricule} dans la mauvaise période")
        
        if len(problemes) == 0:
            print(f"   ✅ Toutes les notes sont cohérentes")
        else:
            print(f"   ❌ {len(problemes)} problème(s) trouvé(s)")
            for p in problemes:
                print(f"      - {p}")
        
        return len(problemes) == 0
    
    def generer_rapport(self, resultats):
        """Génère un rapport final"""
        print("\n" + "="*60)
        print("📊 RAPPORT FINAL")
        print("="*60)
        
        total_tests = len(resultats)
        tests_reussis = sum(1 for r in resultats.values() if r)
        
        print(f"\n✅ Tests réussis : {tests_reussis}/{total_tests}")
        
        print(f"\n📋 Détails :")
        for nom_test, resultat in resultats.items():
            statut = "✅ RÉUSSI" if resultat else "❌ ÉCHOUÉ"
            print(f"   {statut} - {nom_test}")
        
        if tests_reussis == total_tests:
            print(f"\n🎉 TOUS LES TESTS ONT RÉUSSI !")
            print(f"\n✅ Les imports fonctionnent correctement")
            print(f"✅ Les données s'affichent dans le système")
            print(f"✅ La cohérence des données est garantie")
            return True
        else:
            print(f"\n⚠️  {total_tests - tests_reussis} test(s) ont échoué")
            print(f"\nℹ️  Vérifiez les détails ci-dessus pour identifier les problèmes")
            return False
    
    def executer(self):
        """Execute tous les tests"""
        print("\n" + "="*70)
        print("🔬 TEST COMPLET : IMPORT ET AFFICHAGE DANS LE SYSTÈME")
        print("="*70)
        
        # Nettoyer les données de test précédentes
        self.nettoyer_donnees_test()
        
        # Préparer la classe de test
        if not self.preparer_classe_test():
            print("\n❌ Impossible de préparer la classe de test")
            return False
        
        # Exécuter les tests
        resultats = {}
        
        try:
            resultats['Import élèves'] = self.test_import_eleves()
            resultats['Import notes'] = self.test_import_notes()
            resultats['Affichage élèves'] = self.verifier_affichage_liste_eleves()
            resultats['Affichage notes'] = self.verifier_affichage_notes()
            resultats['Cohérence données'] = self.verifier_coherence_donnees()
            
            # Générer le rapport
            return self.generer_rapport(resultats)
            
        except Exception as e:
            print(f"\n❌ Erreur pendant les tests : {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Nettoyer les données de test
            print(f"\n🧹 Nettoyage final...")
            self.nettoyer_donnees_test()
            print(f"   ✅ Données de test supprimées")


if __name__ == "__main__":
    tester = TestImportAffichage()
    success = tester.executer()
    
    print("\n" + "="*70)
    if success:
        print("✅ VALIDATION COMPLÈTE : Le système d'import fonctionne parfaitement !")
    else:
        print("⚠️  Des problèmes ont été détectés - voir les détails ci-dessus")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)
