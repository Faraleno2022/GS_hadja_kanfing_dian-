import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def _colonnes(schema_editor, model):
    with schema_editor.connection.cursor() as cursor:
        return {
            colonne.name
            for colonne in schema_editor.connection.introspection.get_table_description(
                cursor,
                model._meta.db_table,
            )
        }


def _retirer_champ(apps, schema_editor, model_name, field_name):
    model = apps.get_model('depenses', model_name)
    if field_name in _colonnes(schema_editor, model):
        schema_editor.remove_field(model, model._meta.get_field(field_name))


def retirer_ecole_cuisine(apps, schema_editor):
    _retirer_champ(apps, schema_editor, 'DepenseCuisine', 'ecole')


def retirer_ecole_document(apps, schema_editor):
    _retirer_champ(apps, schema_editor, 'DepenseDocument', 'ecole')


def retirer_ecole_versement(apps, schema_editor):
    _retirer_champ(apps, schema_editor, 'Versement', 'ecole')


def _ajouter_date_modification(apps, schema_editor, model_name):
    model = apps.get_model('depenses', model_name)
    if 'date_modification' in _colonnes(schema_editor, model):
        return
    champ = models.DateTimeField(default=django.utils.timezone.now)
    champ.set_attributes_from_name('date_modification')
    champ.model = model
    schema_editor.add_field(model, champ)


def ajouter_date_modification_cuisine(apps, schema_editor):
    _ajouter_date_modification(apps, schema_editor, 'DepenseCuisine')


def ajouter_date_modification_document(apps, schema_editor):
    _ajouter_date_modification(apps, schema_editor, 'DepenseDocument')


def ajouter_date_modification_versement(apps, schema_editor):
    _ajouter_date_modification(apps, schema_editor, 'Versement')


def renommer_date_creation_abonnement(apps, schema_editor):
    model = apps.get_model('depenses', 'AbonnementInformatique')
    colonnes = _colonnes(schema_editor, model)
    if 'created_at' in colonnes or 'date_creation' not in colonnes:
        return
    ancien = model._meta.get_field('date_creation')
    nouveau = models.DateTimeField(auto_now_add=True)
    nouveau.set_attributes_from_name('created_at')
    nouveau.model = model
    schema_editor.alter_field(model, ancien, nouveau)


def retirer_date_abonnement(apps, schema_editor):
    _retirer_champ(apps, schema_editor, 'AbonnementInformatique', 'date')


def ajouter_updated_at_abonnement(apps, schema_editor):
    model = apps.get_model('depenses', 'AbonnementInformatique')
    if 'updated_at' in _colonnes(schema_editor, model):
        return
    champ = models.DateTimeField(default=django.utils.timezone.now)
    champ.set_attributes_from_name('updated_at')
    champ.model = model
    schema_editor.add_field(model, champ)


def ajouter_indexes_abonnement(apps, schema_editor):
    model = apps.get_model('depenses', 'AbonnementInformatique')
    with schema_editor.connection.cursor() as cursor:
        contraintes = schema_editor.connection.introspection.get_constraints(
            cursor,
            model._meta.db_table,
        )
    for index in (
        models.Index(fields=['eleve', 'statut'], name='depenses_ab_eleve_i_6e0175_idx'),
        models.Index(fields=['eleve', 'date_fin'], name='depenses_ab_eleve_i_0b66f5_idx'),
        models.Index(fields=['statut', 'date_fin'], name='depenses_ab_statut_95113d_idx'),
    ):
        if index.name not in contraintes:
            schema_editor.add_index(model, index)


