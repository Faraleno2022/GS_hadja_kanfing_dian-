import unicodedata
from decimal import Decimal

from django.db import migrations, models


INSCRIPTION = "INSCRIPTION"
REINSCRIPTION = "REINSCRIPTION"


def _registration_kind(label):
    normalized = unicodedata.normalize("NFKD", label or "").casefold()
    normalized = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    if "reinscription" in normalized:
        return REINSCRIPTION
    if "inscription" in normalized:
        return INSCRIPTION
    return None


def backfill_nature_frais(apps, schema_editor):
    Echeancier = apps.get_model("paiements", "EcheancierPaiement")
    Paiement = apps.get_model("paiements", "Paiement")
    Grille = apps.get_model("eleves", "GrilleTarifaire")

    # Le dernier paiement d'admission explicite est la meilleure preuve de la
    # nature choisie par l'utilisateur pour l'échéancier courant.
    nature_par_eleve = {}
    paiements = (
        Paiement.objects
        .filter(type_paiement__isnull=False)
        .order_by("eleve_id", "-date_paiement", "-pk")
        .values_list("eleve_id", "type_paiement__nom")
    )
    for eleve_id, type_nom in paiements.iterator():
        if eleve_id in nature_par_eleve:
            continue
        nature = _registration_kind(type_nom)
        if nature:
            nature_par_eleve[eleve_id] = nature

    grilles = {
        (ecole_id, niveau, annee): (
            Decimal(str(inscription or 0)),
            Decimal(str(reinscription or 0)),
        )
        for ecole_id, niveau, annee, inscription, reinscription in (
            Grille.objects.values_list(
                "ecole_id",
                "niveau",
                "annee_scolaire",
                "frais_inscription",
                "frais_reinscription",
            )
        )
    }

    a_mettre_a_jour = []
    echeanciers = Echeancier.objects.select_related("eleve__classe")
    for echeancier in echeanciers.iterator():
        nature = nature_par_eleve.get(echeancier.eleve_id)
        if nature is None:
            classe = getattr(echeancier.eleve, "classe", None)
            tarifs = grilles.get(
                (
                    getattr(classe, "ecole_id", None),
                    getattr(classe, "niveau", None),
                    echeancier.annee_scolaire,
                )
            )
            if tarifs:
                frais = Decimal(str(echeancier.frais_inscription_du or 0))
                tarif_inscription, tarif_reinscription = tarifs
                # Une égalité avec les deux tarifs est ambiguë : on conserve
                # alors le défaut sûr « inscription ».
                if frais == tarif_reinscription and frais != tarif_inscription:
                    nature = REINSCRIPTION
        echeancier.nature_frais = nature or INSCRIPTION
        a_mettre_a_jour.append(echeancier)

    if a_mettre_a_jour:
        Echeancier.objects.bulk_update(
            a_mettre_a_jour,
            ["nature_frais"],
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("eleves", "0016_ecole_bonus_suivi_actif"),
        ("paiements", "0009_complete_sync_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="echeancierpaiement",
            name="nature_frais",
            field=models.CharField(
                choices=[
                    (INSCRIPTION, "Inscription"),
                    (REINSCRIPTION, "Réinscription"),
                ],
                db_index=True,
                default=INSCRIPTION,
                max_length=20,
                verbose_name="Nature des frais d'admission",
            ),
        ),
        migrations.RunPython(backfill_nature_frais, migrations.RunPython.noop),
    ]
