"""Règles communes d'affectation des paiements sur un échéancier."""

from decimal import Decimal
import re
import unicodedata

from .models import Paiement


ALLOCATION_COMPONENTS = (
    ("inscription", "frais_inscription_du", "frais_inscription_paye"),
    ("tranche_1", "tranche_1_due", "tranche_1_payee"),
    ("tranche_2", "tranche_2_due", "tranche_2_payee"),
    ("tranche_3", "tranche_3_due", "tranche_3_payee"),
)


def _decimal(value):
    return Decimal(str(value or 0))


def normalize_payment_type(value):
    """Normalise un libellé pour reconnaître inscription/réinscription."""
    if not isinstance(value, str):
        value = getattr(value, "nom", "") or ""
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in normalized if not unicodedata.combining(char))


def registration_kind_for_type(value):
    """Retourne le tarif d'inscription explicitement demandé par le type."""
    normalized = normalize_payment_type(value)
    if "reinscription" in normalized:
        return "reinscription"
    if "inscription" in normalized:
        return "inscription"
    return None


# Un type qui vise « ce qu'il reste » couvre tous les postes de l'échéancier.
MOTIFS_SOLDE = (
    r"\bsolde\b", r"\bsolder\b", r"\breliquat\b", r"\bcomplement\b",
    r"\breste\s*a\s*payer\b", r"\btotalite\b", r"\bintegralite\b",
    r"\bintegral(?:e|ement)?\b", r"\bpaiement\s+total\b", r"\btout\s+le\s+reste\b",
)

# « 1ère », « 1re », « 1er », « premiere », « t1 »… ramenés au seul numéro.
ORDINAUX = {
    "premiere": 1, "premier": 1, "1ere": 1, "1er": 1, "1re": 1, "1e": 1,
    "deuxieme": 2, "seconde": 2, "second": 2, "2eme": 2, "2e": 2, "2nd": 2,
    "troisieme": 3, "3eme": 3, "3e": 3,
}

# Nombres écrits en toutes lettres. Ils ne sont convertis qu'accolés à un mot
# d'échéance : « un » est trop courant pour être traduit partout.
NOMBRES_LETTRES = {"un": 1, "une": 1, "deux": 2, "trois": 3}

# « Tranche » est le terme officiel ; les écoles saisissent aussi « trimestre »,
# « versement » ou « échéance » dans les types qu'elles créent elles-mêmes.
TERME_TRANCHE = r"(?:tranches?|trimestres?|versements?|echeances?)"

# Le libellé peut retirer un poste au lieu de l'ajouter : « Scolarité sans
# inscription », « Solde hors frais d'inscription », « Annuel sauf tranche 3 ».
TERME_EXCLUSION = r"\b(?:sans|hors|sauf|excepte[e]?s?|hormis)\b"

# Un poste d'admission : inscription, réinscription ou frais d'admission.
TERME_ADMISSION = r"\b(?:re)?inscriptions?\b|\badmissions?\b"

# « + », « , », « et », « plus »… séparent les postes d'un libellé combiné.
SEPARATEURS = r"[+,;/&]|\bet\b|\bplus\b"


def _developper_plages(texte):
    """Remplace « 1 à 3 » ou « T1-T3 » par la liste des tranches couvertes."""
    motif = re.compile(
        r"\b(?:t\s*)?([123])\s*(?:-|a|au|jusqu\s*'?\s*a(?:u)?)\s*(?:t\s*)?([123])\b"
    )

    def remplacer(correspondance):
        debut, fin = int(correspondance.group(1)), int(correspondance.group(2))
        if debut >= fin:
            return correspondance.group(0)
        return " ".join(f"t{numero}" for numero in range(debut, fin + 1))

    return motif.sub(remplacer, texte)


