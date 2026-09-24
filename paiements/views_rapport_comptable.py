from copy import copy
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from django.utils import timezone

from eleves.models import Classe
from eleves.utils_annee import get_debut_periode_reporting
from utilisateurs.permissions import can_view_reports
from utilisateurs.utils import filter_by_user_school, user_school

from .models import EcheancierPaiement, Paiement, Relance
from .payment_engine import situation_echeancier


def _requete_filtree(request):
    """Les liens et le formulaire partagent les mêmes filtres validés."""
    filtered = copy(request)
    query = request.GET.copy()
    for source, target in (('classe', 'classe_id'), ('date_debut', 'du'), ('date_fin', 'au')):
        if source in query:
            query[target] = query[source]
    filtered.GET = query
    return filtered


def _montant_exigible(echeancier, date_reference):
    postes = (
        (echeancier.date_echeance_inscription, echeancier.frais_inscription_du),
        (echeancier.date_echeance_tranche_1, echeancier.tranche_1_due),
        (echeancier.date_echeance_tranche_2, echeancier.tranche_2_due),
        (echeancier.date_echeance_tranche_3, echeancier.tranche_3_due),
    )
    return sum(
        (montant or Decimal("0"))
        for echeance, montant in postes
        if echeance and echeance < date_reference
    )


