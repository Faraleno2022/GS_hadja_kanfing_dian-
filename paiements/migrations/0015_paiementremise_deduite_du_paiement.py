from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0014_alter_echeancierpaiement_annee_scolaire_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='paiementremise',
            name='deduite_du_paiement',
            field=models.BooleanField(
                default=False,
                verbose_name='Déduite du montant du reçu',
            ),
        ),
    ]
