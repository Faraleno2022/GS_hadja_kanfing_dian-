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
    """Recupere tous les changements disponibles depuis since_id, par pages, jusqu'a vidage."""
    if apply_change is None:
        from .engine import apply_sync_change
        apply_change = apply_sync_change

    total = 0
    current_since = since_id
    for _ in range(MAX_CYCLES_PAR_APPEL):
        params = {}
        if current_since:
            params['since_id'] = current_since
        if initial and not current_since:
            params['initial'] = '1'

        response = _get_json(f'{server_url}/api/v1/sync/pull/', device_id, token, params=params)
        if not response.get('ok'):
            raise SyncTransportError(response.get('error') or 'Pull refuse.')

        items = response.get('changes', [])
        for item in items:
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
                apply_change(change)
                total += 1
            except Exception as exc:
                change.statut = SyncChange.STATUT_FAILED
                change.erreur = str(exc)
                change.save(update_fields=['statut', 'erreur'])

        latest_id = response.get('latest_change_id')
        if latest_id:
            current_since = latest_id
        initial = False

        if len(items) < PULL_PAGE_SIZE:
            break
    return total
