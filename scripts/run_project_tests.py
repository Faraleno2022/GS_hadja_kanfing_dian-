"""Tests du projet sur SQLite en mémoire, fichiers temporaires et réseau désactivé."""
import argparse
from contextlib import ExitStack
import logging
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'ecole_moderne.settings'
os.environ['TWILIO_ENABLED'] = 'false'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--schema', action='store_true', help='Vérifier et appliquer les migrations à une base temporaire.')
parser.add_argument('labels', nargs='*')
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix='myschool-tests-') as scratch, ExitStack() as cleanup:
    cleanup.callback(logging.shutdown)
    import django
    from django.conf import settings
    settings.DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
        'TEST': {'MIGRATE': False},
    }}
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.MEDIA_ROOT = str(Path(scratch) / 'media')
    settings.TWILIO_ENABLED = False
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    for handler in settings.LOGGING.get('handlers', {}).values():
        if 'filename' in handler:
            handler['filename'] = str(Path(scratch) / Path(handler['filename']).name)
    with patch.object(socket.socket, 'connect', side_effect=OSError('Réseau désactivé pour les tests')):
        django.setup()
        from django.core.management import call_command
        if args.schema:
            call_command('check')
            call_command('makemigrations', check=True, dry_run=True, interactive=False)
            call_command('migrate', interactive=False)
        else:
            from django.test.runner import DiscoverRunner
            labels = args.labels or [
                'abonnements', 'administration', 'bus', 'chatbot', 'comptes',
                'depenses', 'eleves', 'notes', 'paiements', 'presence', 'rapports',
                'salaires', 'synchronisation', 'utilisateurs', 'ecole_moderne',
                'test_desktop_updater',
            ]
            failures = DiscoverRunner(verbosity=1, interactive=False).run_tests(labels)
            raise SystemExit(bool(failures))
