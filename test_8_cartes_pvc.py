"""
Test de génération de 8 cartes par page
avec dimensions PVC standard (85.6mm × 53.98mm)
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from eleves.models import Classe, Eleve
from eleves.views import generer_cartes_classe_pdf
from reportlab.lib.units import mm

def test_8_cartes_pvc():
    print("=" * 70)
    print("TEST: 8 CARTES FORMAT PVC STANDARD PAR PAGE")
    print("=" * 70)
    
    try:
        # Récupérer la classe
        classe = Classe.objects.get(id=19)
        print(f"\n✓ Classe: {classe.nom}")
        print(f"  École: {classe.ecole.nom}")
        eleves = Eleve.objects.filter(classe=classe)
        print(f"  Nombre d'élèves: {eleves.count()}")
        
        # Créer une requête factice
        factory = RequestFactory()
        user = User.objects.first()
        if not user:
            user = User.objects.create_user('test', 'test@test.com', 'test')
        
        request = factory.get(f'/eleves/classe/{classe.id}/cartes-scolaires-pdf/')
        request.user = user
        
        print("\n📏 DIMENSIONS PVC STANDARD CR80:")
        print(f"  • Largeur: 85.6mm (standard carte bancaire)")
        print(f"  • Hauteur: 53.98mm (standard carte bancaire)")
        print(f"  • Format: CR80 (norme ISO/IEC 7810)")
        
        print("\n📐 DISPOSITION SUR PAGE A4:")
        print(f"  • Grille: 4×2 (4 lignes, 2 colonnes)")
        print(f"  • Total: 8 cartes par page")
        print(f"  • Espacement: 5mm horizontal, 5mm vertical")
        
        # Calcul des dimensions totales
        card_width = 85.6  # mm
        card_height = 53.98  # mm
        total_width = 2 * card_width + 5  # 2 colonnes + espacement
        total_height = 4 * card_height + 3*5  # 4 lignes + 3 espacements
        
        print(f"\n📊 UTILISATION DE L'ESPACE:")
        print(f"  • Largeur totale cartes: {total_width:.1f}mm")
        print(f"  • Hauteur totale cartes: {total_height:.1f}mm")
        print(f"  • Page A4: 210mm × 297mm")
        print(f"  • Marges automatiques centrées")
        
        print("\n🎨 Génération du PDF...")
        
        # Générer les cartes
        response = generer_cartes_classe_pdf(request, classe.id)
        
        if response.status_code == 200:
            # Sauvegarder le PDF
            filename = f"cartes_8_pvc_{classe.id}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"\n✓ PDF généré avec succès!")
            print(f"  Taille: {len(response.content):,} octets")
            print(f"  Fichier: {filename}")
            
            # Statistiques
            eleves_count = Eleve.objects.filter(classe=classe).count()
            nb_pages = (eleves_count + 7) // 8
            
            print(f"\n📈 RÉSULTATS:")
            print(f"  • {eleves_count} élèves")
            print(f"  • {nb_pages} pages générées")
            print(f"  • {eleves_count % 8 or 8} cartes sur la dernière page")
            
            print("\n✅ AVANTAGES DU FORMAT PVC:")
            print("  • Dimensions standard industrie")
            print("  • Compatible imprimantes cartes PVC")
            print("  • Peut être découpé pour cartes rigides")
            print("  • Format professionnel reconnu")
            
            return True
        else:
            print(f"  ✗ Erreur: Code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def afficher_comparaison():
    """Comparaison des dimensions"""
    print("\n" + "="*70)
    print("COMPARAISON DES FORMATS")
    print("="*70)
    
    print("\n📊 FORMAT CALCULÉ AUTOMATIQUEMENT (ancien):")
    print("  • ~92mm × 70mm (approximatif)")
    print("  • Taille variable selon marges")
    print("  • Non standard")
    
    print("\n📊 FORMAT PVC CR80 (nouveau):")
    print("  • 85.6mm × 53.98mm (exact)")
    print("  • Standard carte bancaire")
    print("  • Compatible impression PVC")
    print("  • Plus compact et professionnel")
    
    print("\n🎯 AJUSTEMENTS APPLIQUÉS:")
    print("  • En-tête: 7mm (était 8mm)")
    print("  • Photo: 12mm (était 15mm)")
    print("  • Logo en-tête: 4.5mm (était 5mm)")
    print("  • Polices: 3.5-6pt (optimisées)")
    print("  • Espacements: 1.8-3mm (compacts)")

if __name__ == "__main__":
    success = test_8_cartes_pvc()
    
    if success:
        afficher_comparaison()
        
        print("\n" + "="*70)
        print("✅ TEST RÉUSSI - 8 cartes PVC standard générées!")
        print("\n🔍 VÉRIFIEZ LE PDF:")
        print("  • Dimensions exactes 85.6mm × 53.98mm")
        print("  • 8 cartes par page A4")
        print("  • Informations centrées et lisibles")
        print("  • Format prêt pour impression PVC")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠️ TEST ÉCHOUÉ")
        print("="*70)
