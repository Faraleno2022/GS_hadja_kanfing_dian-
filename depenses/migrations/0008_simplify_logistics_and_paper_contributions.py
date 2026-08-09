import uuid
from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def rattacher_anciens_biens(apps, schema_editor):
    BienEtablissement = apps.get_model('depenses', 'BienEtablissement')
    Profil = apps.get_model('utilisateurs', 'Profil')

    ecoles_par_utilisateur = dict(
        Profil.objects.exclude(ecole_id=None).values_list('user_id', 'ecole_id')
    )
    for bien in BienEtablissement.objects.all().iterator():
        champs_modifies = []
        if not bien.ecole_id and bien.cree_par_id:
            ecole_id = ecoles_par_utilisateur.get(bien.cree_par_id)
            if ecole_id:
                bien.ecole_id = ecole_id
                champs_modifies.append('ecole')

        # Un ancien bien représentait une unité. Sa valeur totale historique
        # devient donc son prix d'achat unitaire sans modifier cette valeur.
        if bien.valeur_acquisition and not bien.prix_achat_unitaire:
            bien.prix_achat_unitaire = bien.valeur_acquisition
            champs_modifies.append('prix_achat_unitaire')

        if champs_modifies:
            bien.save(update_fields=champs_modifies)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('eleves', '0016_ecole_bonus_suivi_actif'),
        ('utilisateurs', '0014_profil_lecture_seule'),
        ('depenses', '0007_logistique_bibliotheque_sync_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='bienetablissement',
            name='ecole',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='biens_etablissement',
                to='eleves.ecole',
                verbose_name='Établissement',
            ),
        ),
        migrations.AddField(
            model_name='bienetablissement',
            name='marque',
            field=models.CharField(blank=True, max_length=100, verbose_name='Marque'),
        ),
        migrations.AddField(
            model_name='bienetablissement',
            name='prix_achat_unitaire',
            field=models.DecimalField(
                decimal_places=0,
                default=Decimal('0'),
                max_digits=15,
                verbose_name="Prix d'achat unitaire (GNF)",
            ),
        ),
        migrations.AddField(
            model_name='bienetablissement',
            name='quantite_achetee',
            field=models.PositiveIntegerField(default=1, verbose_name='Quantité achetée'),
        ),
        migrations.AddField(
            model_name='bienetablissement',
            name='quantite_endommagee',
            field=models.PositiveIntegerField(default=0, verbose_name='Quantité gâtée/perdue'),
        ),
        migrations.AddField(
            model_name='bienetablissement',
            name='quantite_utilisee',
            field=models.PositiveIntegerField(default=0, verbose_name='Quantité utilisée'),
        ),
        migrations.AlterField(
            model_name='bienetablissement',
            name='type_bien',
            field=models.CharField(
                choices=[
                    ('SALLE_CLASSE', 'Salle de classe'),
                    ('BUREAU', 'Bureau'),
                    ('LABORATOIRE', 'Laboratoire'),
                    ('BIBLIOTHEQUE', 'Bibliothèque'),
                    ('TOILETTE', 'Toilette'),
                    ('CANTINE', 'Cantine'),
                    ('TERRAIN_SPORT', 'Terrain de sport'),
                    ('COUR', 'Cour'),
                    ('PARKING', 'Parking'),
                    ('TABLE', 'Table(s)'),
                    ('CHAISE', 'Chaise(s)'),
                    ('ARMOIRE', 'Armoire'),
                    ('ETAGERE', 'Étagère'),
                    ('CLIMATISEUR', 'Climatiseur'),
                    ('ORDINATEUR', 'Ordinateur'),
                    ('IMPRIMANTE', 'Imprimante'),
                    ('PROJECTEUR', 'Projecteur'),
                    ('TABLEAU', 'Tableau'),
                    ('GLOBE_TERRESTRE', 'Globe terrestre'),
                    ('CARTE', 'Carte géographique'),
                    ('COMPAS', 'Compas'),
                    ('EQUERRE', 'Équerre'),
                    ('AMPOULE', 'Ampoule(s)'),
                    ('VENTILATEUR', 'Ventilateur'),
                    ('FOURNITURE', 'Fourniture'),
                    ('MARQUEUR', 'Marqueur(s)'),
                    ('AUTRE', 'Autre'),
                ],
                max_length=20,
                verbose_name='Type de bien',
            ),
        ),
        migrations.RunPython(rattacher_anciens_biens, migrations.RunPython.noop),
        migrations.CreateModel(
            name='ContributionRamePapier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('sync_created_at', models.DateTimeField(auto_now_add=True)),
                ('sync_updated_at', models.DateTimeField(auto_now=True)),
                ('sync_deleted_at', models.DateTimeField(blank=True, null=True)),
                ('sync_version', models.PositiveIntegerField(default=1)),
                ('is_synced', models.BooleanField(db_index=True, default=False)),
                ('annee_scolaire', models.CharField(max_length=9, verbose_name='Année scolaire')),
                ('mode_contribution', models.CharField(choices=[('RAMES', 'Rames de papier'), ('ARGENT', 'Paiement en argent'), ('MIXTE', 'Rames et argent')], max_length=10, verbose_name='Mode de contribution')),
                ('nombre_paquets', models.PositiveIntegerField(default=0, verbose_name='Nombre de paquets/rames')),
                ('montant_paye', models.DecimalField(decimal_places=0, default=Decimal('0'), max_digits=12, verbose_name='Montant payé (GNF)')),
                ('date_contribution', models.DateField(default=django.utils.timezone.localdate, verbose_name='Date de contribution')),
                ('observations', models.TextField(blank=True, verbose_name='Observations')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('cree_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contributions_rames_creees', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('ecole', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contributions_rames', to='eleves.ecole', verbose_name='Établissement')),
                ('eleve', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributions_rames', to='eleves.eleve', verbose_name='Élève')),
            ],
            options={
                'verbose_name': 'Contribution en rames de papier',
                'verbose_name_plural': 'Contributions en rames de papier',
                'ordering': ['-date_contribution', '-date_creation'],
                'indexes': [
                    models.Index(fields=['ecole', 'date_contribution'], name='dep_contr_ecole_date_idx'),
                    models.Index(fields=['eleve', 'date_contribution'], name='dep_contr_eleve_date_idx'),
                    models.Index(fields=['annee_scolaire'], name='dep_contr_annee_idx'),
                ],
            },
        ),
    ]