def _preparer_texte(normalized):
    """Ramène toutes les écritures d'un numéro de tranche à « t<n> »."""
    texte = normalized
    for mot, numero in ORDINAUX.items():
        texte = re.sub(rf"\b{mot}\b", str(numero), texte)
    for mot, numero in NOMBRES_LETTRES.items():
        texte = re.sub(rf"\b({TERME_TRANCHE})\s+{mot}\b", rf"\1 {numero}", texte)
        texte = re.sub(rf"\b{mot}\s+({TERME_TRANCHE})\b", rf"{numero} \1", texte)
    return _developper_plages(texte)


def _couper_exclusion(segment):
    """Sépare un segment en (postes demandés, postes explicitement retirés)."""
    coupure = re.search(TERME_EXCLUSION, segment)
    if not coupure:
        return segment, ""
    return segment[:coupure.start()], segment[coupure.end():]


def _lire_postes(texte, mentionne_tranche):
    """Retourne les tranches et l'admission portées par un fragment de libellé."""
    tranches = {int(n) for n in re.findall(r"\bt\s*([123])\b", texte)}
    for segment in re.split(SEPARATEURS, texte):
        segment = segment.strip()
        if not segment:
            continue
        if re.search(rf"\b{TERME_TRANCHE}\b", segment):
            tranches |= {int(n) for n in re.findall(r"\b([123])\b", segment)}
        elif mentionne_tranche and re.fullmatch(r"[123]", segment):
            # « Tranches 1, 2 et 3 » : le mot n'est écrit qu'une fois.
            tranches.add(int(segment))
    return tranches, bool(re.search(TERME_ADMISSION, texte))


def payment_type_plan(value):
    """Décode un type de paiement en postes métier explicites.

    Les accents, la casse et les variantes usuelles sont acceptés :
    « 1ère tranche », « T1 », « tranche deux », « tranches 1 à 3 »,
    « 2ème trimestre », mais aussi les retraits (« Scolarité sans
    inscription »). Le plan retourné est partagé par la suggestion et la
    validation serveur afin d'éviter deux répartitions contradictoires.
    """
    normalized = normalize_payment_type(value)
    texte = _preparer_texte(normalized)
    mentionne_tranche = bool(re.search(rf"\b{TERME_TRANCHE}\b", texte))

    demandes, retraits = [], []
    for segment in re.split(SEPARATEURS, texte):
        demande, retrait = _couper_exclusion(segment)
        demandes.append(demande)
        retraits.append(retrait)
    texte_demande = " , ".join(demandes)
    texte_retrait = " , ".join(retraits)

    tranches, admission = _lire_postes(texte_demande, mentionne_tranche)
    tranches_retirees, admission_retiree = _lire_postes(texte_retrait, mentionne_tranche)

    registration_kind = registration_kind_for_type(texte_demande)
    is_annual = "annuel" in texte_demande
    is_tuition = "scolarite" in texte_demande
    # « Solde », « reliquat », « complément »… visent tout ce qui reste dû.
    is_solde = any(re.search(motif, texte_demande) for motif in MOTIFS_SOLDE)

    # « Solde tranche 2 » vise cette seule tranche : un poste nommé dans le
    # libellé prime toujours sur l'élargissement au reste de l'année.
    postes_explicites = bool(tranches) or admission
    couvre_tout = is_solde and not postes_explicites

    if is_annual or couvre_tout or (is_tuition and not tranches):
        tranches.update((1, 2, 3))
    if couvre_tout:
        admission = True

    tranches -= tranches_retirees

    return {
        "normalized": normalized,
        "registration_kind": registration_kind,
        "include_registration": (
            (admission or registration_kind is not None) and not admission_retiree
        ),
        "covers_balance": couvre_tout,
        "tranches": tuple(sorted(tranches)),
    }


