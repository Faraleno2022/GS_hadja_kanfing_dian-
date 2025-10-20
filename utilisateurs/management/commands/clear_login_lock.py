from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache

class Command(BaseCommand):
    help = "Clear login lock and failed attempts counters for a given IP and/or username."

    def add_arguments(self, parser):
        parser.add_argument('--ip', type=str, help='Client IP address to clear (e.g., 127.0.0.1)')
        parser.add_argument('--username', type=str, help='Username to clear (case-insensitive)')

    def handle(self, *args, **options):
        ip = options.get('ip')
        username = (options.get('username') or '')
        if not ip and not username:
            raise CommandError('Provide at least --ip or --username')

        keys = []
        if ip and username:
            uname = username.lower()
            keys += [
                f'failed_login_{ip}',
                f'failed_login_{ip}_{uname}',
                f'blocked_login_{ip}',
                f'blocked_login_{ip}_{uname}',
            ]
        elif ip:
            keys += [
                f'failed_login_{ip}',
                f'blocked_login_{ip}',
            ]
        else:  # username only: clear all IP-specific keys is not possible without IP; clear generic patterns is backend-dependent
            uname = username.lower()
            # Attempt to clear known keys if cache backend exposes keys (may not always be available)
            try:
                for k in list(getattr(cache, '_cache', {}).keys()):
                    if isinstance(k, str) and (k.endswith(f'_{uname}') or k.startswith('failed_login_') or k.startswith('blocked_login_')):
                        keys.append(k)
            except Exception:
                self.stdout.write(self.style.WARNING('Cache backend does not expose keys; provide --ip for precise clearing.'))

        cleared = 0
        for k in set(keys):
            try:
                if cache.get(k) is not None:
                    cache.delete(k)
                    cleared += 1
            except Exception:
                pass
        self.stdout.write(self.style.SUCCESS(f'Cleared {cleared} cache entrie(s).'))
