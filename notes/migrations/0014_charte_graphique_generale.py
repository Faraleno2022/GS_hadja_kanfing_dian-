from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0013_creneauemploidutemps'),
    ]

    operations = [
        migrations.AddField(
            model_name='themebulletin',
            name='couleur_carte_attention',
            field=models.CharField(default='#f59e0b', max_length=7, verbose_name="Carte d'attention"),
        ),
        migrations.AddField(
            model_name='themebulletin',
            name='couleur_carte_danger',
            field=models.CharField(default='#dc3545', max_length=7, verbose_name="Carte d'alerte"),
        ),
        migrations.AddField(
            model_name='themebulletin',
            name='couleur_carte_primaire',
            field=models.CharField(default='#0d6efd', max_length=7, verbose_name='Carte principale'),
        ),
        migrations.AddField(
            model_name='themebulletin',
            name='couleur_carte_succes',
            field=models.CharField(default='#198754', max_length=7, verbose_name='Carte positive'),
        ),
        migrations.AlterModelOptions(
            name='themebulletin',
            options={
                'ordering': ['-par_defaut', '-actif', 'nom'],
                'verbose_name': 'Charte graphique',
                'verbose_name_plural': 'Chartes graphiques',
            },
        ),
    ]
