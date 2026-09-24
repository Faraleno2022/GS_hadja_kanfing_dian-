from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('eleves', '0020_eleve_test_accueil_evalue')]

    operations = [
        migrations.AddField(
            model_name='eleve', name='import_verrouille',
            field=models.BooleanField(
                db_index=True, default=False, editable=False,
                verbose_name="Import verrouillé jusqu'au premier paiement validé",
            ),
        ),
        migrations.AlterField(
            model_name='eleve', name='statut',
            field=models.CharField(
                choices=[('ACTIF', 'Actif'), ('ATTENTE_PAIEMENT', 'Verrouillé — premier paiement attendu'),
                         ('SUSPENDU', 'Suspendu'), ('EXCLU', 'Exclu'),
                         ('TRANSFERE', 'Transféré'), ('DIPLOME', 'Diplômé')],
                db_index=True, default='ACTIF', max_length=20, verbose_name='Statut',
            ),
        ),
    ]
