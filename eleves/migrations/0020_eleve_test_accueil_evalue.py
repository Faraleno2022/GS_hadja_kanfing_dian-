from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0019_alter_classe_annee_scolaire_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='eleve',
            name='test_accueil_evalue',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Indique si l'élève a déjà passé son test d'accueil.",
                verbose_name="Évalué au test d'accueil",
            ),
        ),
        migrations.AlterModelOptions(
            name='eleve',
            options={
                'ordering': ['-date_creation', '-id'],
                'verbose_name': 'Élève',
                'verbose_name_plural': 'Élèves',
            },
        ),
    ]
