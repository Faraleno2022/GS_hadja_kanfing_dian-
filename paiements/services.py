"""Services métier reliant les transferts de classe aux échéanciers."""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from eleves.models import GrilleTarifaire

from .allocation import (
    INSCRIPTION,
    TRANCHE_1,
    TRANCHE_2,
    TRANCHE_3,
    allocate_amount,
    echeancier_dues,
    is_reinscription_payment,
    normalize_payment_type,
)
from .models import EcheancierPaiement, Paiement
from .payment_engine import (
    PAID_FIELDS,
    recalculer_echeancier,
    remises_par_tranche,
    situation_echeancier,
)


ZERO = Decimal('0')
BUCKETS = (INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3)


def _decimal(value):
    return Decimal(str(value or 0))


def echeancier_pour_annee(eleve, annee_scolaire=None, *, verrouiller=False):
    """Retourne l'échéancier d'une année, jamais celui d'une autre année."""
    annee = annee_scolaire or getattr(
        getattr(eleve, 'classe', None), 'annee_scolaire', None
    )
    qs = EcheancierPaiement.objects.filter(eleve=eleve)
    if verrouiller:
        qs = qs.select_for_update()
    if annee:
        return qs.filter(annee_scolaire=annee).first()
    return qs.order_by('-annee_scolaire', '-pk').first()


def _total_du(echeancier):
    return sum(echeancier_dues(echeancier).values(), ZERO)


def _nature_frais(eleve, annee_scolaire, *, changement_annee, echeancier=None):
    if echeancier is not None:
        return echeancier.nature_frais

    paiements = (
        Paiement.objects.filter(
            eleve=eleve,
            annee_scolaire=annee_scolaire,
            statut='VALIDE',
        )
        .select_related('type_paiement')
        .order_by('date_paiement', 'date_creation', 'pk')
    )
    for paiement in paiements.iterator():
        nom = getattr(getattr(paiement, 'type_paiement', None), 'nom', '')
        if is_reinscription_payment(nom):
            return 'REINSCRIPTION'
        if 'inscription' in normalize_payment_type(nom):
            return 'INSCRIPTION'
    return 'REINSCRIPTION' if changement_annee else 'INSCRIPTION'


def _dates_nouvel_echeancier(grille, annee_scolaire):
    try:
        annee_fin = int(str(annee_scolaire).split('-', 1)[0]) + 1
    except (TypeError, ValueError, IndexError):
        aujourd_hui = timezone.localdate()
        annee_fin = aujourd_hui.year + (1 if aujourd_hui.month >= 7 else 0)

    aujourd_hui = timezone.localdate()
    return {
        'date_echeance_inscription': (
            grille.date_echeance_inscription_defaut or aujourd_hui
        ),
        'date_echeance_tranche_1': (
            grille.date_echeance_tranche_1_defaut or date(annee_fin, 1, 15)
        ),
        'date_echeance_tranche_2': (
            grille.date_echeance_tranche_2_defaut or date(annee_fin, 3, 15)
        ),
        'date_echeance_tranche_3': (
            grille.date_echeance_tranche_3_defaut or date(annee_fin, 5, 15)
        ),
    }


def _appliquer_grille(echeancier, grille, nature_frais):
    echeancier.nature_frais = nature_frais
    echeancier.frais_inscription_du = (
        grille.frais_reinscription
        if nature_frais == 'REINSCRIPTION'
        else grille.frais_inscription
    ) or ZERO
    echeancier.tranche_1_due = grille.tranche_1 or ZERO
    echeancier.tranche_2_due = grille.tranche_2 or ZERO
    echeancier.tranche_3_due = grille.tranche_3 or ZERO

    for champ_echeancier, champ_grille in (
        ('date_echeance_inscription', 'date_echeance_inscription_defaut'),
        ('date_echeance_tranche_1', 'date_echeance_tranche_1_defaut'),
        ('date_echeance_tranche_2', 'date_echeance_tranche_2_defaut'),
        ('date_echeance_tranche_3', 'date_echeance_tranche_3_defaut'),
    ):
        date_configuree = getattr(grille, champ_grille, None)
        if date_configuree:
            setattr(echeancier, champ_echeancier, date_configuree)


def _statut_depuis_situation(situation):
    if situation['total_du'] <= 0 or situation['solde_restant'] <= 0:
        return 'PAYE_COMPLET'
    if situation['retard_total'] > 0:
        return 'EN_RETARD'
    if situation['total_couvert'] <= 0:
        return 'A_PAYER'
    return 'PAYE_PARTIEL'


