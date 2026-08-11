import logging

from django.contrib import admin, messages
from django.contrib.auth import get_permission_codename
from django.db import transaction
from django.utils.html import format_html

from .models import Ecole, Classe, Eleve, GrilleTarifaire

logger = logging.getLogger(__name__)


def _collecte_suppression(objs, request):
    """Résume, par modèle, tout ce qui sera supprimé en cascade.

    Remplace la liste imbriquée de Django, qui appelle ``__str__`` sur chaque
    objet lié : sur une école comptant des milliers d'enregistrements, cela
    rend la page inutilisable et échoue dès qu'un ``__str__`` référence une
    relation devenue orpheline.

    Retourne le quadruplet attendu par ``ModelAdmin.get_deleted_objects``.
    """
    from django.contrib.admin.utils import NestedObjects
    from django.db import router

    using = router.db_for_write(objs[0].__class__)
    collector = NestedObjects(using=using)
    collector.collect(objs)

    model_count = {}
    perms_needed = set()
    for modele, instances in collector.data.items():
        opts = modele._meta
        model_count[str(opts.verbose_name_plural)] = (
            model_count.get(str(opts.verbose_name_plural), 0) + len(instances)
        )
        if not request.user.has_perm(f"{opts.app_label}.{get_permission_codename('delete', opts)}"):
            perms_needed.add(str(opts.verbose_name))

    lignes = [format_html("<strong>{}</strong>", str(obj)) for obj in objs]
    details = [
        format_html("{} : <strong>{}</strong>", nom, nb)
        for nom, nb in sorted(model_count.items())
    ]
    if details:
        lignes.append(details)

    protected = [str(obj) for obj in collector.protected]
    return lignes, model_count, perms_needed, protected


