"""
Script pour supprimer les tables liées au module notes de la base de données.
À exécuter après avoir retiré l'application 'notes' de INSTALLED_APPS.
"""
import os
import django
import sqlite3

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.conf import settings

def supprimer_tables_notes():
    """Supprime toutes les tables liées au module notes."""
    db_path = settings.DATABASES['default']['NAME']
    
    print(f"📂 Connexion à la base de données: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Liste des tables à supprimer
    tables_notes = [
        'notes_note',
        'notes_evaluation',
        'notes_matiereclasse',
        'notes_seuilappreciation',
        'notes_baremeappreciation',
        'notes_baremematiere',
    ]
    
    print("\n🗑️  Suppression des tables du module notes...")
    
    for table in tables_notes:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"   ✅ Table '{table}' supprimée")
        except Exception as e:
            print(f"   ⚠️  Erreur lors de la suppression de '{table}': {e}")
    
    # Supprimer les migrations du module notes
    try:
        cursor.execute("DELETE FROM django_migrations WHERE app = 'notes'")
        print(f"\n✅ Migrations du module 'notes' supprimées de django_migrations")
    except Exception as e:
        print(f"⚠️  Erreur lors de la suppression des migrations: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Suppression terminée avec succès!")
    print("\n📝 Prochaines étapes:")
    print("   1. Vérifier que l'application fonctionne correctement")
    print("   2. Faire un backup de la base de données si nécessaire")

if __name__ == '__main__':
    response = input("⚠️  Voulez-vous vraiment supprimer toutes les tables du module notes? (oui/non): ")
    if response.lower() in ['oui', 'o', 'yes', 'y']:
        supprimer_tables_notes()
    else:
        print("❌ Opération annulée")
