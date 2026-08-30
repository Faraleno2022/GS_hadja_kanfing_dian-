import django.core.validators
from decimal import Decimal

from django.db import migrations, models


def renseigner_source_pointage(apps, schema_editor):
    EtatSalaire = apps.get_model('salaires', 'EtatSalaire')
    EtatSalaire.objects.filter(
        enseignant__type_enseignant='SECONDAIRE',
        mode_calcul_heures='',
    ).update(mode_calcul_heures='POINTAGE')


def effacer_source_heures(apps, schema_editor):
    EtatSalaire = apps.get_model('salaires', 'EtatSalaire')
    EtatSalaire.objects.update(mode_calcul_heures='')


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0005_etatsalaire_taux_horaire_applique_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='enseignant',
            name='mode_calcul_horaire',
            field=models.CharField(
                choices=[
                    ('POINTAGE', 'Pointage arrivée / départ'),
                    ('MENSUEL', 'Total mensuel global'),
                ],
                default='POINTAGE',
                help_text=(
                    'Pour le secondaire : utiliser les pointages quotidiens '
                    'ou un total mensuel saisi globalement.'
                ),
                max_length=10,
                verbose_name='Mode de calcul des heures',
            ),
        ),
        migrations.AddField(
            model_name='etatsalaire',
            name='mode_calcul_heures',
            field=models.CharField(
                blank=True,
                choices=[
                    ('POINTAGE', 'Pointage arrivée / départ'),
                    ('MENSUEL', 'Total mensuel global'),
                ],
                default='',
                help_text="Mode conservé au moment du calcul pour l'historique",
                max_length=10,
                verbose_name='Source des heures',
            ),
        ),
        migrations.RunPython(
            renseigner_source_pointage,
            effacer_source_heures,
        ),
        migrations.AlterField(
            model_name='enseignant',
            name='heures_mensuelles',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    'Total mensuel global utilisé pour calculer le salaire horaire'
                ),
                max_digits=6,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(Decimal('0')),
                    django.core.validators.MaxValueValidator(Decimal('200')),
                ],
                verbose_name='Heures mensuelles',
            ),
        ),
    ]
