from django.contrib import admin
from django.db import transaction
from .services import synchroniser_echeancier_apres_changement_paiement, aligner_frais_admission
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
    annee_scolaire_coherente,
    recalculer_remises_paiement,
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
            synchroniser_echeancier_apres_changement_paiement(
                echeancier.eleve_id, echeancier.annee_scolaire,
            )

    def after_corbeille_delete(self, request, obj, context):
        self._recalculer_eleves([context])

    def after_corbeille_delete_queryset(self, request, contexts):
        self._recalculer_eleves(contexts)


@admin.register(TypePaiement)
class TypePaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("nom", "actif")
    search_fields = ("nom",)
    list_filter = ("actif",)

    @transaction.atomic
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
            synchroniser_echeancier_apres_changement_paiement(
                echeancier.eleve_id, echeancier.annee_scolaire,
            )


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

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        ancien = Paiement.objects.select_for_update().get(pk=obj.pk) if change else None
        if 'date_paiement' in getattr(form, 'changed_data', []):
            obj.annee_scolaire = annee_scolaire_coherente(obj.annee_scolaire, obj.date_paiement)
        super().save_model(request, obj, form, change)
        echeancier = obj.echeancier_annuel
        if echeancier and (ancien is None or ancien.type_paiement_id != obj.type_paiement_id):
            aligner_frais_admission(echeancier, obj.type_paiement.nom)
        recalculer_remises_paiement(
            obj, ajuster_montant=ancien is not None and ancien.montant != obj.montant,
        )
        contextes = {(obj.eleve_id, obj.annee_scolaire)}
        if ancien:
            contextes.add((ancien.eleve_id, ancien.annee_scolaire))
        for eleve_id, annee in sorted(contextes):
            synchroniser_echeancier_apres_changement_paiement(eleve_id, annee)


@admin.register(RemiseReduction)
class RemiseReductionAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("nom", "type_remise", "valeur", "motif", "actif")
    search_fields = ("nom",)
    list_filter = ("type_remise", "motif", "actif")

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        paiements = list(
            Paiement.objects.filter(remises__remise=obj).distinct()
        )
        eleve_ids = set()
        for paiement in paiements:
            eleve_ids.add(paiement.eleve_id)
        for echeancier in EcheancierPaiement.objects.filter(eleve_id__in=eleve_ids):
            synchroniser_echeancier_apres_changement_paiement(
                echeancier.eleve_id, echeancier.annee_scolaire,
            )


@admin.register(EcheancierPaiement)
class EcheancierPaiementAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ("eleve", "annee_scolaire", "statut", "total_du", "total_paye")
    search_fields = ("eleve__nom", "eleve__prenom", "eleve__matricule")

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        synchroniser_echeancier_apres_changement_paiement(obj.eleve_id, obj.annee_scolaire)


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

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .recalcul_remises import memoriser_regle_remise
        if not change or {'remise', 'base_calcul', 'applique_tranche_1', 'applique_tranche_2', 'applique_tranche_3'} & set(getattr(form, 'changed_data', [])):
            obj.regle_calcul = memoriser_regle_remise(obj.remise, obj.base_calcul, obj.tranches_appliquees)
            obj.save(update_fields=['regle_calcul'])
        synchroniser_echeancier_apres_changement_paiement(obj.paiement.eleve_id, obj.paiement.annee_scolaire)


@admin.register(Relance)
class RelanceAdmin(PaiementsCorbeilleAdminMixin, admin.ModelAdmin):
    list_display = ('eleve', 'canal', 'statut', 'solde_estime', 'date_creation', 'date_envoi')
    list_filter = ('canal', 'statut')
    search_fields = ('eleve__nom', 'eleve__prenom', 'eleve__matricule', 'message')
    date_hierarchy = 'date_creation'
