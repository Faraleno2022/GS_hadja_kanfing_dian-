"""
Synchronisation automatique en arriere-plan (application Desktop).

Un thread daemon envoie (push) periodiquement les changements locaux en attente
puis recupere (pull) ceux des autres postes, via le serveur EN LIGNE configure.
Hors-ligne, chaque tentative echoue silencieusement et est reessayee a cadence
rapprochee : des que la connexion revient, la synchronisation se fait
automatiquement, sans action de l'utilisateur.

La logique push/pull est appelee DIRECTEMENT (et non via `call_command`) afin
de rester fiable dans l'executable PyInstaller, ou la decouverte des commandes
de management n'est pas garantie.

Configuration par machine (aucune recompilation) : fichier `sync_config.json`
charge par run_server.py -> reglages MYSCHOOL_SYNC_SERVER_URL / _ECOLE_ID /
_DEVICE_ID / _TOKEN. Voir `sync_config.example.json`.
"""
import json
import os
import threading
import time
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

_started = False
_lock = threading.Lock()


# ─── Etat local (pull incremental) ────────────────────────────────────────────
def _state_path() -> str:
    base = os.environ.get('MYSCHOOL_BASE_DIR') or os.getcwd()
    return os.path.join(base, '.sync_state.json')


def _load_since_id():
    try:
        with open(_state_path(), 'r', encoding='utf-8') as f:
            return json.load(f).get('since_id')
    except Exception:
        return None


def _save_since_id(value) -> None:
    if not value:
        return
    try:
        with open(_state_path(), 'w', encoding='utf-8') as f:
            json.dump({'since_id': value}, f)
    except Exception:
        pass


# ─── Client HTTP ──────────────────────────────────────────────────────────────
def _request_json(url, device_id, token, payload=None, method='POST', timeout=45):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urlrequest.Request(
        url,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'X-Sync-Device': device_id,
            'X-Sync-Token': token,
        },
        method=method,
    )
    with urlrequest.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


# ─── Configuration ────────────────────────────────────────────────────────────
def _config():
    """Retourne (server, device_id, token, ecole_id) ou None si incomplet."""
    try:
        from django.conf import settings
    except Exception:
        return None
    server = (getattr(settings, 'MYSCHOOL_SYNC_SERVER_URL', '') or '').rstrip('/')
    device_id = getattr(settings, 'MYSCHOOL_SYNC_DEVICE_ID', '') or ''
    token = getattr(settings, 'MYSCHOOL_SYNC_TOKEN', '') or ''
    ecole_id = getattr(settings, 'MYSCHOOL_SYNC_ECOLE_ID', '') or ''
    if server and device_id and token and ecole_id:
        return server, device_id, token, ecole_id
    return None


def _is_configured() -> bool:
    return _config() is not None


# ─── Une passe de synchronisation ─────────────────────────────────────────────
def _push(server, device_id, token, ecole):
    from django.utils import timezone
    from .models import SyncChange
    pending = list(
        SyncChange.objects
        .filter(ecole=ecole, statut=SyncChange.STATUT_PENDING)
        .order_by('id')[:200]
    )
    if not pending:
        return 0
    response = _request_json(
        f'{server}/api/v1/sync/push/', device_id, token,
        {
            'changes': [
                {
                    'model': c.model_label,
                    'object_uuid': str(c.object_uuid) if c.object_uuid else None,
                    'operation': c.operation,
                    'payload': c.payload,
                }
                for c in pending
            ]
        },
    )
    if not response.get('ok'):
        return 0
    accepted = {item['index'] for item in response.get('accepted', [])}
    now = timezone.now()
    updated = 0
    for index, change in enumerate(pending):
        if index in accepted:
            change.statut = SyncChange.STATUT_APPLIED
            change.date_application = now
            change.save(update_fields=['statut', 'date_application'])
            updated += 1
    return updated


def _pull(server, device_id, token, ecole):
    from .models import SyncChange
    from .engine import apply_sync_change
    since_id = _load_since_id()
    suffix = f'?since_id={since_id}' if since_id else ''
    response = _request_json(
        f'{server}/api/v1/sync/pull/{suffix}', device_id, token,
        payload=None, method='GET',
    )
    if not response.get('ok'):
        return 0
    created = 0
    for item in response.get('changes', []):
        server_change_id = item.get('id')
        if server_change_id and SyncChange.objects.filter(
            ecole=ecole, payload__server_change_id=server_change_id,
        ).exists():
            continue
        payload = item.get('payload') or {}
        if server_change_id:
            payload = {**payload, 'server_change_id': server_change_id}
        change = SyncChange.objects.create(
            ecole=ecole,
            model_label=item['model_label'],
            object_uuid=item.get('object_uuid') or None,
            operation=item['operation'],
            payload=payload,
        )
        try:
            apply_sync_change(change)
            created += 1
        except Exception as exc:
            change.statut = SyncChange.STATUT_FAILED
            change.erreur = str(exc)
            change.save(update_fields=['statut', 'erreur'])
    _save_since_id(response.get('latest_change_id'))
    return created


def _run_once() -> bool:
    """Une passe push + pull. Retourne True si le serveur a repondu."""
    cfg = _config()
    if not cfg:
        return False
    server, device_id, token, ecole_id = cfg
    try:
        from eleves.models import Ecole
        ecole = Ecole.objects.filter(pk=ecole_id).first()
        if not ecole:
            return False
        _push(server, device_id, token, ecole)
        _pull(server, device_id, token, ecole)
        return True
    except (HTTPError, URLError, OSError):
        # Hors-ligne ou serveur injoignable -> reessai au prochain cycle.
        return False
    except Exception:
        return False


# ─── Worker ───────────────────────────────────────────────────────────────────
def _worker(interval: int, boot_delay: int):
    time.sleep(max(0, boot_delay))  # laisser Django + le serveur demarrer
    fast = max(10, min(interval, 20))  # reessai rapproche quand hors-ligne
    while True:
        try:
            if not _is_configured():
                time.sleep(interval * 10)  # poste non configure -> veille longue
                continue
            ok = _run_once()
        except Exception:
            ok = False
        # En ligne : cadence normale. Hors-ligne : reessai rapide pour
        # rattraper des que la connexion revient.
        time.sleep(interval if ok else fast)


def start(interval: int = 60, boot_delay: int = 20) -> bool:
    """
    Demarre le worker de synchronisation automatique (idempotent).

    interval    : secondes entre deux synchros lorsque le serveur repond.
    boot_delay  : delai initial avant la premiere tentative.
    Retourne True si le thread vient d'etre demarre.
    """
    global _started
    with _lock:
        if _started:
            return False
        _started = True
    thread = threading.Thread(
        target=_worker, args=(interval, boot_delay),
        name='auto-sync', daemon=True,
    )
    thread.start()
    return True
