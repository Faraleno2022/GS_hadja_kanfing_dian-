"""Moteur comptable unique des paiements scolaires.

Les encaissements et les remises sont calculés par année et par poste. Une
couverture de T2/T3 ne peut donc jamais solder l'inscription, la réinscription
ou une tranche antérieure.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .allocation import (
    INSCRIPTION,
    TRANCHE_1,
    TRANCHE_2,
    TRANCHE_3,
    echeancier_dues,
    replay_payment_allocations,
)


ZERO = Decimal('0')
TRANCHE_BUCKETS = {1: TRANCHE_1, 2: TRANCHE_2, 3: TRANCHE_3}
PAID_FIELDS = {
    INSCRIPTION: 'frais_inscription_paye',
    TRANCHE_1: 'tranche_1_payee',
    TRANCHE_2: 'tranche_2_payee',
    TRANCHE_3: 'tranche_3_payee',
}
DEADLINE_FIELDS = {
    INSCRIPTION: 'date_echeance_inscription',
    TRANCHE_1: 'date_echeance_tranche_1',
    TRANCHE_2: 'date_echeance_tranche_2',
    TRANCHE_3: 'date_echeance_tranche_3',
}
REMISE_FIELDS = {
    1: 'montant_tranche_1',
    2: 'montant_tranche_2',
    3: 'montant_tranche_3',
}


def _decimal(value):
    return Decimal(str(value or 0))


def school_year_from_date(value):
    """Retourne l'année scolaire septembre-août d'une date."""
    value = value or date.today()
    debut = value.year if value.month >= 9 else value.year - 1
    return f'{debut}-{debut + 1}'


def school_year_bounds(annee_scolaire):
    """Bornes inclusives utilisées pour les anciens paiements sans année."""
    try:
        debut = int(str(annee_scolaire).split('-', 1)[0])
    except (TypeError, ValueError):
        return None, None
    return date(debut, 9, 1), date(debut + 1, 8, 31)


def repartir_montant_sur_tranches(montant, bases, numeros):
    """Répartit exactement un montant entre les tranches, au prorata des bases."""
    numeros_valides = set()
    for valeur in numeros or []:
        try:
            numero = int(valeur)
        except (TypeError, ValueError):
            continue
        if numero in (1, 2, 3):
            numeros_valides.add(numero)
    numeros = sorted(numeros_valides)
    resultat = {1: ZERO, 2: ZERO, 3: ZERO}
    capacites = {numero: max(ZERO, _decimal(bases.get(numero, 0))) for numero in numeros}
    total_base = sum(capacites.values(), ZERO)
    total = min(max(ZERO, _decimal(montant)), total_base)
    if total <= 0 or total_base <= 0:
        return resultat

    restant = total
    for index, numero in enumerate(numeros):
        if restant <= 0:
            break
        if index == len(numeros) - 1:
            part = min(restant, capacites[numero])
        else:
            part = (total * capacites[numero] / total_base).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )
            part = min(restant, capacites[numero], max(ZERO, part))
        resultat[numero] += part
        restant -= part

    # Les arrondis ou une capacité atteinte peuvent laisser quelques GNF.
    for numero in numeros:
        if restant <= 0:
            break
        disponible = max(ZERO, capacites[numero] - resultat[numero])
        ajout = min(restant, disponible)
        resultat[numero] += ajout
        restant -= ajout
    return resultat


def preparer_ventilation_remises(paiement, remises, tranches, base_calcul):
    """Calcule une pile de remises sans jamais dépasser les postes visés.

    Le résultat contient, pour chaque remise, sa base nominale, son montant
    effectivement accordé et sa ventilation persistable sur T1/T2/T3.
    """
    from .remise_utils import bases_par_tranche, normaliser_tranches

    numeros = normaliser_tranches(tranches)
    bases = {
        numero: max(ZERO, _decimal(montant))
        for numero, montant in bases_par_tranche(paiement, base_calcul).items()
        if numero in numeros
    }
    base_totale = sum(bases.values(), ZERO)
    capacites = dict(bases)
    resultat = []
    for remise in remises:
        nominal = max(ZERO, _decimal(remise.calculer_remise(base_totale)))
        montant = min(nominal, sum(capacites.values(), ZERO))
        ventilation = repartir_montant_sur_tranches(montant, capacites, numeros)
        montant_effectif = sum(ventilation.values(), ZERO)
        for numero in numeros:
            capacites[numero] = max(
                ZERO, capacites.get(numero, ZERO) - ventilation[numero]
            )
        resultat.append({
            'remise': remise,
            'montant_base': base_totale,
            'montant_nominal': nominal,
            'montant_remise': montant_effectif,
            'ventilation': ventilation,
        })
    return resultat


@transaction.atomic
def recalculer_remises_paiement(paiement):
    """Réajuste les remises après la correction d'un paiement.

    Cette fonction conserve les choix et motifs, mais recalcule les bases et la
    ventilation. Elle empêche aussi un ancien cumul de remises de dépasser le
    montant des tranches concernées.
    """
    from .models import PaiementRemise
    from .remise_utils import bases_par_tranche, normaliser_tranches

    liens = list(
        PaiementRemise.objects.select_for_update()
        .select_related('remise')
        .filter(paiement=paiement)
        .order_by('id')
    )
    capacites_globales = None
    for lien in liens:
        numeros = normaliser_tranches(lien.tranches_appliquees)
        bases_mode = bases_par_tranche(paiement, lien.base_calcul)
        dues = bases_par_tranche(paiement, 'TRANCHE')
        if capacites_globales is None:
            capacites_globales = {
                numero: max(ZERO, _decimal(dues.get(numero, 0)))
                for numero in (1, 2, 3)
            }
        capacites = {
            numero: min(
                capacites_globales.get(numero, ZERO),
                max(ZERO, _decimal(bases_mode.get(numero, 0))),
            )
            for numero in numeros
        }
        base_totale = sum(
            (max(ZERO, _decimal(bases_mode.get(numero, 0))) for numero in numeros),
            ZERO,
        )
        nominal = lien.remise.calculer_remise(base_totale)
        ventilation = repartir_montant_sur_tranches(
            min(nominal, sum(capacites.values(), ZERO)), capacites, numeros
        )
        for numero in numeros:
            capacites_globales[numero] -= ventilation[numero]
        lien.montant_base = base_totale
        lien.montant_remise = sum(ventilation.values(), ZERO)
        lien.montant_tranche_1 = ventilation[1]
        lien.montant_tranche_2 = ventilation[2]
        lien.montant_tranche_3 = ventilation[3]
        lien.save(update_fields=[
            'montant_base', 'montant_remise', 'montant_tranche_1',
            'montant_tranche_2', 'montant_tranche_3',
        ])
    return liens


def paiements_valides_echeancier(echeancier, date_limite=None):
    """Paiements validés appartenant exclusivement à l'année de l'échéancier."""
    from .models import Paiement

    qs = Paiement.objects.select_related('type_paiement').filter(
        eleve_id=echeancier.eleve_id,
        statut='VALIDE',
    )
    debut, fin = school_year_bounds(echeancier.annee_scolaire)
    legacy = Q(annee_scolaire='')
    if debut and fin:
        legacy &= Q(date_paiement__range=(debut, fin))
    qs = qs.filter(Q(annee_scolaire=echeancier.annee_scolaire) | legacy)
    if date_limite is not None:
        qs = qs.filter(date_paiement__lte=date_limite)
    return qs.order_by('date_validation', 'id')


def _repartition_lien_remise(lien, echeancier):
    """Ventilation persistée d'une remise, avec repli pour les anciennes lignes."""
    total = max(ZERO, _decimal(lien.montant_remise))
    stockee = {
        numero: max(ZERO, _decimal(getattr(lien, field, 0)))
        for numero, field in REMISE_FIELDS.items()
    }
    numeros = list(getattr(lien, 'tranches_appliquees', []) or [])
    if not numeros:
        # Compatibilité des lignes créées avant l'ajout des cases T1/T2/T3 :
        # leur ancienne portée "scolarité" signifie les trois tranches,
        # jamais l'inscription/réinscription.
        numeros = [1, 2, 3]

    total_stocke = sum(stockee.values(), ZERO)
    if total_stocke == total and total_stocke > 0:
        return stockee

    # Compatibilité avec les remises créées avant la ventilation détaillée.
    if total_stocke > 0:
        bases = stockee
    else:
        dues = echeancier_dues(echeancier)
        bases = {numero: dues[TRANCHE_BUCKETS[numero]] for numero in numeros}
    return repartir_montant_sur_tranches(total, bases, numeros)


