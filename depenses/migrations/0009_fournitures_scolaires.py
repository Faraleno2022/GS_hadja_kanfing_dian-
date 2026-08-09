import uuid
from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('eleves', '0016_ecole_bonus_suivi_actif'),
        ('depenses', '0008_simplify_logistics_and_paper_contributions'),
    ]

    operations = [
        migrations.CreateModel(
            name='FournitureScolaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('sync_created_at', models.DateTimeField(auto_now_add=True)),
                ('sync_updated_at', models.DateTimeField(auto_now=True)),
                ('sync_deleted_at', models.DateTimeField(blank=True, null=True)),
                ('sync_version', models.PositiveIntegerField(default=1)),
                ('is_synced', models.BooleanField(db_index=True, default=False)),
                ('reference', models.CharField(blank=True, help_text='Laissez vide pour générer une référence automatiquement.', max_length=50, verbose_name='Référence')),
                ('nom', models.CharField(max_length=200, verbose_name='Produit')),
                ('categorie', models.CharField(choices=[('CAHIER_PAPIER', 'Cahiers et papier'), ('ECRITURE', 'Stylos et écriture'), ('MANUEL', 'Manuels et livres'), ('GEOMETRIE', 'Géométrie et dessin'), ('SAC', 'Sacs et cartables'), ('UNIFORME', 'Uniformes'), ('ACCESSOIRE', 'Accessoires scolaires'), ('AUTRE', 'Autre')], default='AUTRE', max_length=30, verbose_name='Catégorie')),
                ('unite', models.CharField(choices=[('PIECE', 'Pièce'), ('PAQUET', 'Paquet'), ('BOITE', 'Boîte'), ('DOUZAINE', 'Douzaine'), ('CARTON', 'Carton')], default='PIECE', max_length=20, verbose_name='Unité')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('quantite_stock', models.PositiveIntegerField(default=0, verbose_name='Quantité mise en stock')),
                ('stock_minimum', models.PositiveIntegerField(default=0, verbose_name='Seuil d’alerte')),
                ('prix_achat_unitaire', models.DecimalField(decimal_places=0, default=Decimal('0'), max_digits=15, verbose_name="Prix d'achat unitaire (GNF)")),
                ('prix_vente_unitaire', models.DecimalField(decimal_places=0, default=Decimal('0'), max_digits=15, verbose_name='Prix de vente unitaire (GNF)')),
                ('actif', models.BooleanField(default=True, verbose_name='Actif')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('cree_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fournitures_scolaires_creees', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('ecole', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fournitures_scolaires', to='eleves.ecole', verbose_name='Établissement')),
            ],
            options={
                'verbose_name': 'Fourniture scolaire',
                'verbose_name_plural': 'Fournitures scolaires',
                'ordering': ['nom', 'reference'],
                'indexes': [
                    models.Index(fields=['ecole', 'actif'], name='dep_four_ecole_actif_idx'),
                    models.Index(fields=['ecole', 'nom'], name='dep_four_ecole_nom_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('ecole', 'reference'), name='uniq_fourniture_ref_ecole'),
                ],
            },
        ),
        migrations.CreateModel(
            name='VenteFourniture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('sync_created_at', models.DateTimeField(auto_now_add=True)),
                ('sync_updated_at', models.DateTimeField(auto_now=True)),
                ('sync_deleted_at', models.DateTimeField(blank=True, null=True)),
                ('sync_version', models.PositiveIntegerField(default=1)),
                ('is_synced', models.BooleanField(db_index=True, default=False)),
                ('numero_vente', models.CharField(blank=True, max_length=30, unique=True, verbose_name='N° vente')),
                ('quantite', models.PositiveIntegerField(verbose_name='Quantité vendue')),
                ('prix_vente_unitaire', models.DecimalField(decimal_places=0, max_digits=15, verbose_name='Prix de vente unitaire (GNF)')),
                ('montant_total', models.DecimalField(decimal_places=0, default=Decimal('0'), editable=False, max_digits=18, verbose_name='Montant total (GNF)')),
                ('client', models.CharField(blank=True, max_length=200, verbose_name='Client / Acheteur')),
                ('date_vente', models.DateField(default=django.utils.timezone.localdate, verbose_name='Date de vente')),
                ('observations', models.TextField(blank=True, verbose_name='Observations')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('date_modification', models.DateTimeField(auto_now=True)),
                ('cree_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ventes_fournitures_creees', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('ecole', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ventes_fournitures', to='eleves.ecole', verbose_name='Établissement')),
                ('produit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ventes', to='depenses.fourniturescolaire', verbose_name='Produit')),
            ],
            options={
                'verbose_name': 'Vente de fourniture',
                'verbose_name_plural': 'Ventes de fournitures',
                'ordering': ['-date_vente', '-date_creation'],
                'indexes': [
                    models.Index(fields=['ecole', 'date_vente'], name='dep_vente_ecole_date_idx'),
                    models.Index(fields=['produit', 'date_vente'], name='dep_vente_prod_date_idx'),
                ],
            },
        ),
    ]
