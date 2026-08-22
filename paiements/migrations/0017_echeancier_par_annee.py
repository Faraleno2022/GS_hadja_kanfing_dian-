from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0001_initial'),
        ('paiements', '0016_realigner_annee_paiements_ete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='echeancierpaiement',
            name='eleve',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='echeanciers',
                to='eleves.eleve',
            ),
        ),
        migrations.AddConstraint(
            model_name='echeancierpaiement',
            constraint=models.UniqueConstraint(
                fields=('eleve', 'annee_scolaire'),
                name='unique_echeancier_eleve_annee',
            ),
        ),
    ]
