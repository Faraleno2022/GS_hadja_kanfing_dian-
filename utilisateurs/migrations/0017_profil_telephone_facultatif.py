from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('utilisateurs', '0016_reparer_comptes_principaux_ecoles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profil',
            name='telephone',
            field=models.CharField(
                blank=True,
                max_length=20,
                validators=[RegexValidator(r'^\+224\d{8,9}$', 'Format: +224XXXXXXXXX')],
                verbose_name='Téléphone',
            ),
        ),
    ]