def allocate_amount_sequentially(echeancier, amount, initial_paid=None):
    """Affecte un montant: inscription, T1, T2 puis T3.

    La fonction ne sauvegarde rien. Elle retourne l'affectation du montant,
    les nouveaux cumuls payés et l'éventuel reliquat au-delà du total dû.
    """
    remaining = max(Decimal("0"), _decimal(amount))
    paid = {
        key: _decimal((initial_paid or {}).get(key, getattr(echeancier, paid_field, 0)))
        for key, _due_field, paid_field in ALLOCATION_COMPONENTS
    }
    allocation = {key: Decimal("0") for key, _due, _paid in ALLOCATION_COMPONENTS}

    for key, due_field, _paid_field in ALLOCATION_COMPONENTS:
        if remaining <= 0:
            break
        due = _decimal(getattr(echeancier, due_field, 0))
        available = max(Decimal("0"), due - paid[key])
        applied = min(remaining, available)
        if applied > 0:
            allocation[key] = applied
            paid[key] += applied
            remaining -= applied

    return allocation, paid, remaining


def reste_par_tranche_avec_couverture(echeancier, couverture_totale):
    """Répartit une couverture totale (encaissements + remises) sur les postes.

    Utilise le même ordre en cascade (inscription -> T1 -> T2 -> T3) que
    l'allocation réelle des paiements, pour que le "reste" par tranche
    reste cohérent avec le solde global (qui, lui, déduit les remises).
    Sans cette répartition, une remise réduit le solde global sans jamais
    réduire aucune tranche, et l'écart affiché induit le caissier en erreur
    sur le montant réellement encore payable.

    Retourne un dict {key: reste} pour chaque poste de ALLOCATION_COMPONENTS.
    """
    zero_paid = {key: Decimal('0') for key, _due, _paid in ALLOCATION_COMPONENTS}
    _allocation, paid, _remaining = allocate_amount_sequentially(
        echeancier, couverture_totale, initial_paid=zero_paid
    )
    return {
        key: max(Decimal('0'), _decimal(getattr(echeancier, due_field, 0)) - paid[key])
        for key, due_field, _paid_field in ALLOCATION_COMPONENTS
    }


def get_payment_allocation(paiement, echeancier=None):
    """Reconstruit l'affectation exacte d'un paiement validé pour les reçus."""
    if echeancier is None:
        try:
            echeancier = paiement.eleve.echeancier
        except Exception:
            return None

    running_paid = {key: Decimal("0") for key, _due, _paid in ALLOCATION_COMPONENTS}
    target_allocation = None
    validated = (
        Paiement.objects
        .filter(
            eleve=paiement.eleve,
            annee_scolaire=paiement.annee_scolaire,
            statut="VALIDE",
        )
        .order_by("date_paiement", "date_creation", "pk")
    )

    for current in validated.iterator():
        allocation, running_paid, unapplied = allocate_amount_sequentially(
            echeancier,
            current.montant,
            initial_paid=running_paid,
        )
        allocation["non_affecte"] = unapplied
        if current.pk == paiement.pk:
            target_allocation = allocation

    return target_allocation


def allocate_discounts(echeancier, discounts, balances=None):
    """Ventile les remises validées sur les tranches réellement concernées.

    Les remises ne couvrent jamais l'inscription/réinscription. Les anciennes
    remises sans information de tranche sont appliquées à T1, T2 puis T3 afin
    de rester compatibles avec les données antérieures.
    """
    current_balances = dict(balances or {
        key: max(
            Decimal('0'),
            _decimal(getattr(echeancier, due_field, 0))
            - _decimal(getattr(echeancier, paid_field, 0)),
        )
        for key, due_field, paid_field in ALLOCATION_COMPONENTS
    })
    allocation = {
        key: Decimal('0') for key, _due, _paid in ALLOCATION_COMPONENTS
    }

    for discount in discounts:
        selected = [
            f"tranche_{number}"
            for number in getattr(discount, 'tranches_concernees_liste', [])
            if number in (1, 2, 3)
        ]
        if not selected:
            selected = ['tranche_1', 'tranche_2', 'tranche_3']

        amount = max(Decimal('0'), _decimal(getattr(discount, 'montant_remise', 0)))
        for key in selected:
            if amount <= 0:
                break
            available = max(Decimal('0'), _decimal(current_balances.get(key, 0)))
            take = min(amount, available)
            allocation[key] += take
            current_balances[key] = available - take
            amount -= take

    return allocation, current_balances
