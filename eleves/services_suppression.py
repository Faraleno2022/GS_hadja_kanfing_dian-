"""Suppression complete d'une ecole.

Supprimer une ecole echouait dans deux cas :

* des modeles pointent vers `Ecole` (ou vers ses enfants) en `on_delete=PROTECT`
  (recouvrement, logistique, fournitures) : Django leve `ProtectedError` ;
* les signaux de synchronisation creent un `SyncChange` rattache a l'ecole pour
  chaque objet supprime, y compris pendant la suppression en cascade. Ces
  lignes, creees apres l'inventaire du collecteur, restent orphelines et la
  suppression de l'ecole viole alors la contrainte de cle etrangere.

`supprimer_ecole_complete` neutralise le journal de synchronisation le temps de
l'operation et supprime d'abord les objets protegeant l'ecole.
"""

from collections import defaultdict

from django.db import transaction
from django.db.models.deletion import ProtectedError

from synchronisation.context import mute_sync

PROFONDEUR_MAX = 10


def _supprimer_en_forcant(queryset, profondeur=0):
    """Supprime un queryset en levant d'abord les protections `PROTECT`."""
    try:
        return queryset.delete()
    except ProtectedError as exc:
        if profondeur >= PROFONDEUR_MAX:
            raise

        par_modele = defaultdict(list)
        for objet in exc.protected_objects:
            par_modele[type(objet)].append(objet.pk)

        for modele, pks in par_modele.items():
            _supprimer_en_forcant(modele._default_manager.filter(pk__in=pks), profondeur + 1)

        return queryset.delete()


def supprimer_ecole_complete(ecole):
    """Supprime l'ecole et toutes ses donnees. Retourne le nom supprime."""
    from .models import Ecole

    nom = ecole.nom
    pk = ecole.pk

    with mute_sync():
        with transaction.atomic():
            # Le journal de synchronisation pointe sur l'ecole : on le purge en premier.
            from synchronisation.models import SyncChange, SyncDevice

            SyncChange.objects.filter(ecole_id=pk).delete()
            SyncDevice.objects.filter(ecole_id=pk).delete()

            _supprimer_en_forcant(Ecole.objects.filter(pk=pk))

    return nom
