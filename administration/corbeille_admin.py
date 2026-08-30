"""Mixin d'administration : toute suppression passe par la corbeille.

À appliquer aux ``ModelAdmin`` des objets métier (paiements, échéanciers,
abonnements...) : au lieu d'un ``DELETE`` définitif, l'objet et ses lignes
filles sont archivés dans ``CorbeilleElement`` et restent restaurables.
"""

import logging

from django.contrib import messages
from django.utils.html import format_html

logger = logging.getLogger(__name__)


class CorbeilleAdminMixin:
    """Redirige les suppressions de l'admin Django vers la corbeille."""

    corbeille_motif = "Suppression depuis l'administration Django"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'mettre_en_corbeille' not in actions:
            actions['mettre_en_corbeille'] = (
                type(self).mettre_en_corbeille,
                'mettre_en_corbeille',
                "Mettre les éléments sélectionnés à la corbeille",
            )
        return actions

    def get_deleted_objects(self, objs, request):
        deletable, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        deletable = list(deletable)
        deletable.append(format_html(
            "<strong>{}</strong>",
            "Ces éléments seront archivés dans la corbeille "
            "(Administration › Corbeille des éléments) et restent restaurables."
        ))
        return deletable, model_count, perms_needed, protected

    def delete_model(self, request, obj):
        self._archiver_corbeille(request, [obj])

    def delete_queryset(self, request, queryset):
        self._archiver_corbeille(request, list(queryset))

    def mettre_en_corbeille(self, request, queryset):
        self._archiver_corbeille(request, list(queryset))
    mettre_en_corbeille.short_description = "Mettre les éléments sélectionnés à la corbeille"

    def _archiver_corbeille(self, request, objets):
        from .audit import mettre_en_corbeille

        succes, echecs = 0, []
        for objet in objets:
            libelle = str(objet)
            try:
                mettre_en_corbeille(objet, request=request, motif=self.corbeille_motif)
                succes += 1
            except Exception as exc:
                logger.exception("Mise en corbeille impossible pour %s", libelle)
                echecs.append(f"{libelle} ({exc})")

        if succes:
            self.message_user(
                request,
                f"{succes} élément(s) déplacé(s) vers la corbeille. "
                "Vous pouvez les restaurer depuis Administration › Corbeille des éléments.",
                level=messages.SUCCESS,
            )
        if echecs:
            self.message_user(
                request,
                "Suppression impossible pour : " + " ; ".join(echecs),
                level=messages.ERROR,
            )
