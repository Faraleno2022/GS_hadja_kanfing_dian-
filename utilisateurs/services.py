from django.db import transaction
from django.db.models import Q

from .models import MENUS, Profil


PERMISSIONS_COMPTE_PRINCIPAL = (
    'peut_valider_paiements',
    'peut_valider_depenses',
    'peut_generer_rapports',
    'peut_gerer_utilisateurs',
    'peut_gerer_classes',
    'peut_gerer_grilles_tarifaires',
    'peut_ajouter_paiements',
    'peut_ajouter_depenses',
    'peut_ajouter_enseignants',
    'peut_importer_eleves',
    'peut_modifier_paiements',
    'peut_modifier_depenses',
    'peut_supprimer_paiements',
    'peut_supprimer_depenses',
    'peut_supprimer_abonnements',
    'peut_supprimer_eleves_definitivement',
    'peut_supprimer_enseignants_definitivement',
    'peut_consulter_rapports',
    'peut_gerer_notes',
)


@transaction.atomic
def attribuer_compte_principal(profil, ecole, *, rattacher_utilisateurs=True):
    """Active toutes les fonctions du compte principal d'une école."""
    profil.role = 'DIRECTEUR'
    profil.ecole = ecole
    profil.est_compte_principal = True
    profil.compte_principal = None
    profil.allowed_menus = [key for key, _label in MENUS]
    profil.is_validated = True
    profil.actif = True
    profil.lecture_seule = False
    for permission_name in PERMISSIONS_COMPTE_PRINCIPAL:
        setattr(profil, permission_name, True)
    profil.save()

    if rattacher_utilisateurs:
        autres_profils = (
            Profil.objects
            .filter(ecole=ecole, user__is_superuser=False)
            .exclude(pk=profil.pk)
            .select_related('user')
        )
        for sous_profil in autres_profils:
            etait_deja_rattache = bool(sous_profil.compte_principal_id)
            sous_profil.est_compte_principal = False
            sous_profil.compte_principal = profil
            sous_profil.peut_gerer_utilisateurs = False
            # Avant la gestion des sous-utilisateurs, une liste vide signifiait
            # que le compte n'était pas restreint. Préserver les comptes déjà
            # rattachés dont l'absence de menus peut être volontaire.
            if not etait_deja_rattache and not sous_profil.allowed_menus:
                sous_profil.allowed_menus = [key for key, _label in MENUS]
            sous_profil.save()

    return profil


@transaction.atomic
def garantir_compte_principal_ecole(ecole):
    """Trouve ou crée l'attribution principale d'une école ancienne ou nouvelle."""
    principal = (
        Profil.objects
        .filter(ecole=ecole, est_compte_principal=True, user__is_superuser=False)
        .order_by('id')
        .first()
    )

    if principal is None and ecole.created_by_id:
        principal = (
            Profil.objects
            .filter(user_id=ecole.created_by_id, user__is_superuser=False)
            .filter(Q(ecole=ecole) | Q(ecole__isnull=True))
            .order_by('id')
            .first()
        )

    if principal is None:
        principal = (
            Profil.objects
            .filter(
                ecole=ecole,
                role__in=['DIRECTEUR', 'ADMIN'],
                user__is_superuser=False,
            )
            .order_by('-is_validated', '-user__is_active', 'id')
            .first()
        )

    # Compatibilité avec les anciennes écoles qui ne possédaient qu'un
    # comptable, un secrétaire ou un autre compte déjà associé.
    if principal is None:
        principal = (
            Profil.objects
            .filter(ecole=ecole, user__is_superuser=False)
            .order_by('-is_validated', '-user__is_active', 'id')
            .first()
        )

    if principal is None:
        return None

    return attribuer_compte_principal(principal, ecole)
