"""Règles de calcul du moteur de paie.

Les enseignants au forfait sont payés au prorata de leur date d'embauche.
Les enseignants du secondaire sont payés soit sur les heures réellement
pointées, soit sur un total mensuel explicitement saisi. Les affectations
servent à ventiler ces heures par classe.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Count, Q, Sum

from .models import (
    AvanceSalaire,
    DetailHeuresClasse,
    Enseignant,
    EtatSalaire,
    CategoriePaie,
    ModeCalculHoraire,
    ParametrePaie,
    PeriodeSalaire,
    RemboursementAvance,
    categorie_paie,
)


HEURE = Decimal('0.01')
MONTANT = Decimal('0.01')
STATUTS_HEURES_PAYEES = ('PRESENT', 'RETARD', 'PERMISSION')
STATUTS_JOURS_PRESENCE = ('PRESENT', 'RETARD')


def arrondir_heures(valeur):
    return Decimal(valeur or 0).quantize(HEURE, rounding=ROUND_HALF_UP)


def arrondir_montant(valeur):
    return Decimal(valeur or 0).quantize(MONTANT, rounding=ROUND_HALF_UP)


def synthese_etats_salaire(etats):
    """Cumule tous les montants d'un état de salaire mensuel.

    La fonction accepte un QuerySet ou un gestionnaire lié de période. Elle
    fournit une source de vérité commune à l'écran, au CSV et au PDF afin que
    le total affiché soit toujours la somme exacte des salaires disponibles.
    """
    if hasattr(etats, 'all'):
        etats = etats.all()

    cumuls = etats.aggregate(
        total_salaire_base=Sum('salaire_base'),
        total_primes=Sum('primes'),
        total_deductions=Sum('deductions'),
        total_sanctions=Sum('imputation_sanctions'),
        total_avances=Sum('avances_deduites'),
        total_net=Sum('salaire_net'),
        total_heures=Sum('total_heures'),
    )
    synthese = {
        cle: arrondir_montant(valeur)
        for cle, valeur in cumuls.items()
    }
    # Les sanctions (jours chômés) font partie des retenues affichées.
    synthese['total_deductions'] += synthese['total_sanctions']
    synthese['total_etats'] = etats.count()
    synthese['total_brut'] = arrondir_montant(
        synthese['total_salaire_base'] + synthese['total_primes']
    )
    return synthese


def bornes_periode(periode):
    premier_jour = date(periode.annee, periode.mois, 1)
    dernier_jour = date(
        periode.annee,
        periode.mois,
        monthrange(periode.annee, periode.mois)[1],
    )
    return premier_jour, dernier_jour


def enseignants_eligibles(periode):
    """Enseignants actifs déjà embauchés à la fin de la période."""
    _, dernier_jour = bornes_periode(periode)
    return Enseignant.objects.filter(
        ecole=periode.ecole,
        statut='ACTIF',
        date_embauche__lte=dernier_jour,
    ).order_by('nom', 'prenoms')


def resume_pointage(enseignant, periode):
    """Retourne les heures et jours de présence du mois en une seule requête."""
    premier_jour, dernier_jour = bornes_periode(periode)
    resume = enseignant.presences.filter(
        date__range=(premier_jour, dernier_jour),
    ).aggregate(
        total_heures=Sum(
            'heures_travaillees',
            filter=Q(statut__in=STATUTS_HEURES_PAYEES),
        ),
        jours_presence=Count(
            'id', filter=Q(statut__in=STATUTS_JOURS_PRESENCE)
        ),
        jours_chomes=Count(
            'id', filter=Q(statut='ABSENT', justifie=False)
        ),
    )
    return {
        'total_heures': arrondir_heures(resume['total_heures']),
        'jours_presence': resume['jours_presence'] or 0,
        'jours_chomes': resume['jours_chomes'] or 0,
    }


def heures_emploi_du_temps(enseignant, periode):
    """Heures à prester du mois : Σ heures du jour × nombre de ce jour travaillé.

    Reprend la colonne « Heures à prester » de la feuille Etat Prof final.
    """
    return arrondir_heures(sum(
        (
            heures * occurrences
            for heures, occurrences in zip(
                enseignant.heures_par_jour_semaine,
                periode.occurrences_jours_semaine(),
            )
        ),
        Decimal('0'),
    ))


def heures_reellement_travaillees(enseignant, periode):
    return resume_pointage(enseignant, periode)['total_heures']


def heures_pour_calcul(enseignant, periode):
    """Retourne les heures selon le mode explicitement choisi."""
    if enseignant.mode_calcul_horaire == ModeCalculHoraire.MENSUEL:
        return arrondir_heures(enseignant.heures_mensuelles)
    if enseignant.mode_calcul_horaire == ModeCalculHoraire.HEBDOMADAIRE:
        return heures_emploi_du_temps(enseignant, periode)
    return heures_reellement_travaillees(enseignant, periode)


def affectations_de_la_periode(enseignant, periode):
    """Affectations dont les dates chevauchent la période de paie.

    Une affectation clôturée reste utilisable pour un calcul historique.
    Une affectation désactivée sans date de fin est ignorée.
    """
    premier_jour, dernier_jour = bornes_periode(periode)
    return (
        enseignant.affectations
        .filter(date_debut__lte=dernier_jour)
        .filter(Q(date_fin__isnull=True) | Q(date_fin__gte=premier_jour))
        .filter(Q(actif=True) | Q(date_fin__isnull=False))
        .select_related('classe')
        .order_by('classe__nom', 'id')
    )


def heures_prevues_par_affectation(enseignant, periode):
    premier_jour, dernier_jour = bornes_periode(periode)
    jours_periode = Decimal((dernier_jour - premier_jour).days + 1)
    lignes = []

    for affectation in affectations_de_la_periode(enseignant, periode):
        debut = max(premier_jour, affectation.date_debut)
        fin = min(dernier_jour, affectation.date_fin or dernier_jour)
        jours_couverts = Decimal((fin - debut).days + 1)
        prorata = jours_couverts / jours_periode
        heures_prevues = (
            (affectation.heures_par_semaine or Decimal('0'))
            * periode.nombre_semaines
            * prorata
        )
        lignes.append((affectation, heures_prevues))

    return lignes


def repartir_heures(total_heures, lignes_prevues):
    """Ventile le total réel proportionnellement aux heures prévues.

    Le reliquat d'arrondi est placé sur la dernière affectation afin que la
    somme des détails reste exactement égale au total de l'état de salaire.
    """
    total_heures = arrondir_heures(total_heures)
    total_prevu = sum((heures for _, heures in lignes_prevues), Decimal('0'))
    if not lignes_prevues or total_prevu <= 0:
        return []

    reste = total_heures
    repartition = []
    for index, (affectation, heures_prevues) in enumerate(lignes_prevues):
        if index == len(lignes_prevues) - 1:
            heures_realisees = reste
        else:
            heures_realisees = arrondir_heures(
                total_heures * heures_prevues / total_prevu
            )
            reste -= heures_realisees
        repartition.append(
            (affectation, arrondir_heures(heures_prevues), heures_realisees)
        )

    return repartition


def reconstruire_details_heures(etat):
    """Aligne la ventilation par classe sur le total courant du brouillon."""
    etat.details_heures.all().delete()
    if not etat.enseignant.est_taux_horaire:
        return

    lignes_prevues = heures_prevues_par_affectation(
        etat.enseignant, etat.periode
    )
    for affectation, heures_prevues, heures_realisees in repartir_heures(
        etat.total_heures or Decimal('0'), lignes_prevues
    ):
        DetailHeuresClasse.objects.create(
            etat_salaire=etat,
            affectation_classe=affectation,
            heures_prevues=heures_prevues,
            heures_realisees=heures_realisees,
            taux_horaire_applique=(
                etat.taux_horaire_applique or Decimal('0')
            ),
        )


def salaire_fixe_proratise(enseignant, periode):
    premier_jour, dernier_jour = bornes_periode(periode)
    if enseignant.date_embauche > dernier_jour:
        return Decimal('0.00')

    premier_jour_paye = max(premier_jour, enseignant.date_embauche)
    jours_payes = Decimal((dernier_jour - premier_jour_paye).days + 1)
    jours_periode = Decimal((dernier_jour - premier_jour).days + 1)
    return arrondir_montant(
        (enseignant.salaire_fixe or Decimal('0')) * jours_payes / jours_periode
    )


def effectif_classe_principale(enseignant):
    if not enseignant.utilise_classe_principale or not enseignant.classe_principale_id:
        return 0
    return enseignant.classe_principale.eleves.filter(statut='ACTIF').count()


def appliquer_sanctions(etat, parametre, jours_chomes=None):
    """Imputation liée aux sanctions : jours chômés × retenue par jour."""
    if jours_chomes is not None:
        etat.jours_chomes = jours_chomes
    etat.imputation_sanctions = arrondir_montant(
        Decimal(etat.jours_chomes or 0) * parametre.retenue_par_jour_chome
    )
    return etat


def appliquer_primes_bareme(etat, parametre=None):
    """Calcule les rubriques de primes selon les barèmes de l'école.

    Règles reprises de l'état de salaire Excel :
    - ancienneté : années depuis l'embauche × taux annuel ;
    - éloignement : km × taux par km ;
    - craie : effectif de la classe × taux par élève (garderie à primaire),
      ou heures de révision × taux horaire de révision (secondaire) ;
    - fonction : prime fixe du dossier (+ prime de professeur principal au secondaire) ;
    - performance et exceptionnelle : montants fixes du dossier ;
    - sanctions : jours chômés (absences non justifiées pointées) × retenue
      par jour chômé.

    Un état dont les primes ont été saisies à la main est laissé intact.
    """
    if etat.primes_ajustees:
        return etat

    enseignant = etat.enseignant
    if parametre is None:
        parametre = ParametrePaie.pour_ecole(etat.periode.ecole)
    appliquer_sanctions(
        etat, parametre, resume_pointage(enseignant, etat.periode)['jours_chomes']
    )

    prime_fonction = enseignant.prime_fonction or Decimal('0')
    if enseignant.est_taux_horaire:
        etat.effectif_classe = 0
        prime_craie = (etat.heures_revision or Decimal('0')) * parametre.prime_par_heure_revision
        if enseignant.professeur_principal:
            prime_fonction += parametre.prime_professeur_principal
    else:
        etat.effectif_classe = effectif_classe_principale(enseignant)
        prime_craie = Decimal(etat.effectif_classe) * parametre.prime_craie_par_eleve

    etat.prime_fonction = arrondir_montant(prime_fonction)
    etat.prime_craie = arrondir_montant(prime_craie)
    etat.prime_anciennete = arrondir_montant(
        Decimal(enseignant.anciennete_annees(etat.periode.annee))
        * parametre.taux_anciennete_par_an
    )
    etat.prime_eloignement = arrondir_montant(
        (enseignant.distance_km or Decimal('0')) * parametre.taux_eloignement_par_km
    )
    etat.prime_performance = arrondir_montant(enseignant.prime_performance)
    etat.prime_exceptionnelle = arrondir_montant(enseignant.prime_exceptionnelle)
    # Le total est recalculé par EtatSalaire.save() à partir des rubriques.
    etat.primes = Decimal('0')
    return etat


def _periode_est_anterieure_ou_egale(periode_source, periode_cible):
    return (periode_source.annee, periode_source.mois) <= (
        periode_cible.annee,
        periode_cible.mois,
    )


@transaction.atomic
def synchroniser_avances_etat(etat):
    """Rejoue les avances sur un brouillon de salaire, de la plus ancienne à la plus récente.

    Une avance supérieure au salaire disponible est partiellement récupérée et
    son reliquat reste disponible pour les périodes suivantes.
    """
    etat = (
        EtatSalaire.objects.select_for_update()
        .select_related('enseignant', 'periode')
        .get(pk=etat.pk)
    )
    if etat.valide or etat.paye or etat.periode.cloturee:
        return etat

    etat.remboursements_avances.all().delete()
    disponible = max(
        (etat.salaire_base or Decimal('0'))
        + (etat.primes or Decimal('0'))
        - (etat.deductions or Decimal('0'))
        - (etat.imputation_sanctions or Decimal('0')),
        Decimal('0'),
    )
    total_impute = Decimal('0')

    avances = (
        AvanceSalaire.objects.select_for_update()
        .filter(enseignant=etat.enseignant)
        .select_related('periode_prevue')
        .order_by(
            'periode_prevue__annee',
            'periode_prevue__mois',
            'date_avance',
            'id',
        )
    )
    for avance in avances:
        if disponible <= 0:
            break
        if not _periode_est_anterieure_ou_egale(avance.periode_prevue, etat.periode):
            continue

        deja_rembourse = avance.remboursements.exclude(
            etat_salaire=etat
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
        reste_avance = max(avance.montant - deja_rembourse, Decimal('0'))
        montant_impute = min(reste_avance, disponible)
        if montant_impute <= 0:
            continue

        RemboursementAvance.objects.create(
            avance=avance,
            etat_salaire=etat,
            montant=arrondir_montant(montant_impute),
        )
        total_impute += montant_impute
        disponible -= montant_impute

    etat.avances_deduites = arrondir_montant(total_impute)
    etat.save(update_fields=['avances_deduites', 'salaire_net'])
    return etat


@transaction.atomic
def synchroniser_avances_enseignant(enseignant):
    """Recalcule toutes les périodes encore modifiables d'un enseignant."""
    etats = list(
        EtatSalaire.objects.select_for_update()
        .filter(
            enseignant=enseignant,
            valide=False,
            paye=False,
            periode__cloturee=False,
        )
        .select_related('enseignant', 'periode')
        .order_by('periode__annee', 'periode__mois', 'id')
    )
    # Retirer d'abord toutes les imputations modifiables. Sans cela, une
    # retenue provisoire d'un mois futur pourrait réduire à tort le montant
    # disponible lors du recalcul d'un mois antérieur.
    if etats:
        RemboursementAvance.objects.filter(etat_salaire__in=etats).delete()
        for etat in etats:
            etat.avances_deduites = Decimal('0')
            etat.save(update_fields=['avances_deduites', 'salaire_net'])
    return [synchroniser_avances_etat(etat) for etat in etats]


