from django.contrib import admin
from administration.admin_mixins import CorbeilleAdminMixin

from .models import (
    ConfigurationPaiement,
    EcheancierPaiement,
    ModePaiement,
    Paiement,
    PaiementRemise,
    Relance,
    RemiseReduction,
    TwilioInboundMessage,
    TypePaiement,
)
from .payment_engine import (
    recalculer_echeancier,
    recalculer_remises_paiement,
    school_year_from_date,
)


class PaiementsCorbeilleAdminMixin(CorbeilleAdminMixin):
    """Corbeille + resynchronisation des échéanciers impactés."""

    def get_corbeille_delete_context(self, obj):
        if isinstance(obj, Paiement):
            return {obj.eleve_id}
        if isinstance(obj, PaiementRemise):
            eleve_id = Paiement.objects.filter(pk=obj.paiement_id).values_list(
                'eleve_id', flat=True
            ).first()
            return {eleve_id} if eleve_id else set()
        if isinstance(obj, RemiseReduction):
            return set(
                PaiementRemise.objects.filter(remise=obj).values_list(
                    'paiement__eleve_id', flat=True
                )
            )
        if isinstance(obj, (TypePaiement, ModePaiement)):
            filtre = {'type_paiement': obj} if isinstance(obj, TypePaiement) else {
                'mode_paiement': obj
            }
            return set(Paiement.objects.filter(**filtre).values_list('eleve_id', flat=True))
        return set()

    @staticmethod
    def _recalculer_eleves(contextes):
        ids = set()
        for contexte in contextes:
            ids.update(contexte or set())
        for echeancier in EcheancierPaiement.objects.filter(eleve_id__in=ids):
            recalculer_echeancier(echeancier)

    def after_corbeille_delete(self, request, obj, context):
        self._recalculer_eleves([context])

    def after_corbeille_delete_queryset(self, request, contexts):
        self._recalculer_eleves(contexts)


@admin.register(TypePaiement)
class TypePaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("nom", "actif")
    search_fields = ("nom",)
    list_filter = ("actif",)

    def save_model(self, request, obj, form, change):
        eleve_ids = set()
        if change and obj.pk:
            eleve_ids.update(
                Paiement.objects.filter(type_paiement=obj).values_list(
                    'eleve_id', flat=True
                )
            )
        super().save_model(request, obj, form, change)
        for echeancier in EcheancierPaiement.objects.filter(eleve_id__in=eleve_ids):
            recalculer_echeancier(echeancier)


@admin.register(ModePaiement)
class ModePaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("nom", "frais_supplementaires", "actif")
    search_fields = ("nom",)
    list_filter = ("actif",)


@admin.register(Paiement)
class PaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("numero_recu", "eleve", "annee_scolaire", "type_paiement", "mode_paiement", "montant", "date_paiement", "statut")
    search_fields = ("numero_recu", "eleve__nom", "eleve__prenom", "eleve__matricule")
    list_filter = ("statut", "type_paiement", "mode_paiement")
    date_hierarchy = "date_paiement"

    def save_model(self, request, obj, form, change):
        ancien_eleve_id = None
        if change and obj.pk:
            ancien_eleve_id = Paiement.objects.filter(pk=obj.pk).values_list(
                'eleve_id', flat=True
            ).first()
        if 'date_paiement' in getattr(form, 'changed_data', []):
            obj.annee_scolaire = school_year_from_date(obj.date_paiement)
        super().save_model(request, obj, form, change)
        recalculer_remises_paiement(obj)
        eleve_ids = {obj.eleve_id, ancien_eleve_id} - {None}
        for echeancier in EcheancierPaiement.objects.filter(eleve_id__in=eleve_ids):
            recalculer_echeancier(echeancier)


@admin.register(RemiseReduction)
class RemiseReductionAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("nom", "type_remise", "valeur", "motif", "actif")
    search_fields = ("nom",)
    list_filter = ("type_remise", "motif", "actif")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        paiements = list(
            Paiement.objects.filter(remises__remise=obj).distinct()
        )
        eleve_ids = set()
        for paiement in paiements:
            recalculer_remises_paiement(paiement)
            eleve_ids.add(paiement.eleve_id)
        for echeancier in EcheancierPaiement.objects.filter(eleve_id__in=eleve_ids):
            recalculer_echeancier(echeancier)


@admin.register(EcheancierPaiement)
class EcheancierPaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("eleve", "annee_scolaire", "statut", "total_du", "total_paye")
    search_fields = ("eleve__nom", "eleve__prenom", "eleve__matricule")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        recalculer_echeancier(obj)


@admin.register(TwilioInboundMessage)
class TwilioInboundMessageAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("received_at", "channel", "from_number", "to_number", "message_sid", "delivery_status")
    list_filter = ("channel", "delivery_status")
    search_fields = ("from_number", "to_number", "message_sid", "body")
    date_hierarchy = "received_at"


@admin.register(ConfigurationPaiement)
class ConfigurationPaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
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


@admin.register(PaiementRemise)
class PaiementRemiseAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = (
        'paiement', 'remise', 'libelle_portee', 'base_calcul',
        'montant_base', 'montant_remise', 'motif',
    )
    list_filter = ('base_calcul', 'motif', 'applique_tranche_1', 'applique_tranche_2', 'applique_tranche_3')
    search_fields = ('paiement__numero_recu', 'paiement__eleve__nom', 'remise__nom')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        recalculer_echeancier(obj.paiement.eleve)


@admin.register(Relance)
class RelanceAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ('eleve', 'canal', 'statut', 'solde_estime', 'date_creation', 'date_envoi')
    list_filter = ('canal', 'statut')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule', 'message')
    date_hierarchy = 'date_creation'
