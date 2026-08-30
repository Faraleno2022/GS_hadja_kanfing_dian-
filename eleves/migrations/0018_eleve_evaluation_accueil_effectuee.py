from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eleves", "0017_alter_classe_niveau_alter_grilletarifaire_niveau"),
    ]

    operations = [
        migrations.AddField(
            model_name="eleve",
            name="evaluation_accueil_effectuee",
            field=models.BooleanField(
                db_index=True,
                default=False,
                verbose_name="Évalué au test d'accueil",
            ),
        ),
    ]
