from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .context import sync_is_muted
from .engine import ecole_for_instance, is_sync_model, model_label_for, serialize_instance
from .models import SyncChange


@receiver(post_save)
def create_sync_change_on_save(sender, instance, created, **kwargs):
    if sync_is_muted() or not is_sync_model(instance):
        return

    ecole = ecole_for_instance(instance)
    if not ecole:
        return

    SyncChange.objects.create(
        ecole=ecole,
        model_label=model_label_for(instance),
        object_uuid=instance.sync_uuid,
        operation=SyncChange.OPERATION_CREATE if created else SyncChange.OPERATION_UPDATE,
        payload=serialize_instance(instance),
    )


@receiver(pre_delete)
def create_sync_change_on_delete(sender, instance, **kwargs):
    if sync_is_muted() or not is_sync_model(instance):
        return

    ecole = ecole_for_instance(instance)
    if not ecole:
        return

    SyncChange.objects.create(
        ecole=ecole,
        model_label=model_label_for(instance),
        object_uuid=instance.sync_uuid,
        operation=SyncChange.OPERATION_DELETE,
        payload={'sync_uuid': str(instance.sync_uuid)},
    )
