import json
import secrets
from uuid import UUID

from django.conf import settings
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from eleves.models import Ecole
from utilisateurs.utils import user_is_admin, user_school

from .models import SyncChange, SyncDevice


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _current_school(user, data=None):
    if user and user.is_authenticated and user.is_superuser and data and data.get('ecole_id'):
        return Ecole.objects.filter(pk=data['ecole_id']).first()
    if user and user.is_authenticated:
        return user_school(user)
    if data and data.get('ecole_id'):
        return Ecole.objects.filter(pk=data['ecole_id']).first()
    return None


def _has_sync_admin_access(request):
    token = request.headers.get('X-Sync-Admin-Token', '')
    expected = getattr(settings, 'MYSCHOOL_SYNC_ADMIN_TOKEN', '')
    if expected and token and secrets.compare_digest(token, expected):
        return True
    user = getattr(request, 'user', None)
    return bool(user and user.is_authenticated and user_is_admin(user))


def _device_from_headers(request):
    device_id = request.headers.get('X-Sync-Device')
    token = request.headers.get('X-Sync-Token')
    if not device_id or not token:
        return None, JsonResponse({'ok': False, 'error': 'Identifiants de synchronisation manquants.'}, status=401)
    try:
        UUID(device_id)
    except ValueError:
        return None, JsonResponse({'ok': False, 'error': 'Identifiant appareil invalide.'}, status=400)

    device = SyncDevice.objects.select_related('ecole').filter(device_id=device_id, actif=True).first()
    if not device or not device.verifier_token(token):
        return None, JsonResponse({'ok': False, 'error': 'Appareil non autorise.'}, status=403)
    device.marquer_connexion()
    return device, None


@require_GET
def health(request):
    return JsonResponse({
        'ok': True,
        'service': 'myschoolgn-sync',
        'version': 1,
        'server_time': timezone.now().isoformat(),
    })


@csrf_exempt
@require_POST
def register_device(request):
    if not _has_sync_admin_access(request):
        return JsonResponse({'ok': False, 'error': 'Permission refusee.'}, status=403)

    data = _json_body(request)
    if data is None:
        return JsonResponse({'ok': False, 'error': 'JSON invalide.'}, status=400)

    ecole = _current_school(request.user, data)
    if not ecole:
        return JsonResponse({'ok': False, 'error': 'Aucune ecole associee a cet utilisateur.'}, status=400)

    nom = (data.get('nom') or data.get('name') or 'Poste local').strip()[:120]
    token = secrets.token_urlsafe(32)
    device = SyncDevice(ecole=ecole, nom=nom)
    device.definir_token(token)
    device.save()

    return JsonResponse({
        'ok': True,
        'device_id': str(device.device_id),
        'sync_token': token,
        'ecole_id': ecole.id,
        'message': 'Conservez ce token sur le poste local. Il ne sera plus affiche.',
    }, status=201)


@csrf_exempt
@require_POST
def push(request):
    device, error_response = _device_from_headers(request)
    if error_response:
        return error_response

    data = _json_body(request)
    if data is None:
        return JsonResponse({'ok': False, 'error': 'JSON invalide.'}, status=400)

    changes = data.get('changes', [])
    if not isinstance(changes, list):
        return JsonResponse({'ok': False, 'error': 'Le champ changes doit etre une liste.'}, status=400)

    accepted = []
    rejected = []
    valid_operations = {choice[0] for choice in SyncChange.OPERATION_CHOICES}

    for index, change in enumerate(changes):
        if not isinstance(change, dict):
            rejected.append({'index': index, 'error': 'Changement invalide.'})
            continue

        operation = (change.get('operation') or '').upper()
        model_label = (change.get('model') or change.get('model_label') or '').strip()
        payload = change.get('payload') or {}
        raw_uuid = change.get('object_uuid')

        if operation not in valid_operations:
            rejected.append({'index': index, 'error': 'Operation invalide.'})
            continue
        if not model_label:
            rejected.append({'index': index, 'error': 'Modele manquant.'})
            continue
        if not isinstance(payload, dict):
            rejected.append({'index': index, 'error': 'Payload invalide.'})
            continue

        object_uuid = None
        if raw_uuid:
            try:
                object_uuid = UUID(str(raw_uuid))
            except ValueError:
                rejected.append({'index': index, 'error': 'UUID objet invalide.'})
                continue

        sync_change = SyncChange.objects.create(
            ecole=device.ecole,
            device=device,
            model_label=model_label[:120],
            object_uuid=object_uuid,
            operation=operation,
            payload=payload,
        )
        accepted.append({'index': index, 'change_id': sync_change.id})

    return JsonResponse({
        'ok': True,
        'accepted_count': len(accepted),
        'rejected_count': len(rejected),
        'accepted': accepted,
        'rejected': rejected,
        'server_time': timezone.now().isoformat(),
    })


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def pull(request):
    device, error_response = _device_from_headers(request)
    if error_response:
        return error_response

    since = request.GET.get('since')
    since_id = request.GET.get('since_id')
    if request.method == 'POST':
        data = _json_body(request)
        if data is None:
            return JsonResponse({'ok': False, 'error': 'JSON invalide.'}, status=400)
        since = data.get('since') or since
        since_id = data.get('since_id') or since_id

    changes = SyncChange.objects.filter(ecole=device.ecole).exclude(device=device)
    if since_id:
        try:
            changes = changes.filter(id__gt=int(since_id))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'since_id invalide.'}, status=400)
    elif since:
        parsed_since = parse_datetime(str(since))
        if not parsed_since:
            return JsonResponse({'ok': False, 'error': 'since invalide. Utilisez une date ISO ou since_id.'}, status=400)
        if timezone.is_naive(parsed_since):
            parsed_since = timezone.make_aware(parsed_since, timezone.get_current_timezone())
        changes = changes.filter(date_creation__gt=parsed_since)

    changes = changes.order_by('id')[:200]
    serialized_changes = [
        {
            'id': change.id,
            'model': change.model_label,
            'model_label': change.model_label,
            'object_uuid': str(change.object_uuid) if change.object_uuid else None,
            'operation': change.operation,
            'payload': change.payload,
            'device_id': str(change.device.device_id) if change.device else None,
            'device_name': change.device.nom if change.device else None,
            'date_creation': change.date_creation.isoformat(),
        }
        for change in changes
    ]

    return JsonResponse({
        'ok': True,
        'device_id': str(device.device_id),
        'ecole_id': device.ecole_id,
        'since': since,
        'since_id': since_id,
        'changes': serialized_changes,
        'latest_change_id': serialized_changes[-1]['id'] if serialized_changes else since_id,
        'server_time': timezone.now().isoformat(),
    })
