from django.db import migrations, models


def renseigner_taux_historiques(apps, schema_editor):
    EtatSalaire = apps.get_model('salaires', 'EtatSalaire')
    for etat in EtatSalaire.objects.filter(total_heures__isnull=False).select_related('enseignant'):
        etat.taux_horaire_applique = etat.enseignant.taux_horaire
        etat.save(update_fields=['taux_horaire_applique'])


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0004_add_sync_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='etatsalaire',
            name='taux_horaire_applique',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Taux figé au moment du calcul pour conserver l'historique de paie",
                max_digits=10,
                null=True,
                verbose_name='Taux horaire appliqué',
            ),
        ),
        migrations.RunPython(renseigner_taux_historiques, migrations.RunPython.noop),
    ]

