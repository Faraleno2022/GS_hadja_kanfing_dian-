"""
Tests Complets de l'Application
Vérifie toutes les fonctionnalités principales
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from eleves.models import Eleve, Classe, Ecole, Responsable
from paiements.models import TypePaiement, ModePaiement, Paiement
from notes.models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from django.test import RequestFactory, Client
from django.urls import reverse
import sys

User = get_user_model()

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.tests = []
    
    def test(self, name, condition, message=""):
        """Exécuter un test"""
        if condition:
            print(f"   ✅ {name}")
            self.passed += 1
            self.tests.append(('PASS', name))
        else:
            print(f"   ❌ {name}")
            if message:
                print(f"      → {message}")
            self.failed += 1
            self.tests.append(('FAIL', name, message))
    
    def warning(self, name, message=""):
        """Avertissement"""
        print(f"   ⚠️  {name}")
        if message:
            print(f"      → {message}")
        self.warnings += 1
        self.tests.append(('WARN', name, message))
    
    def summary(self):
        """Afficher le résumé"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print("RÉSUMÉ DES TESTS")
        print("=" * 70)
        print(f"✅ Tests réussis: {self.passed}/{total} ({self.passed/total*100:.1f}%)")
        print(f"❌ Tests échoués: {self.failed}/{total}")
        print(f"⚠️  Avertissements: {self.warnings}")
        
        if self.failed == 0:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        else:
            print("\n⚠️  Certains tests ont échoué. Vérifiez les détails ci-dessus.")

def test_base_de_donnees(runner):
    """Tester la base de données"""
    print("\n" + "=" * 70)
    print("TEST 1: BASE DE DONNÉES")
    print("=" * 70)
    
    # Écoles
    ecoles = Ecole.objects.all()
    runner.test("Écoles présentes", ecoles.exists(), f"Trouvé: {ecoles.count()}")
    
    # Classes
    classes = Classe.objects.all()
    runner.test("Classes présentes", classes.exists(), f"Trouvé: {classes.count()}")
    
    # Élèves
    eleves = Eleve.objects.all()
    runner.test("Élèves présents", eleves.exists(), f"Trouvé: {eleves.count()}")
    runner.test("Au moins 100 élèves", eleves.count() >= 100, f"Trouvé: {eleves.count()}")
    
    # Responsables
    responsables = Responsable.objects.all()
    runner.test("Responsables présents", responsables.exists(), f"Trouvé: {responsables.count()}")
    
    # Types de paiement
    types_paiement = TypePaiement.objects.all()
    runner.test("Types de paiement présents", types_paiement.exists(), f"Trouvé: {types_paiement.count()}")
    runner.test("Au moins 5 types", types_paiement.count() >= 5, f"Trouvé: {types_paiement.count()}")
    
    # Modes de paiement
    modes_paiement = ModePaiement.objects.all()
    runner.test("Modes de paiement présents", modes_paiement.exists(), f"Trouvé: {modes_paiement.count()}")
    runner.test("Au moins 3 modes", modes_paiement.count() >= 3, f"Trouvé: {modes_paiement.count()}")

def test_utilisateurs(runner):
    """Tester les utilisateurs"""
    print("\n" + "=" * 70)
    print("TEST 2: UTILISATEURS")
    print("=" * 70)
    
    # Superutilisateurs
    superusers = User.objects.filter(is_superuser=True)
    runner.test("Superutilisateurs présents", superusers.exists(), f"Trouvé: {superusers.count()}")
    
    # Utilisateurs avec profil
    users_with_profile = User.objects.filter(profil__isnull=False)
    runner.test("Utilisateurs avec profil", users_with_profile.exists(), f"Trouvé: {users_with_profile.count()}")

def test_photos_logos(runner):
    """Tester les photos et logos"""
    print("\n" + "=" * 70)
    print("TEST 3: PHOTOS ET LOGOS")
    print("=" * 70)
    
    # Logos d'écoles
    ecoles_avec_logo = Ecole.objects.exclude(logo='').exclude(logo__isnull=True)
    total_ecoles = Ecole.objects.count()
    runner.test("Écoles avec logo", ecoles_avec_logo.exists(), 
                f"{ecoles_avec_logo.count()}/{total_ecoles}")
    
    # Photos d'élèves
    eleves_avec_photo = Eleve.objects.exclude(photo='').exclude(photo__isnull=True)
    total_eleves = Eleve.objects.count()
    runner.test("Élèves avec photo", eleves_avec_photo.exists(), 
                f"{eleves_avec_photo.count()}/{total_eleves}")
    
    if eleves_avec_photo.count() < total_eleves * 0.5:
        runner.warning("Moins de 50% des élèves ont une photo", 
                      "Exécutez: python assigner_photos_logos_defaut.py")