def _synchroniser_couverture(echeancier, total_manuel_initial):
    """Rejoue paiements/remises sans modifier les journaux historiques."""
    paiements = Paiement.objects.filter(
        eleve_id=echeancier.eleve_id,
        annee_scolaire=echeancier.annee_scolaire,
        statut='VALIDE',
    )
    total_valide = _decimal(paiements.aggregate(total=Sum('montant'))['total'])

    if paiements.exists():
        recalculer_echeancier(echeancier)
        echeancier.refresh_from_db()
        situation = situation_echeancier(
            echeancier, utiliser_cumuls_legacy=False
        )
        encaissements_conserves = total_valide
    else:
        # Certains anciens imports n'ont pas de journal Paiement mais seulement
        # les cumuls *_paye. On les reventile sur la nouvelle dette au lieu de
        # les effacer.
        remises = remises_par_tranche(echeancier)
        dues = echeancier_dues(echeancier)
        dues_apres_remises = dict(dues)
        dues_apres_remises[TRANCHE_1] = max(ZERO, dues[TRANCHE_1] - remises[1])
        dues_apres_remises[TRANCHE_2] = max(ZERO, dues[TRANCHE_2] - remises[2])
        dues_apres_remises[TRANCHE_3] = max(ZERO, dues[TRANCHE_3] - remises[3])
        _allocation, payes, credit = allocate_amount(
            total_manuel_initial,
            dues_apres_remises,
            payment_type='inscription et scolarite annuelle',
        )
        for bucket, champ in PAID_FIELDS.items():
            setattr(echeancier, champ, payes[bucket])
        echeancier.save()
        situation = situation_echeancier(
            echeancier, utiliser_cumuls_legacy=True
        )
        situation['non_alloue'] = max(situation['non_alloue'], credit)
        statut = _statut_depuis_situation(situation)
        if echeancier.statut != statut:
            echeancier.statut = statut
            echeancier.save(update_fields=['statut', 'date_modification'])
        encaissements_conserves = total_manuel_initial

    return {
        'encaissements_valides': total_valide,
        'encaissements_conserves': encaissements_conserves,
        'credit_non_affecte': situation['non_alloue'],
        'total_remises': situation['total_remises'],
        'solde_restant': situation['solde_restant'],
    }


@transaction.atomic
def reconcilier_transfert_classe(
    eleve, ancienne_classe, nouvelle_classe, *, cree_par=None
):
    """Applique la grille cible en conservant paiements et anciennes années."""
    ancienne_annee = getattr(ancienne_classe, 'annee_scolaire', '') or ''
    nouvelle_annee = getattr(nouvelle_classe, 'annee_scolaire', '') or ''
    changement_annee = ancienne_annee != nouvelle_annee
    resultat = {
        'ancienne_annee': ancienne_annee,
        'nouvelle_annee': nouvelle_annee,
        'changement_annee': changement_annee,
        'echeancier_cree': False,
        'echeancier_mis_a_jour': False,
        'grille_manquante': False,
        'ancien_total_du': ZERO,
        'nouveau_total_du': ZERO,
        'encaissements_valides': ZERO,
        'encaissements_conserves': ZERO,
        'credit_non_affecte': ZERO,
        'total_remises': ZERO,
        'solde_restant': ZERO,
    }

    grille = GrilleTarifaire.objects.filter(
        ecole_id=nouvelle_classe.ecole_id,
        niveau=nouvelle_classe.niveau,
        annee_scolaire=nouvelle_annee,
    ).first()
    if grille is None:
        resultat['grille_manquante'] = True
        return resultat

    ancien_echeancier = echeancier_pour_annee(eleve, ancienne_annee)
    if ancien_echeancier is not None:
        resultat['ancien_total_du'] = _total_du(ancien_echeancier)

    echeancier = echeancier_pour_annee(
        eleve, nouvelle_annee, verrouiller=True
    )
    nature = _nature_frais(
        eleve,
        nouvelle_annee,
        changement_annee=changement_annee,
        echeancier=echeancier,
    )

    if echeancier is None:
        echeancier = EcheancierPaiement(
            eleve=eleve,
            annee_scolaire=nouvelle_annee,
            nature_frais=nature,
            cree_par=(
                cree_par if getattr(cree_par, 'is_authenticated', False) else None
            ),
            **_dates_nouvel_echeancier(grille, nouvelle_annee),
        )
        total_manuel_initial = ZERO
        _appliquer_grille(echeancier, grille, nature)
        echeancier.save()
        resultat['echeancier_cree'] = True
    else:
        total_manuel_initial = sum(
            (_decimal(getattr(echeancier, champ, 0)) for champ in PAID_FIELDS.values()),
            ZERO,
        )
        _appliquer_grille(echeancier, grille, nature)
        echeancier.save()

    resultat.update(_synchroniser_couverture(echeancier, total_manuel_initial))
    resultat['echeancier_mis_a_jour'] = True
    resultat['nouveau_total_du'] = _total_du(echeancier)
    resultat['echeancier_id'] = echeancier.pk
    return resultat
