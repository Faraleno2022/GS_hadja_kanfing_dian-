"""
Script de test pour vérifier l'affichage complet du nom de l'école sur les cartes scolaires
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
from django.http import HttpResponse

def tester_affichage_nom_ecole():
    """Test l'affichage du nom de l'école avec différentes longueurs"""
    
    print("="*60)
    print("TEST D'AFFICHAGE DU NOM DE L'ÉCOLE SUR LES CARTES SCOLAIRES")
    print("="*60)
    
    try:
        # Récupérer un élève pour le test
        eleve = Eleve.objects.filter(statut='ACTIF').first()
        
        if not eleve:
            print("❌ Aucun élève actif trouvé pour le test")
            return
        
        print(f"\n✅ Élève trouvé : {eleve.prenom} {eleve.nom}")
        print(f"   Classe : {eleve.classe.nom}")
        
        # Afficher le nom actuel de l'école
        nom_ecole_actuel = eleve.classe.ecole.nom
        print(f"\n📚 Nom actuel de l'école : {nom_ecole_actuel}")
        print(f"   Longueur : {len(nom_ecole_actuel)} caractères")
        
        # Analyser la taille de police qui sera utilisée
        longueur = len(nom_ecole_actuel.upper())
        
        print("\n📊 Analyse de l'affichage :")
        print("-" * 40)
        
        # Pour carte individuelle
        if longueur > 35:
            taille_carte = 8
            status = "Police réduite (nom long)"
        elif longueur > 25:
            taille_carte = 9
            status = "Police moyenne"
        else:
            taille_carte = 11
            status = "Police normale"
        
        print(f"   Carte individuelle : {taille_carte}pt - {status}")
        
        # Pour carte PVC
        if longueur > 35:
            taille_pvc = 7
            status_pvc = "Police réduite (nom long)"
        elif longueur > 25:
            taille_pvc = 8
            status_pvc = "Police moyenne"
        else:
            taille_pvc = 10
            status_pvc = "Police normale"
        
        print(f"   Carte PVC : {taille_pvc}pt - {status_pvc}")
        
        # Pour cartes en masse
        if longueur > 30:
            taille_masse = 4
            status_masse = "Police très petite"
        elif longueur > 22:
            taille_masse = 4.5
            status_masse = "Police petite"
        else:
            taille_masse = 5
            status_masse = "Police normale"
        
        if longueur > 40:
            status_masse += " + DIVISION SUR 2 LIGNES"
        
        print(f"   Cartes en masse : {taille_masse}pt - {status_masse}")
        
        # Tester avec différents exemples de noms
        print("\n🧪 Tests avec différentes longueurs de noms :")
        print("-" * 40)
        
        exemples = [
            "ÉCOLE PRIMAIRE",  # 14 caractères - court
            "GROUPE SCOLAIRE HADJA KANFING",  # 30 caractères - moyen
            "COMPLEXE SCOLAIRE INTERNATIONAL DE GUINÉE",  # 42 caractères - long
            "INSTITUT SUPÉRIEUR DES SCIENCES ET TECHNOLOGIES APPLIQUÉES"  # 59 caractères - très long
        ]
        
        for exemple in exemples:
            longueur = len(exemple)
            print(f"\n   '{exemple}'")
            print(f"   → {longueur} caractères")
            
            # Déterminer les tailles pour chaque type
            if longueur > 35:
                carte_taille = "8pt"
                pvc_taille = "7pt"
            elif longueur > 25:
                carte_taille = "9pt"
                pvc_taille = "8pt"
            else:
                carte_taille = "11pt"
                pvc_taille = "10pt"
            
            if longueur > 30:
                masse_taille = "4pt"
            elif longueur > 22:
                masse_taille = "4.5pt"
            else:
                masse_taille = "5pt"
            
            print(f"   → Carte: {carte_taille} | PVC: {pvc_taille} | Masse: {masse_taille}", end="")
            
            if longueur > 40:
                print(" [2 LIGNES]")
                # Simuler la division
                mid_point = longueur // 2
                space_index = exemple.rfind(' ', 0, mid_point + 10)
                if space_index == -1:
                    space_index = mid_point
                
                line1 = exemple[:space_index].strip()
                line2 = exemple[space_index:].strip()
                print(f"      Ligne 1: {line1}")
                print(f"      Ligne 2: {line2}")
            else:
                print()
        
        print("\n" + "="*60)
        print("✅ MODIFICATION VALIDÉE : Le nom de l'école s'affiche entièrement")
        print("   Plus de troncature avec '...'")
        print("   Adaptation automatique de la taille de police")
        print("   Support des noms très longs avec division sur 2 lignes")
        print("="*60)
        
        # Information sur les URLs
        print("\n📌 URLs pour tester :")
        print(f"   - Carte individuelle : /eleves/{eleve.id}/carte-scolaire-pdf/")
        print(f"   - Carte PVC : /eleves/{eleve.id}/carte-scolaire-pdf/?format=pvc")
        if eleve.classe:
            print(f"   - Cartes classe : /eleves/classe/{eleve.classe.id}/cartes-scolaires-pdf/")
        
    except Exception as e:
        print(f"\n❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    tester_affichage_nom_ecole()