@transaction.atomic
def calculer_etat_salaire(enseignant, periode, utilisateur):
    """Crée ou recalcule un état non validé et retourne ``(etat, modifie)``."""
    etat, _ = EtatSalaire.objects.select_for_update().get_or_create(
        enseignant=enseignant,
        periode=periode,
        defaults={
            'calcule_par': utilisateur,
            'salaire_base': Decimal('0'),
            'salaire_net': Decimal('0'),
        },
    )

    if etat.valide:
        return etat, False

    etat.details_heures.all().delete()
    # Le salaire brut doit pouvoir être recalculé même s'il devient inférieur
    # à une ancienne imputation. Les avances sont rejouées juste après.
    etat.remboursements_avances.all().delete()
    etat.avances_deduites = Decimal('0')
    pointage = resume_pointage(enseignant, periode)
    etat.jours_presence = pointage['jours_presence']
    appliquer_primes_bareme(etat)

    if enseignant.est_taux_horaire:
        etat.heures_a_prester = None
        if enseignant.mode_calcul_horaire == ModeCalculHoraire.MENSUEL:
            total_heures = arrondir_heures(enseignant.heures_mensuelles)
        elif enseignant.mode_calcul_horaire == ModeCalculHoraire.HEBDOMADAIRE:
            # Heures prestées = heures à prester - heures d'absence (saisies
            # sur l'état et conservées d'un recalcul à l'autre).
            etat.heures_a_prester = heures_emploi_du_temps(enseignant, periode)
            total_heures = max(
                etat.heures_a_prester - (etat.heures_absence or Decimal('0')),
                Decimal('0'),
            )
        else:
            total_heures = pointage['total_heures']
        taux_horaire = enseignant.taux_horaire or Decimal('0')
        etat.total_heures = total_heures
        etat.mode_calcul_heures = enseignant.mode_calcul_horaire
        etat.taux_horaire_applique = taux_horaire
        etat.salaire_base = arrondir_montant(total_heures * taux_horaire)
        etat.calcule_par = utilisateur
        etat.save()
        reconstruire_details_heures(etat)
    else:
        etat.total_heures = None
        etat.heures_a_prester = None
        etat.mode_calcul_heures = ''
        etat.taux_horaire_applique = None
        etat.salaire_base = salaire_fixe_proratise(enseignant, periode)
        etat.calcule_par = utilisateur
        etat.save()

    etats_recalcules = synchroniser_avances_enseignant(enseignant)
    etat = next((item for item in etats_recalcules if item.pk == etat.pk), etat)
    return etat, True


