from decimal import Decimal

from django.db import migrations, models


def initialiser_prix_vente(apps, schema_editor):
    Article = apps.get_model('depenses', 'Article')
    Article.objects.filter(prix_vente_unitaire=0).update(
        prix_vente_unitaire=models.F('prix_unitaire')
    )


class Migration(migrations.Migration):

    dependencies = [
        ('depenses', '0008_simplification_logistique_papier_rame'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='prix_vente_unitaire',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=12,
                verbose_name='Prix de vente unitaire (GNF)',
            ),
        ),
        migrations.AlterField(
            model_name='article',
            name='prix_unitaire',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=12,
                verbose_name="Prix d'achat unitaire (GNF)",
            ),
        ),
        migrations.RunPython(initialiser_prix_vente, migrations.RunPython.noop),
    ]
