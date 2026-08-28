"""Répare les paiements de juillet-août étiquetés sur l'année précédente.

La migration 0013 a figé l'année de chaque paiement existant à partir de sa
seule date, avec une coupure au 1er septembre. Les réinscriptions et premiers
versements encaissés en juillet et août ont donc reçu l'année qui s'achève,
alors que la classe et l'échéancier de l'élève portaient déjà l'année qui
commence. Résultat chez le client, après mise à jour : ces paiements
disparaissaient de la liste (filtrée sur l'année active) et n'entraient plus
dans les soldes ni dans les reçus.

Seuls ces versements-là sont réétiquetés, et uniquement vers l'année de
l'échéancier de l'élève. Aucun montant n'est modifié.
"""

from django.db import migrations

from paiements.payment_engine import realigner_annees_paiements


def realigner(apps, schema_editor):
    realigner_annees_paiements(
        apps.get_model('paiements', 'Paiement'),
        apps.get_model('paiements', 'EcheancierPaiement'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0015_paiementremise_deduite_du_paiement'),
    ]

    operations = [
        migrations.RunPython(realigner, migrations.RunPython.noop),
    ]
