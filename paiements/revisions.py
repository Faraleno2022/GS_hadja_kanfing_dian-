"""Option annuelle de révision : réduction fixe, sans modifier l'encaissement."""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import EcheancierPaiement, Paiement, PaiementRemise, RemiseReduction

MONTANT_REVISION = Decimal('20000')
PRECISION_REVISION = 'Révision : réduction de 20 000 GNF sur la scolarité'


def annee_revision_eleve(eleve, date_paiement=None):
    """Année à laquelle un nouveau paiement de l'élève serait rattaché (cf. Paiement.save)."""
    annee = getattr(getattr(eleve, 'classe', None), 'annee_scolaire', '') or ''
    if not annee:
        from .payment_engine import school_year_from_date
        annee = school_year_from_date(date_paiement)
    return annee


def paiement_revision_existant(eleve, annee_scolaire, exclude_pk=None):
    """Paiement actif portant déjà la révision de l'élève pour l'année, ou None."""
    if not eleve or not annee_scolaire:
        return None
    qs = Paiement.objects.filter(
        eleve=eleve, annee_scolaire=annee_scolaire,
        frais_revision_inclus=True, statut__in=['EN_ATTENTE', 'VALIDE'],
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.order_by('date_paiement', 'pk').first()


def message_revision_deja_payee(paiement):
    etat = 'payés' if paiement.statut == 'VALIDE' else 'déjà sélectionnés'
    return (f"Frais de révision {etat} pour cette année scolaire "
            f"(reçu {paiement.numero_recu}). Ils ne peuvent pas être prélevés une deuxième fois.")


def verifier_unicite_revision(paiement):
    if not paiement.frais_revision_inclus or paiement.statut not in ('EN_ATTENTE', 'VALIDE'):
        return
    if Paiement.objects.filter(
        eleve_id=paiement.eleve_id, annee_scolaire=paiement.annee_scolaire,
        frais_revision_inclus=True, statut__in=['EN_ATTENTE', 'VALIDE'],
    ).exclude(pk=paiement.pk).exists():
        raise ValidationError('La révision est déjà sélectionnée sur un paiement de cet élève pour cette année scolaire.')


@transaction.atomic
def synchroniser_revisions(echeancier):
    """Reconstruit aussi l'option après correction ou restauration de la corbeille."""
    echeancier = EcheancierPaiement.objects.select_for_update().get(pk=echeancier.pk)
    paiements = Paiement.objects.select_for_update().filter(
        eleve_id=echeancier.eleve_id, annee_scolaire=echeancier.annee_scolaire,
    ).filter(Q(frais_revision_inclus=True) | Q(pk__in=PaiementRemise.objects.filter(origine_revision=True).values('paiement_id')))
    total_scolarite = sum((getattr(echeancier, f'tranche_{n}_due') for n in (1, 2, 3)), Decimal('0'))
    for paiement in paiements:
        liens = PaiementRemise.objects.filter(paiement=paiement, origine_revision=True)
        if not paiement.frais_revision_inclus:
            liens.delete()
            continue
        verifier_unicite_revision(paiement)
        if total_scolarite < MONTANT_REVISION and paiement.statut in ('EN_ATTENTE', 'VALIDE'):
            raise ValidationError('La scolarité ne permet pas de déduire les 20 000 GNF de révision.')
        if liens.exists():
            continue
        catalogue = RemiseReduction.objects.filter(nom='Frais de révision (option automatique)', actif=False).first()
        if catalogue is None:
            catalogue = RemiseReduction.objects.create(
                nom='Frais de révision (option automatique)', type_remise='MONTANT_FIXE',
                valeur=MONTANT_REVISION, motif='AUTRE', actif=False,
                date_debut=date(2000, 1, 1), date_fin=date(9999, 12, 31),
                description=PRECISION_REVISION,
            )
        PaiementRemise.objects.create(
            paiement=paiement, remise=catalogue, origine_revision=True,
            montant_remise=MONTANT_REVISION, montant_base=total_scolarite,
            base_calcul='TRANCHE', deduite_du_paiement=False,
            applique_tranche_1=True, applique_tranche_2=True, applique_tranche_3=True,
            regle_calcul={'base': 'TRANCHE', 'tranches': [1, 2, 3], 'type': 'MONTANT_FIXE', 'valeur': '20000'},
        )
