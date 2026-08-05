from django.contrib import admin
from .models import (
    CategorieDepense, Fournisseur, Depense, PieceJustificative,
    BudgetAnnuel, HistoriqueDepense
)
from .models_logistique import (
    BienEtablissement, ContributionPapierRame
)
from .models_bibliotheque import (
    CategorieLivre, Livre, Emprunt, Reservation,
    HistoriqueLivre, ParametreBibliotheque
)
from .models_recouvrement import (
    DepenseCuisine, DepenseDocument, Versement, AbonnementInformatique
)


# ===== DÉPENSES =====
@admin.register(CategorieDepense)
class CategorieDepenseAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'actif']
    list_filter = ['actif']
    search_fields = ['nom', 'code']


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_fournisseur', 'telephone', 'email', 'actif']
    list_filter = ['type_fournisseur', 'actif']
    search_fields = ['nom', 'telephone', 'email']


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ['numero_facture', 'libelle', 'fournisseur', 'montant_ttc', 'date_facture', 'statut']
    list_filter = ['statut', 'type_depense', 'categorie']
    search_fields = ['numero_facture', 'libelle', 'fournisseur__nom']
    date_hierarchy = 'date_facture'


# ===== RECOUVREMENT (nouveaux modules) =====
@admin.register(DepenseCuisine)
class DepenseCuisineAdmin(admin.ModelAdmin):
    list_display = ['designation', 'montant', 'date', 'cree_par']
    list_filter = ['date']
    search_fields = ['designation', 'observation']
    date_hierarchy = 'date'


@admin.register(DepenseDocument)
class DepenseDocumentAdmin(admin.ModelAdmin):
    list_display = ['designation', 'montant', 'date', 'cree_par']
    list_filter = ['date']
    search_fields = ['designation', 'observation']
    date_hierarchy = 'date'


@admin.register(Versement)
class VersementAdmin(admin.ModelAdmin):
    list_display = ['lieu_versement', 'montant', 'date', 'cree_par']
    list_filter = ['date']
    search_fields = ['lieu_versement', 'observation']
    date_hierarchy = 'date'


@admin.register(AbonnementInformatique)
class AbonnementInformatiqueAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'montant', 'date_debut', 'date_fin', 'statut']
    list_filter = ['statut']
    search_fields = ['eleve__nom', 'eleve__prenom', 'eleve__matricule']
    date_hierarchy = 'date_fin'


# ===== LOGISTIQUE =====
@admin.register(BienEtablissement)
class BienEtablissementAdmin(admin.ModelAdmin):
    list_display = [
        'code_bien', 'nom', 'type_bien', 'quantite_achetee',
        'quantite_utilisee', 'quantite_gatee', 'quantite_disponible', 'etat',
    ]
    list_filter = ['type_bien', 'etat', 'actif']
    search_fields = ['code_bien', 'nom', 'localisation']


@admin.register(ContributionPapierRame)
class ContributionPapierRameAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'type_contribution', 'nombre_paquets', 'montant_paye', 'date_contribution']
    list_filter = ['type_contribution', 'date_contribution']
    search_fields = ['eleve__matricule', 'eleve__nom', 'eleve__prenom']
    date_hierarchy = 'date_contribution'


# ===== BIBLIOTHÈQUE =====
@admin.register(CategorieLivre)
class CategorieLivreAdmin(admin.ModelAdmin):
    list_display = ['code', 'nom', 'actif']
    list_filter = ['actif']
    search_fields = ['nom', 'code']


@admin.register(Livre)
class LivreAdmin(admin.ModelAdmin):
    list_display = ['code_livre', 'titre', 'auteur', 'categorie', 'statut', 'exemplaires_disponibles', 'etat']
    list_filter = ['categorie', 'statut', 'etat', 'langue']
    search_fields = ['code_livre', 'isbn', 'titre', 'auteur', 'editeur']
    readonly_fields = ['est_disponible', 'taux_disponibilite']


@admin.register(Emprunt)
class EmpruntAdmin(admin.ModelAdmin):
    list_display = ['numero_emprunt', 'livre', 'eleve', 'date_emprunt', 'date_retour_prevue', 'statut', 'jours_retard']
    list_filter = ['statut', 'date_emprunt']
    search_fields = ['numero_emprunt', 'livre__titre', 'eleve__nom', 'eleve__prenom']
    date_hierarchy = 'date_emprunt'
    readonly_fields = ['est_en_retard', 'jours_restants']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['numero_reservation', 'livre', 'eleve', 'date_reservation', 'statut']
    list_filter = ['statut', 'date_reservation']
    search_fields = ['numero_reservation', 'livre__titre', 'eleve__nom']
    date_hierarchy = 'date_reservation'


@admin.register(ParametreBibliotheque)
class ParametreBibliothequeAdmin(admin.ModelAdmin):
    list_display = ['duree_emprunt_defaut', 'nombre_emprunts_max', 'penalite_retard_journalier']
    
    def has_add_permission(self, request):
        # Permettre seulement un seul enregistrement
        return not ParametreBibliotheque.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
