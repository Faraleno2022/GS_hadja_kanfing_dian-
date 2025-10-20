import sqlite3
import mysql.connector
from mysql.connector import Error
import sys

SQLITE_DB = 'db.sqlite3'

# Configuration PythonAnywhere
MYSQL_CONFIG = {
    'host': 'GSHadjaKanfingDiane.mysql.pythonanywhere-services.com',
    'user': 'GSHadjaKanfingDi',
    'password': 'FELIXSUZANELENO1994@',
    'database': 'GSHadjaKanfingDi$default',
    'port': 3306,
    'charset': 'utf8mb4',
    'use_unicode': True
}

def get_sqlite_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return [table[0] for table in cursor.fetchall()]

def get_table_schema(cursor, table_name):
    cursor.execute(f"PRAGMA table_info(`{table_name}`);")
    return cursor.fetchall()

def get_table_pk(cursor, table_name):
    cursor.execute(f"PRAGMA table_info(`{table_name}`);")
    cols = cursor.fetchall()
    return [col[1] for col in cols if col[5] > 0]

def sqlite_to_mysql_type(sqlite_type, col_name):
    sqlite_type = (sqlite_type or 'TEXT').upper()
    if 'CHAR' in sqlite_type or 'VARCHAR' in sqlite_type:
        return sqlite_type
    elif sqlite_type == 'INTEGER':
        return 'TINYINT(1)' if 'is_' in col_name.lower() else 'INT'
    elif sqlite_type == 'TEXT':
        return 'TEXT'
    elif sqlite_type in ('REAL', 'FLOAT'):
        return 'DOUBLE'
    elif 'DECIMAL' in sqlite_type:
        return 'DECIMAL(15,2)'
    elif sqlite_type == 'BLOB':
        return 'BLOB'
    elif sqlite_type == 'DATETIME':
        return 'DATETIME'
    elif sqlite_type == 'DATE':
        return 'DATE'
    elif sqlite_type in ('BOOL', 'BOOLEAN'):
        return 'TINYINT(1)'
    return 'TEXT'

def create_mysql_table(mysql_cursor, table_name, schema, pk_cols):
    columns = []
    for col in schema:
        col_name, col_type, not_null, default_value, is_pk = col[1], col[2] or 'TEXT', col[3], col[4], col[5]
        mysql_type = sqlite_to_mysql_type(col_type, col_name)
        col_def = f"`{col_name}` {mysql_type}"
        if is_pk and 'INT' in mysql_type:
            col_def += " AUTO_INCREMENT"
        if not_null and not is_pk:
            col_def += " NOT NULL"
        if default_value is not None and not is_pk:
            col_def += f" DEFAULT '{default_value}'" if isinstance(default_value, str) else f" DEFAULT {default_value}"
        columns.append(col_def)
    
    if pk_cols:
        columns.append(f"PRIMARY KEY ({', '.join([f'`{col}`' for col in pk_cols])})")
    
    create_query = f"CREATE TABLE `{table_name}` ({', '.join(columns)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    try:
        mysql_cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")
        mysql_cursor.execute(create_query)
        return True
    except Error as e:
        print(f"  ❌ {e}")
        return False

def migrate_table_data(sqlite_cursor, mysql_cursor, mysql_conn, table_name):
    try:
        sqlite_cursor.execute(f"SELECT * FROM `{table_name}`")
        rows = sqlite_cursor.fetchall()
        if not rows:
            print(f"  ℹ️  Vide")
            return True
        
        column_names = [d[0] for d in sqlite_cursor.description]
        placeholders = ', '.join(['%s'] * len(column_names))
        columns_str = ', '.join([f'`{col}`' for col in column_names])
        insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
        
        total = len(rows)
        for i in range(0, total, 500):
            batch = [tuple(val if val is not None else None for val in row) for row in rows[i:i+500]]
            mysql_cursor.executemany(insert_query, batch)
            mysql_conn.commit()
            if total > 100:
                print(f"  ⏳ {min(i+500, total)}/{total}...")
        
        print(f"  ✅ {total} lignes migrées")
        return True
    except Error as e:
        print(f"  ❌ {e}")
        mysql_conn.rollback()
        return False

def migrate_database():
    try:
        print("\n" + "="*70)
        print("  🔄 MIGRATION SQLite → MySQL (PythonAnywhere)")
        print("  École Hadja Kanfing Dian")
        print("="*70 + "\n")
        
        print("📂 Connexion à SQLite...")
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_cursor = sqlite_conn.cursor()
        print("✅ SQLite connecté\n")
        
        print("📊 Connexion à MySQL PythonAnywhere...")
        print(f"   Host: {MYSQL_CONFIG['host']}")
        print(f"   Database: {MYSQL_CONFIG['database']}")
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
        print("✅ MySQL connecté\n")
        
        tables = get_sqlite_tables(sqlite_cursor)
        print(f"📋 {len(tables)} tables à migrer\n")
        print("="*70 + "\n")
        
        success = 0
        errors = 0
        
        for idx, table in enumerate(tables, 1):
            print(f"[{idx}/{len(tables)}] 📦 {table}")
            schema = get_table_schema(sqlite_cursor, table)
            pk_cols = get_table_pk(sqlite_cursor, table)
            
            if create_mysql_table(mysql_cursor, table, schema, pk_cols):
                mysql_conn.commit()
                if migrate_table_data(sqlite_cursor, mysql_cursor, mysql_conn, table):
                    success += 1
                else:
                    errors += 1
            else:
                errors += 1
            print()
        
        print("="*70)
        print(f"✨ MIGRATION TERMINÉE!")
        print(f"✅ Tables réussies: {success}/{len(tables)}")
        if errors > 0:
            print(f"❌ Erreurs: {errors}")
        print("="*70 + "\n")
        
        # Vérification finale
        print("🔍 Vérification rapide des données migrées:\n")
        
        # Vérifier les élèves
        mysql_cursor.execute("SELECT COUNT(*) FROM eleves_eleve")
        count = mysql_cursor.fetchone()[0]
        print(f"👨‍🎓 Élèves: {count}")
        
        # Vérifier les paiements
        mysql_cursor.execute("SELECT COUNT(*) FROM paiements_paiement")
        count = mysql_cursor.fetchone()[0]
        print(f"💰 Paiements: {count}")
        
        # Vérifier les abonnements bus
        mysql_cursor.execute("SELECT COUNT(*) FROM bus_abonnementbus")
        count = mysql_cursor.fetchone()[0]
        print(f"🚌 Abonnements bus: {count}")
        
        print("\n" + "="*70)
        
        sqlite_conn.close()
        mysql_conn.close()
        
    except Error as e:
        print(f"\n❌ Erreur MySQL: {e}")
        print("\nVérifiez:")
        print("  - Que vous êtes connecté à Internet")
        print("  - Que les credentials sont corrects")
        print("  - Que la base MySQL existe sur PythonAnywhere")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ATTENTION: Cette opération va:")
    print("  1. Se connecter à votre base MySQL sur PythonAnywhere")
    print("  2. SUPPRIMER toutes les tables existantes")
    print("  3. Créer de nouvelles tables")
    print("  4. Migrer toutes vos données depuis SQLite")
    print("="*70)
    
    response = input("\n❓ Voulez-vous continuer? (oui/non): ")
    if response.lower() in ['oui', 'o', 'yes', 'y']:
        migrate_database()
        print("\n✅ Vous pouvez maintenant configurer Django pour utiliser MySQL!")
    else:
        print("\n❌ Migration annulée")
