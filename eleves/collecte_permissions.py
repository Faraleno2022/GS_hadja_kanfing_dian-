"""Droits de gestion des liens de collecte, indépendants de leur accès public."""
def peut_gerer_collecte(user):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    profil = getattr(user, 'profil', None)
    return bool(
        profil and profil.ecole_id and profil.actif and profil.is_validated
        and not profil.lecture_seule
        and (profil.role in ('ADMIN', 'DIRECTEUR', 'COMPTABLE')
             or profil.est_compte_principal or profil.peut_importer_eleves)
        and (not profil.compte_principal_id or 'eleves' in (profil.allowed_menus or []))
    )
