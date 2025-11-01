"""Script pour recréer toutes les tables notes proprement"""
import sqlite3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.conf import settings
from django.core.management import call_command

db_path = settings.DATABASES['default']['NAME']
print(f"📂 Base de données: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Supprimer TOUTES les tables notes_
print("🗑️  Suppression de toutes les tables notes_...\n")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'notes_%'")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        print(f"✓ Supprimé: {table_name}")
    except Exception as e:
        print(f"✗ Erreur sur {table_name}: {e}")

conn.commit()
conn.close()

print("\n🔨 Recréation des tables...")

# Annuler toutes les migrations notes
try:
    call_command('migrate', 'notes', 'zero', '--fake')
    print("✓ Migrations notes annulées (fake)")
except Exception as e:
    print(f"⚠️  Avertissement: {e}")

# Appliquer toutes les migrations
try:
    call_command('migrate', 'notes')
    print("✓ Migrations notes appliquées")
    print("\n✅ Tables recréées avec succès!")
except Exception as e:
    print(f"\n❌ Erreur: {e}")

# Vérifier le résultat
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'notes_%' ORDER BY name")
tables_finales = cursor.fetchall()

print(f"\n📋 Tables 'notes_' finales:")
for table in tables_finales:
    print(f"  ✓ {table[0]}")

conn.close()