@transaction.atomic
def initialiser_etats_salaire_periode(periode, utilisateur):
    """Crée immédiatement les états groupés de tous les enseignants éligibles."""
    enseignants = list(
        enseignants_eligibles(periode).select_for_update()
    )
    etats = []
    for enseignant in enseignants:
        etat, _modifie = calculer_etat_salaire(
            enseignant, periode, utilisateur
        )
        etats.append(etat)
    return etats


def recalculer_salaire_ouvert_pour_date(
    enseignant, date_reference, utilisateur
):
    """Recalcule immédiatement le brouillon du mois s'il existe.

    Les périodes clôturées et les états validés restent intacts. La fonction
    retourne ``(etat, modifie)`` ou ``(None, False)`` lorsqu'aucune période
    ouverte et éligible ne correspond.
    """
    if enseignant.statut != 'ACTIF':
        return None, False

    periode = PeriodeSalaire.objects.filter(
        ecole=enseignant.ecole,
        mois=date_reference.month,
        annee=date_reference.year,
        cloturee=False,
    ).first()
    if periode is None or not enseignants_eligibles(periode).filter(
        pk=enseignant.pk
    ).exists():
        return None, False

    return calculer_etat_salaire(enseignant, periode, utilisateur)


ORDRE_CATEGORIES = (
    CategoriePaie.DIRECTION,
    CategoriePaie.PRIMAIRE,
    CategoriePaie.SECONDAIRE,
)


