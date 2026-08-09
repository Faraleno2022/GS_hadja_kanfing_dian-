from django.contrib import messages
from django.db import transaction

from .corbeille import enregistrer_suppression


class CorbeilleAdminMixin:
    """Fait passer les suppressions de l'admin Django par la corbeille.

    Les objets supprimés en cascade sont inclus dans le même instantané afin
    que la restauration puisse remettre l'ensemble cohérent.
    """

    def get_corbeille_delete_context(self, obj):
        return None

    def after_corbeille_delete(self, request, obj, context):
        return None

    def after_corbeille_delete_queryset(self, request, contexts):
        return None

    @transaction.atomic
    def delete_model(self, request, obj):
        contexte = self.get_corbeille_delete_context(obj)
        enregistrer_suppression(obj, request=request)
        obj.delete()
        self.after_corbeille_delete(request, obj, contexte)
        self.message_user(
            request,
            "L'élément et ses données liées ont été placés dans la "
            "corbeille et peuvent être restaurés.",
            level=messages.WARNING,
        )

    @transaction.atomic
    def delete_queryset(self, request, queryset):
        objets = list(queryset)
        contextes = []
        for obj in objets:
            contexte = self.get_corbeille_delete_context(obj)
            enregistrer_suppression(obj, request=request)
            obj.delete()
            contextes.append(contexte)
        self.after_corbeille_delete_queryset(request, contextes)
        self.message_user(
            request,
            f"{len(objets)} élément(s) placé(s) dans la corbeille avec leurs "
            "données liées.",
            level=messages.WARNING,
        )
