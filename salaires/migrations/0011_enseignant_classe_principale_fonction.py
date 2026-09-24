from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0020_eleve_test_accueil_evalue'),
        ('salaires', '0010_etatsalaire_jours_presence_et_source_manuelle'),
    ]

    operations = [
        migrations.AddField(
            model_name='enseignant',
            name='classe_principale',
            field=models.ForeignKey(
                blank=True,
                help_text="Classe tenue par l'enseignant en garderie, maternelle ou primaire.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='enseignants_principaux',
                to='eleves.classe',
                verbose_name='Classe principale',
            ),
        ),
        migrations.AddField(
            model_name='enseignant',
            name='fonction',
            field=models.CharField(
                blank=True,
                help_text='Ex. Directeur, comptable, secrétaire ou surveillant général.',
                max_length=150,
                verbose_name='Fonction administrative',
            ),
        ),
    ]
