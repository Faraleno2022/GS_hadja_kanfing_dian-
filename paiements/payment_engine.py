"""Moteur comptable unique des paiements scolaires.

Les encaissements et les remises sont calculés par année et par poste. Une
couverture de T2/T3 ne peut donc jamais solder l'inscription, la réinscription
ou une tranche antérieure.
"""

import logging
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


logger = logging.getLogger(__name__)

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


# Les inscriptions et réinscriptions d'une année scolaire s'encaissent dès
# juillet, avant la rentrée de septembre. Rattacher ces versements à l'année qui
# s'achève les rendait invisibles : la liste des paiements est filtrée sur
# l'année active (celle des classes) et le moteur n'apparie que les paiements
# portant l'année de l'échéancier.
MOIS_DEBUT_INSCRIPTIONS = 7


def school_year_from_date(value):
    """Retourne l'année scolaire d'une date, période d'inscription comprise."""
    value = value or date.today()
    debut = (
        value.year if value.month >= MOIS_DEBUT_INSCRIPTIONS else value.year - 1
    )
    return f'{debut}-{debut + 1}'


def school_year_bounds(annee_scolaire):
    """Bornes inclusives utilisées pour les anciens paiements sans année.

    La fenêtre s'ouvre en juillet, avec les réinscriptions, et se ferme fin
    août, après les derniers règlements de la 3ème tranche. Deux années
    consécutives se recouvrent donc sur juillet-août : sans conséquence, un
    élève n'ayant qu'un seul échéancier.
    """
    try:
        debut = int(str(annee_scolaire).split('-', 1)[0])
    except (TypeError, ValueError):
        return None, None
    return date(debut, MOIS_DEBUT_INSCRIPTIONS, 1), date(debut + 1, 8, 31)


def annee_scolaire_coherente(annee_actuelle, date_paiement):
    """Année à conserver après correction de la date d'un paiement.

    L'année comptable est figée à l'enregistrement, à partir de la classe de
    l'élève. La recalculer à partir de la seule date déplaçait un versement de
    juillet ou d'août vers l'année précédente : le paiement disparaissait alors
    de la liste et ne comptait plus dans aucun solde. On ne la recalcule donc
    que si la date corrigée sort de la période de l'année figée.
    """
    debut, fin = school_year_bounds(annee_actuelle)
    if debut and fin and date_paiement and debut <= date_paiement <= fin:
        return annee_actuelle
    return school_year_from_date(date_paiement)


def realigner_annees_paiements(Paiement, EcheancierPaiement):
    """Recolle les paiements d'été sur l'année scolaire de leur échéancier.

    Les versements de juillet et août ont été étiquetés « année précédente »
    (ancienne règle de la date, coupure en septembre) alors que la classe et
    l'échéancier de l'élève portent déjà l'année qui commence : ces paiements
    n'apparaissaient plus dans la liste et n'entraient dans aucun solde ni
    reçu. Seuls ces versements-là sont réétiquetés ; aucune autre année n'est
    touchée. Retourne le nombre de paiements corrigés.
    """
    annees_attendues = dict(
        EcheancierPaiement.objects.values_list('eleve_id', 'annee_scolaire')
    )
    corriges = 0
    for paiement in Paiement.objects.exclude(annee_scolaire='').iterator():
        attendue = annees_attendues.get(paiement.eleve_id)
        date_paiement = paiement.date_paiement
        if not attendue or not date_paiement:
            continue
        if paiement.annee_scolaire == attendue:
            continue
        # Fenêtre des (ré)inscriptions uniquement : juillet et août.
        if not MOIS_DEBUT_INSCRIPTIONS <= date_paiement.month <= 8:
            continue
        if school_year_from_date(date_paiement) != attendue:
            continue
        paiement.annee_scolaire = attendue
        paiement.save(update_fields=['annee_scolaire'])
        corriges += 1
    return corriges


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
    # Une remise déduite du reçu a amputé son montant. Recalculer la remise sans
    # re-dériver le reçu laisserait un net incohérent avec la remise accordée.
    deja_deduit = sum(
        (_decimal(lien.montant_remise) for lien in liens if lien.deduite_du_paiement),
        ZERO,
    )
    paiement._montant_brut_fige = _decimal(paiement.montant) + deja_deduit

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

    brut = paiement._montant_brut_fige
    del paiement._montant_brut_fige

    nouveau_deduit = sum(
        (_decimal(lien.montant_remise) for lien in liens if lien.deduite_du_paiement),
        ZERO,
    )
    if deja_deduit != nouveau_deduit:
        paiement.montant = max(ZERO, brut - nouveau_deduit)
        paiement.save()
    return liens