def test_module_notes(runner):
    """Tester le module notes"""
    print("\n" + "=" * 70)
    print("TEST 4: MODULE NOTES")
    print("=" * 70)
    
    # Classes notes
    classes_notes = ClasseNote.objects.all()
    runner.test("Classes notes présentes", classes_notes.exists(), 
                f"Trouvé: {classes_notes.count()}")
    
    # Matières
    matieres = MatiereNote.objects.all()
    runner.test("Matières présentes", matieres.exists(), 
                f"Trouvé: {matieres.count()}")
    
    # Notes mensuelles
    notes_mensuelles = NoteMensuelle.objects.all()
    if notes_mensuelles.exists():
        runner.test("Notes mensuelles présentes", True, 
                    f"Trouvé: {notes_mensuelles.count()}")
    else:
        runner.warning("Aucune note mensuelle", 
                      "Saisissez des notes via /notes/saisir/")
    
    # Compositions
    compositions = CompositionNote.objects.all()
    if compositions.exists():
        runner.test("Compositions présentes", True, 
                    f"Trouvé: {compositions.count()}")
    else:
        runner.warning("Aucune composition", 
                      "Saisissez des notes via /notes/saisir/")

def test_urls(runner):
    """Tester les URLs principales"""
    print("\n" + "=" * 70)
    print("TEST 5: URLS ET ROUTES")
    print("=" * 70)
    
    client = Client()
    
    urls_to_test = [
        ('/', 'Page d\'accueil'),
        ('/admin/', 'Admin Django'),
        ('/eleves/liste/', 'Liste élèves'),
        ('/notes/', 'Tableau de bord notes'),
        ('/notes/classes/', 'Gestion classes'),
        ('/notes/matieres/', 'Gestion matières'),
        ('/notes/saisir/', 'Saisie notes'),
        ('/notes/consulter/', 'Consultation notes'),
    ]
    
    for url, name in urls_to_test:
        try:
            response = client.get(url)
            # 200 (OK), 302 (Redirect), 301 (Moved) sont acceptables
            success = response.status_code in [200, 301, 302]
            runner.test(f"URL {name}", success, 
                       f"Status: {response.status_code}")
        except Exception as e:
            runner.test(f"URL {name}", False, str(e))

def test_vues_suppression(runner):
    """Tester les vues de suppression"""
    print("\n" + "=" * 70)
    print("TEST 6: VUES DE SUPPRESSION")
    print("=" * 70)
    
    # Vérifier que les vues existent
    try:
        from notes.views import supprimer_classe, supprimer_matiere
        runner.test("Vue supprimer_classe", True)
        runner.test("Vue supprimer_matiere", True)
    except ImportError as e:
        runner.test("Vues de suppression", False, str(e))
    
    try:
        from eleves.views import supprimer_eleve
        runner.test("Vue supprimer_eleve", True)
    except ImportError as e:
        runner.test("Vue supprimer_eleve", False, str(e))

def test_generation_pdf(runner):
    """Tester la génération de PDF"""
    print("\n" + "=" * 70)
    print("TEST 7: GÉNÉRATION DE PDF")
    print("=" * 70)
    
    # Vérifier que les vues existent
    try:
        from eleves.views import generer_ticket_retrait_pdf, generer_ticket_bus_pdf
        runner.test("Vue ticket retrait", True)
        runner.test("Vue ticket bus", True)
    except ImportError as e:
        runner.test("Vues PDF", False, str(e))
    
    # Vérifier ReportLab
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        runner.test("ReportLab installé", True)
    except ImportError:
        runner.test("ReportLab installé", False, 
                   "Installez: pip install reportlab")
    
    # Vérifier PIL
    try:
        from PIL import Image
        runner.test("Pillow installé", True)
    except ImportError:
        runner.test("Pillow installé", False, 
                   "Installez: pip install Pillow")

