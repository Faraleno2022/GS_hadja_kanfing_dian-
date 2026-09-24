"""Recalcul chronologique des remises, avec conservation du taux accordé."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q

from .allocation import ALL_BUCKETS, allocate_amount, echeancier_dues, replay_payment_allocations
from .models import EcheancierPaiement, Paiement, PaiementRemise
from .remise_utils import normaliser_tranches

ZERO = Decimal('0')


def memoriser_regle_remise(remise, base_calcul, tranches, *, montant_brut=None):
    regle = {
        'base': base_calcul,
        'tranches': normaliser_tranches(tranches),
        'type': remise.type_remise,
        'valeur': str(remise.valeur),
    }
    if montant_brut is not None:
        regle['montant_brut'] = str(montant_brut)
    return regle


@transaction.atomic
def recalculer_remises_echeancier(echeancier, *, paiement_corrige=None):
    """Rejoue chaque remise avant de consommer le versement correspondant.

    Les lignes sans règle enregistrée gardent leur montant. Les paiements en
    attente ne consomment pas de solde. Les encaissements sont conservés, sauf
    la déduction explicitement recalculée sur le reçu en cours de correction.
    """
    from .payment_engine import (
        _repartition_lien_remise, repartir_montant_sur_tranches, school_year_bounds,
    )

    echeancier = EcheancierPaiement.objects.select_for_update().get(pk=echeancier.pk)
    from .revisions import synchroniser_revisions
    synchroniser_revisions(echeancier)
    debut, fin = school_year_bounds(echeancier.annee_scolaire)
    legacy = Q(annee_scolaire='')
    if debut and fin:
        legacy &= Q(date_paiement__range=(debut, fin))
    paiements = (
        Paiement.objects.select_for_update().select_related('type_paiement')
        .filter(eleve_id=echeancier.eleve_id, statut__in=['VALIDE', 'EN_ATTENTE'])
        .filter(Q(annee_scolaire=echeancier.annee_scolaire) | legacy)
        .order_by('date_paiement', 'date_creation', 'pk')
    )
    dues = echeancier_dues(echeancier)
    couverture = {bucket: ZERO for bucket in ALL_BUCKETS}
    remises_validees = {bucket: ZERO for bucket in ALL_BUCKETS}
    valides = []
    for paiement in paiements:
        liens = list(PaiementRemise.objects.select_for_update().filter(
            paiement=paiement,
        ).order_by('-origine_revision', 'pk'))
        ancien_deduit = sum((l.montant_remise for l in liens if l.deduite_du_paiement), ZERO)
        brut = paiement.montant + ancien_deduit
        corrige = paiement.pk == getattr(paiement_corrige, 'pk', None)
        references = [l.regle_calcul.get('montant_brut') for l in liens
                      if l.deduite_du_paiement and l.regle_calcul.get('montant_brut') is not None]
        if references and not corrige:
            brut = Decimal(references[0])
        allocation, _, _ = allocate_amount(brut, dues, couverture, paiement.type_paiement.nom)
        capacites = {n: max(ZERO, dues[f'tranche_{n}'] - remises_validees[f'tranche_{n}'])
                     for n in (1, 2, 3)}
        # Réserver les anciennes remises fixes avant les règles recalculables.
        for lien in liens:
            if not lien.regle_calcul:
                for n, montant in _repartition_lien_remise(lien, echeancier).items():
                    capacites[n] = max(ZERO, capacites[n] - montant)
        for lien in liens:
            if not lien.regle_calcul:
                continue
            regle = dict(lien.regle_calcul)
            numeros = normaliser_tranches(regle['tranches'])
            sur_tranches = regle['base'] in ('TRANCHE', 'tranches_dues')
            bases = {n: dues[f'tranche_{n}'] if sur_tranches else allocation[f'tranche_{n}']
                     for n in numeros}
            base = sum(bases.values(), ZERO)
            valeur = Decimal(regle['valeur'])
            nominal = base * valeur / 100 if regle['type'] == 'POURCENTAGE' else valeur
            nominal = max(ZERO, min(base, nominal)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            disponibles = {n: min(bases[n], capacites[n]) for n in numeros}
            repartition = repartir_montant_sur_tranches(nominal, disponibles, numeros)
            updates = {
                'montant_base': base, 'montant_remise': sum(repartition.values(), ZERO),
                **{f'montant_tranche_{n}': repartition[n] for n in (1, 2, 3)},
            }
            if lien.origine_revision and updates['montant_remise'] != Decimal('20000'):
                from django.core.exceptions import ValidationError
                raise ValidationError('Les remises existantes ne permettent pas la réduction de révision de 20 000 GNF.')
            if lien.deduite_du_paiement:
                regle['montant_brut'] = str(brut)
                updates['regle_calcul'] = regle
            changed = []
            for field, value in updates.items():
                if getattr(lien, field) != value:
                    setattr(lien, field, value)
                    changed.append(field)
            if changed:
                lien.save(update_fields=changed)
            for n in numeros:
                capacites[n] = max(ZERO, capacites[n] - repartition[n])
        if corrige:
            nouveau_deduit = sum((l.montant_remise for l in liens if l.deduite_du_paiement), ZERO)
            if nouveau_deduit != ancien_deduit:
                paiement.montant = brut - nouveau_deduit
                paiement.save(update_fields=['montant', 'date_modification'])
        if paiement.statut == 'VALIDE':
            for lien in liens:
                for n, montant in _repartition_lien_remise(lien, echeancier).items():
                    bucket = f'tranche_{n}'
                    remises_validees[bucket] = min(dues[bucket], remises_validees[bucket] + montant)
            valides.append(paiement)
            net = {bucket: max(ZERO, dues[bucket] - remises_validees[bucket]) for bucket in ALL_BUCKETS}
            _, payes, _ = replay_payment_allocations(valides, net)
            couverture = {bucket: min(dues[bucket], payes[bucket] + remises_validees[bucket])
                          for bucket in ALL_BUCKETS}