def paiements_valides_echeancier(echeancier, date_limite=None):
    """Paiements validés appartenant exclusivement à l'année de l'échéancier."""
    from .models import Paiement

    qs = Paiement.objects.select_related('type_paiement').prefetch_related('remises').filter(
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


def montant_affectable_sans_report_remise(paiement):
    """Montant à montrer dans les colonnes de tranches et sur le reçu.

    Une remise non déduite laisse le reçu au brut. La rejouer telle quelle sur
    les dus nets faisait glisser exactement son montant sur la tranche
    suivante. Pour l'affichage seulement, on retire donc ces remises du montant
    ventilé. Une remise déjà déduite ne l'est pas une seconde fois.
    """
    montant = max(ZERO, _decimal(getattr(paiement, 'montant', 0)))
    try:
        liens = list(paiement.remises.all())
    except Exception:
        return montant
    non_deduites = sum(
        (
            max(ZERO, _decimal(lien.montant_remise))
            for lien in liens
            if not getattr(lien, 'deduite_du_paiement', False)
        ),
        ZERO,
    )
    return max(ZERO, montant - non_deduites)


def paiements_annee_incoherente(echeancier, date_limite=None):
    """Paiements validés tombant dans l'année de l'échéancier mais étiquetés autrement.

    Sert de garde-fou : si l'échéancier porte « 2025-2027 » alors que les
    paiements portent « 2025-2026 », l'appariement par année ne retient rien et
    le solde affiché redevient le dû intégral. Plutôt que de laisser passer ce
    zéro silencieux, on remonte les paiements concernés pour pouvoir alerter.
    """
    from .models import Paiement

    debut, fin = school_year_bounds(echeancier.annee_scolaire)
    if not debut or not fin:
        return []
    qs = Paiement.objects.filter(
        eleve_id=echeancier.eleve_id,
        statut='VALIDE',
        date_paiement__range=(debut, fin),
    ).exclude(annee_scolaire__in=('', echeancier.annee_scolaire))
    if date_limite is not None:
        qs = qs.filter(date_paiement__lte=date_limite)
    return list(qs.order_by('date_paiement', 'id'))


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
    ecartes = (
        paiements_annee_incoherente(echeancier, date_limite=date_limite)
        if not paiements
        else []
    )
    if paiements:
        allocations, payes, non_alloues = replay_payment_allocations(
            paiements, dues_apres_remises
        )
        montants_affichables = {
            paiement.pk: montant_affectable_sans_report_remise(paiement)
            for paiement in paiements
        }
        allocations_affichees, payes_affiches, _non_alloues_affiches = (
            replay_payment_allocations(
                paiements,
                dues_apres_remises,
                amounts_by_payment=montants_affichables,
            )
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
        allocations_affichees = {}
        payes_affiches = dict(payes)
    else:
        allocations = {}
        payes = {bucket: ZERO for bucket in dues}
        non_alloues = {}
        allocations_affichees = {}
        payes_affiches = dict(payes)
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
    if ecartes:
        logger.warning(
            "Échéancier %s (élève %s) en année %r : %d paiement(s) validé(s) de "
            "la même période sont écartés car étiquetés %s. Le solde affiché "
            "ignore ces encaissements — corriger l'année scolaire.",
            echeancier.pk,
            echeancier.eleve_id,
            echeancier.annee_scolaire,
            len(ecartes),
            sorted({p.annee_scolaire for p in ecartes}),
        )
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
        # Ventilation réservée aux reçus et rapports. Elle empêche une remise
        # non déduite d'apparaître comme paiement de la tranche suivante.
        'payes_affiches': payes_affiches,
        'allocations_affichees': allocations_affichees,
        # Non vide = le solde ci-dessus est faux : des paiements de la période
        # sont écartés par une incohérence d'année scolaire.
        'paiements_ecartes_annee': ecartes,
    }


@transaction.atomic
def recalculer_echeancier(eleve_ou_echeancier, date_reference=None):
    """Rejoue l'année courante et synchronise champs payés + statut."""
    from .models import EcheancierPaiement

    if isinstance(eleve_ou_echeancier, EcheancierPaiement):
        echeancier_id = eleve_ou_echeancier.pk
    else:
        echeancier = getattr(eleve_ou_echeancier, 'echeancier', None)
        echeancier_id = getattr(echeancier, 'pk', None)
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
