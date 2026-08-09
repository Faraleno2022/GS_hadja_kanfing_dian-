import unicodedata
from decimal import Decimal

from django.db import migrations, models


def _normalize(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.casefold()


def _allocation_order(value):
    name = _normalize(value)
    if "inscription" in name:
        return (0, 1, 2, 3)
    if any(token in name for token in ("tranche 1", "tranche1", "1ere tranche", "t1")):
        return (1, 2, 3)
    if any(token in name for token in ("tranche 2", "tranche2", "2eme tranche", "t2")):
        return (2, 3)
    if any(token in name for token in ("tranche 3", "tranche3", "3eme tranche", "t3")):
        return (3,)
    if "annuel" in name or "scolarite" in name:
        return (1, 2, 3)
    return (0, 1, 2, 3)


def backfill_nature_frais(apps, schema_editor):
    Echeancier = apps.get_model("paiements", "EcheancierPaiement")
    Paiement = apps.get_model("paiements", "Paiement")
    Grille = apps.get_model("eleves", "GrilleTarifaire")

    for echeancier in Echeancier.objects.select_related("eleve__classe").iterator():
        classe = getattr(echeancier.eleve, "classe", None)
        grille = None
        if classe is not None:
            grille = Grille.objects.filter(
                ecole_id=classe.ecole_id,
                niveau=classe.niveau,
                annee_scolaire=echeancier.annee_scolaire,
            ).first()

        type_names = Paiement.objects.filter(
            eleve_id=echeancier.eleve_id,
        ).values_list("type_paiement__nom", flat=True)
        is_reinscription = any("reinscription" in _normalize(name) for name in type_names)

        if (
            not is_reinscription
            and grille is not None
            and grille.frais_reinscription != grille.frais_inscription
            and echeancier.frais_inscription_du == grille.frais_reinscription
        ):
            is_reinscription = True

        if is_reinscription:
            echeancier.nature_frais = "REINSCRIPTION"
            if grille is not None:
                target_fee = Decimal(str(grille.frais_reinscription or 0))
                old_paid = Decimal(str(echeancier.frais_inscription_paye or 0))
                overflow = max(Decimal("0"), old_paid - target_fee)
                echeancier.frais_inscription_du = target_fee
                echeancier.frais_inscription_paye = min(old_paid, target_fee)

                for due_attr, paid_attr in (
                    ("tranche_1_due", "tranche_1_payee"),
                    ("tranche_2_due", "tranche_2_payee"),
                    ("tranche_3_due", "tranche_3_payee"),
                ):
                    if overflow <= 0:
                        break
                    due_value = Decimal(str(getattr(echeancier, due_attr) or 0))
                    paid_value = Decimal(str(getattr(echeancier, paid_attr) or 0))
                    take = min(overflow, max(Decimal("0"), due_value - paid_value))
                    setattr(echeancier, paid_attr, paid_value + take)
                    overflow -= take

            echeancier.save(update_fields=[
                "nature_frais",
                "frais_inscription_du",
                "frais_inscription_paye",
                "tranche_1_payee",
                "tranche_2_payee",
                "tranche_3_payee",
            ])

        # Rejouer les encaissements validés avec la nouvelle règle pour réparer
        # aussi les anciennes affectations (par exemple un paiement T1 placé à
        # tort sur l'inscription). Les remises restent volontairement séparées.
        dues = [
            Decimal(str(echeancier.frais_inscription_du or 0)),
            Decimal(str(echeancier.tranche_1_due or 0)),
            Decimal(str(echeancier.tranche_2_due or 0)),
            Decimal(str(echeancier.tranche_3_due or 0)),
        ]
        paid = [Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")]
        validated_payments = (
            Paiement.objects
            .filter(eleve_id=echeancier.eleve_id, statut="VALIDE")
            .select_related("type_paiement")
            .order_by("date_validation", "id")
        )
        for payment in validated_payments.iterator():
            remaining = max(Decimal("0"), Decimal(str(payment.montant or 0)))
            for index in _allocation_order(payment.type_paiement.nom):
                if remaining <= 0:
                    break
                room = max(Decimal("0"), dues[index] - paid[index])
                take = min(remaining, room)
                paid[index] += take
                remaining -= take

        echeancier.frais_inscription_paye = paid[0]
        echeancier.tranche_1_payee = paid[1]
        echeancier.tranche_2_payee = paid[2]
        echeancier.tranche_3_payee = paid[3]
        echeancier.save(update_fields=[
            "frais_inscription_paye",
            "tranche_1_payee",
            "tranche_2_payee",
            "tranche_3_payee",
        ])


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
                choices=[("INSCRIPTION", "Inscription"), ("REINSCRIPTION", "Réinscription")],
                default="INSCRIPTION",
                max_length=20,
                verbose_name="Nature des frais d'admission",
            ),
        ),
        migrations.RunPython(backfill_nature_frais, migrations.RunPython.noop),
    ]
