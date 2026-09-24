from calendar import monthrange
from datetime import date

from django.db import migrations, models


def renseigner_jours_presence(apps, schema_editor):
    EtatSalaire = apps.get_model('salaires', 'EtatSalaire')
    PresenceEnseignant = apps.get_model('salaires', 'PresenceEnseignant')
    alias = schema_editor.connection.alias

    for etat in (
        EtatSalaire.objects.using(alias).select_related('periode').iterator()
    ):
        premier_jour = date(etat.periode.annee, etat.periode.mois, 1)
        dernier_jour = date(
            etat.periode.annee,
            etat.periode.mois,
            monthrange(etat.periode.annee, etat.periode.mois)[1],
        )
        jours = PresenceEnseignant.objects.using(alias).filter(
            enseignant_id=etat.enseignant_id,
            date__range=(premier_jour, dernier_jour),
            statut__in=('PRESENT', 'RETARD'),
        ).count()
        EtatSalaire.objects.using(alias).filter(pk=etat.pk).update(
            jours_presence=jours
        )


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0009_etatsalaire_avances_deduites_avancesalaire_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='etatsalaire',
            name='jours_presence',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'Nombre de jours présents ou en retard conservé au moment du calcul.'
                ),
                verbose_name='Jours de présence',
            ),
        ),
        migrations.AlterField(
            model_name='etatsalaire',
            name='mode_calcul_heures',
            field=models.CharField(
                blank=True,
                choices=[
                    ('POINTAGE', 'Pointage arrivée / départ'),
                    ('MENSUEL', 'Total mensuel global'),
                    ('MANUEL', "Saisie manuelle sur l'état"),
                ],
                default='',
                help_text="Mode conservé au moment du calcul pour l'historique",
                max_length=10,
                verbose_name='Source des heures',
            ),
        ),
        migrations.AlterField(
            model_name='enseignant',
            name='mode_calcul_horaire',
            field=models.CharField(
                choices=[
                    ('POINTAGE', 'Pointage arrivée / départ'),
                    ('MENSUEL', 'Total mensuel global'),
                    ('MANUEL', "Saisie manuelle sur l'état"),
                ],
                default='POINTAGE',
                help_text=(
                    'Pour le secondaire : utiliser les pointages quotidiens ou un total '
                    'mensuel saisi globalement.'
                ),
                max_length=10,
                verbose_name='Mode de calcul des heures',
            ),
        ),
        migrations.RunPython(renseigner_jours_presence, migrations.RunPython.noop),
    ]
