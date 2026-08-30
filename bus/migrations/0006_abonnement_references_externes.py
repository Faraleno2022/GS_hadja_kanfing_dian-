from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bus", "0005_abonnementbus_annee_scolaire_abonnementbus_cree_par_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="abonnementbus",
            name="reference_externe",
            field=models.CharField(
                blank=True,
                help_text="Numéro du reçu externe, transaction Mobile Money, chèque, etc.",
                max_length=100,
                verbose_name="Référence externe du paiement",
            ),
        ),
        migrations.AddField(
            model_name="abonnementcantine",
            name="reference_externe",
            field=models.CharField(
                blank=True,
                help_text="Numéro du reçu externe, transaction Mobile Money, chèque, etc.",
                max_length=100,
                verbose_name="Référence externe du paiement",
            ),
        ),
    ]
