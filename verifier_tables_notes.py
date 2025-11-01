"""Script pour vérifier les tables notes existantes"""
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

# Chercher toutes les tables commençant par "notes_"
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'notes_%' ORDER BY name")
tables = cursor.fetchall()

if tables:
    print("📋 Tables 'notes_' existantes:")
    for table in tables:
        table_name = table[0]
        print(f"\n✓ {table_name}")
        
        # Compter les enregistrements
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  → {count} enregistrement(s)")
else:
    print("❌ Aucune table 'notes_' trouvée")

conn.close()
