"""Rejoue les bases de remise enregistrées sans deviner les règles historiques."""
from decimal import Decimal, ROUND_HALF_UP

from .allocation import ALLOCATION_COMPONENTS, allocate_amount_sequentially
from .models import Paiement


def memoriser_regle_remise(remise, base_calcul, tranches, *, montant_avant_remise=None, montant_net_enregistre=False):
    regle = {
        'base': base_calcul,
        'tranches': sorted(int(n) for n in tranches),
        'type': remise.type_remise,
        'valeur': str(remise.valeur),
    }
    if montant_net_enregistre:
        regle['montant_net_enregistre'] = True
    if montant_avant_remise is not None:
        regle['montant_avant_remise'] = str(montant_avant_remise)
    return regle


def montant_brut_pour_remise(paiement):
    """Retrouve le tarif saisi pour ne pas déduire deux fois une remise."""
    for ligne in paiement.remises.all():
        brut = (ligne.regle_calcul or {}).get('montant_avant_remise')
        if brut is not None:
            return Decimal(str(brut))
    return Decimal(str(paiement.montant))


def montant_affiche_sur_recu(paiement):
    """Les remises déduites avant encaissement sont déjà dans le montant net."""
    remises_non_deduites = sum((
        ligne.montant_remise for ligne in paiement.remises.all()
        if 'montant_avant_remise' not in (ligne.regle_calcul or {})
        and not (ligne.regle_calcul or {}).get('montant_net_enregistre')
    ), Decimal('0'))
    return max(Decimal('0'), Decimal(str(paiement.montant)) - remises_non_deduites)


def recalculer_remises_echeancier(echeancier):
    """Recalcule chaque remise depuis les versements validés qui la précèdent.

    Les paiements en attente sont recalculés mais ne consomment aucun solde.
    Le taux/montant accordé reste celui enregistré, même si le catalogue change.
    """
    paiements = (
        Paiement.objects.filter(eleve_id=echeancier.eleve_id,
                               annee_scolaire=echeancier.annee_scolaire,
                               statut__in=['VALIDE', 'EN_ATTENTE'])
        .prefetch_related('remises')
        .order_by('date_paiement', 'date_creation', 'pk')
    )
    payes = {key: Decimal('0') for key, _, _ in ALLOCATION_COMPONENTS}
    for paiement in paiements:
        allocation, nouveaux_payes, _ = allocate_amount_sequentially(
            echeancier, paiement.montant, initial_paid=payes,
        )
        for ligne in paiement.remises.all():
            regle = ligne.regle_calcul
            if not regle:
                continue
            allocation_base = allocation
            if regle.get('montant_avant_remise') is not None:
                allocation_base, _, _ = allocate_amount_sequentially(
                    echeancier, Decimal(regle['montant_avant_remise']), initial_paid=payes,
                )
            base = sum((
                Decimal(str(getattr(echeancier, f'tranche_{n}_due') or 0))
                if regle['base'] == 'tranches_dues'
                else allocation_base[f'tranche_{n}']
                for n in regle['tranches']
            ), Decimal('0'))
            valeur = Decimal(regle['valeur'])
            montant = base * valeur / 100 if regle['type'] == 'POURCENTAGE' else valeur
            montant = max(Decimal('0'), min(base, montant)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            if montant != ligne.montant_remise:
                ligne.montant_remise = montant
                ligne.save(update_fields=['montant_remise'])
        if paiement.statut == 'VALIDE':
            payes = nouveaux_payes
