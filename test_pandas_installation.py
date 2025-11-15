#!/usr/bin/env python
"""
Script de test pour vérifier l'installation de pandas et openpyxl
Exécuter sur le serveur après installation des dépendances
"""

import sys

def test_imports():
    """Teste l'importation des modules nécessaires"""
    print("=" * 50)
    print("Test d'installation des dépendances")
    print("=" * 50)
    
    errors = []
    
    # Test pandas
    try:
        import pandas as pd
        print("✅ pandas installé - Version:", pd.__version__)
    except ImportError as e:
        print("❌ pandas NON installé")
        errors.append(f"pandas: {e}")
    
    # Test openpyxl
    try:
        import openpyxl
        print("✅ openpyxl installé - Version:", openpyxl.__version__)
    except ImportError as e:
        print("❌ openpyxl NON installé")
        errors.append(f"openpyxl: {e}")
    
    # Test des imports du projet
    print("\n" + "=" * 50)
    print("Test des imports du projet")
    print("=" * 50)
    
    try:
        from notes.import_notes import ImportNotesValidator, ImportNotesProcessor
        print("✅ Module notes.import_notes accessible")
    except ImportError as e:
        print("❌ Erreur import notes.import_notes:", e)
        errors.append(f"import_notes: {e}")
    
    try:
        from notes.views_import import importer_notes
        print("✅ Module notes.views_import accessible")
    except ImportError as e:
        print("❌ Erreur import notes.views_import:", e)
        errors.append(f"views_import: {e}")
    
    # Résultat final
    print("\n" + "=" * 50)
    if errors:
        print("❌ ÉCHEC - Des dépendances sont manquantes:")
        for error in errors:
            print(f"  - {error}")
        print("\nInstallez les dépendances avec:")
        print("  pip install pandas==2.0.3 openpyxl==3.1.2")
        return False
    else:
        print("✅ SUCCÈS - Toutes les dépendances sont installées!")
        print("\nLa fonctionnalité d'importation de notes est opérationnelle.")
        print("URL: https://www.myschoolgn.space/notes/importer/")
        return True
    print("=" * 50)

if __name__ == "__main__":
    # Ajouter le chemin du projet si nécessaire
    import os
    if os.path.exists("/home/myschoolgn/GS_hadja_kanfing_dian-"):
        sys.path.insert(0, "/home/myschoolgn/GS_hadja_kanfing_dian-")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecole_moderne.settings")
        
        try:
            import django
            django.setup()
        except:
            pass
    
    success = test_imports()
    sys.exit(0 if success else 1)
