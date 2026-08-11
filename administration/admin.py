from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    CorbeilleElement, CorbeilleEleve, JournalModification, MaintenanceMode, SystemLog,
)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'description', 'user', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['description', 'user__username', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        # Les logs ne peuvent pas être ajoutés manuellement
        return False
    
    def has_change_permission(self, request, obj=None):
        # Les logs ne peuvent pas être modifiés
        return False


@admin.register(CorbeilleEleve)
class CorbeilleEleveAdmin(admin.ModelAdmin):
    list_display = ['date_suppression', 'matricule', 'nom_complet', 'classe_nom',
                    'ecole_nom', 'supprime_par', 'restaure']
    list_filter = ['restaure', 'ecole_nom', 'annee_scolaire', 'date_suppression']
    search_fields = ['matricule', 'nom', 'prenom', 'classe_nom']
    readonly_fields = ['eleve_id_origine', 'matricule', 'nom', 'prenom', 'classe_nom',
                       'ecole_nom', 'annee_scolaire', 'donnees', 'supprime_par',
                       'date_suppression', 'restaure', 'date_restauration', 'restaure_par']
    date_hierarchy = 'date_suppression'
    actions = ['restaurer_eleves']

    def has_add_permission(self, request):
        return False

    def restaurer_eleves(self, request, queryset):
        from .audit import restaurer_eleve

        for entree in queryset.filter(restaure=False):
            try:
                _, message = restaurer_eleve(entree, request=request)
                self.message_user(request, message, level=messages.SUCCESS)
            except Exception as exc:
                self.message_user(
                    request,
                    f"Restauration impossible pour {entree} : {exc}",
                    level=messages.ERROR,
                )
    restaurer_eleves.short_description = "Restaurer les élèves sélectionnés"


@admin.register(CorbeilleElement)
class CorbeilleElementAdmin(admin.ModelAdmin):
    list_display = ['date_suppression', 'modele_libelle', 'objet_repr', 'contexte',
                    'ecole_nom', 'supprime_par', 'restaure']
    list_filter = ['restaure', 'model_name', 'ecole_nom', 'date_suppression']
    search_fields = ['objet_repr', 'contexte', 'motif']
    readonly_fields = ['app_label', 'model_name', 'modele_libelle', 'objet_id_origine',
                       'objet_repr', 'contexte', 'ecole_nom', 'donnees', 'motif',
                       'supprime_par', 'date_suppression', 'restaure',
                       'date_restauration', 'restaure_par']
    date_hierarchy = 'date_suppression'
    actions = ['restaurer_elements']

    def has_add_permission(self, request):
        return False

    def restaurer_elements(self, request, queryset):
        from .audit import restaurer_element

        for entree in queryset.filter(restaure=False):
            try:
                _, message = restaurer_element(entree, request=request)
                self.message_user(request, message, level=messages.SUCCESS)
            except Exception as exc:
                self.message_user(
                    request,
                    f"Restauration impossible pour {entree} : {exc}",
                    level=messages.ERROR,
                )
    restaurer_elements.short_description = "Restaurer les éléments sélectionnés"


@admin.register(JournalModification)
class JournalModificationAdmin(admin.ModelAdmin):
    list_display = ['date_modification', 'action', 'libelle_modele', 'objet_repr',
                    'utilisateur', 'resume_changements']
    list_filter = ['action', 'app_label', 'model_name', 'date_modification']
    search_fields = ['objet_repr', 'commentaire', 'utilisateur__username']
    readonly_fields = ['app_label', 'model_name', 'objet_id', 'objet_repr', 'action',
                       'changements', 'commentaire', 'utilisateur', 'ip_address',
                       'date_modification', 'annule', 'date_annulation', 'annule_par']
    date_hierarchy = 'date_modification'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def resume_changements(self, obj):
        champs = list((obj.changements or {}).keys())
        if not champs:
            return "—"
        return format_html("<span title='{}'>{}</span>", ", ".join(champs), f"{len(champs)} champ(s)")
    resume_changements.short_description = "Champs modifiés"


@admin.register(MaintenanceMode)
class MaintenanceModeAdmin(admin.ModelAdmin):
    list_display = ['is_active', 'activated_by', 'activated_at']
    fields = ['is_active', 'message', 'allowed_users']
    filter_horizontal = ['allowed_users']
    
    def save_model(self, request, obj, form, change):
        if obj.is_active and not obj.activated_by:
            obj.activated_by = request.user
        super().save_model(request, obj, form, change)