def remises_par_tranche(echeancier, date_limite=None):
    """Total des remises validées par tranche, filtré par année scolaire."""
    from .models import PaiementRemise

    liens = PaiementRemise.objects.select_related('paiement').filter(
        paiement__eleve_id=echeancier.eleve_id,
        paiement__statut='VALIDE',
    )
    debut, fin = school_year_bounds(echeancier.annee_scolaire)
    legacy = Q(paiement__annee_scolaire='')
    if debut and fin:
        legacy &= Q(paiement__date_paiement__range=(debut, fin))
    liens = liens.filter(
        Q(paiement__annee_scolaire=echeancier.annee_scolaire) | legacy
    )
    if date_limite is not None:
        liens = liens.filter(paiement__date_paiement__lte=date_limite)

    totaux = {1: ZERO, 2: ZERO, 3: ZERO}
    for lien in liens:
        repartition = _repartition_lien_remise(lien, echeancier)
        for numero in totaux:
            totaux[numero] += repartition[numero]

    # Plusieurs remises ne peuvent jamais annuler plus que le dû du poste.
    dues = echeancier_dues(echeancier)
    for numero, bucket in TRANCHE_BUCKETS.items():
        totaux[numero] = min(totaux[numero], dues[bucket])
    return totaux


def situation_echeancier(
    echeancier, date_reference=None, *, utiliser_cumuls_legacy=True
):
    """Calcule encaissements, remises, restes et retards poste par poste."""
    reference = date_reference or timezone.localdate()
    date_limite = reference
    remises_numeros = remises_par_tranche(echeancier, date_limite=date_limite)
    remises = {
        INSCRIPTION: ZERO,
        TRANCHE_1: remises_numeros[1],
        TRANCHE_2: remises_numeros[2],
        TRANCHE_3: remises_numeros[3],
    }
    dues = echeancier_dues(echeancier)
    # Les encaissements se placent sur ce qui reste après remise. Cela évite
    # qu'un paiement et une remise se chevauchent sur T1 alors qu'une T2 reste
    # à payer.
    dues_apres_remises = {
        bucket: max(ZERO, dues[bucket] - remises[bucket])
        for bucket in dues
    }
    paiements = list(paiements_valides_echeancier(echeancier, date_limite=date_limite))
    if paiements:
        allocations, payes, non_alloues = replay_payment_allocations(
            paiements, dues_apres_remises
        )
    elif utiliser_cumuls_legacy:
        # Compatibilité avec les anciens dossiers importés qui ne possèdent
        # pas le journal de paiements mais dont les cumuls *_paye sont renseignés.
        # Dès qu'un journal existe pour l'année, celui-ci redevient l'unique
        # source afin d'éviter toute contamination interannuelle.
        payes_stockes = {
            bucket: max(ZERO, _decimal(getattr(echeancier, field, 0)))
            for bucket, field in PAID_FIELDS.items()
        }
        payes = {
            bucket: min(dues_apres_remises[bucket], payes_stockes[bucket])
            for bucket in dues
        }
        allocations = {}
        non_alloues = {}
    else:
        allocations = {}
        payes = {bucket: ZERO for bucket in dues}
        non_alloues = {}
    couverts = {}
    restes = {}
    retards = {}
    exigibles = {}
    for bucket, du in dues.items():
        couverts[bucket] = min(du, payes[bucket] + remises[bucket])
        restes[bucket] = max(ZERO, du - couverts[bucket])
        echeance = getattr(echeancier, DEADLINE_FIELDS[bucket], None)
        est_exigible = bool(echeance and echeance < reference)
        exigibles[bucket] = du if est_exigible else ZERO
        retards[bucket] = restes[bucket] if est_exigible else ZERO

    total_du = sum(dues.values(), ZERO)
    total_encaisse = sum(payes.values(), ZERO)
    total_remises = sum(remises.values(), ZERO)
    total_couvert = sum(couverts.values(), ZERO)
    return {
        'dues': dues,
        'payes': payes,
        'remises': remises,
        'couverts': couverts,
        'restes': restes,
        'exigibles': exigibles,
        'retards': retards,
        'total_du': total_du,
        'total_encaisse': total_encaisse,
        'total_remises': total_remises,
        'total_couvert': total_couvert,
        'solde_restant': max(ZERO, total_du - total_couvert),
        'montant_exigible': sum(exigibles.values(), ZERO),
        'retard_total': sum(retards.values(), ZERO),
        'non_alloue': sum(non_alloues.values(), ZERO),
        'allocations': allocations,
    }


