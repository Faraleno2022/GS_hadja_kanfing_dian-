from django.contrib import admin
from .models import (
    Enseignant, TypeEnseignant, StatutEnseignant, 
    AffectationClasse, AvanceSalaire, PeriodeSalaire, EtatSalaire,
    DetailHeuresClasse, PresenceEnseignant
)


class AffectationClasseInline(admin.TabularInline):
    model = AffectationClasse
    extra = 1
    fields = [
        'classe', 'matiere', 'heures_par_semaine',
        'date_debut', 'date_fin', 'actif',
    ]


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'prenoms', 'ecole', 'type_enseignant',
        'fonction', 'statut', 'date_embauche',
    ]
    list_filter = ['ecole', 'type_enseignant', 'statut', 'date_embauche']
    search_fields = ['nom', 'prenoms', 'telephone', 'email', 'fonction']
    ordering = ['ecole__nom', 'nom', 'prenoms']
    inlines = [AffectationClasseInline]
    fieldsets = (
        ('Identité', {
            'fields': (
                'nom', 'prenoms', 'telephone', 'email', 'adresse',
            ),
        }),
        ('Poste', {
            'fields': (
                'ecole', 'type_enseignant', 'fonction',
                'statut', 'date_embauche',
            ),
        }),
        ('Rémunération', {
            'fields': (
                'salaire_fixe', 'prime_mensuelle', 'taux_horaire',
                'mode_calcul_horaire', 'heures_mensuelles',
            ),
        }),
        ('Traçabilité', {
            'fields': ('cree_par', 'date_creation', 'date_modification'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['cree_par', 'date_creation', 'date_modification']

    def save_model(self, request, obj, form, change):
        if not obj.cree_par_id:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)


@admin.register(AffectationClasse)
class AffectationClasseAdmin(admin.ModelAdmin):
    list_display = [
        'enseignant', 'classe', 'matiere', 'heures_par_semaine',
        'date_debut', 'date_fin', 'actif',
    ]
    list_filter = [
        'actif', 'classe__ecole', 'enseignant__type_enseignant',
        'date_debut',
    ]
    search_fields = [
        'enseignant__nom', 'enseignant__prenoms',
        'classe__nom', 'matiere',
    ]
    autocomplete_fields = ['enseignant', 'classe']


@admin.register(AvanceSalaire)
class AvanceSalaireAdmin(admin.ModelAdmin):
    list_display = [
        'enseignant', 'periode', 'montant', 'date_avance',
        'mode_paiement', 'reference_externe',
    ]
    list_filter = [
        'date_avance', 'periode__annee', 'periode__mois',
        'enseignant__ecole', 'mode_paiement',
    ]
    search_fields = [
        'enseignant__nom', 'enseignant__prenoms',
        'reference_externe', 'motif',
    ]
    date_hierarchy = 'date_avance'
    ordering = ['-date_avance', '-date_creation']
    readonly_fields = ['cree_par', 'date_creation', 'date_modification']
    fieldsets = (
        ('Bénéficiaire et période', {
            'fields': ('enseignant', 'periode'),
        }),
        ('Versement', {
            'fields': (
                'montant', 'date_avance', 'mode_paiement',
                'reference_externe', 'motif',
            ),
        }),
        ('Traçabilité', {
            'fields': ('cree_par', 'date_creation', 'date_modification'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.cree_par_id:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset):
        for avance in queryset:
            avance.delete()


@admin.register(PresenceEnseignant)
class PresenceEnseignantAdmin(admin.ModelAdmin):
    list_display = ['enseignant', 'date', 'statut', 'heure_arrivee', 'heure_depart', 'heures_travaillees', 'justifie']
    list_filter = ['statut', 'date', 'justifie', 'enseignant__ecole']
    search_fields = ['enseignant__nom', 'enseignant__prenoms', 'observations']
    date_hierarchy = 'date'
    ordering = ['-date', 'enseignant__nom']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('enseignant', 'date', 'statut')
        }),
        ('Heures', {
            'fields': ('heure_arrivee', 'heure_depart', 'heures_travaillees')
        }),
        ('Détails', {
            'fields': ('observations', 'justifie')
        }),
        ('Métadonnées', {
            'fields': ('pointe_par', 'date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['date_creation', 'date_modification']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nouveau pointage
            obj.pointe_par = request.user
        super().save_model(request, obj, form, change)
