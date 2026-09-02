from decimal import Decimal
from calendar import monthrange
from datetime import date

from django.core.validators import MinValueValidator
from django.db import migrations, models


def renseigner_jours_presence(apps, schema_editor):
    EtatSalaire = apps.get_model('salaires', 'EtatSalaire')
    PresenceEnseignant = apps.get_model('salaires', 'PresenceEnseignant')

    for etat in EtatSalaire.objects.select_related('periode').iterator():
        debut = date(etat.periode.annee, etat.periode.mois, 1)
        fin = date(
            etat.periode.annee,
            etat.periode.mois,
            monthrange(etat.periode.annee, etat.periode.mois)[1],
        )
        jours = (
            PresenceEnseignant.objects.filter(
                enseignant_id=etat.enseignant_id,
                date__range=(debut, fin),
                statut__in=('PRESENT', 'RETARD'),
            )
            .values('date')
            .distinct()
            .count()
        )
        EtatSalaire.objects.filter(pk=etat.pk).update(
            nombre_jours_presence=jours
        )


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0007_etatsalaire_avances_avancesalaire'),
    ]

    operations = [
        migrations.AlterField(
            model_name='etatsalaire',
            name='mode_calcul_heures',
            field=models.CharField(
                blank=True,
                choices=[
                    ('POINTAGE', 'Pointage arrivée / départ'),
                    ('MENSUEL', 'Total mensuel global'),
                    ('SAISIE', 'Saisie manuelle de la période'),
                ],
                default='',
                help_text='Mode conservé au moment du calcul pour l\'historique',
                max_length=10,
                verbose_name='Source des heures',
            ),
        ),
        migrations.AlterField(
            model_name='etatsalaire',
            name='total_heures',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Total des heures enseignées dans le mois',
                max_digits=8,
                null=True,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Total heures',
            ),
        ),
        migrations.AddField(
            model_name='etatsalaire',
            name='nombre_jours_presence',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'Nombre de jours avec une présence ou un retard pendant la période'
                ),
                verbose_name='Jours de présence',
            ),
        ),
        migrations.AddField(
            model_name='etatsalaire',
            name='ajuste_manuellement',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Conserve les paramètres de salaire modifiés avant la validation'
                ),
                verbose_name='Ajusté manuellement',
            ),
        ),
        migrations.RunPython(
            renseigner_jours_presence,
            migrations.RunPython.noop,
        ),
    ]
