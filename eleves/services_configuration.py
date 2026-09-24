"""Actions de configuration tarifaire, limitées à l'école sélectionnée."""
from calendar import monthrange

from django.core.exceptions import ValidationError
from django.db import transaction

from ecole_moderne.validators import valider_annee_scolaire
from .models import GrilleTarifaire


CHAMPS_DATES = (
    'date_echeance_inscription', 'date_echeance_tranche_1',
    'date_echeance_tranche_2', 'date_echeance_tranche_3',
)


@transaction.atomic
def dupliquer_grille(ecole, source_id, annee):
    valider_annee_scolaire(annee)
    source = GrilleTarifaire.objects.select_for_update().get(pk=source_id, ecole=ecole)
    if GrilleTarifaire.objects.filter(ecole=ecole, niveau=source.niveau, annee_scolaire=annee).exists():
        raise ValidationError("Une grille existe déjà pour ce niveau et cette année. Modifiez-la directement.")
    valider_annee_scolaire(source.annee_scolaire)
    decalage = int(annee[:4]) - int(source.annee_scolaire[:4])
    champs = ('frais_inscription', 'frais_reinscription', 'tranche_1', 'tranche_2', 'tranche_3', 'periode_1', 'periode_2', 'periode_3')
    valeurs = {champ: getattr(source, champ) for champ in champs}
    for champ in CHAMPS_DATES:
        date = getattr(source, champ + '_defaut')
        if date:
            annee_date = date.year + decalage
            date = date.replace(year=annee_date, day=min(date.day, monthrange(annee_date, date.month)[1]))
        valeurs[champ + '_defaut'] = date
    nouvelle = GrilleTarifaire(ecole=ecole, niveau=source.niveau, annee_scolaire=annee, **valeurs)
    nouvelle.full_clean()
    nouvelle.save()
    return nouvelle


@transaction.atomic
def completer_dates_grille(ecole, grille_id):
    from paiements.models import EcheancierPaiement
    from paiements.services import _statut_depuis_situation

    grille = GrilleTarifaire.objects.get(pk=grille_id, ecole=ecole)
    echeanciers = EcheancierPaiement.objects.select_for_update().filter(
        eleve__classe__ecole=ecole, eleve__classe__niveau=grille.niveau,
        annee_scolaire=grille.annee_scolaire,
    )
    nombre = 0
    for echeancier in echeanciers:
        modifies = []
        for champ in CHAMPS_DATES:
            valeur = getattr(grille, champ + '_defaut')
            if valeur and not getattr(echeancier, champ):
                setattr(echeancier, champ, valeur)
                modifies.append(champ)
        if not modifies:
            continue
        dates = [getattr(echeancier, champ) for champ in CHAMPS_DATES if getattr(echeancier, champ)]
        if dates != sorted(dates):
            raise ValidationError("Les dates proposées ne respectent pas l'ordre des échéances. Aucune date n'a été modifiée.")
        echeancier.statut = _statut_depuis_situation(echeancier.situation_financiere())
        echeancier.save(update_fields=modifies + ['statut', 'date_modification'])
        nombre += 1
    return nombre
