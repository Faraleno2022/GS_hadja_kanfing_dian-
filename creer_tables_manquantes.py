"""Script pour créer les tables manquantes"""
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

# Vérifier les tables nécessaires
tables_necessaires = ['notes_classenote', 'notes_matierenote', 'notes_evaluation', 'notes_noteeleve']

print("🔍 Vérification des tables...\n")
for table in tables_necessaires:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    result = cursor.fetchone()
    if result:
        print(f"✓ {table} existe")
    else:
        print(f"✗ {table} MANQUANTE")

conn.close()

# Créer les tables manquantes
print("\n🔨 Création des tables manquantes...")
try:
    # Annuler la migration fake
    call_command('migrate', 'notes', '0001', '--fake')
    print("✓ Migration 0001 fake")
    
    # Appliquer la migration 0002 réellement
    call_command('migrate', 'notes', '0002')
    print("✓ Migration 0002 appliquée")
    
    print("\n✅ Tables créées avec succès!")
except Exception as e:
    print(f"\n❌ Erreur: {e}")
