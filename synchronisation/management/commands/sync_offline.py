from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from eleves.models import Ecole
from synchronisation.client import SyncTransportError, pull_changes, push_pending, rejouer_refuses
from synchronisation.models import SyncChange


class Command(BaseCommand):
    help = "Push local pending sync changes and pull changes from other offline devices."

    def add_arguments(self, parser):
        parser.add_argument('--server-url', default=getattr(settings, 'MYSCHOOL_SYNC_SERVER_URL', ''))
        parser.add_argument('--device-id', default=getattr(settings, 'MYSCHOOL_SYNC_DEVICE_ID', ''))
        parser.add_argument('--token', default=getattr(settings, 'MYSCHOOL_SYNC_TOKEN', ''))
        parser.add_argument('--ecole-id', default=getattr(settings, 'MYSCHOOL_SYNC_ECOLE_ID', ''))
        parser.add_argument('--since-id', default='')
        parser.add_argument('--initial', action='store_true')
        parser.add_argument('--pull-only', action='store_true')
        parser.add_argument('--push-only', action='store_true')
        parser.add_argument('--rejouer-refuses', action='store_true',
                            help='Remet en file les changements refuses par le serveur.')
        parser.add_argument('--etat', action='store_true',
                            help="Affiche l'etat de la file locale et les derniers refus.")

    def handle(self, *args, **options):
        server_url = (options['server_url'] or '').rstrip('/')
        device_id = options['device_id'] or ''
        token = options['token'] or ''
        ecole_id = options['ecole_id'] or ''

        if not server_url or not device_id or not token or not ecole_id:
            raise CommandError(
                'Configuration incomplete. Definissez MYSCHOOL_SYNC_SERVER_URL, '
                'MYSCHOOL_SYNC_DEVICE_ID, MYSCHOOL_SYNC_TOKEN et MYSCHOOL_SYNC_ECOLE_ID.'
            )

        # Un poste desktop est toujours dedie a une seule ecole : son
        # identifiant local (auto-attribue lors de l'amorçage) n'a aucune
        # raison de correspondre a l'identifiant sur le serveur. ecole_id
        # sert uniquement a valider que la configuration est complete et a
        # enregistrer l'appareil (register_sync_device) ; la recherche
        # locale se fait sur l'ecole unique deja presente, quel que soit
        # son id.
        ecole = Ecole.objects.first()
        if not ecole and not options['initial']:
            raise CommandError(
                f"Ecole locale introuvable: {ecole_id}. "
                "Utilisez --initial pour amorcer un poste tout juste installe."
            )

        if options['etat']:
            self._afficher_etat(ecole)
            return

        if options['rejouer_refuses'] and ecole is not None:
            nb = rejouer_refuses(ecole)
            self.stdout.write(self.style.SUCCESS(f'{nb} changement(s) refuse(s) remis en file.'))

        try:
            if not options['pull_only'] and ecole is not None:
                pushed = push_pending(server_url, device_id, token, ecole)
                self.stdout.write(self.style.SUCCESS(f'{pushed} changement(s) envoye(s).'))

            if not options['push_only']:
                pulled = pull_changes(
                    server_url, device_id, token, ecole,
                    since_id=options['since_id'] or None,
                    initial=options['initial'],
                )
                self.stdout.write(self.style.SUCCESS(f'{pulled} changement(s) recu(s).'))
        except SyncTransportError as exc:
            raise CommandError(str(exc)) from exc

    def _afficher_etat(self, ecole):
        if ecole is None:
            self.stdout.write("Aucune ecole locale : le poste n'a pas encore ete amorce.")
            return
        base = SyncChange.objects.filter(ecole=ecole)
        for statut, _libelle in SyncChange.STATUT_CHOICES:
            self.stdout.write(f'{statut}: {base.filter(statut=statut).count()}')
        refuses = base.filter(statut=SyncChange.STATUT_FAILED).order_by('-id')[:10]
        if refuses:
            self.stdout.write('
Derniers refus :')
            for change in refuses:
                self.stdout.write(f'  {change.operation} {change.model_label} -> {change.erreur[:200]}')
