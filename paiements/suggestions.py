"""Aperçu des sommes à payer, sans créer ni modifier d'échéancier."""
from copy import copy
from decimal import Decimal

from django.utils import timezone

from eleves.models import GrilleTarifaire
from .allocation import INSCRIPTION, TRANCHE_1, TRANCHE_2, TRANCHE_3, is_reinscription_payment
from .models import EcheancierPaiement
from .payment_engine import school_year_from_date, situation_echeancier


def echeancier_apercu(eleve, type_nom):
    classe = eleve.classe
    if classe is None:
        return None
    annee = classe.annee_scolaire or school_year_from_date(timezone.localdate())
    ech = EcheancierPaiement.objects.filter(eleve=eleve, annee_scolaire=annee).first()
    if ech is not None:
        ech = copy(ech)
    grilles = GrilleTarifaire.objects.filter(ecole_id=classe.ecole_id, niveau=classe.niveau)
    grille = grilles.filter(annee_scolaire=annee).first()
    if grille is None:
        grille = grilles.filter(annee_scolaire=school_year_from_date(timezone.localdate())).first()
    if grille is None:
        grille = grilles.order_by('-annee_scolaire', '-pk').first()
    if ech is None and grille is None:
        return None
    reinscription = is_reinscription_payment(type_nom)
    if ech is None:
        ech = EcheancierPaiement(eleve=eleve, annee_scolaire=annee)
    total = sum((getattr(ech, field) or Decimal('0')) for field in ('frais_inscription_du', 'tranche_1_due', 'tranche_2_due', 'tranche_3_due'))
    if grille is not None and (not total or reinscription):
        ech.frais_inscription_du = grille.frais_reinscription if reinscription else grille.frais_inscription
        ech.tranche_1_due = grille.tranche_1
        ech.tranche_2_due = grille.tranche_2
        ech.tranche_3_due = grille.tranche_3
    if reinscription:
        ech.nature_frais = EcheancierPaiement.NATURE_REINSCRIPTION
    return ech


def suggestion_paiement(echeancier, type_nom):
    from .views import libelle_poste, libelle_postes, montant_attendu_pour_type
    situation = situation_echeancier(echeancier)
    suggested, detail = montant_attendu_pour_type(type_nom, situation['dues'], situation['couverts'])
    reinscription = echeancier.est_reinscription or is_reinscription_payment(type_nom)
    postes = [{'label': libelle_poste(bucket, reinscription), 'montant': int(reste)} for bucket, reste in detail]
    description = libelle_postes([bucket for bucket, _ in detail], reinscription)
    restes = situation['restes']
    breakdown = {
        'fi_restant': int(restes[INSCRIPTION]), 't1_restant': int(restes[TRANCHE_1]),
        't2_restant': int(restes[TRANCHE_2]), 't3_restant': int(restes[TRANCHE_3]),
        'description': f'{description} (reste)' if description else 'Montant à saisir à la main.',
        'postes': postes,
        'lignes': [{'libelle': (poste['label'] if i == 0 and detail[i][0] == INSCRIPTION else f'Tranche {int(detail[i][0][-1])}'), 'reste': poste['montant']} for i, poste in enumerate(postes)],
        'postes_reconnus': bool(detail),
        'frais_admission_label': 'Réinscription' if reinscription else 'Inscription',
    }
    return {
        'ok': True, 'suggested': int(suggested or 0), 'breakdown': breakdown,
        'solde_total': int(situation['solde_restant']),
        'echeancier': {'solde_restant': int(situation['solde_restant'])},
    }
