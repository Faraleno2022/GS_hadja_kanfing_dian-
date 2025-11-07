"""
Script pour ajouter la permission de suppression définitive des enseignants au modèle Profil
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db import migrations, models

# Contenu de la migration à créer
migration_content = '''# Generated manually for teacher deletion permission

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utilisateurs', '0008_profil_peut_supprimer_abonnements'),
    ]

    operations = [
        migrations.AddField(
            model_name='profil',
            name='peut_supprimer_enseignants_definitivement',
            field=models.BooleanField(default=False, verbose_name='Peut supprimer les enseignants définitivement'),
        ),
    ]
'''

# Créer le fichier de migration
migration_file = 'utilisateurs/migrations/0009_profil_peut_supprimer_enseignants_definitivement.py'

with open(migration_file, 'w', encoding='utf-8') as f:
    f.write(migration_content)

print(f"✅ Migration créée: {migration_file}")
print("\nPour appliquer la migration:")
print("  python manage.py migrate")

# Ajouter aussi le champ directement dans le modèle
print("\n📝 N'oubliez pas d'ajouter le champ dans utilisateurs/models.py après ligne 43:")
print("""
    peut_supprimer_enseignants_definitivement = models.BooleanField(
        default=False, 
        verbose_name="Peut supprimer les enseignants définitivement"
    )
""")