def test_configuration(runner):
    """Tester la configuration"""
    print("\n" + "=" * 70)
    print("TEST 8: CONFIGURATION")
    print("=" * 70)
    
    from django.conf import settings
    
    # MEDIA_ROOT
    runner.test("MEDIA_ROOT défini", hasattr(settings, 'MEDIA_ROOT'))
    if hasattr(settings, 'MEDIA_ROOT'):
        runner.test("MEDIA_ROOT existe", os.path.exists(settings.MEDIA_ROOT), 
                   settings.MEDIA_ROOT)
    
    # MEDIA_URL
    runner.test("MEDIA_URL défini", hasattr(settings, 'MEDIA_URL'))
    
    # DEBUG
    if hasattr(settings, 'DEBUG'):
        if settings.DEBUG:
            runner.warning("DEBUG activé", 
                          "Désactivez en production: DEBUG = False")
        else:
            runner.test("DEBUG désactivé (production)", True)

def test_donnees_coherence(runner):
    """Tester la cohérence des données"""
    print("\n" + "=" * 70)
    print("TEST 9: COHÉRENCE DES DONNÉES")
    print("=" * 70)
    
    # Élèves sans classe
    eleves_sans_classe = Eleve.objects.filter(classe__isnull=True)
    runner.test("Tous les élèves ont une classe", 
                not eleves_sans_classe.exists(), 
                f"{eleves_sans_classe.count()} élève(s) sans classe")
    
    # Élèves sans responsable
    eleves_sans_responsable = Eleve.objects.filter(responsable_principal__isnull=True)
    runner.test("Tous les élèves ont un responsable", 
                not eleves_sans_responsable.exists(), 
                f"{eleves_sans_responsable.count()} élève(s) sans responsable")
    
    # Classes sans école
    classes_sans_ecole = Classe.objects.filter(ecole__isnull=True)
    runner.test("Toutes les classes ont une école", 
                not classes_sans_ecole.exists(), 
                f"{classes_sans_ecole.count()} classe(s) sans école")
    
    # Matières sans classe
    matieres_sans_classe = MatiereNote.objects.filter(classe__isnull=True)
    runner.test("Toutes les matières ont une classe", 
                not matieres_sans_classe.exists(), 
                f"{matieres_sans_classe.count()} matière(s) sans classe")

def test_performance(runner):
    """Tester les performances"""
    print("\n" + "=" * 70)
    print("TEST 10: PERFORMANCE")
    print("=" * 70)
    
    import time
    
    # Test de requête simple
    start = time.time()
    eleves = list(Eleve.objects.all()[:100])
    duration = time.time() - start
    runner.test("Requête 100 élèves < 1s", duration < 1.0, 
                f"Durée: {duration:.3f}s")
    
    # Test de requête avec relations
    start = time.time()
    eleves = list(Eleve.objects.select_related('classe', 'responsable_principal')[:100])
    duration = time.time() - start
    runner.test("Requête optimisée < 1s", duration < 1.0, 
                f"Durée: {duration:.3f}s")

def main():
    """Fonction principale"""
    print("\n" + "=" * 70)
    print("TESTS COMPLETS DE L'APPLICATION")
    print("=" * 70)
    print("Date: 31 Octobre 2024")
    print("=" * 70)
    
    runner = TestRunner()
    
    try:
        # Exécuter tous les tests
        test_base_de_donnees(runner)
        test_utilisateurs(runner)
        test_photos_logos(runner)
        test_module_notes(runner)
        test_urls(runner)
        test_vues_suppression(runner)
        test_generation_pdf(runner)
        test_configuration(runner)
        test_donnees_coherence(runner)
        test_performance(runner)
        
        # Afficher le résumé
        runner.summary()
        
        # Recommandations
        print("\n" + "=" * 70)
        print("RECOMMANDATIONS")
        print("=" * 70)
        
        if runner.failed > 0:
            print("\n⚠️  Actions requises:")
            print("   1. Vérifier les tests échoués ci-dessus")
            print("   2. Corriger les problèmes identifiés")
            print("   3. Relancer les tests")
        
        if runner.warnings > 0:
            print("\n💡 Améliorations suggérées:")
            print("   1. Assigner des photos à tous les élèves")
            print("   2. Saisir des notes pour tester le module")
            print("   3. Vérifier la configuration pour la production")
        
        if runner.failed == 0 and runner.warnings == 0:
            print("\n🎉 L'application est prête pour la production !")
            print("\n📝 Prochaines étapes:")
            print("   1. Saisir des notes réelles")
            print("   2. Créer des paiements")
            print("   3. Générer des bulletins")
            print("   4. Former les utilisateurs")
        
        # Code de sortie
        sys.exit(0 if runner.failed == 0 else 1)
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