class Migration(migrations.Migration):

    dependencies = [
        ('depenses', '0011_merge_20260829_0740'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(retirer_ecole_cuisine, migrations.RunPython.noop)],
            state_operations=[migrations.RemoveField(model_name='depensecuisine', name='ecole')],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ajouter_date_modification_cuisine, migrations.RunPython.noop)],
            state_operations=[
                migrations.AddField(
                    model_name='depensecuisine',
                    name='date_modification',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(retirer_ecole_document, migrations.RunPython.noop)],
            state_operations=[migrations.RemoveField(model_name='depensedocument', name='ecole')],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ajouter_date_modification_document, migrations.RunPython.noop)],
            state_operations=[
                migrations.AddField(
                    model_name='depensedocument',
                    name='date_modification',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(retirer_ecole_versement, migrations.RunPython.noop)],
            state_operations=[migrations.RemoveField(model_name='versement', name='ecole')],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ajouter_date_modification_versement, migrations.RunPython.noop)],
            state_operations=[
                migrations.AddField(
                    model_name='versement',
                    name='date_modification',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(renommer_date_creation_abonnement, migrations.RunPython.noop)],
            state_operations=[
                migrations.RenameField(
                    model_name='abonnementinformatique',
                    old_name='date_creation',
                    new_name='created_at',
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(retirer_date_abonnement, migrations.RunPython.noop)],
            state_operations=[migrations.RemoveField(model_name='abonnementinformatique', name='date')],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ajouter_updated_at_abonnement, migrations.RunPython.noop)],
            state_operations=[
                migrations.AddField(
                    model_name='abonnementinformatique',
                    name='updated_at',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
        ),
        migrations.AlterModelOptions(
            name='depensecuisine',
            options={
                'ordering': ['-date', '-date_creation'],
                'verbose_name': 'Dépense cuisine',
                'verbose_name_plural': 'Dépenses cuisine',
            },
        ),
        migrations.AlterModelOptions(
            name='depensedocument',
            options={
                'ordering': ['-date', '-date_creation'],
                'verbose_name': 'Dépense document',
                'verbose_name_plural': 'Dépenses document',
            },
        ),
        migrations.AlterModelOptions(
            name='versement',
            options={
                'ordering': ['-date', '-date_creation'],
                'verbose_name': 'Versement',
                'verbose_name_plural': 'Versements',
            },
        ),
        migrations.AlterModelOptions(
            name='abonnementinformatique',
            options={
                'ordering': ['-updated_at'],
                'verbose_name': 'Abonnement informatique',
                'verbose_name_plural': 'Abonnements informatique',
            },
        ),
        migrations.AlterField(
            model_name='depensecuisine',
            name='date',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Date'),
        ),
        migrations.AlterField(
            model_name='depensecuisine',
            name='cree_par',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='depenses_cuisine_creees', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='depensedocument',
            name='date',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Date'),
        ),
        migrations.AlterField(
            model_name='depensedocument',
            name='cree_par',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='depenses_document_creees', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='versement',
            name='date',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Date'),
        ),
        migrations.AlterField(
            model_name='versement',
            name='cree_par',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='versements_crees', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='abonnementinformatique',
            name='eleve',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='abonnements_informatique', to='eleves.eleve'),
        ),
        migrations.AlterField(
            model_name='abonnementinformatique',
            name='montant',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name="Montant d'abonnement (GNF)"),
        ),
        migrations.AlterField(
            model_name='abonnementinformatique',
            name='date_debut',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Date de début'),
        ),
        migrations.AlterField(
            model_name='abonnementinformatique',
            name='statut',
            field=models.CharField(choices=[('ACTIF', 'Actif'), ('EXPIRE', 'Expiré'), ('SUSPENDU', 'Suspendu')], db_index=True, default='ACTIF', max_length=10),
        ),
        migrations.AlterField(
            model_name='abonnementinformatique',
            name='cree_par',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='abonnements_informatique_crees', to=settings.AUTH_USER_MODEL),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(ajouter_indexes_abonnement, migrations.RunPython.noop)],
            state_operations=[
                migrations.AddIndex(
                    model_name='abonnementinformatique',
                    index=models.Index(fields=['eleve', 'statut'], name='depenses_ab_eleve_i_6e0175_idx'),
                ),
                migrations.AddIndex(
                    model_name='abonnementinformatique',
                    index=models.Index(fields=['eleve', 'date_fin'], name='depenses_ab_eleve_i_0b66f5_idx'),
                ),
                migrations.AddIndex(
                    model_name='abonnementinformatique',
                    index=models.Index(fields=['statut', 'date_fin'], name='depenses_ab_statut_95113d_idx'),
                ),
            ],
        ),
    ]