def etats_par_categorie(etats):
    """Regroupe les états par section (Direction, Primaire, Secondaire).

    Retourne une liste ordonnée de dictionnaires contenant les états de la
    section et leurs totaux : c'est la base des états détaillés, de la fiche
    d'émargement et de la masse salariale.
    """
    groupes = {categorie: [] for categorie in ORDRE_CATEGORIES}
    for etat in etats:
        groupes[categorie_paie(etat.enseignant.type_enseignant)].append(etat)

    sections = []
    for categorie in ORDRE_CATEGORIES:
        lignes = sorted(
            groupes[categorie],
            key=lambda e: (e.enseignant.nom.lower(), e.enseignant.prenoms.lower()),
        )
        if not lignes:
            continue
        total = lambda champ: arrondir_montant(
            sum((getattr(e, champ) or Decimal('0') for e in lignes), Decimal('0'))
        )
        sections.append({
            'categorie': categorie,
            'libelle': CategoriePaie(categorie).label,
            'etats': lignes,
            'effectif': len(lignes),
            'total_base': total('salaire_base'),
            'total_primes': total('primes'),
            'total_brut': total('salaire_base') + total('primes'),
            'total_deductions': total('deductions') + total('imputation_sanctions'),
            'total_sanctions': total('imputation_sanctions'),
            'total_avances': total('avances_deduites'),
            'total_net': total('salaire_net'),
            'totaux_rubriques': {
                champ: total(champ) for champ, _ in EtatSalaire.RUBRIQUES_PRIMES
            },
        })
    return sections


