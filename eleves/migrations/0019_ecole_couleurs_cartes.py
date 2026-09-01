from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0018_eleve_evaluation_accueil_effectuee'),
    ]

    operations = [
        migrations.AddField(
            model_name='ecole',
            name='couleur_carte_bus',
            field=models.CharField(
                default='#2563EB',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        '^#[0-9A-Fa-f]{6}$',
                        'Utilisez une couleur hexadécimale au format #RRGGBB.',
                    ),
                ],
                verbose_name='Couleur de la carte bus',
            ),
        ),
        migrations.AddField(
            model_name='ecole',
            name='couleur_carte_cantine',
            field=models.CharField(
                default='#B45309',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        '^#[0-9A-Fa-f]{6}$',
                        'Utilisez une couleur hexadécimale au format #RRGGBB.',
                    ),
                ],
                verbose_name='Couleur de la carte cantine',
            ),
        ),
        migrations.AddField(
            model_name='ecole',
            name='couleur_carte_retrait',
            field=models.CharField(
                default='#0F766E',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        '^#[0-9A-Fa-f]{6}$',
                        'Utilisez une couleur hexadécimale au format #RRGGBB.',
                    ),
                ],
                verbose_name='Couleur de la carte de retrait',
            ),
        ),
        migrations.AddField(
            model_name='ecole',
            name='couleur_carte_scolaire',
            field=models.CharField(
                default='#1746A2',
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        '^#[0-9A-Fa-f]{6}$',
                        'Utilisez une couleur hexadécimale au format #RRGGBB.',
                    ),
                ],
                verbose_name='Couleur de la carte scolaire',
            ),
        ),
    ]
