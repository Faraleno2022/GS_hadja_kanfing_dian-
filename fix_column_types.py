import mysql.connector

conn = mysql.connector.connect(
    host='GSHadjaKanfingDiane.mysql.pythonanywhere-services.com',
    user='GSHadjaKanfingDi',
    password='FELIXSUZANELENO1994@',
    database='GSHadjaKanfingDi$default',
    port=3306
)
cursor = conn.cursor()

print("🔧 Correction des types de colonnes...\n")

# Désactiver les contraintes
cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

# 1. Convertir classe_id de LONGTEXT à INT
print("1️⃣ Correction de classe_id...")
try:
    cursor.execute("""
        ALTER TABLE eleves_eleve 
        MODIFY COLUMN classe_id INT NULL
    """)
    conn.commit()
    print("   ✅ classe_id converti en INT\n")
except Exception as e:
    print(f"   ⚠️  {e}\n")

# 2. Convertir responsable_principal_id
print("2️⃣ Correction de responsable_principal_id...")
try:
    cursor.execute("""
        ALTER TABLE eleves_eleve 
        MODIFY COLUMN responsable_principal_id INT NULL
    """)
    conn.commit()
    print("   ✅ responsable_principal_id converti en INT\n")
except Exception as e:
    print(f"   ⚠️  {e}\n")

# 3. Convertir responsable_secondaire_id
print("3️⃣ Correction de responsable_secondaire_id...")
try:
    cursor.execute("""
        ALTER TABLE eleves_eleve 
        MODIFY COLUMN responsable_secondaire_id INT NULL
    """)
    conn.commit()
    print("   ✅ responsable_secondaire_id converti en INT\n")
except Exception as e:
    print(f"   ⚠️  {e}\n")

# Réactiver les contraintes
cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

# Vérification
cursor.execute("DESCRIBE eleves_eleve")
print("📊 Structure corrigée:")
for col in cursor.fetchall():
    if 'id' in col[0]:
        print(f"   {col[0]:<30} {col[1]}")

print("\n✅ Correction terminée!")

conn.close()
