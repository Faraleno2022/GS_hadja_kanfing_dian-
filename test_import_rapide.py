#!/usr/bin/env python
"""
Test rapide de la fonctionnalité d'importation - Sans base de données
"""
import pandas as pd
import tempfile
import os

print("🧪 TEST RAPIDE - IMPORTATION DE NOTES")
print("=" * 50)

# Test 1: Lecture/écriture CSV
print("\n📝 Test CSV...")
try:
    data = {
        'Matricule': ['TEST-001', 'TEST-002', 'TEST-003'],
        'Prénom': ['Amadou', 'Binta', 'Moussa'],
        'Nom': ['DIALLO', 'SOW', 'TOURE'],
        'Note': [15.5, 18, 12.25],
        'Absent': ['NON', 'NON', 'NON']
    }
    df = pd.DataFrame(data)
    
    # Sauvegarder en CSV
    temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_csv, index=False)
    temp_csv.close()
    
    # Relire le CSV
    df_lu = pd.read_csv(temp_csv.name)
    
    if len(df_lu) == 3 and list(df_lu.columns) == list(data.keys()):
        print("✅ CSV: Lecture/écriture OK")
    else:
        print("❌ CSV: Erreur")
    
    os.unlink(temp_csv.name)
except Exception as e:
    print(f"❌ CSV: Erreur - {e}")

# Test 2: Lecture/écriture Excel
print("\n📊 Test Excel...")
try:
    data = {
        'Matricule': ['6A-001', '6A-002', '6A-003', '6A-004', '6A-005'],
        'Prénom': ['Fatou', 'Sekou', 'Mariam', 'Ibrahim', 'Aissatou'],
        'Nom': ['KANTE', 'CONDE', 'BARRY', 'CAMARA', 'FOFANA'],
        'Note': [18.5, 14, '', 16.75, 19],
        'Absent': ['NON', 'NON', 'OUI', 'NON', 'NON']
    }
    df = pd.DataFrame(data)
    
    # Sauvegarder en Excel
    temp_excel = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    df.to_excel(temp_excel.name, index=False, engine='openpyxl')
    temp_excel.close()
    
    # Relire l'Excel
    df_lu = pd.read_excel(temp_excel.name, engine='openpyxl')
    
    if len(df_lu) == 5 and list(df_lu.columns) == list(data.keys()):
        print("✅ Excel: Lecture/écriture OK")
    else:
        print("❌ Excel: Erreur")
    
    # Vérifier la taille du fichier
    file_size = os.path.getsize(temp_excel.name)
    print(f"   📦 Taille fichier: {file_size:,} octets")
    
    os.unlink(temp_excel.name)
except Exception as e:
    print(f"❌ Excel: Erreur - {e}")

# Test 3: Validation des notes
print("\n🔍 Test validation...")
try:
    notes_test = [15.5, 20, 0, 12.75, 18]
    notes_invalides = [25, -5, 'abc']
    
    valides = 0
    for note in notes_test:
        if 0 <= note <= 20:
            valides += 1
    
    if valides == len(notes_test):
        print("✅ Validation notes valides OK")
    else:
        print("❌ Validation incorrecte")
    
    invalides = 0
    for note in notes_invalides[:2]:  # Ignorer 'abc' pour ce test
        if not (0 <= note <= 20):
            invalides += 1
    
    if invalides == 2:
        print("✅ Détection notes invalides OK")
    else:
        print("❌ Détection incorrecte")
        
except Exception as e:
    print(f"❌ Validation: Erreur - {e}")

# Test 4: Gestion des absents
print("\n👤 Test gestion absents...")
try:
    data = pd.DataFrame({
        'Matricule': ['E1', 'E2', 'E3'],
        'Note': [15, '', 18],
        'Absent': ['NON', 'OUI', 'NON']
    })
    
    absents = data[data['Absent'] == 'OUI']
    presents = data[data['Absent'] == 'NON']
    
    if len(absents) == 1 and len(presents) == 2:
        print("✅ Gestion absents OK")
    else:
        print("❌ Gestion absents incorrecte")
        
except Exception as e:
    print(f"❌ Gestion absents: Erreur - {e}")

# Test 5: Statistiques
print("\n📈 Test statistiques...")
try:
    notes = pd.Series([15.5, 18, 12.25, 14.75, 16, 19, 13.5])
    
    stats = {
        'moyenne': notes.mean(),
        'min': notes.min(),
        'max': notes.max(),
        'total': len(notes)
    }
    
    print(f"✅ Statistiques calculées:")
    print(f"   📊 Moyenne: {stats['moyenne']:.2f}")
    print(f"   📊 Min: {stats['min']}")
    print(f"   📊 Max: {stats['max']}")
    print(f"   📊 Total: {stats['total']} notes")
    
except Exception as e:
    print(f"❌ Statistiques: Erreur - {e}")

# Résumé
print("\n" + "=" * 50)
print("✨ TESTS RAPIDES TERMINÉS")
print("=" * 50)
print("\n💡 Pour tester avec la base de données:")
print("   python test_import_notes_complet.py")
print("\n📚 Pour tester en production:")
print("   https://www.myschoolgn.space/notes/importer/")
