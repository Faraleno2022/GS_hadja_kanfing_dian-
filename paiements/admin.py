from django.contrib import admin

from administration.corbeille_admin import CorbeilleAdminMixin

from .models import TypePaiement, ModePaiement, Paiement, RemiseReduction, EcheancierPaiement, TwilioInboundMessage, ConfigurationPaiement


@admin.register(TypePaiement)
class TypePaiementAdmin(admin.ModelAdmin):
    list_display = ("nom", "actif")
    search_fields = ("nom",)
    list_filter = ("actif",)


@admin.register(ModePaiement)
class ModePaiementAdmin(admin.ModelAdmin):
    list_display = ("nom", "frais_supplementaires", "actif")
    search_fields = ("nom",)
    list_filter = ("actif",)


@admin.register(Paiement)
class PaiementAdmin(CorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("numero_recu", "eleve", "annee_scolaire", "type_paiement", "mode_paiement", "montant", "date_paiement", "statut")
    search_fields = ("numero_recu", "eleve__nom", "eleve__prenom", "eleve__matricule")
    list_filter = ("statut", "annee_scolaire", "type_paiement", "mode_paiement")
    list_select_related = ("eleve", "type_paiement", "mode_paiement")
    raw_id_fields = ("eleve",)
    date_hierarchy = "date_paiement"

    def save_model(self, request, obj, form, change):
        from django.db import transaction
        from .services import synchroniser_echeancier_apres_changement_paiement
        from .views import _align_enrollment_fee

        with transaction.atomic():
            ancien = Paiement.objects.select_for_update().get(pk=obj.pk) if change else None
            if ancien and ancien.statut == 'VALIDE' and ancien.montant != obj.montant:
                obj.statut = 'EN_ATTENTE'
                obj.date_validation = None
                obj.valide_par = None
            super().save_model(request, obj, form, change)
            if ancien and ancien.type_paiement_id != obj.type_paiement_id:
                echeancier = EcheancierPaiement.objects.select_for_update().filter(
                    eleve_id=obj.eleve_id, annee_scolaire=obj.annee_scolaire,
                ).first()
                if echeancier:
                    _align_enrollment_fee(obj.eleve, echeancier,
                                          preferred_type_name=obj.type_paiement.nom)
            contextes = {(obj.eleve_id, obj.annee_scolaire)}
            if ancien:
                contextes.add((ancien.eleve_id, ancien.annee_scolaire))
            for eleve_id, annee in sorted(contextes):
                synchroniser_echeancier_apres_changement_paiement(eleve_id, annee)


@admin.register(RemiseReduction)
class RemiseReductionAdmin(CorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("nom", "type_remise", "valeur", "motif", "actif")
    search_fields = ("nom",)
    list_filter = ("type_remise", "motif", "actif")


@admin.register(EcheancierPaiement)
class EcheancierPaiementAdmin(CorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("eleve", "annee_scolaire", "nature_frais", "statut", "total_du", "total_paye")
    list_filter = ("nature_frais", "statut", "annee_scolaire")
    search_fields = ("eleve__nom", "eleve__prenom", "eleve__matricule")
    list_select_related = ("eleve",)
    raw_id_fields = ("eleve",)


@admin.register(TwilioInboundMessage)
class TwilioInboundMessageAdmin(admin.ModelAdmin):
    list_display = ("received_at", "channel", "from_number", "to_number", "message_sid", "delivery_status")
    list_filter = ("channel", "delivery_status")
    search_fields = ("from_number", "to_number", "message_sid", "body")
    date_hierarchy = "received_at"


@admin.register(ConfigurationPaiement)
class ConfigurationPaiementAdmin(admin.ModelAdmin):
    list_display = ("classe", "montant_inscription", "montant_scolarite", "nombre_tranches", "montant_total")
    search_fields = ("classe__nom", "classe__ecole__nom")
    list_filter = ("nombre_tranches", "classe__niveau")
    readonly_fields = ("montant_total", "montant_par_tranche", "repartition_tranches_affichage",
                       "date_creation", "date_modification")

    @admin.display(description="Répartition exacte des tranches (somme = scolarité)")
    def repartition_tranches_affichage(self, obj):
        if not obj or not obj.pk:
            return "-"
        tranches = obj.repartition_tranches()
        if not tranches:
            return "-"
        details = " + ".join(f"{t:,.0f}" for t in tranches)
        return f"{details} = {sum(tranches):,.0f} GNF"
