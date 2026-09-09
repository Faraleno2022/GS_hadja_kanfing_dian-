"""Périmètre des objets échangés entre une école et ses postes."""
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.contrib.auth import get_user_model

# Référentiels historiques communs : lecture permise, écriture distante interdite.
SHARED_MODELS = {
    'paiements.TypePaiement', 'paiements.ModePaiement', 'paiements.RemiseReduction',
    'depenses.CategorieDepense', 'depenses.CategorieArticle', 'depenses.CategorieLivre',
    'abonnements.TypeAbonnement',
}
OWNER_FIELDS = (
    'ecole', 'eleve', 'paiement', 'classe', 'enseignant', 'etat_salaire',
    'periode', 'evaluation', 'matiere', 'activite', 'abonnement', 'depense',
    'inventaire', 'article', 'livre', 'tableau_bord',
    'cree_par', 'genere_par', 'proprietaire', 'modifie_par', 'uploaded_by',
)


def label_for(model):
    return f'{model._meta.app_label}.{model.__name__}'


def school_path(model, seen=()):
    if model in seen:
        return None
    if label_for(model) == 'eleves.Ecole':
        return 'pk'
    if model == get_user_model():
        return 'profil__ecole'
    fields = {f.name: f for f in model._meta.concrete_fields}
    for name in OWNER_FIELDS:
        field = fields.get(name)
        if not isinstance(field, models.ForeignKey):
            continue
        if name == 'ecole':
            return 'ecole'
        path = school_path(field.remote_field.model, (*seen, model))
        if path:
            return name + '__' + path
    return None


def ownership(model):
    from .models import SyncOwnership
    return SyncOwnership.objects.filter(model_label=label_for(model))


def scoped_queryset(model, ecole):
    if ecole is None:
        return model.objects.none()
    owned = ownership(model).filter(ecole=ecole).values('object_uuid')
    label = label_for(model)
    if label in SHARED_MODELS:
        foreign = ownership(model).exclude(ecole=ecole).values('object_uuid')
        return model.objects.exclude(sync_uuid__in=foreign)
    if label == 'eleves.Responsable':
        linked = Q(eleves_principal__classe__ecole=ecole) | Q(eleves_secondaire__classe__ecole=ecole)
        orphan = Q(eleves_principal__isnull=True, eleves_secondaire__isnull=True)
        return model.objects.filter(linked | (orphan & Q(sync_uuid__in=owned))).distinct()
    if label == 'depenses.Fournisseur':
        return model.objects.filter(
            Q(depenses__cree_par__profil__ecole=ecole) | Q(sync_uuid__in=owned)
        ).exclude(sync_uuid__in=ownership(model).exclude(ecole=ecole).values('object_uuid')).distinct()
    if label == 'abonnements.Itineraire':
        return model.objects.filter(
            Q(abonnementbus__eleve__classe__ecole=ecole) | Q(sync_uuid__in=owned)
        ).distinct()
    path = school_path(model)
    if path == 'pk':
        return model.objects.filter(pk=ecole.pk)
    if path:
        return model.objects.filter(
            Q(**{path: ecole}) | (Q(**{path+'__isnull': True}) & Q(sync_uuid__in=owned))
        ).distinct()
    return model.objects.filter(sync_uuid__in=owned)


def direct_school_id(instance):
    label = label_for(type(instance))
    if label == 'eleves.Responsable':
        if not instance.pk:
            return None
        from eleves.models import Eleve
        ids = set(Eleve.objects.filter(
            Q(responsable_principal=instance) | Q(responsable_secondaire=instance)
        ).values_list('classe__ecole_id', flat=True))
        return next(iter(ids)) if len(ids) == 1 else None
    path = school_path(type(instance))
    if not path:
        return None
    value = instance
    try:
        for part in path.split('__'):
            value = getattr(value, part)
            if value is None:
                return None
    except (AttributeError, ObjectDoesNotExist):
        return None
    return value.pk if isinstance(value, models.Model) else value


def school_for_instance(instance):
    from eleves.models import Ecole
    school_id = direct_school_id(instance)
    if school_id:
        return Ecole.objects.filter(pk=school_id).first()
    scope = ownership(type(instance)).filter(object_uuid=instance.sync_uuid).select_related('ecole').first()
    return scope.ecole if scope else None


def validate_scope(instance, ecole, *, existing=False, trusted=False):
    from django.core.exceptions import PermissionDenied
    model = type(instance)
    if existing and not scoped_queryset(model, ecole).filter(pk=instance.pk).exists():
        raise PermissionDenied("Objet hors de l'établissement autorisé.")
    if label_for(model) in SHARED_MODELS and existing and not trusted:
        if not ownership(model).filter(object_uuid=instance.sync_uuid, ecole=ecole).exists():
            raise PermissionDenied("Le référentiel partagé est en lecture seule sur les postes.")
    if existing and label_for(model) == 'eleves.Responsable' and not trusted:
        from eleves.models import Eleve
        if Eleve.objects.filter(
            Q(responsable_principal=instance) | Q(responsable_secondaire=instance)
        ).exclude(classe__ecole=ecole).exists():
            raise PermissionDenied("Responsable partagé avec un autre établissement.")
    direct = direct_school_id(instance)
    if direct is not None and direct != ecole.pk:
        raise PermissionDenied("Rattachement à une autre école interdit.")
    # Validate every foreign key, not only the relation used by the main queryset.
    for field in model._meta.concrete_fields:
        if not isinstance(field, models.ForeignKey) or not getattr(instance, field.attname, None):
            continue
        related = getattr(instance, field.name)
        if field.remote_field.model == get_user_model():
            # Author/validator metadata is never accepted from a device. A platform
            # administrator may legitimately have created a record for this school.
            continue
        elif not scoped_queryset(type(related), ecole).filter(pk=related.pk).exists():
            raise PermissionDenied(f"Relation hors établissement : {field.name}.")


def remember_school(instance, ecole):
    from .models import SyncOwnership
    scope, created = SyncOwnership.objects.get_or_create(
        model_label=label_for(type(instance)), object_uuid=instance.sync_uuid,
        defaults={'ecole': ecole},
    )
    if not created and scope.ecole_id != ecole.pk:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Cet objet appartient déjà à une autre école.")
