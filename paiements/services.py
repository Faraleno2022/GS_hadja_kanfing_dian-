"""Services metier reliant les changements de classe aux echeanciers."""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from eleves.models import GrilleTarifaire

from .allocation import (
    ALLOCATION_COMPONENTS,
    allocate_amount_sequentially,
    allocate_discounts,
    registration_kind_for_type,
)
from .models import EcheancierPaiement, Paiement, PaiementRemise


def _decimal(value):
    return Decimal(str(value or 0))


def _total_du(echeancier):
    return sum(
        (_decimal(getattr(echeancier, due_field, 0)) for _, due_field, _ in ALLOCATION_COMPONENTS),
        Decimal("0"),
    )


def _nature_frais(eleve, annee_scolaire, *, nouvelle_annee, echeancier=None):
    """Determine si la grille doit utiliser l'inscription ou la reinscription."""
    if echeancier is not None:
        return echeancier.nature_frais

    paiement_admission = (
        Paiement.objects.filter(
            eleve=eleve,
            annee_scolaire=annee_scolaire,
            statut="VALIDE",
        )
        .select_related("type_paiement")
        .order_by("date_paiement", "date_creation", "pk")
    )
    for paiement in paiement_admission.iterator():
        nature = registration_kind_for_type(paiement.type_paiement)
        if nature == "reinscription":
            return EcheancierPaiement.NATURE_REINSCRIPTION
        if nature == "inscription":
            return EcheancierPaiement.NATURE_INSCRIPTION

    if nouvelle_annee:
        return EcheancierPaiement.NATURE_REINSCRIPTION
    return EcheancierPaiement.NATURE_INSCRIPTION


def _dates_nouvel_echeancier(grille, annee_scolaire):
    try:
        annee_fin = int(str(annee_scolaire).split("-")[0]) + 1
    except (TypeError, ValueError, IndexError):
        aujourd_hui = timezone.localdate()
        annee_fin = aujourd_hui.year + (1 if aujourd_hui.month >= 9 else 0)

    aujourd_hui = timezone.localdate()
    return {
        "date_echeance_inscription": (
            grille.date_echeance_inscription_defaut or aujourd_hui
        ),
        "date_echeance_tranche_1": (
            grille.date_echeance_tranche_1_defaut or date(annee_fin, 1, 15)
        ),
        "date_echeance_tranche_2": (
            grille.date_echeance_tranche_2_defaut or date(annee_fin, 3, 15)
        ),
        "date_echeance_tranche_3": (
            grille.date_echeance_tranche_3_defaut or date(annee_fin, 5, 15)
        ),
    }


def _appliquer_grille(echeancier, grille, nature_frais):
    echeancier.nature_frais = nature_frais
    echeancier.frais_inscription_du = (
        grille.frais_reinscription
        if nature_frais == EcheancierPaiement.NATURE_REINSCRIPTION
        else grille.frais_inscription
    ) or 0
    echeancier.tranche_1_due = grille.tranche_1 or 0
    echeancier.tranche_2_due = grille.tranche_2 or 0
    echeancier.tranche_3_due = grille.tranche_3 or 0

    # Une date explicitement configuree sur la nouvelle grille est prioritaire.
    # En son absence, une date personnalisee deja presente est preservee.
    correspondances_dates = (
        ("date_echeance_inscription", "date_echeance_inscription_defaut"),
        ("date_echeance_tranche_1", "date_echeance_tranche_1_defaut"),
        ("date_echeance_tranche_2", "date_echeance_tranche_2_defaut"),
        ("date_echeance_tranche_3", "date_echeance_tranche_3_defaut"),
    )
    for champ_echeancier, champ_grille in correspondances_dates:
        date_configuree = getattr(grille, champ_grille, None)
        if date_configuree:
            setattr(echeancier, champ_echeancier, date_configuree)


