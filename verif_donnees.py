import sqlite3
import sys

SQLITE_DB = 'db.sqlite3'

def verifier_donnees():
    """Vérifie et affiche un résumé des données dans SQLite"""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("  VÉRIFICATION DES DONNÉES - École Hadja Kanfing Dian")
        print("=" * 60)
        print()
        
        # Récupérer toutes les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("❌ Aucune table trouvée dans la base de données!")
            return
        
        print(f"📋 {len(tables)} tables trouvées\n")
        
        # Statistiques globales
        total_records = 0
        table_stats = []
        
        # Pour chaque table, compter les enregistrements
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                total_records += count
                
                # Récupérer quelques infos sur les colonnes
                cursor.execute(f"PRAGMA table_info(`{table}`)")
                columns = cursor.fetchall()
                col_count = len(columns)
                
                table_stats.append({
                    'name': table,
                    'count': count,
                    'columns': col_count
                })
                
            except sqlite3.Error as e:
                print(f"⚠️  Erreur lecture table {table}: {e}")
        
        # Afficher les statistiques triées par nombre d'enregistrements
        table_stats.sort(key=lambda x: x['count'], reverse=True)
        
        print("📊 STATISTIQUES DES TABLES:")
        print("-" * 60)
        print(f"{'Table':<40} {'Enreg.':<10} {'Colonnes':<10}")
        print("-" * 60)
        
        # Tables importantes à mettre en évidence
        important_tables = ['eleve', 'paiement', 'bus', 'abonnement', 'enseignant', 'note']
        
        for stat in table_stats:
            table_name = stat['name']
            count = stat['count']
            cols = stat['columns']
            
            # Mettre en évidence les tables importantes
            marker = "⭐" if any(keyword in table_name.lower() for keyword in important_tables) else "  "
            
            if count > 0:
                print(f"{marker} {table_name:<38} {count:<10} {cols:<10}")
            else:
                print(f"   {table_name:<38} {'(vide)':<10} {cols:<10}")
        
        print("-" * 60)
        print(f"{'TOTAL':<40} {total_records:<10}")
        print("-" * 60)
        print()
        
        # Détails des tables importantes
        print("🔍 DÉTAILS DES TABLES PRINCIPALES:\n")
        
        # Élèves
        tables_eleves = [t for t in tables if 'eleve' in t.lower()]
        if tables_eleves:
            for table in tables_eleves:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"👨‍🎓 {table}: {count} élèves")
                    
                    # Afficher un exemple
                    cursor.execute(f"SELECT * FROM `{table}` LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        cursor.execute(f"PRAGMA table_info(`{table}`)")
                        columns = [col[1] for col in cursor.fetchall()]
                        print(f"   Colonnes: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
                    print()
        
        # Paiements
        tables_paiements = [t for t in tables if 'paiement' in t.lower() or 'payment' in t.lower()]
        if tables_paiements:
            for table in tables_paiements:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"💰 {table}: {count} paiements")
                    
                    # Total des montants si colonne montant existe
                    cursor.execute(f"PRAGMA table_info(`{table}`)")
                    columns = [col[1].lower() for col in cursor.fetchall()]
                    if 'montant' in columns or 'amount' in columns:
                        montant_col = 'montant' if 'montant' in columns else 'amount'
                        try:
                            cursor.execute(f"SELECT SUM(`{montant_col}`) FROM `{table}`")
                            total = cursor.fetchone()[0]
                            if total:
                                print(f"   Total: {total:,.2f} GNF")
                        except:
                            pass
                    print()
        
        # Abonnements bus
        tables_bus = [t for t in tables if 'bus' in t.lower() or 'abonnement' in t.lower()]
        if tables_bus:
            for table in tables_bus:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"🚌 {table}: {count} abonnements")
                    print()
        
        print("=" * 60)
        print("✅ Vérification terminée!")
        print("=" * 60)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Fichier {SQLITE_DB} non trouvé!")
        sys.exit(1)

if __name__ == "__main__":
    verifier_donnees()
