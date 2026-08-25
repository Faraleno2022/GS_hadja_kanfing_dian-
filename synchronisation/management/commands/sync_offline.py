from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from eleves.models import Ecole
from synchronisation.client import SyncTransportError, pull_changes, push_pending


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

        ecole = Ecole.objects.filter(pk=ecole_id).first()
        if not ecole:
            raise CommandError(f"Ecole locale introuvable: {ecole_id}")

        try:
            if not options['pull_only']:
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
