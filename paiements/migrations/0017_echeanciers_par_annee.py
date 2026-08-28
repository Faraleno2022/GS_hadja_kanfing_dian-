import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0016_realigner_annee_paiements_ete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='echeancierpaiement',
            name='eleve',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='echeanciers',
                related_query_name='echeancier',
                to='eleves.eleve',
            ),
        ),
        migrations.AddConstraint(
            model_name='echeancierpaiement',
            constraint=models.UniqueConstraint(
                fields=('eleve', 'annee_scolaire'),
                name='echeancier_unique_eleve_annee',
            ),
        ),
    ]