@transaction.atomic
def recalculer_echeancier(eleve_ou_echeancier, date_reference=None):
    """Rejoue l'année courante et synchronise champs payés + statut."""
    from .models import EcheancierPaiement

    if isinstance(eleve_ou_echeancier, EcheancierPaiement):
        echeancier_id = eleve_ou_echeancier.pk
    else:
        echeancier_id = EcheancierPaiement.objects.filter(
            eleve=eleve_ou_echeancier
        ).values_list('pk', flat=True).first()
    if not echeancier_id:
        return None

    echeancier = EcheancierPaiement.objects.select_for_update().get(pk=echeancier_id)
    situation = situation_echeancier(
        echeancier,
        date_reference=date_reference,
        utiliser_cumuls_legacy=False,
    )
    changed = []
    for bucket, field in PAID_FIELDS.items():
        if _decimal(getattr(echeancier, field)) != situation['payes'][bucket]:
            setattr(echeancier, field, situation['payes'][bucket])
            changed.append(field)

    if situation['total_du'] <= 0 or situation['solde_restant'] <= 0:
        statut = 'PAYE_COMPLET'
    elif situation['retard_total'] > 0:
        statut = 'EN_RETARD'
    elif situation['total_couvert'] <= 0:
        statut = 'A_PAYER'
    else:
        statut = 'PAYE_PARTIEL'
    if echeancier.statut != statut:
        echeancier.statut = statut
        changed.append('statut')
    if changed:
        echeancier.save(update_fields=changed + ['date_modification'])
    return echeancier
