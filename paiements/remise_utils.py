"""Règles de portée et de calcul des remises de scolarité.

Une remise porte toujours sur une ou plusieurs tranches (1, 2, 3) et jamais sur
les frais d'inscription ou de réinscription. Deux bases de calcul sont
possibles :

- ``TRANCHE``  : le montant dû des tranches sélectionnées ;
- ``ECHEANCE`` : la part du paiement en cours effectivement affectée à ces
  mêmes tranches (le reliquat d'inscription est donc exclu).
"""

from decimal import Decimal

from .allocation import (
    INSCRIPTION,
    TRANCHE_1,
    TRANCHE_2,
    TRANCHE_3,
    allocate_amount,
    allocation_order_for_type,
    echeancier_dues,
    echeancier_paid,
)

BASE_TRANCHE = 'TRANCHE'
BASE_ECHEANCE = 'ECHEANCE'

BASE_CALCUL_CHOICES = [
    (BASE_TRANCHE, "Montant des tranches sélectionnées"),
    (BASE_ECHEANCE, "Paiement à l'échéance (part scolarité du reçu)"),
]

TRANCHE_CHOICES = [
    ('1', "1ère tranche"),
    ('2', "2ème tranche"),
    ('3', "3ème tranche"),
]

TRANCHE_NUMEROS = (1, 2, 3)

_BUCKET_PAR_NUMERO = {
    1: TRANCHE_1,
    2: TRANCHE_2,
    3: TRANCHE_3,
}


def _decimal(value):
    return Decimal(str(value or 0))


def normaliser_tranches(tranches):
    """Retourne une liste triée de numéros de tranches valides (1, 2, 3)."""
    numeros = set()
    for valeur in tranches or []:
        try:
            numero = int(valeur)
        except (TypeError, ValueError):
            continue
        if numero in TRANCHE_NUMEROS:
            numeros.add(numero)
    return sorted(numeros)


def montants_tranches_dues(eleve):
    """Montants dus par tranche, depuis l'échéancier ou la grille tarifaire."""
    montants = {numero: Decimal('0') for numero in TRANCHE_NUMEROS}

    echeancier = getattr(eleve, 'echeancier', None)
    if echeancier is not None:
        montants[1] = _decimal(echeancier.tranche_1_due)
        montants[2] = _decimal(echeancier.tranche_2_due)
        montants[3] = _decimal(echeancier.tranche_3_due)

    if any(montant > 0 for montant in montants.values()):
        return montants

    # Repli sur la grille tarifaire de la classe quand l'échéancier est vide
    try:
        from eleves.models import GrilleTarifaire

        classe = getattr(eleve, 'classe', None)
        ecole = getattr(classe, 'ecole', None)
        niveau = getattr(classe, 'niveau', None)
        annee = getattr(classe, 'annee_scolaire', None)
        grille = None
        if ecole and niveau and annee:
            grille = GrilleTarifaire.objects.filter(
                ecole=ecole, niveau=niveau, annee_scolaire=annee
            ).first()
        if not grille and ecole and niveau:
            grille = GrilleTarifaire.objects.filter(
                ecole=ecole, niveau=niveau
            ).order_by('-annee_scolaire').first()
        if grille:
            montants[1] = _decimal(grille.tranche_1)
            montants[2] = _decimal(grille.tranche_2)
            montants[3] = _decimal(grille.tranche_3)
    except Exception:
        pass

    return montants


def montants_tranches_paiement(paiement):
    """Part du paiement affectée à chaque tranche (hors inscription).

    Le paiement n'étant pas encore validé, on rejoue sa ventilation sur
    l'échéancier tel qu'il est aujourd'hui. Sans échéancier, on considère que
    la totalité du reçu porte sur la première tranche visée par son type.
    """
    montants = {numero: Decimal('0') for numero in TRANCHE_NUMEROS}
    montant_paiement = _decimal(getattr(paiement, 'montant', 0))
    if montant_paiement <= 0:
        return montants

    echeancier = getattr(getattr(paiement, 'eleve', None), 'echeancier', None)
    type_nom = getattr(getattr(paiement, 'type_paiement', None), 'nom', '')

    if echeancier is None:
        # Sans échéancier, une saisie d'inscription/réinscription est ambiguë :
        # aucune remise n'est autorisée, car on ne peut pas isoler de façon sûre
        # la part de scolarité. Pour une tranche explicite, respecter son numéro.
        ordre = allocation_order_for_type(type_nom)
        if INSCRIPTION in ordre:
            return montants
        bucket_vers_numero = {TRANCHE_1: 1, TRANCHE_2: 2, TRANCHE_3: 3}
        premier_bucket = next((bucket for bucket in ordre if bucket in bucket_vers_numero), None)
        if premier_bucket:
            montants[bucket_vers_numero[premier_bucket]] = montant_paiement
        return montants

    # Les remises déjà validées sont une couverture du poste au même
    # titre qu'un encaissement pour déterminer où tombe le paiement courant.
    try:
        from .payment_engine import situation_echeancier
        situation = situation_echeancier(echeancier)
        couverture_depart = situation['couverts']
    except Exception:
        couverture_depart = echeancier_paid(echeancier)

    allocation, _paid, _reliquat = allocate_amount(
        montant_paiement,
        echeancier_dues(echeancier),
        couverture_depart,
        type_nom,
    )
    for numero, bucket in _BUCKET_PAR_NUMERO.items():
        montants[numero] = _decimal(allocation.get(bucket, 0))
    return montants


def bases_par_tranche(paiement, base_calcul):
    """Montants de base par tranche pour la base de calcul demandée."""
    if base_calcul == BASE_ECHEANCE:
        return montants_tranches_paiement(paiement)
    return montants_tranches_dues(getattr(paiement, 'eleve', None))


def calculer_base_remise(paiement, tranches, base_calcul):
    """Base de calcul retenue = somme des tranches sélectionnées."""
    numeros = normaliser_tranches(tranches)
    if not numeros:
        return Decimal('0')
    montants = bases_par_tranche(paiement, base_calcul)
    return sum((montants.get(numero, Decimal('0')) for numero in numeros), Decimal('0'))