def _synchroniser_couverture(echeancier, *, conserver_saisie_manuelle=True):
    """Reventile les encaissements sans modifier les objets Paiement historiques."""
    total_valide = _decimal(
        Paiement.objects.filter(
            eleve_id=echeancier.eleve_id,
            annee_scolaire=echeancier.annee_scolaire,
            statut="VALIDE",
        ).aggregate(total=Sum("montant"))["total"]
    )
    total_saisi = sum(
        (
            _decimal(getattr(echeancier, paid_field, 0))
            for _, _, paid_field in ALLOCATION_COMPONENTS
        ),
        Decimal("0"),
    )
    encaissement = max(total_valide, total_saisi) if conserver_saisie_manuelle else total_valide

    allocation, nouveaux_payes, credit = allocate_amount_sequentially(
        echeancier,
        encaissement,
        initial_paid={key: Decimal("0") for key, _, _ in ALLOCATION_COMPONENTS},
    )
    for key, _due_field, paid_field in ALLOCATION_COMPONENTS:
        setattr(echeancier, paid_field, nouveaux_payes[key])

    remises = (
        PaiementRemise.objects.filter(
            paiement__eleve_id=echeancier.eleve_id,
            paiement__annee_scolaire=echeancier.annee_scolaire,
            paiement__statut="VALIDE",
        )
        .select_related("paiement")
        .order_by("paiement__date_paiement", "paiement_id", "pk")
    )
    soldes_apres_encaissement = {
        key: max(
            Decimal("0"),
            _decimal(getattr(echeancier, due_field, 0)) - nouveaux_payes[key],
        )
        for key, due_field, _paid_field in ALLOCATION_COMPONENTS
    }
    allocation_remises, _ = allocate_discounts(
        echeancier,
        remises,
        balances=soldes_apres_encaissement,
    )

    couverture = sum(allocation.values(), Decimal("0")) + sum(
        allocation_remises.values(), Decimal("0")
    )
    total_du = _total_du(echeancier)
    aujourd_hui = timezone.localdate()
    exigible = Decimal("0")
    exigible_couvert = Decimal("0")
    dates = {
        "inscription": echeancier.date_echeance_inscription,
        "tranche_1": echeancier.date_echeance_tranche_1,
        "tranche_2": echeancier.date_echeance_tranche_2,
        "tranche_3": echeancier.date_echeance_tranche_3,
    }
    for key, due_field, _paid_field in ALLOCATION_COMPONENTS:
        date_echeance = dates[key]
        if date_echeance and date_echeance < aujourd_hui:
            exigible += _decimal(getattr(echeancier, due_field, 0))
            exigible_couvert += allocation[key] + allocation_remises[key]

    if total_du <= 0 or couverture >= total_du:
        echeancier.statut = "PAYE_COMPLET"
    elif exigible > 0 and exigible_couvert < exigible:
        echeancier.statut = "EN_RETARD"
    elif couverture <= 0:
        echeancier.statut = "A_PAYER"
    else:
        echeancier.statut = "PAYE_PARTIEL"

    return {
        "encaissements_valides": total_valide,
        "encaissements_conserves": encaissement,
        "credit_non_affecte": credit,
        "solde_restant": max(Decimal("0"), total_du - couverture),
    }


@transaction.atomic
def synchroniser_echeancier_apres_changement_paiement(eleve_id, annee_scolaire):
    """Recalcule la couverture après suppression ou restauration d'un paiement.

    L'échéancier appartient à l'élève et à l'année, pas à un versement unique.
    Il reste donc en place et seuls ses montants payés ainsi que son statut sont
    reconstruits depuis les paiements validés encore actifs.
    """
    echeancier = (
        EcheancierPaiement.objects.select_for_update()
        .filter(eleve_id=eleve_id, annee_scolaire=annee_scolaire)
        .first()
    )
    if echeancier is None:
        return None

    _synchroniser_couverture(echeancier, conserver_saisie_manuelle=False)
    echeancier.save()
    return echeancier


@transaction.atomic
def reconcilier_transfert_classe(eleve, ancienne_classe, nouvelle_classe, *, cree_par=None):
    """Applique la grille cible tout en preservant l'historique financier.

    Un changement dans la meme annee met a jour l'echeancier existant. Un
    changement d'annee conserve l'ancien echeancier et cree (ou actualise)
    celui de la nouvelle annee. Les paiements ne changent jamais d'annee.
    """
    ancienne_annee = getattr(ancienne_classe, "annee_scolaire", "") or ""
    nouvelle_annee = getattr(nouvelle_classe, "annee_scolaire", "") or ""
    changement_annee = ancienne_annee != nouvelle_annee
    resultat = {
        "ancienne_annee": ancienne_annee,
        "nouvelle_annee": nouvelle_annee,
        "changement_annee": changement_annee,
        "echeancier_cree": False,
        "echeancier_mis_a_jour": False,
        "grille_manquante": False,
        "ancien_total_du": Decimal("0"),
        "nouveau_total_du": Decimal("0"),
        "encaissements_valides": Decimal("0"),
        "encaissements_conserves": Decimal("0"),
        "credit_non_affecte": Decimal("0"),
        "solde_restant": Decimal("0"),
    }

    grille = GrilleTarifaire.objects.filter(
        ecole_id=nouvelle_classe.ecole_id,
        niveau=nouvelle_classe.niveau,
        annee_scolaire=nouvelle_annee,
    ).first()
    if grille is None:
        resultat["grille_manquante"] = True
        return resultat

    ancien_echeancier = EcheancierPaiement.objects.filter(
        eleve=eleve,
        annee_scolaire=ancienne_annee,
    ).first()
    if ancien_echeancier is not None:
        resultat["ancien_total_du"] = _total_du(ancien_echeancier)

    echeancier = (
        EcheancierPaiement.objects.select_for_update()
        .filter(eleve=eleve, annee_scolaire=nouvelle_annee)
        .first()
    )
    nature = _nature_frais(
        eleve,
        nouvelle_annee,
        nouvelle_annee=changement_annee,
        echeancier=echeancier,
    )

    if echeancier is None:
        valeurs_dates = _dates_nouvel_echeancier(grille, nouvelle_annee)
        echeancier = EcheancierPaiement(
            eleve=eleve,
            annee_scolaire=nouvelle_annee,
            nature_frais=nature,
            cree_par=cree_par if getattr(cree_par, "is_authenticated", False) else None,
            **valeurs_dates,
        )
        _appliquer_grille(echeancier, grille, nature)
        echeancier.save()
        resultat["echeancier_cree"] = True
    else:
        _appliquer_grille(echeancier, grille, nature)

    couverture = _synchroniser_couverture(
        echeancier,
        conserver_saisie_manuelle=not changement_annee,
    )
    echeancier.save()

    resultat.update(couverture)
    resultat["echeancier_mis_a_jour"] = True
    resultat["nouveau_total_du"] = _total_du(echeancier)
    resultat["echeancier_id"] = echeancier.pk
    return resultat
