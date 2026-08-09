from decimal import Decimal

from django.db import migrations, models


def marquer_remises_existantes(apps, schema_editor):
    """Les remises déjà saisies portaient sur toute la scolarité (T1+T2+T3)."""
    PaiementRemise = apps.get_model('paiements', 'PaiementRemise')
    PaiementRemise.objects.update(
        applique_tranche_1=True,
        applique_tranche_2=True,
        applique_tranche_3=True,
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0010_echeancier_nature_frais'),
    ]

    operations = [
        migrations.AddField(
            model_name='paiementremise',
            name='applique_tranche_1',
            field=models.BooleanField(default=False, verbose_name='Appliquée sur la 1ère tranche'),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='applique_tranche_2',
            field=models.BooleanField(default=False, verbose_name='Appliquée sur la 2ème tranche'),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='applique_tranche_3',
            field=models.BooleanField(default=False, verbose_name='Appliquée sur la 3ème tranche'),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='base_calcul',
            field=models.CharField(
                choices=[('TRANCHE', 'Montant des tranches'), ('ECHEANCE', "Paiement à l'échéance")],
                default='TRANCHE',
                max_length=10,
                verbose_name='Base de calcul',
            ),
        ),
        migrations.AddField(
            model_name='paiementremise',
            name='montant_base',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=12,
                verbose_name='Base de calcul retenue (GNF)',
            ),
        ),
        migrations.RunPython(marquer_remises_existantes, noop),
    ]
