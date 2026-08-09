"""Service de corbeille : journalise les suppressions et les modifications,
et sait les annuler.

Les instantanes reutilisent la serialisation du moteur de synchronisation
(`synchronisation.engine`) : un dictionnaire par champ concret, les cles
etrangeres etant stockees avec leur pk et leur libelle.
"""

from django.db import transaction
from django.utils import timezone

from synchronisation.engine import (
    deserialize_field,
    ecole_for_instance,
    model_label_for,
    serialize_instance,
)

from .models import ElementCorbeille

# Champs recalcules par la base : on ne les rejoue pas a la restauration.
CHAMPS_NON_RESTAURABLES = {'date_creation', 'date_modification', 'created_at', 'updated_at'}


class CorbeilleError(Exception):
    """Restauration impossible."""


def _ecole(instance):
    try:
        return ecole_for_instance(instance)
    except Exception:
        return None


def _ip(request):
    return request.META.get('REMOTE_ADDR') if request else None


def _utilisateur(request, user=None):
    if user is not None:
        return user
    if request is not None and getattr(request, 'user', None) and request.user.is_authenticated:
        return request.user
    return None


def instantane(instance):
    """Instantane serialisable d'une instance."""
    return serialize_instance(instance)


def collecter_objets_lies(instance, limite=1000):
    """Instantane des objets qui seront supprimes en cascade avec `instance`.

    La liste est rendue dans l'ordre de suppression de Django (enfants d'abord) ;
    la restauration la rejoue a l'envers pour respecter les cles etrangeres.
    """
    from django.db import router
    from django.db.models.deletion import Collector

    collector = Collector(using=router.db_for_write(type(instance)))
    collector.collect([instance])
    try:
        collector.sort()
    except Exception:
        pass

    lies = []
    for modele, objets in collector.data.items():
        for obj in objets:
            if modele is type(instance) and obj.pk == instance.pk:
                continue
            if len(lies) >= limite:
                return lies, True
            lies.append({
                'model_label': model_label_for(obj),
                'pk': obj.pk,
                'libelle': str(obj)[:255],
                'donnees': serialize_instance(obj),
            })
    return lies, False


def enregistrer_suppression(instance, request=None, user=None, objets_lies=None):
    """Place une copie de l'objet dans la corbeille, avant sa suppression."""
    if objets_lies is None:
        objets_lies, _tronque = collecter_objets_lies(instance)

    return ElementCorbeille.objects.create(
        type_operation=ElementCorbeille.SUPPRESSION,
        model_label=model_label_for(instance),
        objet_id=instance.pk,
        libelle=str(instance)[:255],
        donnees_avant=instantane(instance),
        objets_lies=objets_lies or [],
        ecole=_ecole(instance),
        utilisateur=_utilisateur(request, user),
        adresse_ip=_ip(request),
    )


def enregistrer_modification(instance, donnees_avant, request=None, user=None, motif=''):
    """Journalise une modification. Retourne None si rien n'a change."""
    donnees_apres = instantane(instance)

    champs_modifies = [
        champ for champ, valeur in donnees_apres.items()
        if champ not in CHAMPS_NON_RESTAURABLES and donnees_avant.get(champ) != valeur
    ]
    if not champs_modifies:
        return None

    return ElementCorbeille.objects.create(
        type_operation=ElementCorbeille.MODIFICATION,
        model_label=model_label_for(instance),
        objet_id=instance.pk,
        libelle=str(instance)[:255],
        donnees_avant=donnees_avant,
        donnees_apres=donnees_apres,
        champs_modifies=champs_modifies,
        motif=(motif or '')[:255],
        ecole=_ecole(instance),
        utilisateur=_utilisateur(request, user),
        adresse_ip=_ip(request),
    )


def _modele_depuis_label(label):
    from django.apps import apps
    try:
        app_label, model_name = (label or '').split('.', 1)
        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError, AttributeError):
        raise CorbeilleError(f"Modèle introuvable : {label}")


def _modele(element):
    return _modele_depuis_label(element.model_label)


def _recalculer_paiements(instance):
    """Resynchronise les échéanciers après une restauration comptable."""
    try:
        from paiements.models import (
            EcheancierPaiement,
            ModePaiement,
            Paiement,
            PaiementRemise,
            RemiseReduction,
            TypePaiement,
        )
        from paiements.payment_engine import (
            recalculer_echeancier,
            recalculer_remises_paiement,
        )

        eleve_ids = set()
        if isinstance(instance, Paiement):
            recalculer_remises_paiement(instance)
            eleve_ids.add(instance.eleve_id)
        elif isinstance(instance, PaiementRemise):
            eleve_ids.add(instance.paiement.eleve_id)
        elif isinstance(instance, EcheancierPaiement):
            eleve_ids.add(instance.eleve_id)
        elif isinstance(instance, RemiseReduction):
            eleve_ids.update(
                PaiementRemise.objects.filter(remise=instance).values_list(
                    'paiement__eleve_id', flat=True
                )
            )
        elif isinstance(instance, (TypePaiement, ModePaiement)):
            filtre = (
                {'type_paiement': instance}
                if isinstance(instance, TypePaiement)
                else {'mode_paiement': instance}
            )
            eleve_ids.update(
                Paiement.objects.filter(**filtre).values_list('eleve_id', flat=True)
            )

        for echeancier in EcheancierPaiement.objects.filter(eleve_id__in=eleve_ids):
            recalculer_echeancier(echeancier)
    except Exception:
        # La corbeille reste utilisable pour toutes les autres applications,
        # même si le module paiements n'est pas installé ou est en migration.
        return


