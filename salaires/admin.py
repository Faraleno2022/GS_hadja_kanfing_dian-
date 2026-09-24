from django.contrib import admin
from .models import (
    Enseignant, TypeEnseignant, StatutEnseignant, 
    AffectationClasse, PeriodeSalaire, EtatSalaire, 
    DetailHeuresClasse, PresenceEnseignant, AvanceSalaire,
    RemboursementAvance, ParametrePaie,
)


@admin.register(ParametrePaie)
class ParametrePaieAdmin(admin.ModelAdmin):
    list_display = [
        'ecole', 'taux_anciennete_par_an', 'taux_eloignement_par_km',
        'prime_craie_par_eleve', 'prime_par_heure_revision',
        'prime_professeur_principal',
    ]


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = [
        'nom', 'prenoms', 'ecole', 'type_enseignant',
        'classe_principale', 'fonction', 'statut',
    ]
    list_filter = ['ecole', 'type_enseignant', 'statut']
    search_fields = [
        'nom', 'prenoms', 'telephone', 'email', 'fonction',
        'classe_principale__nom',
    ]
    list_select_related = ['ecole', 'classe_principale']


@admin.register(AffectationClasse)
class AffectationClasseAdmin(admin.ModelAdmin):
    list_display = [
        'enseignant', 'classe', 'matiere', 'heures_par_semaine',
        'date_debut', 'date_fin', 'actif',
    ]
    list_filter = ['actif', 'classe__ecole', 'classe__annee_scolaire']
    search_fields = [
        'enseignant__nom', 'enseignant__prenoms', 'classe__nom', 'matiere',
    ]
    list_select_related = ['enseignant', 'classe']


@admin.register(EtatSalaire)
class EtatSalaireAdmin(admin.ModelAdmin):
    list_display = [
        'enseignant', 'periode', 'jours_presence', 'total_heures',
        'salaire_base', 'salaire_net', 'valide', 'paye',
    ]
    list_filter = ['periode', 'valide', 'paye', 'mode_calcul_heures']
    search_fields = ['enseignant__nom', 'enseignant__prenoms']


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


@admin.register(AvanceSalaire)
class AvanceSalaireAdmin(admin.ModelAdmin):
    list_display = [
        'enseignant', 'date_avance', 'periode_prevue', 'montant',
        'montant_rembourse', 'solde_restant', 'reference_externe',
    ]
    list_filter = ['date_avance', 'periode_prevue__ecole', 'periode_prevue']
    search_fields = [
        'enseignant__nom', 'enseignant__prenoms', 'reference_externe', 'motif'
    ]
    readonly_fields = ['date_creation', 'date_modification']


@admin.register(RemboursementAvance)
class RemboursementAvanceAdmin(admin.ModelAdmin):
    list_display = ['avance', 'etat_salaire', 'montant', 'date_creation']
    list_filter = ['etat_salaire__periode', 'etat_salaire__periode__ecole']
    search_fields = ['avance__enseignant__nom', 'avance__enseignant__prenoms']
    readonly_fields = ['date_creation']