def _rapport_data(request):
    aujourd_hui = timezone.localdate()
    ecole_utilisateur = user_school(request.user)
    debut_defaut = get_debut_periode_reporting(
        request, ecole_utilisateur, today=aujourd_hui
    )
    from .rapports_professionnels import _parse_filters
    filtered = _requete_filtree(request)
    scope = _parse_filters(filtered)
    annee = scope['school_year']
    if annee:
        debut_defaut = date(int(annee[:4]), 7, 1)
    date_fin = scope['cutoff']
    date_debut = scope['start'] or min(debut_defaut, date_fin)
    classe_id = filtered.GET.get('classe_id', '').strip()
    statut = (request.GET.get('statut') or 'VALIDE').strip().upper()
    if statut not in {code for code, _ in Paiement.STATUT_CHOICES} | {'TOUS'}:
        raise ValueError('Le statut sélectionné est invalide.')
    classes = filter_by_user_school(
        Classe.objects.select_related('ecole').order_by('annee_scolaire', 'nom'),
        request.user, 'ecole',
    )
    classe_selectionnee = classes.get(pk=int(classe_id)) if classe_id else None

    paiements = filter_by_user_school(
        Paiement.objects.select_related(
            "eleve", "eleve__classe", "eleve__classe__ecole",
            "type_paiement", "mode_paiement",
        ),
        request.user,
        "eleve__classe__ecole",
    ).filter(date_paiement__range=(date_debut, date_fin), eleve__classe_id__in=scope['class_ids'])
    if annee:
        paiements = paiements.filter(annee_scolaire=annee)
    if statut != "TOUS":
        paiements = paiements.filter(statut=statut)
    if classe_selectionnee:
        paiements = paiements.filter(eleve__classe=classe_selectionnee)
    paiements = paiements.order_by(
        "eleve__classe__nom", "-date_paiement", "eleve__nom"
    )

    echeanciers = filter_by_user_school(
        EcheancierPaiement.objects.select_related(
            "eleve", "eleve__classe", "eleve__classe__ecole"
        ).filter(eleve__statut="ACTIF"),
        request.user,
        "eleve__classe__ecole",
    )
    echeanciers = echeanciers.filter(eleve__classe_id__in=scope['class_ids'])
    if annee:
        echeanciers = echeanciers.filter(annee_scolaire=annee)
    if classe_selectionnee:
        echeanciers = echeanciers.filter(eleve__classe=classe_selectionnee)

    retards = []
    for echeancier in echeanciers.order_by(
        "eleve__classe__nom", "eleve__nom", "eleve__prenom"
    ):
        situation = situation_echeancier(
            echeancier, date_reference=date_fin
        )
        montant_retard = situation['retard_total']
        if montant_retard > 0:
            retards.append({
                "echeancier": echeancier,
                "montant_retard": montant_retard,
            })

    relances = filter_by_user_school(
        Relance.objects.select_related(
            "eleve", "eleve__classe", "eleve__classe__ecole"
        ),
        request.user,
        "eleve__classe__ecole",
    ).filter(date_creation__date__range=(date_debut, date_fin), eleve__classe_id__in=scope['class_ids'])
    if classe_selectionnee:
        relances = relances.filter(eleve__classe=classe_selectionnee)
    relances = relances.order_by("eleve__classe__nom", "-date_creation")

    paiements_list = list(paiements)
    relances_list = list(relances)
    total_paiements = sum(
        (paiement.montant or Decimal("0") for paiement in paiements_list),
        Decimal("0"),
    )
    total_retards = sum(
        (retard["montant_retard"] for retard in retards), Decimal("0")
    )

    modes = []
    for ligne in paiements.values("mode_paiement__nom").annotate(
        nombre=Count("id"), montant=Sum("montant")
    ).order_by("mode_paiement__nom"):
        montant = ligne["montant"] or Decimal("0")
        modes.append({
            "nom": ligne["mode_paiement__nom"] or "Non renseigné",
            "nombre": ligne["nombre"],
            "montant": montant,
            "pourcentage": (
                montant * Decimal("100") / total_paiements
                if total_paiements else Decimal("0")
            ),
        })

    classes_stats = {}
    for paiement in paiements_list:
        classe = paiement.eleve.classe
        ligne = classes_stats.setdefault(classe.id, {
            "classe": classe, "paiements": 0, "montant": Decimal("0"),
            "retards": Decimal("0"), "relances": 0,
        })
        ligne["paiements"] += 1
        ligne["montant"] += paiement.montant or Decimal("0")
    for retard in retards:
        classe = retard["echeancier"].eleve.classe
        ligne = classes_stats.setdefault(classe.id, {
            "classe": classe, "paiements": 0, "montant": Decimal("0"),
            "retards": Decimal("0"), "relances": 0,
        })
        ligne["retards"] += retard["montant_retard"]
    for relance in relances_list:
        classe = relance.eleve.classe
        ligne = classes_stats.setdefault(classe.id, {
            "classe": classe, "paiements": 0, "montant": Decimal("0"),
            "retards": Decimal("0"), "relances": 0,
        })
        ligne["relances"] += 1

    ecole = classe_selectionnee.ecole if classe_selectionnee else ecole_utilisateur
    return {
        "annees_disponibles": sorted(set(classes.values_list("annee_scolaire", flat=True)), reverse=True),
        "annee_scolaire": annee,
        "titre_page": "Rapport comptable consolidé",
        "ecole": ecole,
        "classes": classes,
        "classe_selectionnee": classe_selectionnee,
        "classe_id": str(classe_selectionnee.id) if classe_selectionnee else "",
        "date_debut": date_debut,
        "date_fin": date_fin,
        "statut": statut,
        "paiements": paiements_list,
        "retards": retards,
        "relances": relances_list,
        "modes": modes,
        "classes_stats": sorted(
            classes_stats.values(),
            key=lambda ligne: (ligne["classe"].annee_scolaire, ligne["classe"].nom),
        ),
        "total_paiements": total_paiements,
        "total_retards": total_retards,
        "nombre_paiements": len(paiements_list),
        "nombre_retards": len(retards),
        "nombre_relances": len(relances_list),
    }


@can_view_reports
def rapport_comptable(request):
    try:
        data = _rapport_data(request)
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    return render(request, "paiements/rapport_comptable.html", data)


def export_rapport_comptable_pdf(request):
    """Adapte les filtres de la page au rapport PDF professionnel."""
    from .rapports_professionnels import export_comptabilite_pdf

    request = _requete_filtree(request)
    return export_comptabilite_pdf(request)


def export_rapport_comptable_excel(request):
    """Adapte les filtres de la page au rapport Excel professionnel."""
    from .rapports_professionnels import export_comptabilite_excel

    request = _requete_filtree(request)
    return export_comptabilite_excel(request)
