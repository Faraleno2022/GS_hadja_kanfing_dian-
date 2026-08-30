from django.contrib import admin

from administration.corbeille_admin import CorbeilleAdminMixin
from utilisateurs.utils import user_is_superadmin, user_school

from .models import AbonnementBus, AbonnementCantine, GrilleTarifaireBus


@admin.register(GrilleTarifaireBus)
class GrilleTarifaireBusAdmin(admin.ModelAdmin):
    list_display = (
        'ecole', 'zone', 'annee_scolaire',
        'tranche_1', 'tranche_2', 'tranche_3', 'actif',
    )
    list_filter = ('ecole', 'annee_scolaire', 'actif')
    search_fields = ('ecole__nom', 'zone', 'annee_scolaire')
    list_select_related = ('ecole', 'cree_par')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if user_is_superadmin(request.user):
            return queryset
        ecole = user_school(request.user)
        return queryset.filter(ecole=ecole) if ecole else queryset.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'ecole' and not user_is_superadmin(request.user):
            ecole = user_school(request.user)
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                pk=getattr(ecole, 'pk', None)
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not user_is_superadmin(request.user):
            obj.ecole = user_school(request.user)
        if not obj.cree_par_id:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)

@admin.register(AbonnementBus)
class AbonnementBusAdmin(CorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ('numero_recu', 'eleve', 'montant', 'periodicite', 'mode_paiement', 'date_debut', 'statut', 'zone')
    list_filter = ('statut', 'periodicite', 'zone', 'mode_paiement')
    search_fields = ('numero_recu', 'eleve__nom', 'eleve__prenom', 'eleve__matricule', 'zone', 'point_arret', 'contact_parent')
    list_select_related = ('eleve', 'grille', 'mode_paiement')
    raw_id_fields = ('eleve',)


@admin.register(AbonnementCantine)
class AbonnementCantineAdmin(CorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ('eleve', 'type_repas', 'montant', 'periodicite', 'date_debut', 'date_expiration', 'statut', 'jours_restants')
    list_filter = ('statut', 'periodicite', 'type_repas', 'regime_alimentaire')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule', 'contact_parent', 'regime_alimentaire')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informations Élève', {
            'fields': ('eleve', 'contact_parent')
        }),
        ('Abonnement', {
            'fields': ('montant', 'periodicite', 'type_repas', 'date_debut', 'date_expiration', 'statut')
        }),
        ('Régime Alimentaire', {
            'fields': ('regime_alimentaire', 'allergies'),
            'classes': ('collapse',)
        }),
        ('Alertes', {
            'fields': ('alerte_avant_jours', 'derniere_relance')
        }),
        ('Observations', {
            'fields': ('observations',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
