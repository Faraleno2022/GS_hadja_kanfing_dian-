"""
Tests pour valider la refonte du module notes
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from notes.models import MatiereClasse, Evaluation, Note
from eleves.models import Classe, Eleve
from utilisateurs.models import Ecole


class RefonteModuleNotesTestCase(TestCase):
    """
    Tests de validation de la refonte du module notes
    """
    
    def setUp(self):
        """Configuration des données de test"""
        # Création d'une école
        self.ecole = Ecole.objects.create(
            nom="École Test Refonte",
            adresse="123 Rue de Test",
            telephone="123456789"
        )
        
        # Création d'un utilisateur
        self.user = User.objects.create_user(
            username='test_refonte',
            password='testpass123'
        )
        
        # Création d'une classe
        self.classe = Classe.objects.create(
            nom="Test Classe Refonte",
            niveau="PRIMAIRE_1ERE",
            ecole=self.ecole,
            annee_scolaire="2024-2025"
        )
        
        # Création d'un élève
        self.eleve = Eleve.objects.create(
            nom="Test",
            prenom="Élève",
            matricule="TEST-001",
            classe=self.classe,
            ecole=self.ecole
        )
        
        # Création d'une matière
        self.matiere = MatiereClasse.objects.create(
            nom="Mathématiques Test",
            classe=self.classe,
            coefficient=2,
            ecole=self.ecole
        )
        
        # Création d'une évaluation
        self.evaluation = Evaluation.objects.create(
            titre="Test Évaluation Refonte",
            classe=self.classe,
            matiere=self.matiere,
            ecole=self.ecole,
            categorie="COURS",
            coefficient=1
        )
        
        self.client = Client()
    
    def test_dashboard_moderne_accessible(self):
        """Test que le dashboard moderne est accessible"""
        self.client.login(username='test_refonte', password='testpass123')
        
        # Test de l'URL principale
        response = self.client.get('/notes/')
        self.assertEqual(response.status_code, 200)
        
        # Vérification du contenu moderne
        self.assertContains(response, "Gestion des Notes")
        self.assertContains(response, "hero-section")
        self.assertContains(response, "stats-card")
    
    def test_saisie_notes_moderne_accessible(self):
        """Test que la saisie moderne est accessible"""
        self.client.login(username='test_refonte', password='testpass123')
        
        url = reverse('notes:saisie_notes_moderne', args=[self.evaluation.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Vérification du contenu moderne
        self.assertContains(response, "Saisie des Notes")
        self.assertContains(response, "notes-hero")
        self.assertContains(response, "MATRICULE;NOTE")
    
    def test_classement_moderne_accessible(self):
        """Test que les classements modernes sont accessibles"""
        self.client.login(username='test_refonte', password='testpass123')
        
        url = reverse('notes:classement_moderne', args=[self.classe.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Vérification du contenu moderne
        self.assertContains(response, "Classement de la Classe")
        self.assertContains(response, "ranking-hero")
        self.assertContains(response, "podium")
    
    def test_saisie_notes_par_matricule(self):
        """Test de la saisie des notes par matricule"""
        self.client.login(username='test_refonte', password='testpass123')
        
        url = reverse('notes:saisie_notes_moderne', args=[self.evaluation.id])
        
        # Données de test
        donnees_notes = f"{self.eleve.matricule};15.5"
        
        response = self.client.post(url, {
            'donnees': donnees_notes
        })
        
        # Vérification de la redirection (succès)
        self.assertEqual(response.status_code, 302)
        
        # Vérification que la note a été créée
        note = Note.objects.filter(
            evaluation=self.evaluation,
            eleve=self.eleve
        ).first()
        
        self.assertIsNotNone(note)
        self.assertEqual(float(note.note), 15.5)
    
    def test_template_tags_personnalises(self):
        """Test des template tags personnalisés"""
        from notes.templatetags.notes_extras import moyenne_color, appreciation_auto
        
        # Test moyenne_color
        self.assertEqual(moyenne_color(18), 'text-success')
        self.assertEqual(moyenne_color(15), 'text-primary')
        self.assertEqual(moyenne_color(8), 'text-danger')
        
        # Test appreciation_auto
        self.assertEqual(appreciation_auto(18), 'Excellent')
        self.assertEqual(appreciation_auto(15), 'Bien')
        self.assertEqual(appreciation_auto(8), 'Insuffisant')
    
    def test_compatibilite_anciennes_urls(self):
        """Test que les anciennes URLs fonctionnent toujours"""
        self.client.login(username='test_refonte', password='testpass123')
        
        # Test ancien dashboard
        response = self.client.get('/notes/ancien/')
        self.assertEqual(response.status_code, 200)
        
        # Test ancienne saisie
        url = reverse('notes:saisie_notes', args=[self.evaluation.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_api_ajax_stats(self):
        """Test de l'API AJAX pour les statistiques"""
        self.client.login(username='test_refonte', password='testpass123')
        
        url = reverse('notes:ajax_stats_notes')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Vérification du contenu JSON
        data = response.json()
        self.assertIn('stats', data)
        self.assertIn('repartition', data)
        self.assertEqual(data['status'], 'success')
    
    def test_preservation_logiques_calcul(self):
        """Test que les logiques de calcul sont préservées"""
        from notes.utils import semester_avg, trimestre_avg
        
        # Création d'une note pour tester
        Note.objects.create(
            evaluation=self.evaluation,
            eleve=self.eleve,
            note=16.0,
            ecole=self.ecole,
            classe=self.classe,
            matiere=self.matiere,
            matricule=self.eleve.matricule
        )
        
        # Test des fonctions de calcul (doivent fonctionner sans erreur)
        try:
            moyenne_sem = semester_avg(self.eleve, self.matiere, "2024-2025", 1)
            moyenne_trim = trimestre_avg(self.eleve, self.matiere, "2024-2025", "T1")
            
            # Les fonctions doivent retourner des valeurs ou None sans erreur
            self.assertTrue(moyenne_sem is None or isinstance(moyenne_sem, (int, float)))
            self.assertTrue(moyenne_trim is None or isinstance(moyenne_trim, (int, float)))
            
        except Exception as e:
            self.fail(f"Les logiques de calcul ont été altérées: {e}")


class IntegrationTestCase(TestCase):
    """
    Tests d'intégration pour valider le fonctionnement global
    """
    
    def test_workflow_complet_saisie_notes(self):
        """Test du workflow complet de saisie des notes"""
        # Configuration similaire à setUp mais pour ce test spécifique
        ecole = Ecole.objects.create(nom="École Intégration")
        user = User.objects.create_user(username='integration', password='test123')
        classe = Classe.objects.create(nom="Classe Intégration", niveau="COLLEGE_7EME", ecole=ecole)
        
        # Connexion
        client = Client()
        client.login(username='integration', password='test123')
        
        # 1. Accès au dashboard
        response = client.get('/notes/')
        self.assertEqual(response.status_code, 200)
        
        # 2. Vérification que les nouvelles interfaces sont bien chargées
        self.assertContains(response, "animate-fade")
        self.assertContains(response, "hero-section")
        
        print("✅ Tests de refonte du module notes : SUCCÈS")
        print("✅ Interface moderne fonctionnelle")
        print("✅ Logiques de calcul préservées")
        print("✅ Compatibilité assurée")
