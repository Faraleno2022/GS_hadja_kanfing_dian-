from django.contrib import admin
from .models import (
    CategorieDepense, Fournisseur, Depense, PieceJustificative,
    BudgetAnnuel, HistoriqueDepense
)
from .models_logistique import BienEtablissement, ContributionRamePapier
from .models_fournitures import FournitureScolaire, VenteFourniture
from .models_bibliotheque import (
    CategorieLivre, Livre, Emprunt, Reservation,
    HistoriqueLivre, ParametreBibliotheque
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


# ===== LOGISTIQUE =====
@admin.register(BienEtablissement)
class BienEtablissementAdmin(admin.ModelAdmin):
    list_display = [
        'code_bien', 'nom', 'ecole', 'type_bien', 'quantite_achetee',
        'quantite_utilisee', 'quantite_endommagee', 'quantite_disponible',
        'prix_achat_unitaire', 'etat',
    ]
    list_filter = ['ecole', 'type_bien', 'etat', 'actif']
    search_fields = ['code_bien', 'nom', 'marque', 'localisation']
    readonly_fields = ['valeur_achat']


@admin.register(ContributionRamePapier)
class ContributionRamePapierAdmin(admin.ModelAdmin):
    list_display = [
        'date_contribution', 'eleve', 'ecole', 'annee_scolaire',
        'mode_contribution', 'nombre_paquets', 'montant_paye',
    ]
    list_filter = ['ecole', 'annee_scolaire', 'mode_contribution', 'date_contribution']
    search_fields = ['eleve__matricule', 'eleve__nom', 'eleve__prenom']
    date_hierarchy = 'date_contribution'


# ===== FOURNITURES SCOLAIRES =====
@admin.register(FournitureScolaire)
class FournitureScolaireAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'nom', 'ecole', 'categorie', 'quantite_stock',
        'quantite_vendue', 'quantite_restante', 'prix_achat_unitaire',
        'prix_vente_unitaire', 'actif',
    ]
    list_filter = ['ecole', 'categorie', 'unite', 'actif']
    search_fields = ['reference', 'nom', 'description']
    readonly_fields = ['quantite_vendue', 'quantite_restante', 'chiffre_affaires', 'solde']


@admin.register(VenteFourniture)
class VenteFournitureAdmin(admin.ModelAdmin):
    list_display = [
        'numero_vente', 'date_vente', 'produit', 'ecole', 'quantite',
        'prix_vente_unitaire', 'montant_total', 'client',
    ]
    list_filter = ['ecole', 'date_vente', 'produit__categorie']
    search_fields = ['numero_vente', 'produit__nom', 'produit__reference', 'client']
    date_hierarchy = 'date_vente'
    readonly_fields = ['numero_vente', 'montant_total', 'marge']


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


# ── Modules de recouvrement ────────────────────────────────────────────────

from .models_recouvrement import (
    AbonnementInformatique, DepenseCuisine, DepenseDocument, Versement,
)


@admin.register(DepenseCuisine)
class DepenseCuisineAdmin(admin.ModelAdmin):
    list_display = ['date', 'designation', 'montant', 'ecole', 'cree_par']
    list_filter = ['ecole', 'date']
    search_fields = ['designation', 'observation']
    date_hierarchy = 'date'


@admin.register(DepenseDocument)
class DepenseDocumentAdmin(admin.ModelAdmin):
    list_display = ['date', 'designation', 'montant', 'ecole', 'cree_par']
    list_filter = ['ecole', 'date']
    search_fields = ['designation', 'observation']
    date_hierarchy = 'date'


@admin.register(Versement)
class VersementAdmin(admin.ModelAdmin):
    list_display = ['date', 'lieu_versement', 'montant', 'ecole', 'cree_par']
    list_filter = ['ecole', 'date']
    search_fields = ['lieu_versement', 'observation']
    date_hierarchy = 'date'


@admin.register(AbonnementInformatique)
class AbonnementInformatiqueAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'montant', 'date_debut', 'date_fin', 'statut', 'jours_restants']
    list_filter = ['statut', 'date_fin']
    search_fields = ['eleve__matricule', 'eleve__nom', 'eleve__prenom']
    date_hierarchy = 'date_fin'
    readonly_fields = ['jours_restants']
