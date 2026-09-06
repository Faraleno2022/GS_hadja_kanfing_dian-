"""Rejoue les bases de remise enregistrées sans deviner les règles historiques."""
from decimal import Decimal

from .allocation import ALLOCATION_COMPONENTS, allocate_amount_sequentially
from .models import Paiement


def memoriser_regle_remise(remise, base_calcul, tranches):
    return {
        'base': base_calcul,
        'tranches': sorted(int(n) for n in tranches),
        'type': remise.type_remise,
        'valeur': str(remise.valeur),
    }


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
            base = sum((
                Decimal(str(getattr(echeancier, f'tranche_{n}_due') or 0))
                if regle['base'] == 'tranches_dues'
                else allocation[f'tranche_{n}']
                for n in regle['tranches']
            ), Decimal('0'))
            valeur = Decimal(regle['valeur'])
            montant = base * valeur / 100 if regle['type'] == 'POURCENTAGE' else valeur
            montant = max(Decimal('0'), min(base, montant)).quantize(Decimal('1'))
            if montant != ligne.montant_remise:
                ligne.montant_remise = montant
                ligne.save(update_fields=['montant_remise'])
        if paiement.statut == 'VALIDE':
            payes = nouveaux_payes
