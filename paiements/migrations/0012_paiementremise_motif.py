from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0011_paiementremise_portee_tranches'),
    ]

    operations = [
        migrations.AddField(
            model_name='paiementremise',
            name='motif',
            field=models.CharField(
                blank=True,
                choices=[
                    ('CLIENT_FIDELE', 'Client fidèle'),
                    ('PROMOTION', 'Promotion'),
                    ('ERREUR_COMMERCIALE', 'Erreur commerciale'),
                    ('PARTENAIRE', 'Partenaire'),
                    ('GESTE_COMMERCIAL', 'Geste commercial'),
                    ('NE_PAIE_RIEN', 'Ne paie rien'),
                    ('LA_MOITIE', 'La moitié'),
                ],
                default='',
                max_length=30,
                verbose_name='Motif de la remise',
            ),
        ),
    ]
