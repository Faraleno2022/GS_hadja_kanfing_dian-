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
    list_display = (
        'numero_recu', 'eleve', 'montant', 'periodicite', 'mode_paiement',
        'date_debut', 'date_expiration', 'statut', 'zone',
    )
    list_filter = (
        'statut', 'periodicite', 'eleve__classe__ecole', 'eleve__classe',
        'zone', 'mode_paiement',
    )
    search_fields = (
        'numero_recu', 'reference_externe', 'eleve__nom', 'eleve__prenom',
        'eleve__matricule', 'zone', 'point_arret', 'contact_parent',
    )
    list_select_related = (
        'eleve', 'eleve__classe', 'eleve__classe__ecole', 'grille', 'mode_paiement'
    )
    autocomplete_fields = ('eleve',)
    readonly_fields = ('numero_recu', 'created_at', 'updated_at', 'derniere_relance')
    radio_fields = {
        'periodicite': admin.HORIZONTAL,
        'statut': admin.HORIZONTAL,
    }
    fieldsets = (
        ('Élève et grille tarifaire', {
            'fields': ('eleve', 'grille', 'annee_scolaire'),
        }),
        ('Paiement de l’abonnement', {
            'fields': (
                'periodicite', 'montant', 'mode_paiement', 'numero_recu',
                'reference_externe', 'date_debut', 'date_expiration', 'statut',
            ),
            'description': "Le choix Annuel correspond au total des trois tranches de la grille.",
        }),
        ('Transport et contact', {
            'fields': ('zone', 'itineraire', 'point_arret', 'contact_parent'),
        }),
        ('Alertes', {
            'fields': ('alerte_avant_jours', 'derniere_relance'),
        }),
        ('Observations', {
            'fields': ('observations',),
            'classes': ('collapse',),
        }),
        ('Métadonnées', {
            'fields': ('cree_par', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AbonnementCantine)
class AbonnementCantineAdmin(CorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ('eleve', 'type_repas', 'montant', 'periodicite', 'date_debut', 'date_expiration', 'statut', 'jours_restants')
    list_filter = (
        'statut', 'periodicite', 'type_repas', 'eleve__classe__ecole',
        'eleve__classe', 'regime_alimentaire',
    )
    search_fields = (
        'eleve__nom', 'eleve__prenom', 'eleve__matricule',
        'reference_externe', 'contact_parent', 'regime_alimentaire',
    )
    list_select_related = ('eleve', 'eleve__classe', 'eleve__classe__ecole')
    autocomplete_fields = ('eleve',)
    readonly_fields = ('created_at', 'updated_at')
    radio_fields = {
        'periodicite': admin.HORIZONTAL,
        'type_repas': admin.HORIZONTAL,
        'statut': admin.HORIZONTAL,
    }
    
    fieldsets = (
        ('Informations Élève', {
            'fields': ('eleve', 'contact_parent')
        }),
        ('Abonnement', {
            'fields': (
                'montant', 'periodicite', 'type_repas', 'reference_externe',
                'date_debut', 'date_expiration', 'statut',
            ),
            'description': "Les périodicités et horaires de repas sont proposés sous forme de choix rapides.",
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
