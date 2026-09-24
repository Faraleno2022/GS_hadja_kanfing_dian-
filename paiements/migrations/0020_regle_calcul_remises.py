from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('paiements', '0019_alter_echeancierpaiement_annee_scolaire_and_more')]
    operations = [
        migrations.AddField(
            model_name='paiementremise', name='regle_calcul',
            field=models.JSONField(default=dict, blank=True, editable=False),
        ),
    ]
