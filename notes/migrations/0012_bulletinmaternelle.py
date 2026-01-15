# Generated manually for BulletinMaternelle model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0001_initial'),
        ('notes', '0011_optimisation_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulletinMaternelle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trimestre', models.CharField(max_length=20, verbose_name='Trimestre')),
                ('annee_scolaire', models.CharField(max_length=9, verbose_name='Année scolaire')),
                ('analyses', models.JSONField(blank=True, default=list, verbose_name='Analyses du travail')),
                ('recommandations', models.JSONField(blank=True, default=list, verbose_name='Recommandations')),
                ('appreciation_generale', models.TextField(blank=True, null=True, verbose_name='Appréciation générale')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('classe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notes.classenote', verbose_name='Classe')),
                ('eleve', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eleves.eleve', verbose_name='Élève')),
            ],
            options={
                'verbose_name': 'Bulletin Maternelle',
                'verbose_name_plural': 'Bulletins Maternelle',
                'ordering': ['eleve__nom', 'eleve__prenom'],
                'unique_together': {('eleve', 'classe', 'trimestre', 'annee_scolaire')},
            },
        ),
    ]
