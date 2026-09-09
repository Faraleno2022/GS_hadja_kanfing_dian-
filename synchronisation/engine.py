from decimal import Decimal
from uuid import UUID

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone

from eleves.models import Ecole
from .context import mute_sync
from .registry import SYNC_MODEL_LABELS, SYNC_MODEL_SET
from .scope import scoped_queryset, school_for_instance, validate_scope, remember_school


SYNC_FIELD_NAMES = {
    'sync_uuid',
    'sync_created_at',
    'sync_updated_at',
    'sync_deleted_at',
    'sync_version',
    'is_synced',
}


def model_label_for(instance_or_model):
    model = instance_or_model if isinstance(instance_or_model, type) else instance_or_model.__class__
    return f'{model._meta.app_label}.{model.__name__}'


def is_sync_model(instance_or_model):
    return model_label_for(instance_or_model) in SYNC_MODEL_SET


def get_model(label):
    try:
        app_label, model_name = label.split('.', 1)
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return None


def serialize_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def serialize_instance(instance):
    payload = {}
    for field in instance._meta.concrete_fields:
        if field.name == 'id' or field.name in SYNC_FIELD_NAMES:
            continue
        value = getattr(instance, field.name)
        if isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField):
            related = value
            if related is None or field.remote_field.model == get_user_model():
                payload[field.name] = None
            else:
                payload[field.name] = {
                    'model': model_label_for(related),
                    'sync_uuid': str(getattr(related, 'sync_uuid', '') or ''),
                    'pk': related.pk,
                    'text': str(related),
                }
        elif isinstance(field, models.FileField):
            payload[field.name] = value.name if value else ''
        else:
            payload[field.name] = serialize_value(value)
    return payload


def resolve_related(field, raw_value):
    if not raw_value:
        return None
    model = field.remote_field.model
    if model == get_user_model():
        return None

    sync_uuid = raw_value.get('sync_uuid') if isinstance(raw_value, dict) else None
    if sync_uuid and hasattr(model, 'sync_uuid'):
        obj = model.objects.filter(sync_uuid=sync_uuid).first()
        return obj

    pk = raw_value.get('pk') if isinstance(raw_value, dict) else None
    if pk:
        return model.objects.filter(pk=pk).first()
    return None


def deserialize_field(field, raw_value):
    if isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField):
        return resolve_related(field, raw_value)
    if raw_value in ('', None):
        return None if field.null else raw_value
    return raw_value


def ecole_for_instance(instance):
    return school_for_instance(instance)


def _financial_keys(obj):
    if obj is None:
        return set()
    label = model_label_for(obj)
    if label == 'paiements.PaiementRemise':
        obj = obj.paiement
    if model_label_for(obj) in {'paiements.Paiement', 'paiements.EcheancierPaiement'}:
        return {(obj.eleve_id, obj.annee_scolaire)}
    return set()


@transaction.atomic
def build_change_instance(model_label, object_uuid, payload, *, operation='UPDATE', ecole=None, trusted=False):
    """Cree/met a jour l'objet cible depuis un changement, sans toucher a une
    ligne SyncChange.

    Extrait d'apply_sync_change() pour l'amorçage d'un poste tout juste
    installe : SyncChange.ecole est une cle etrangere obligatoire vers
    Ecole, donc aucune ligne SyncChange ne peut exister tant que l'ecole
    elle-meme n'a pas ete materialisee localement. Ce cas particulier
    (le tout premier changement d'un poste vide est justement l'ecole)
    doit pouvoir s'appliquer directement, en dehors de la file d'attente.
    """
    model = get_model(model_label)
    if not model or model_label not in SYNC_MODEL_SET:
        raise ValueError(f'Modele non synchronisable: {model_label}')

    if not isinstance(payload, dict):
        raise ValueError('Le payload doit être un objet JSON.')
    if not object_uuid:
        raw_uuid = (payload or {}).get('sync_uuid')
        object_uuid = UUID(str(raw_uuid)) if raw_uuid else None
    elif not isinstance(object_uuid, UUID):
        object_uuid = UUID(str(object_uuid))
    if not object_uuid:
        raise ValueError('sync_uuid manquant.')

    if not isinstance(payload, dict):
        raise ValueError('Le payload doit être un objet JSON.')
    if operation not in {'CREATE', 'UPDATE', 'DELETE'}:
        raise ValueError('Opération invalide.')
    if ecole is None and model_label != 'eleves.Ecole':
        raise ValueError('École obligatoire.')
    if model_label == 'eleves.Ecole' and ecole is not None and object_uuid != ecole.sync_uuid:
        raise ValueError("L'appareil ne peut créer une autre école.")
    if model_label == 'eleves.Ecole' and operation == 'DELETE':
        raise ValueError("La suppression d'une école ne passe pas par la synchronisation.")

    with mute_sync():
        obj = model.objects.select_for_update().filter(sync_uuid=object_uuid).first()
        if obj is not None and ecole is not None:
            validate_scope(obj, ecole, existing=True, trusted=trusted)
        keys = _financial_keys(obj)
        ancienne_classe = obj.classe if obj is not None and model_label == 'eleves.Eleve' else None
        if operation == 'DELETE':
            if obj:
                obj.delete()
        else:
            if obj is None:
                obj = model(sync_uuid=object_uuid)
            for field in model._meta.concrete_fields:
                if field.primary_key or field.name in SYNC_FIELD_NAMES or field.name not in payload:
                    continue
                # The server owns approval. A stale desktop snapshot must not
                # change it or prevent unrelated school updates from syncing.
                if model_label == 'eleves.Ecole' and field.name == 'etat' and not trusted:
                    continue
                # User IDs differ between machines. Never accept identities from a device.
                if isinstance(field, models.ForeignKey) and field.remote_field.model == get_user_model():
                    continue
                raw_value = payload[field.name]
                value = deserialize_field(field, raw_value)
                if isinstance(field, models.ForeignKey):
                    if raw_value and value is None:
                        raise ValueError(f"Relation introuvable pour {field.name}.")
                    if value is None and not field.null:
                        raise ValueError(f"Relation obligatoire : {field.name}.")
                else:
                    value = field.to_python(value)
                setattr(obj, field.name, value)
            if ecole is not None:
                validate_scope(obj, ecole, trusted=trusted)
            if model_label == 'paiements.Paiement' and obj.montant < 0:
                raise ValueError('Le montant du paiement ne peut pas être négatif.')
            obj.is_synced = True
            obj.sync_version = getattr(obj, 'sync_version', 1) + 1
            obj.save()
            if ecole is not None:
                remember_school(obj, ecole)
            keys |= _financial_keys(obj)
            if ancienne_classe is not None and ancienne_classe.pk != obj.classe_id:
                from paiements.services import reconcilier_transfert_classe
                reconcilier_transfert_classe(obj, ancienne_classe, obj.classe)
        from paiements.services import synchroniser_echeancier_apres_changement_paiement
        for eleve_id, annee in sorted(keys):
            synchroniser_echeancier_apres_changement_paiement(eleve_id, annee)
        return None if operation == 'DELETE' else obj


