"""Transport HTTP rapide pour la synchronisation offline <-> serveur.

Reutilise une session `requests` (connexions persistantes, keep-alive) au lieu
d'ouvrir une connexion TCP/TLS par appel, compresse les gros payloads en gzip,
et boucle jusqu'a vidage complet de la file (au lieu de s'arreter a une seule
page de 200 changements).
"""
import gzip
import json
import threading

import requests
from requests.adapters import HTTPAdapter

from .models import SyncChange


PUSH_BATCH_SIZE = 300
PULL_PAGE_SIZE = 500
MAX_CYCLES_PAR_APPEL = 25  # garde-fou anti-boucle-infinie
GZIP_SEUIL_OCTETS = 512

_session = None
_session_lock = threading.Lock()


class SyncTransportError(Exception):
    pass


def _get_session():
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                session = requests.Session()
                adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                _session = session
    return _session


def _headers(device_id, token, gzip_body=False):
    headers = {
        'X-Sync-Device': device_id,
        'X-Sync-Token': token,
        'Accept-Encoding': 'gzip',
    }
    if gzip_body:
        headers['Content-Encoding'] = 'gzip'
        headers['Content-Type'] = 'application/json'
    elif gzip_body is not None:
        headers['Content-Type'] = 'application/json'
    return headers


def _post_json(url, device_id, token, payload, timeout=25):
    session = _get_session()
    body = json.dumps(payload).encode('utf-8')
    compress = len(body) > GZIP_SEUIL_OCTETS
    if compress:
        body = gzip.compress(body, compresslevel=6)
    try:
        response = session.post(url, data=body, headers=_headers(device_id, token, compress), timeout=timeout)
    except requests.RequestException as exc:
        raise SyncTransportError(f"Serveur de synchronisation inaccessible: {exc}") from exc
    return _parse_response(response)


def _get_json(url, device_id, token, params=None, timeout=25):
    session = _get_session()
    try:
        response = session.get(url, params=params, headers=_headers(device_id, token, gzip_body=None), timeout=timeout)
    except requests.RequestException as exc:
        raise SyncTransportError(f"Serveur de synchronisation inaccessible: {exc}") from exc
    return _parse_response(response)


def _parse_response(response):
    try:
        data = response.json()
    except ValueError as exc:
        raise SyncTransportError(f"Reponse serveur invalide (HTTP {response.status_code}).") from exc
    if response.status_code >= 400:
        raise SyncTransportError(data.get('error') or f"Erreur serveur {response.status_code}")
    return data


def push_pending(server_url, device_id, token, ecole, batch_size=PUSH_BATCH_SIZE):
    """Envoie tous les changements PENDING de l'ecole, par lots, jusqu'a vidage."""
    total = 0
    for _ in range(MAX_CYCLES_PAR_APPEL):
        pending = list(
            SyncChange.objects
            .filter(ecole=ecole, statut=SyncChange.STATUT_PENDING)
            .order_by('id')[:batch_size]
        )
        if not pending:
            break

        response = _post_json(
            f'{server_url}/api/v1/sync/push/',
            device_id, token,
            {
                'changes': [
                    {
                        'model': change.model_label,
                        'object_uuid': str(change.object_uuid) if change.object_uuid else None,
                        'operation': change.operation,
                        'payload': change.payload,
                    }
                    for change in pending
                ]
            },
        )
        if not response.get('ok'):
            raise SyncTransportError(response.get('error') or 'Push refuse.')

        accepted_indexes = {item['index'] for item in response.get('accepted', [])}
        from django.utils import timezone
        now = timezone.now()
        applied_ids = [c.id for i, c in enumerate(pending) if i in accepted_indexes]
        if applied_ids:
            SyncChange.objects.filter(id__in=applied_ids).update(statut=SyncChange.STATUT_APPLIED, date_application=now)
            total += len(applied_ids)

        if len(pending) < batch_size:
            break
    return total


def pull_changes(server_url, device_id, token, ecole, since_id=None, initial=False, apply_change=None):
    """Import paginé et reprenable ; un lot en échec ne fait jamais avancer le curseur."""
    from django.db import transaction
    from .models import SyncCheckpoint
    from .engine import build_change_instance
    if apply_change is None:
        from .engine import apply_sync_change
        apply_change = apply_sync_change
    checkpoint, _ = SyncCheckpoint.objects.get_or_create(device_id=device_id)
    if initial:
        checkpoint.initial_complete = False
        checkpoint.snapshot_cursor = ''
        checkpoint.save(update_fields=['initial_complete', 'snapshot_cursor'])
    if since_id is not None:
        checkpoint.last_change_id = int(since_id)
    total = 0
    for _ in range(MAX_CYCLES_PAR_APPEL):
        bootstrapping = not checkpoint.initial_complete
        params = {'since_id': checkpoint.last_change_id}
        if bootstrapping:
            params.update(initial='1', snapshot_version='2')
            if checkpoint.snapshot_cursor:
                params['snapshot_cursor'] = checkpoint.snapshot_cursor
        response = _get_json(f'{server_url}/api/v1/sync/pull/', device_id, token, params=params)
        if not response.get('ok'):
            raise SyncTransportError(response.get('error') or 'Pull refusé.')
        items = response.get('changes', [])
        if not isinstance(items, list):
            raise SyncTransportError('Lot de synchronisation invalide.')
        applied = 0
        try:
            with transaction.atomic():
                if ecole is None:
                    premier = items[0] if items else None
                    if not premier or premier.get('model_label') != 'eleves.Ecole':
                        raise SyncTransportError("École absente du premier lot reçu.")
                    ecole = build_change_instance(
                        'eleves.Ecole', premier.get('object_uuid'), premier.get('payload') or {},
                        trusted=True,
                    )
                for item in items:
                    server_change_id = item.get('id')
                    if server_change_id and SyncChange.objects.filter(
                        ecole=ecole, statut=SyncChange.STATUT_APPLIED,
                        payload__server_change_id=server_change_id,
                    ).exists():
                        continue
                    payload = item.get('payload') or {}
                    if server_change_id:
                        payload = {**payload, 'server_change_id': server_change_id}
                    change = SyncChange.objects.create(
                        ecole=ecole, model_label=item['model_label'],
                        object_uuid=item.get('object_uuid') or None,
                        operation=item['operation'], payload=payload,
                    )
                    apply_change(change)
                    applied += 1
                if bootstrapping:
                    next_cursor = response.get('next_snapshot_cursor') or ''
                    if next_cursor and next_cursor == checkpoint.snapshot_cursor:
                        raise SyncTransportError('Le curseur initial ne progresse pas.')
                    checkpoint.snapshot_cursor = next_cursor
                    checkpoint.initial_complete = not bool(next_cursor)
                    if checkpoint.initial_complete:
                        checkpoint.last_change_id = int(response.get('latest_change_id') or 0)
                else:
                    checkpoint.last_change_id = int(response.get('latest_change_id') or checkpoint.last_change_id)
                checkpoint.save()
        except Exception as exc:
            raise SyncTransportError(f"Lot non appliqué, reprise conservée : {exc}") from exc
        total += applied
        if bootstrapping:
            # Once the snapshot is complete, read changes made while it was being downloaded.
            continue
        if not response.get('has_more', len(items) >= PULL_PAGE_SIZE):
            break
    return total