@admin.register(Ecole)
class EcoleAdmin(admin.ModelAdmin):
    list_display = ("nom", "etat", "code_prefixe", "telephone", "email", "directeur", "censeur", "created_by", "logo_mini")
    list_filter = ("etat",)
    search_fields = ("nom", "directeur", "censeur", "telephone", "email")
    readonly_fields = ("logo_preview", "image_preview")
    fieldsets = (
        ("Identité", {
            "fields": ("nom", "directeur", "censeur", "etat", "created_by")
        }),
        ("Paramètres matricules", {
            "fields": ("code_prefixe",),
            "description": "Préfixe d'école pour les matricules (ex: AL-FUR/). Laissez vide pour ne pas utiliser de préfixe explicite."
        }),
        ("Coordonnées", {
            "fields": ("adresse", "telephone", "telephone2", "telephone3", "email")
        }),
        ("Logo & Image", {
            "fields": ("logo", "logo_preview", "image", "image_preview"),
            "description": "Logo pour filigrane et en-tetes. Photo de l'ecole pour le livret scolaire."
        }),
    )
    actions = ("valider_ecoles", "rejeter_ecoles")

    # ── Suppression fiable ────────────────────────────────────────────────
    def get_deleted_objects(self, objs, request):
        """Affiche un résumé chiffré au lieu de la liste complète des objets."""
        objs = list(objs)
        if not objs:
            return [], {}, set(), []
        try:
            return _collecte_suppression(objs, request)
        except Exception:
            logger.exception("Impossible de collecter les objets liés à l'école")
            return (
                [format_html("<strong>{}</strong>", str(o)) for o in objs],
                {}, set(), [],
            )

    def _supprimer(self, request, queryset):
        """Supprime en neutralisant le suivi de synchronisation.

        Le signal ``pre_delete`` de la synchronisation crée une trace liée à
        l'école ; comme elle naît après la collecte des objets, elle survit à
        la suppression et provoque une violation de clé étrangère.
        """
        from administration.audit import suspendre_journal
        from synchronisation.context import mute_sync

        with mute_sync(), suspendre_journal(), transaction.atomic():
            queryset.delete()

    def delete_model(self, request, obj):
        try:
            self._supprimer(request, Ecole.objects.filter(pk=obj.pk))
        except Exception as exc:
            logger.exception("Erreur lors de la suppression de l'école %s", obj.pk)
            self.message_user(
                request,
                f"Suppression impossible pour « {obj} » : {exc}",
                level=messages.ERROR,
            )

    def delete_queryset(self, request, queryset):
        try:
            self._supprimer(request, queryset)
        except Exception as exc:
            logger.exception("Erreur lors de la suppression d'écoles")
            self.message_user(
                request,
                f"Suppression impossible : {exc}",
                level=messages.ERROR,
            )

    def valider_ecoles(self, request, queryset):
        updated = queryset.update(etat="VALIDE")
        self.message_user(request, f"{updated} école(s) validée(s).")
    valider_ecoles.short_description = "Valider les écoles sélectionnées"

    def rejeter_ecoles(self, request, queryset):
        updated = queryset.update(etat="REJETE")
        self.message_user(request, f"{updated} école(s) rejetée(s).")
    rejeter_ecoles.short_description = "Rejeter les écoles sélectionnées"

    def logo_preview(self, obj):
        if getattr(obj, 'logo', None) and getattr(obj.logo, 'url', None):
            return format_html('<img src="{}" style="max-height:80px; border:1px solid #ddd; padding:2px;" />', obj.logo.url)
        return "—"
    logo_preview.short_description = "Aperçu du logo"

    def logo_mini(self, obj):
        if getattr(obj, 'logo', None) and getattr(obj.logo, 'url', None):
            return format_html('<img src="{}" style="height:24px; width:auto;" />', obj.logo.url)
        return ""
    logo_mini.short_description = "Logo"

    def image_preview(self, obj):
        if getattr(obj, 'image', None) and getattr(obj.image, 'url', None):
            return format_html('<img src="{}" style="max-height:120px; border:1px solid #ddd; padding:2px;" />', obj.image.url)
        return "—"
    image_preview.short_description = "Apercu de l'image"


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    """Gestion des élèves. Toute suppression passe par la corbeille."""

    list_display = ("matricule", "prenom", "nom", "sexe", "classe", "statut", "date_inscription")
    list_filter = ("statut", "sexe", "classe__ecole", "classe__annee_scolaire", "classe")
    search_fields = ("matricule", "nom", "prenom", "responsable_principal__telephone")
    list_select_related = ("classe", "classe__ecole")
    date_hierarchy = "date_inscription"
    ordering = ("nom", "prenom")
    raw_id_fields = ("responsable_principal", "responsable_secondaire", "cree_par")
    readonly_fields = ("date_creation", "date_modification")
    fieldsets = (
        ("Identité", {
            "fields": ("matricule", "prenom", "nom", "sexe", "date_naissance", "lieu_naissance", "photo")
        }),
        ("Scolarité", {
            "fields": ("classe", "date_inscription", "statut")
        }),
        ("Responsables", {
            "fields": ("responsable_principal", "responsable_secondaire")
        }),
        ("Métadonnées", {
            "classes": ("collapse",),
            "fields": ("cree_par", "date_creation", "date_modification")
        }),
    )
    actions = ("mettre_en_corbeille",)

    def get_deleted_objects(self, objs, request):
        objs = list(objs)
        if not objs:
            return [], {}, set(), []
        try:
            lignes, model_count, perms_needed, protected = _collecte_suppression(objs, request)
        except Exception:
            logger.exception("Impossible de collecter les objets liés aux élèves")
            return ([format_html("<strong>{}</strong>", str(o)) for o in objs], {}, set(), [])
        lignes.append(
            "Les élèves supprimés sont archivés dans la corbeille "
            "(Administration › Corbeille des élèves) et restent restaurables."
        )
        return lignes, model_count, perms_needed, protected

    def delete_model(self, request, obj):
        self._archiver(request, [obj])

    def delete_queryset(self, request, queryset):
        self._archiver(request, list(queryset))

    def mettre_en_corbeille(self, request, queryset):
        self._archiver(request, list(queryset))
    mettre_en_corbeille.short_description = "Mettre les élèves sélectionnés à la corbeille"

    def _archiver(self, request, eleves):
        from administration.audit import mettre_eleve_en_corbeille

        succes, echecs = 0, []
        for eleve in eleves:
            nom = f"{eleve.prenom} {eleve.nom}"
            try:
                mettre_eleve_en_corbeille(
                    eleve, request=request,
                    motif="Suppression depuis l'administration Django",
                )
                succes += 1
            except Exception as exc:
                logger.exception("Erreur lors de la mise en corbeille de l'élève %s", eleve.pk)
                echecs.append(f"{nom} ({exc})")

        if succes:
            self.message_user(
                request,
                f"{succes} élève(s) déplacé(s) vers la corbeille. "
                "Vous pouvez les restaurer depuis Administration › Corbeille des élèves.",
                level=messages.SUCCESS,
            )
        if echecs:
            self.message_user(
                request,
                "Suppression impossible pour : " + " ; ".join(echecs),
                level=messages.ERROR,
            )


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ("nom", "niveau", "annee_scolaire", "ecole")
    list_filter = ("ecole", "niveau", "annee_scolaire")
    search_fields = ("nom", "ecole__nom")


@admin.register(GrilleTarifaire)
class GrilleTarifaireAdmin(admin.ModelAdmin):
    list_display = (
        "ecole", "niveau", "annee_scolaire",
        "frais_inscription", "tranche_1", "tranche_2", "tranche_3",
    )
    list_filter = ("ecole", "niveau", "annee_scolaire")
    search_fields = ("ecole__nom",)
    fieldsets = (
        ("Ciblage", {
            "fields": ("ecole", "niveau", "annee_scolaire"),
        }),
        ("Montants", {
            "fields": (
                "frais_inscription", "frais_reinscription",
                "tranche_1", "tranche_2", "tranche_3",
            ),
        }),
        ("Périodes (texte)", {
            "classes": ("collapse",),
            "fields": ("periode_1", "periode_2", "periode_3"),
        }),
        ("Échéances par défaut (dates)", {
            "fields": (
                "date_echeance_inscription_defaut",
                "date_echeance_tranche_1_defaut",
                "date_echeance_tranche_2_defaut",
                "date_echeance_tranche_3_defaut",
            ),
            "description": "Si ces dates sont renseignées, elles seront utilisées pour initialiser les échéanciers des élèves de cette école/niveau/année."
        }),
    )