def _appliquer_donnees(objet, modele, donnees, champs=None):
    """Réécrit les champs de `donnees` sur `objet`. Retourne les champs ignorés."""
    ignores = []
    for field in modele._meta.concrete_fields:
        if field.primary_key or field.name in CHAMPS_NON_RESTAURABLES:
            continue
        if champs is not None and field.name not in champs:
            continue
        if field.name not in donnees:
            continue

        valeur = deserialize_field(field, donnees[field.name])
        if valeur is None and donnees[field.name] and field.is_relation:
            # La cible de la clé étrangère n'existe plus.
            ignores.append(field.verbose_name or field.name)
            continue
        setattr(objet, field.name, valeur)
    return ignores


@transaction.atomic
def restaurer(element, request=None, user=None):
    """Recrée un objet supprimé. Retourne (objet, champs_ignores)."""
    if element.restaure:
        raise CorbeilleError("Cet élément a déjà été restauré.")
    if element.type_operation != ElementCorbeille.SUPPRESSION:
        raise CorbeilleError("Cet élément n'est pas une suppression.")

    modele = _modele(element)

    if element.objet_id and modele.objects.filter(pk=element.objet_id).exists():
        raise CorbeilleError(
            f"Un {modele._meta.verbose_name} portant l'identifiant {element.objet_id} existe déjà."
        )

    objet = modele()
    ignores = _appliquer_donnees(objet, modele, element.donnees_avant)
    if element.objet_id:
        objet.pk = element.objet_id
    objet.save(force_insert=True)

    # Les objets liés ont été collectés dans l'ordre de suppression
    # (enfants d'abord) : on les recrée dans l'ordre inverse.
    for lie in reversed(element.objets_lies or []):
        try:
            modele_lie = _modele_depuis_label(lie.get('model_label'))
        except CorbeilleError:
            ignores.append(lie.get('libelle') or lie.get('model_label'))
            continue

        if lie.get('pk') and modele_lie.objects.filter(pk=lie['pk']).exists():
            continue

        enfant = modele_lie()
        ignores += _appliquer_donnees(enfant, modele_lie, lie.get('donnees') or {})
        if lie.get('pk'):
            enfant.pk = lie['pk']
        try:
            enfant.save(force_insert=True)
        except Exception as exc:
            ignores.append(f"{lie.get('libelle') or modele_lie._meta.verbose_name} ({exc})")

    element.restaure = True
    element.date_restauration = timezone.now()
    element.restaure_par = _utilisateur(request, user)
    element.save(update_fields=['restaure', 'date_restauration', 'restaure_par'])

    _recalculer_paiements(objet)

    return objet, ignores


@transaction.atomic
def annuler_modification(element, request=None, user=None):
    """Réapplique l'état antérieur d'un objet modifié. Retourne (objet, champs_ignores)."""
    if element.restaure:
        raise CorbeilleError("Cette modification a déjà été annulée.")
    if element.type_operation != ElementCorbeille.MODIFICATION:
        raise CorbeilleError("Cet élément n'est pas une modification.")

    modele = _modele(element)
    objet = modele.objects.filter(pk=element.objet_id).first()
    if objet is None:
        raise CorbeilleError(
            f"L'objet d'origine n'existe plus : impossible d'annuler la modification."
        )

    ignores = _appliquer_donnees(objet, modele, element.donnees_avant, champs=element.champs_modifies)
    objet.save()

    _recalculer_paiements(objet)

    element.restaure = True
    element.date_restauration = timezone.now()
    element.restaure_par = _utilisateur(request, user)
    element.save(update_fields=['restaure', 'date_restauration', 'restaure_par'])

    return objet, ignores


def differences(element):
    """Liste [(champ, avant, apres)] lisible pour l'affichage."""
    modele = None
    try:
        modele = _modele(element)
    except CorbeilleError:
        pass

    def libelle(nom):
        if modele is None:
            return nom
        try:
            return modele._meta.get_field(nom).verbose_name
        except Exception:
            return nom

    def lisible(valeur):
        if isinstance(valeur, dict):
            return valeur.get('text') or valeur.get('pk') or '—'
        if valeur in (None, ''):
            return '—'
        return valeur

    return [
        (libelle(champ), lisible(element.donnees_avant.get(champ)), lisible(element.donnees_apres.get(champ)))
        for champ in (element.champs_modifies or [])
    ]
