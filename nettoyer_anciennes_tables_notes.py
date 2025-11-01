"""Script pour nettoyer les anciennes tables notes et créer les nouvelles"""
import sqlite3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.conf import settings

db_path = settings.DATABASES['default']['NAME']
print(f"📂 Base de données: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tables à supprimer (anciennes)
anciennes_tables = [
    'notes_baremeappreciation',
    'notes_baremematiere',
    'notes_matiereclasse',
    'notes_note',
    'notes_seuilappreciation'
]

print("🗑️  Suppression des anciennes tables...\n")
for table in anciennes_tables:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"✓ Supprimé: {table}")
    except Exception as e:
        print(f"✗ Erreur sur {table}: {e}")

conn.commit()

# Vérifier les tables restantes
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'notes_%' ORDER BY name")
tables_restantes = cursor.fetchall()

print(f"\n📋 Tables 'notes_' restantes:")
for table in tables_restantes:
    print(f"  ✓ {table[0]}")

conn.close()
print("\n✅ Nettoyage terminé!")
