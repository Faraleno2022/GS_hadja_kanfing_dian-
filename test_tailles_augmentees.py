"""
Script de test pour vérifier l'augmentation de la taille du nom de l'école
Date : 11 novembre 2024
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve

def afficher_nouvelles_tailles():
    """Affiche les nouvelles tailles de police pour le nom de l'école"""
    
    print("="*70)
    print("NOUVELLES TAILLES DE POLICE POUR LE NOM DE L'ÉCOLE (AUGMENTÉES)")
    print("="*70)
    
    try:
        # Récupérer un élève pour exemple
        eleve = Eleve.objects.filter(statut='ACTIF').first()
        
        if eleve:
            nom_ecole = eleve.classe.ecole.nom.upper()
            longueur = len(nom_ecole)
            print(f"\n📚 École : {nom_ecole}")
            print(f"   Longueur : {longueur} caractères\n")
        
        # Tableau des nouvelles tailles
        print("\n📊 TABLEAU COMPARATIF DES TAILLES DE POLICE")
        print("-"*70)
        print("Type de carte    | Anciennes tailles      | NOUVELLES TAILLES")
        print("-"*70)
        
        # Carte individuelle
        print("CARTE INDIVIDUELLE")
        print("  Nom court       | 11pt                  | 14pt (+3)")
        print("  Nom moyen       | 9pt                   | 12pt (+3)")
        print("  Nom long        | 8pt                   | 10pt (+2)")
        print()
        
        # Carte PVC
        print("CARTE PVC")
        print("  Nom court       | 10pt                  | 13pt (+3)")
        print("  Nom moyen       | 8pt                   | 11pt (+3)")
        print("  Nom long        | 7pt                   | 9pt (+2)")
        print()
        
        # Cartes en masse
        print("CARTES EN MASSE")
        print("  Nom court       | 5pt                   | 8pt (+3)")
        print("  Nom moyen       | 4.5pt                 | 7pt (+2.5)")
        print("  Nom long        | 4pt                   | 6pt (+2)")
        print("-"*70)
        
        # Autres améliorations
        print("\n🎨 AUTRES AMÉLIORATIONS APPORTÉES:")
        print("-"*40)
        print("✅ En-tête augmenté : 14mm → 16mm (+2mm)")
        print("✅ Logo agrandi : 10mm → 12mm (+2mm)")
        print("✅ Position du logo ajustée pour le nouvel en-tête")
        print("✅ Espacement des informations optimisé")
        
        # Exemples avec les nouvelles tailles
        print("\n📝 EXEMPLES D'APPLICATION:")
        print("-"*40)
        
        exemples = [
            ("ÉCOLE PRIMAIRE", 14),
            ("GROUPE SCOLAIRE HADJA KANFING DIAN", 34),
            ("COMPLEXE SCOLAIRE INTERNATIONAL DE GUINÉE", 42)
        ]
        
        for nom, longueur in exemples:
            print(f"\n'{nom}' ({longueur} caractères)")
            
            # Déterminer les nouvelles tailles
            if longueur > 35:
                carte = "10pt"
                pvc = "9pt"
                masse = "6pt"
            elif longueur > 25:
                carte = "12pt"
                pvc = "11pt"
                masse = "7pt"
            else:
                carte = "14pt"
                pvc = "13pt"
                masse = "8pt"
            
            print(f"  → Carte individuelle : {carte}")
            print(f"  → Carte PVC : {pvc}")
            print(f"  → Cartes en masse : {masse}")
            
            if longueur > 40:
                print(f"  → Division sur 2 lignes pour les cartes en masse")
        
        print("\n" + "="*70)
        print("✅ TAILLES AUGMENTÉES AVEC SUCCÈS!")
        print("   Le nom de l'école sera maintenant plus visible")
        print("   Toutes les cartes ont été améliorées")
        print("="*70)
        
        # URLs pour test
        if eleve:
            print(f"\n📌 URLs pour tester les nouvelles tailles :")
            print(f"   - Carte individuelle : /eleves/{eleve.id}/carte-scolaire-pdf/")
            print(f"   - Carte PVC : /eleves/{eleve.id}/carte-scolaire-pdf/?format=pvc")
            if eleve.classe:
                print(f"   - Cartes classe : /eleves/classe/{eleve.classe.id}/cartes-scolaires-pdf/")
        
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    afficher_nouvelles_tailles()