@transaction.atomic
def apply_sync_change(change):
    obj = build_change_instance(
        change.model_label, change.object_uuid, change.payload,
        operation=change.operation, ecole=change.ecole, trusted=change.device_id is None,
    )
    change.statut = change.STATUT_APPLIED
    change.date_application = timezone.now()
    change.erreur = ''
    change.save(update_fields=['statut', 'date_application', 'erreur'])
    return obj


def queryset_for_ecole(model, ecole):
    return scoped_queryset(model, ecole)


def snapshot_changes_for_ecole(ecole):
    snapshot = []
    for label in SYNC_MODEL_LABELS:
        model = get_model(label)
        if not model:
            continue
        for obj in queryset_for_ecole(model, ecole).order_by('pk').iterator():
            snapshot.append({
                'id': None,
                'model': label,
                'model_label': label,
                'object_uuid': str(obj.sync_uuid),
                'operation': 'UPDATE',
                'payload': {**serialize_instance(obj), 'sync_uuid': str(obj.sync_uuid)},
                'device_id': None,
                'device_name': 'Snapshot initial',
                'date_creation': timezone.now().isoformat(),
            })
    return snapshot


def snapshot_page_for_ecole(ecole, cursor=None, page_size=500):
    """Pages ordonnées par modèle puis PK ; le curseur conserve le point de reprise."""
    from django.core import signing
    from django.db.models import Max, Q
    from .models import SyncChange
    if cursor:
        try:
            state = signing.loads(cursor, salt='sync-snapshot-v2', max_age=86400)
            if state['school'] != str(ecole.sync_uuid):
                raise ValueError('École du curseur invalide.')
            index, last_pk, watermark = state['model'], state['pk'], state['watermark']
            if not isinstance(index, int) or not 0 <= index < len(SYNC_MODEL_LABELS) or not isinstance(last_pk, int) or last_pk < 0:
                raise ValueError('Curseur invalide.')
        except (signing.BadSignature, KeyError, TypeError) as exc:
            raise ValueError('Curseur de synchronisation invalide ou expiré.') from exc
    else:
        index, last_pk = 0, 0
        watermark = SyncChange.objects.filter(ecole=ecole).filter(Q(statut=SyncChange.STATUT_APPLIED) | Q(device__isnull=True, statut=SyncChange.STATUT_PENDING)).aggregate(n=Max('pk'))['n'] or 0
    rows = []
    while index < len(SYNC_MODEL_LABELS):
        label = SYNC_MODEL_LABELS[index]
        model = get_model(label)
        objects = list(queryset_for_ecole(model, ecole).filter(pk__gt=last_pk).order_by('pk')[:page_size-len(rows)]) if model else []
        for obj in objects:
            rows.append({
                'id': None, 'model': label, 'model_label': label,
                'object_uuid': str(obj.sync_uuid), 'operation': 'UPDATE',
                'payload': {**serialize_instance(obj), 'sync_uuid': str(obj.sync_uuid)},
                'device_id': None, 'device_name': 'Snapshot initial',
                'date_creation': timezone.now().isoformat(),
            })
            last_pk = obj.pk
        if len(rows) == page_size:
            next_cursor = signing.dumps({
                'school': str(ecole.sync_uuid), 'model': index, 'pk': last_pk,
                'watermark': watermark,
            }, salt='sync-snapshot-v2')
            return rows, next_cursor, watermark
        index += 1
        last_pk = 0
    return rows, None, watermark
