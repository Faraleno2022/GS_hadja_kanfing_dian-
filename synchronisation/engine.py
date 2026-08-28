from decimal import Decimal
from uuid import UUID

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from eleves.models import Ecole
from .context import mute_sync
from .registry import SYNC_MODEL_LABELS, SYNC_MODEL_SET


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
        if obj:
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
    if isinstance(instance, Ecole):
        return instance
    if hasattr(instance, 'ecole_id') and getattr(instance, 'ecole_id'):
        return instance.ecole
    if hasattr(instance, 'classe') and getattr(instance, 'classe_id', None):
        classe = instance.classe
        if hasattr(classe, 'ecole_id'):
            return classe.ecole
    if hasattr(instance, 'eleve') and getattr(instance, 'eleve_id', None):
        eleve = instance.eleve
        if getattr(eleve, 'classe_id', None):
            return eleve.classe.ecole
    if hasattr(instance, 'paiement') and getattr(instance, 'paiement_id', None):
        paiement = instance.paiement
        if getattr(paiement, 'eleve_id', None) and getattr(paiement.eleve, 'classe_id', None):
            return paiement.eleve.classe.ecole
    if hasattr(instance, 'depense') and getattr(instance, 'depense_id', None):
        return Ecole.objects.order_by('id').first()
    return Ecole.objects.order_by('id').first()


def build_change_instance(model_label, object_uuid, payload, *, operation='UPDATE'):
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

    if not object_uuid:
        raw_uuid = (payload or {}).get('sync_uuid')
        object_uuid = UUID(str(raw_uuid)) if raw_uuid else None
    elif not isinstance(object_uuid, UUID):
        object_uuid = UUID(str(object_uuid))
    if not object_uuid:
        raise ValueError('sync_uuid manquant.')

    with mute_sync():
        obj = model.objects.filter(sync_uuid=object_uuid).first()
        if operation == 'DELETE':
            if obj:
                obj.delete()
            return None

        if obj is None:
            obj = model(sync_uuid=object_uuid)

        for field in model._meta.concrete_fields:
            if field.name == 'id' or field.name in SYNC_FIELD_NAMES:
                continue
            if field.name not in payload:
                continue
            value = deserialize_field(field, payload.get(field.name))
            if value is None and not field.null and not field.blank and isinstance(field, (models.ForeignKey, models.OneToOneField)):
                raise ValueError(f"Relation introuvable pour {field.name}.")
            setattr(obj, field.name, value)

        obj.is_synced = True
        obj.sync_version = getattr(obj, 'sync_version', 1) + 1
        obj.save()
        return obj


def apply_sync_change(change):
    if change.operation == 'DELETE':
        build_change_instance(change.model_label, change.object_uuid, change.payload, operation='DELETE')
        change.statut = change.STATUT_APPLIED
        change.date_application = timezone.now()
        change.erreur = ''
        change.save(update_fields=['statut', 'date_application', 'erreur'])
        return None

    obj = build_change_instance(change.model_label, change.object_uuid, change.payload, operation=change.operation)

    change.statut = change.STATUT_APPLIED
    change.date_application = timezone.now()
    change.erreur = ''
    change.save(update_fields=['statut', 'date_application', 'erreur'])
    return obj


def queryset_for_ecole(model, ecole):
    label = model_label_for(model)
    if label == 'eleves.Ecole':
        return model.objects.filter(pk=ecole.pk)
    if label in {
        'eleves.Classe',
        'eleves.GrilleTarifaire',
        'notes.ClasseNote',
        'notes.ThemeBulletin',
        'salaires.Enseignant',
        'salaires.PeriodeSalaire',
    }:
        return model.objects.filter(ecole=ecole)
    if label == 'eleves.Eleve':
        return model.objects.filter(classe__ecole=ecole)
    if label == 'eleves.HistoriqueEleve':
        return model.objects.filter(eleve__classe__ecole=ecole)
    if label == 'eleves.Responsable':
        return model.objects.all()
    if label.startswith('paiements.'):
        if label in {'paiements.TypePaiement', 'paiements.ModePaiement', 'paiements.RemiseReduction'}:
            return model.objects.all()
        if hasattr(model, 'eleve'):
            return model.objects.filter(eleve__classe__ecole=ecole)
        if label == 'paiements.PaiementRemise':
            return model.objects.filter(paiement__eleve__classe__ecole=ecole)
        if label == 'paiements.ConfigurationPaiement':
            return model.objects.filter(classe__ecole=ecole)
    if label.startswith('depenses.'):
        return model.objects.all()
    if label == 'bus.GrilleTarifaireBus':
        return model.objects.filter(ecole=ecole)
    if label.startswith('bus.'):
        return model.objects.filter(eleve__classe__ecole=ecole)
    if label.startswith('salaires.'):
        if hasattr(model, 'enseignant'):
            return model.objects.filter(enseignant__ecole=ecole)
        if hasattr(model, 'periode'):
            return model.objects.filter(periode__ecole=ecole)
        if hasattr(model, 'etat_salaire'):
            return model.objects.filter(etat_salaire__periode__ecole=ecole)
        if hasattr(model, 'classe'):
            return model.objects.filter(classe__ecole=ecole)
    if label.startswith('abonnements.'):
        if label in {'abonnements.TypeAbonnement', 'abonnements.Itineraire', 'abonnements.MenuCantine'}:
            return model.objects.all()
        if hasattr(model, 'eleve'):
            return model.objects.filter(eleve__classe__ecole=ecole)
        if hasattr(model, 'abonnement'):
            return model.objects.filter(abonnement__eleve__classe__ecole=ecole)
    if label.startswith('rapports.'):
        return model.objects.all()
    if label.startswith('notes.'):
        if hasattr(model, 'classe'):
            return model.objects.filter(classe__ecole=ecole)
        if hasattr(model, 'matiere'):
            return model.objects.filter(matiere__classe__ecole=ecole)
        if hasattr(model, 'evaluation'):
            if label in {'notes.AnalyseTravailMaternelle', 'notes.RecommandationMaternelle'}:
                return model.objects.filter(evaluation__classe__ecole=ecole)
            return model.objects.filter(evaluation__matiere__classe__ecole=ecole)
        if hasattr(model, 'eleve'):
            return model.objects.filter(eleve__classe__ecole=ecole)
        if hasattr(model, 'activite'):
            return model.objects.filter(activite__eleve__classe__ecole=ecole)
    return model.objects.none()


def snapshot_changes_for_ecole(ecole):
    snapshot = []
    for label in SYNC_MODEL_LABELS:
        model = get_model(label)
        if not model:
            continue
        for obj in queryset_for_ecole(model, ecole).order_by('pk')[:5000]:
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
