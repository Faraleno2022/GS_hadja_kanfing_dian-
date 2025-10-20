"""
Commande pour activer la permission de gestion des notes pour les comptables
Usage: python manage.py activer_permission_notes
"""
from django.core.management.base import BaseCommand
from utilisateurs.models import Profil

class Command(BaseCommand):
    help = 'Active la permission de gestion des notes pour tous les comptables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait fait sans l\'exécuter',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('🔓 ACTIVATION PERMISSION NOTES POUR COMPTABLES')
        )
        self.stdout.write('=' * 60)
        
        # Récupérer tous les comptables
        comptables = Profil.objects.filter(role='COMPTABLE')
        total_comptables = comptables.count()
        
        self.stdout.write(f'📊 Comptables trouvés: {total_comptables}')
        
        if total_comptables == 0:
            self.stdout.write(
                self.style.WARNING('⚠️  Aucun comptable trouvé dans la base de données.')
            )
            return
        
        # Compter ceux qui n'ont pas déjà la permission
        sans_permission = comptables.filter(peut_gerer_notes=False).count()
        avec_permission = total_comptables - sans_permission
        
        self.stdout.write(f'✅ Déjà autorisés: {avec_permission}')
        self.stdout.write(f'🔒 À autoriser: {sans_permission}')
        
        if sans_permission == 0:
            self.stdout.write(
                self.style.SUCCESS('🎉 Tous les comptables ont déjà la permission!')
            )
            return
        
        if dry_run:
            self.stdout.write('\n🔍 MODE DRY-RUN - Aucune modification effectuée')
            self.stdout.write('Comptables qui seraient modifiés:')
            for comptable in comptables.filter(peut_gerer_notes=False):
                self.stdout.write(
                    f'  • {comptable.user.get_full_name() or comptable.user.username} '
                    f'({comptable.ecole.nom if comptable.ecole else "Sans école"})'
                )
        else:
            # Activer la permission pour tous les comptables
            updated = comptables.filter(peut_gerer_notes=False).update(peut_gerer_notes=True)
            
            self.stdout.write('\n✅ PERMISSIONS MISES À JOUR:')
            for comptable in comptables.filter(peut_gerer_notes=True):
                self.stdout.write(
                    f'  ✓ {comptable.user.get_full_name() or comptable.user.username} '
                    f'({comptable.ecole.nom if comptable.ecole else "Sans école"})'
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 {updated} comptables autorisés avec succès!')
            )
        
        self.stdout.write('\n📋 ACCÈS AUTORISÉ À:')
        self.stdout.write('  • /notes/classes/<id>/matieres/ (Gestion des matières)')
        self.stdout.write('  • Toutes les fonctionnalités du module Notes')
        self.stdout.write('  • Création, modification, suppression des matières')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ Commande terminée!')
        )
