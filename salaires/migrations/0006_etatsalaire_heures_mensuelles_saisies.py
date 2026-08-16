from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0005_etatsalaire_taux_horaire_applique'),
    ]

    operations = [
        migrations.AddField(
            model_name='etatsalaire',
            name='heures_mensuelles_saisies',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Total réel saisi globalement pour ce mois. Laisser vide pour "
                    "utiliser les pointages d'arrivée et de départ."
                ),
                max_digits=8,
                null=True,
                verbose_name='Heures mensuelles saisies',
            ),
        ),
        migrations.AlterField(
            model_name='enseignant',
            name='type_enseignant',
            field=models.CharField(
                choices=[
                    ('GARDERIE', 'Garderie'),
                    ('MATERNELLE', 'Maternelle'),
                    ('PRIMAIRE', 'Primaire'),
                    ('SECONDAIRE', 'Secondaire (taux horaire)'),
                    ('ADMINISTRATEUR', 'Cadre / Administrateur'),
                ],
                max_length=20,
                verbose_name="Type d'enseignant",
            ),
        ),
    ]
