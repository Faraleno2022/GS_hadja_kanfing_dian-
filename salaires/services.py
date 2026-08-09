import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q, Sum

from .models import (
    AffectationClasse,
    DetailHeuresClasse,
    Enseignant,
    EtatSalaire,
    PresenceEnseignant,
)


CENTIME = Decimal('0.01')


def arrondir_montant(valeur):
    return Decimal(valeur or 0).quantize(CENTIME, rounding=ROUND_HALF_UP)


def bornes_periode(periode):
    """Retourne le premier et le dernier jour du mois de paie."""
    dernier_jour = calendar.monthrange(periode.annee, periode.mois)[1]
    return date(periode.annee, periode.mois, 1), date(
        periode.annee, periode.mois, dernier_jour
    )


def _heures_reelles(enseignant, debut, fin):
    total = PresenceEnseignant.objects.filter(
        enseignant=enseignant,
        date__range=(debut, fin),
        statut__in=('PRESENT', 'RETARD'),
    ).aggregate(total=Sum('heures_travaillees'))['total']
    return arrondir_montant(total or Decimal('0'))


def _affectations_de_la_periode(enseignant, debut, fin):
    """Inclut les affectations historiques qui chevauchent le mois de paie."""
    return list(
        AffectationClasse.objects.filter(
            enseignant=enseignant,
            date_debut__lte=fin,
        )
        .filter(Q(date_fin__isnull=True) | Q(date_fin__gte=debut))
        .filter(Q(actif=True) | Q(date_fin__isnull=False))
        .select_related('classe')
        .order_by('date_debut', 'id')
    )


def _repartir_heures(total_heures, affectations):
    """Répartit un total selon le poids des heures hebdomadaires, sans perte d'arrondi."""
    affectations_ponderees = [
        affectation
        for affectation in affectations
        if (affectation.heures_par_semaine or Decimal('0')) > 0
    ]
    poids_total = sum(
        (affectation.heures_par_semaine for affectation in affectations_ponderees),
        Decimal('0'),
    )
    if not affectations_ponderees or poids_total <= 0:
        return []

    repartition = []
    deja_reparti = Decimal('0')
    for index, affectation in enumerate(affectations_ponderees):
        if index == len(affectations_ponderees) - 1:
            heures = total_heures - deja_reparti
        else:
            heures = arrondir_montant(
                total_heures * affectation.heures_par_semaine / poids_total
            )
            deja_reparti += heures
        repartition.append((affectation, heures))
    return repartition


def _salaire_fixe_proratise(enseignant, debut, fin):
    salaire = enseignant.salaire_fixe or Decimal('0')
    if enseignant.date_embauche <= debut:
        return arrondir_montant(salaire)
    if enseignant.date_embauche > fin:
        return Decimal('0')

    jours_du_mois = Decimal((fin - debut).days + 1)
    jours_remuneres = Decimal((fin - enseignant.date_embauche).days + 1)
    return arrondir_montant(salaire * jours_remuneres / jours_du_mois)


def _calculer_etat_enseignant(etat, enseignant, periode, debut, fin, utilisateur):
    etat.details_heures.all().delete()

    if enseignant.est_salaire_fixe:
        etat.total_heures = None
        etat.taux_horaire_applique = None
        etat.salaire_base = _salaire_fixe_proratise(enseignant, debut, fin)
    else:
        debut_effectif = max(debut, enseignant.date_embauche)
        total_heures = _heures_reelles(enseignant, debut_effectif, fin)
        taux_horaire = enseignant.taux_horaire or Decimal('0')
        affectations = _affectations_de_la_periode(enseignant, debut_effectif, fin)

        etat.total_heures = total_heures
        etat.taux_horaire_applique = taux_horaire
        etat.salaire_base = arrondir_montant(total_heures * taux_horaire)

        # L'état doit exister avant les détails. Le taux est figé ici afin
        # qu'une modification future de l'enseignant ne change pas l'historique.
        etat.calcule_par = utilisateur
        etat.save()

        for affectation, heures_realisees in _repartir_heures(total_heures, affectations):
            heures_prevues = arrondir_montant(
                affectation.heures_par_semaine * periode.nombre_semaines
            )
            DetailHeuresClasse.objects.create(
                etat_salaire=etat,
                affectation_classe=affectation,
                heures_prevues=heures_prevues,
                heures_realisees=heures_realisees,
                taux_horaire_applique=taux_horaire,
                montant=Decimal('0'),
            )

    etat.calcule_par = utilisateur
    etat.save()
    return etat


@transaction.atomic
def calculer_salaires_periode(periode, utilisateur):
    """Calcule tous les salaires d'une période dans une transaction unique."""
    debut, fin = bornes_periode(periode)
    # Nettoyer les états non validés créés par l'ancien moteur pour des
    # enseignants qui n'étaient pas encore embauchés durant cette période.
    EtatSalaire.objects.filter(
        periode=periode,
        enseignant__date_embauche__gt=fin,
        valide=False,
        paye=False,
    ).delete()

    enseignants = Enseignant.objects.filter(
        ecole=periode.ecole,
        statut='ACTIF',
        date_embauche__lte=fin,
    ).order_by('id')

    calculs_effectues = 0
    for enseignant in enseignants:
        etat, cree = EtatSalaire.objects.get_or_create(
            enseignant=enseignant,
            periode=periode,
            defaults={
                'calcule_par': utilisateur,
                'salaire_base': Decimal('0'),
                'salaire_net': Decimal('0'),
            },
        )
        if not cree and etat.valide:
            continue

        _calculer_etat_enseignant(
            etat, enseignant, periode, debut, fin, utilisateur
        )
        calculs_effectues += 1

    return calculs_effectues
