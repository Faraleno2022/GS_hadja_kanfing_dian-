"""Script pour vérifier que la table notes_classenote existe"""
import sqlite3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.conf import settings

db_path = settings.DATABASES['default']['NAME']
print(f"📂 Base de données: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Vérifier si la table existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes_classenote'")
result = cursor.fetchone()

if result:
    print("✅ Table 'notes_classenote' existe!")
    
    # Afficher la structure de la table
    cursor.execute("PRAGMA table_info(notes_classenote)")
    columns = cursor.fetchall()
    print("\n📋 Structure de la table:")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")
    
    # Compter les enregistrements
    cursor.execute("SELECT COUNT(*) FROM notes_classenote")
    count = cursor.fetchone()[0]
    print(f"\n📊 Nombre d'enregistrements: {count}")
else:
    print("❌ Table 'notes_classenote' n'existe PAS!")

conn.close()
