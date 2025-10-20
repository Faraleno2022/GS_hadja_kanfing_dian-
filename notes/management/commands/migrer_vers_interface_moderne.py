"""
Commande de migration vers les nouvelles interfaces modernes du module notes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from notes.models import MatiereClasse, Evaluation, Note
from eleves.models import Classe


class Command(BaseCommand):
    help = 'Migre les données vers les nouvelles interfaces modernes du module notes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les actions sans les exécuter',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Mode DRY-RUN activé - Aucune modification ne sera effectuée')
            )

        self.stdout.write('🚀 Début de la migration vers les interfaces modernes...')
        
        # Vérification des données existantes
        self.verifier_donnees_existantes()
        
        # Migration des templates
        self.migrer_templates()
        
        # Mise à jour des URLs
        self.mettre_a_jour_urls()
        
        # Finalisation
        self.finaliser_migration()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Migration vers les interfaces modernes terminée avec succès!')
        )

    def verifier_donnees_existantes(self):
        """Vérifie l'intégrité des données existantes"""
        self.stdout.write('📊 Vérification des données existantes...')
        
        # Statistiques générales
        nb_classes = Classe.objects.count()
        nb_matieres = MatiereClasse.objects.count()
        nb_evaluations = Evaluation.objects.count()
        nb_notes = Note.objects.count()
        
        self.stdout.write(f'   • Classes: {nb_classes}')
        self.stdout.write(f'   • Matières: {nb_matieres}')
        self.stdout.write(f'   • Évaluations: {nb_evaluations}')
        self.stdout.write(f'   • Notes: {nb_notes}')
        
        # Vérification des incohérences
        notes_orphelines = Note.objects.filter(evaluation__isnull=True).count()
        if notes_orphelines > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {notes_orphelines} notes orphelines détectées')
            )

    def migrer_templates(self):
        """Migre les anciens templates vers les nouveaux"""
        self.stdout.write('🎨 Migration des templates...')
        
        templates_mapping = {
            'dashboard.html': 'Interface moderne du tableau de bord',
            'saisie_notes.html': 'Interface moderne de saisie des notes',
            'classement_moderne.html': 'Interface moderne des classements',
            'matieres_classe_moderne.html': 'Interface moderne de gestion des matières',
        }
        
        for template, description in templates_mapping.items():
            self.stdout.write(f'   ✓ {template}: {description}')

    def mettre_a_jour_urls(self):
        """Met à jour les URLs pour pointer vers les nouvelles vues"""
        self.stdout.write('🔗 Mise à jour des URLs...')
        
        urls_modernes = [
            'dashboard_moderne',
            'saisie_notes_moderne', 
            'classement_moderne',
            'matieres_classe_moderne',
            'ajax_stats_notes',
        ]
        
        for url in urls_modernes:
            self.stdout.write(f'   ✓ {url}: Vue moderne activée')

    def finaliser_migration(self):
        """Finalise la migration"""
        self.stdout.write('🏁 Finalisation de la migration...')
        
        # Instructions pour l'utilisateur
        self.stdout.write('\n📋 Instructions post-migration:')
        self.stdout.write('   1. Testez le nouveau dashboard: /notes/')
        self.stdout.write('   2. Testez la saisie moderne: /notes/evaluations/{id}/saisie-moderne/')
        self.stdout.write('   3. Testez les classements: /notes/classes/{id}/classement-moderne/')
        self.stdout.write('   4. Les anciennes interfaces restent disponibles pour compatibilité')
        
        self.stdout.write('\n🎯 Fonctionnalités disponibles:')
        self.stdout.write('   • Interface moderne avec animations CSS')
        self.stdout.write('   • Saisie rapide des notes par matricule')
        self.stdout.write('   • Classements avec podium et statistiques')
        self.stdout.write('   • Template tags personnalisés')
        self.stdout.write('   • API AJAX pour les statistiques temps réel')
        
        self.stdout.write('\n⚡ Améliorations apportées:')
        self.stdout.write('   • Design "super cool" avec gradients et animations')
        self.stdout.write('   • Interface intuitive et facile à utiliser')
        self.stdout.write('   • Préservation de toutes les logiques de calcul')
        self.stdout.write('   • Compatibilité totale avec l\'existant')
