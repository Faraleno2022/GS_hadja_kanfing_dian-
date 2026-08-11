"""Alimente automatiquement la corbeille mémoire des modifications.

Les modèles listés dans ``MODELES_SUIVIS`` sont surveillés : à chaque
enregistrement, l'état précédent est relu en base puis comparé au nouvel état,
et seuls les champs réellement modifiés sont journalisés.
"""

import logging

from django.apps import apps as django_apps
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# 'app_label.ModelName' des objets métier dont on trace les modifications
MODELES_SUIVIS = {
    'eleves.Eleve',
    'eleves.Responsable',
    'eleves.Classe',
    'eleves.Ecole',
    'eleves.GrilleTarifaire',
    'paiements.Paiement',
    'paiements.EcheancierPaiement',
    'paiements.RemiseReduction',
    'paiements.PaiementRemise',
    'bus.AbonnementBus',
    'bus.AbonnementCantine',
    'depenses.Depense',
    'salaires.Enseignant',
    'salaires.EtatSalaire',
}

# Champs purement techniques : leur variation n'a pas d'intérêt fonctionnel
CHAMPS_IGNORES = {
    'date_modification', 'updated_at', 'sync_updated_at', 'sync_version',
    'is_synced', 'date_creation', 'created_at', 'sync_created_at',
}

_ATTRIBUT_ETAT = '_audit_etat_avant'


def _est_suivi(sender):
    try:
        # Ignorer les modèles historiques utilisés pendant les migrations
        if getattr(sender._meta, 'apps', django_apps) is not django_apps:
            return False
        return f'{sender._meta.app_label}.{sender.__name__}' in MODELES_SUIVIS
    except Exception:
        return False


@receiver(pre_save)
def memoriser_etat_avant(sender, instance, **kwargs):
    if kwargs.get('raw') or not _est_suivi(sender) or not instance.pk:
        return
    from .audit import capturer_etat

    try:
        precedent = sender.objects.filter(pk=instance.pk).first()
        setattr(instance, _ATTRIBUT_ETAT, capturer_etat(precedent) if precedent else None)
    except Exception:
        setattr(instance, _ATTRIBUT_ETAT, None)


@receiver(post_save)
def journaliser_enregistrement(sender, instance, created, **kwargs):
    if kwargs.get('raw') or not _est_suivi(sender):
        return
    from .audit import capturer_etat, comparer_etats, enregistrer_modification
    from .middleware.audit import get_current_request
    from .models import JournalModification

    request = get_current_request()

    try:
        if created:
            enregistrer_modification(
                instance, {}, request=request,
                action=JournalModification.ACTION_CREATION,
            )
            return

        avant = getattr(instance, _ATTRIBUT_ETAT, None)
        if avant is None:
            return

        changements = comparer_etats(avant, capturer_etat(instance))
        for champ in list(changements):
            if champ in CHAMPS_IGNORES:
                del changements[champ]

        enregistrer_modification(instance, changements, request=request)
    except Exception:
        logger.exception("Journalisation de la modification impossible")
    finally:
        if hasattr(instance, _ATTRIBUT_ETAT):
            delattr(instance, _ATTRIBUT_ETAT)


@receiver(post_delete)
def journaliser_suppression(sender, instance, **kwargs):
    if not _est_suivi(sender):
        return
    from .audit import capturer_etat, enregistrer_modification
    from .middleware.audit import get_current_request
    from .models import JournalModification

    try:
        etat = capturer_etat(instance)
        enregistrer_modification(
            instance,
            {champ: {'avant': valeur, 'apres': None} for champ, valeur in etat.items()},
            request=get_current_request(),
            action=JournalModification.ACTION_SUPPRESSION,
        )
    except Exception:
        logger.exception("Journalisation de la suppression impossible")
