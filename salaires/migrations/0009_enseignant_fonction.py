from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0008_etatsalaire_presence_et_ajustement'),
    ]

    operations = [
        migrations.AddField(
            model_name='enseignant',
            name='fonction',
            field=models.CharField(
                blank=True,
                help_text=(
                    'Poste occupé par un membre du personnel administratif '
                    '(ex. directeur, secrétaire, comptable).'
                ),
                max_length=150,
                verbose_name='Fonction administrative',
            ),
        ),
    ]
