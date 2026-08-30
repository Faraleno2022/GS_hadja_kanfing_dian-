from django.db import migrations, models


MENUS_COMPLETS = [
    'eleves',
    'paiements',
    'depenses',
    'salaires',
    'bus',
    'notes',
    'rapports',
]

PERMISSIONS_COMPLETES = (
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


def reparer_comptes_principaux(apps, schema_editor):
    Profil = apps.get_model('utilisateurs', 'Profil')
    Ecole = apps.get_model('eleves', 'Ecole')

    for ecole in Ecole.objects.all().iterator():
        principal = (
            Profil.objects
            .filter(
                ecole_id=ecole.id,
                est_compte_principal=True,
                user__is_superuser=False,
            )
            .order_by('id')
            .first()
        )

        if principal is None and ecole.created_by_id:
            principal = (
                Profil.objects
                .filter(user_id=ecole.created_by_id, user__is_superuser=False)
                .filter(models.Q(ecole_id=ecole.id) | models.Q(ecole_id__isnull=True))
                .order_by('id')
                .first()
            )

        if principal is None:
            principal = (
                Profil.objects
                .filter(
                    ecole_id=ecole.id,
                    role__in=['DIRECTEUR', 'ADMIN'],
                    user__is_superuser=False,
                )
                .order_by('-is_validated', '-user__is_active', 'id')
                .first()
            )

        if principal is None:
            principal = (
                Profil.objects
                .filter(ecole_id=ecole.id, user__is_superuser=False)
                .order_by('-is_validated', '-user__is_active', 'id')
                .first()
            )

        # Une école sans aucun utilisateur reste disponible dans l'écran
        # d'activation afin que le superadministrateur crée son compte principal.
        if principal is None:
            continue

        principal.ecole_id = ecole.id
        principal.role = 'DIRECTEUR'
        principal.est_compte_principal = True
        principal.compte_principal_id = None
        principal.allowed_menus = MENUS_COMPLETS
        principal.is_validated = True
        principal.actif = True
        principal.lecture_seule = False
        for permission_name in PERMISSIONS_COMPLETES:
            setattr(principal, permission_name, True)
        principal.save()

        for sous_profil in (
            Profil.objects
            .filter(ecole_id=ecole.id, user__is_superuser=False)
            .exclude(pk=principal.pk)
            .iterator()
        ):
            etait_deja_rattache = bool(sous_profil.compte_principal_id)
            sous_profil.est_compte_principal = False
            sous_profil.compte_principal_id = principal.pk
            sous_profil.peut_gerer_utilisateurs = False
            if not etait_deja_rattache and not sous_profil.allowed_menus:
                sous_profil.allowed_menus = MENUS_COMPLETS
            sous_profil.save()


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0015_profil_compte_principal_profil_est_compte_principal_and_more'),
    ]

    operations = [
        migrations.RunPython(reparer_comptes_principaux, migrations.RunPython.noop),
    ]