def masse_salariale(periode):
    """Synthèse Direction / Primaire / Secondaire d'une période."""
    etats = (
        periode.etats_salaire.select_related('enseignant')
        .order_by('enseignant__nom', 'enseignant__prenoms')
    )
    sections = etats_par_categorie(etats)
    totaux = {
        'effectif': sum(s['effectif'] for s in sections),
        'total_brut': sum((s['total_brut'] for s in sections), Decimal('0')),
        'total_avances': sum((s['total_avances'] for s in sections), Decimal('0')),
        'total_deductions': sum((s['total_deductions'] for s in sections), Decimal('0')),
        'total_sanctions': sum((s['total_sanctions'] for s in sections), Decimal('0')),
        'total_net': sum((s['total_net'] for s in sections), Decimal('0')),
    }
    return sections, totaux


def acomptes_periode(periode, nombre_bons=5):
    """Liste les bons d'acompte (avances) de la période, par enseignant.

    Reprend la feuille « Acompte » : jusqu'à cinq bons par personne, le
    cumul payé et la section. Les bons au-delà du cinquième sont cumulés
    dans la dernière colonne afin que le total reste exact.
    """
    avances = (
        AvanceSalaire.objects.filter(periode_prevue=periode)
        .select_related('enseignant')
        .order_by('enseignant__nom', 'enseignant__prenoms', 'date_avance', 'id')
    )
    lignes = {}
    for avance in avances:
        ligne = lignes.setdefault(avance.enseignant_id, {
            'enseignant': avance.enseignant,
            'section': CategoriePaie(avance.enseignant.categorie_paie).label,
            'bons': [],
            'total': Decimal('0'),
            'references': [],
        })
        ligne['bons'].append(avance.montant)
        ligne['total'] += avance.montant
        if avance.reference_externe:
            ligne['references'].append(avance.reference_externe)

    resultat = []
    for ligne in lignes.values():
        bons = ligne['bons']
        if len(bons) > nombre_bons:
            bons = bons[:nombre_bons - 1] + [sum(bons[nombre_bons - 1:], Decimal('0'))]
        ligne['bons'] = bons + [None] * (nombre_bons - len(bons))
        resultat.append(ligne)
    total = sum((ligne['total'] for ligne in resultat), Decimal('0'))
    return resultat, total
