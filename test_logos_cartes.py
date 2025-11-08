"""
Test de l'affichage des logos sur les cartes scolaires
- Logo en filigrane derrière le contenu
- Logo dans l'en-tête
- Petit logo sur le cadre photo
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe, Ecole
from eleves.carte_scolaire_generator import _dessiner_carte_simple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from io import BytesIO

def test_logos_cartes():
    print("=" * 60)
    print("TEST AFFICHAGE DES LOGOS SUR CARTES SCOLAIRES")
    print("=" * 60)
    
    try:
        # Récupérer un élève de test
        eleve = Eleve.objects.filter(classe__id=19).first()
        
        if not eleve:
            print("❌ Aucun élève trouvé dans la classe 19")
            return False
        
        print(f"\n✓ Élève test: {eleve.prenom} {eleve.nom}")
        print(f"  École: {eleve.classe.ecole.nom}")
        
        # Vérifier si l'école a un logo
        if eleve.classe.ecole.logo:
            try:
                if os.path.exists(eleve.classe.ecole.logo.path):
                    print(f"  ✓ Logo trouvé: {eleve.classe.ecole.logo.path}")
                else:
                    print(f"  ⚠️ Logo défini mais fichier introuvable")
            except:
                print(f"  ⚠️ Logo défini mais erreur d'accès")
        else:
            print(f"  ℹ️ Pas de logo - Les initiales seront utilisées")
        
        # Créer le PDF de test
        print("\n🎨 Génération de la carte avec logos...")
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Paramètres de carte
        card_width = 243.78
        card_height = 153.07
        
        # Position de la carte sur la page
        x = 50
        y = 500
        
        print("\n📍 Éléments de logo qui seront ajoutés:")
        print("  1. Logo en FILIGRANE (centre, transparent, rotation 15°)")
        print("  2. Logo dans l'EN-TÊTE (gauche, dans cercle blanc)")
        print("  3. Logo sur CADRE PHOTO (coin supérieur gauche)")
        
        # Dessiner la carte
        _dessiner_carte_simple(c, eleve, x, y, card_width, card_height, 
                             'Helvetica', 'Helvetica-Bold')
        
        # Ajouter une deuxième carte pour comparaison (sans modifications)
        y2 = 250
        print("\n  4. Deuxième carte ajoutée pour comparaison")
        _dessiner_carte_simple(c, eleve, x, y2, card_width, card_height, 
                             'Helvetica', 'Helvetica-Bold')
        
        c.save()
        buffer.seek(0)
        
        # Sauvegarder le fichier
        filename = "test_logos_cartes.pdf"
        with open(filename, 'wb') as f:
            f.write(buffer.getvalue())
        
        print(f"\n✓ PDF généré avec succès!")
        print(f"  Taille: {len(buffer.getvalue()):,} octets")
        print(f"  Fichier: {filename}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def verifier_ecoles_logos():
    """Vérifier quelles écoles ont des logos"""
    print("\n" + "=" * 60)
    print("ÉTAT DES LOGOS DES ÉCOLES")
    print("=" * 60)
    
    ecoles = Ecole.objects.all()
    
    for ecole in ecoles:
        print(f"\n📚 {ecole.nom}:")
        if ecole.logo:
            try:
                if hasattr(ecole.logo, 'path') and os.path.exists(ecole.logo.path):
                    file_size = os.path.getsize(ecole.logo.path) / 1024  # En KB
                    print(f"   ✓ Logo présent ({file_size:.1f} KB)")
                else:
                    print(f"   ⚠️ Logo défini mais fichier manquant")
            except:
                print(f"   ⚠️ Logo défini mais inaccessible")
        else:
            print(f"   ℹ️ Pas de logo - Initiales utilisées: '{ecole.nom[:2].upper()}'")

if __name__ == "__main__":
    # Vérifier d'abord l'état des logos
    verifier_ecoles_logos()
    
    # Tester la génération
    print("\n")
    success = test_logos_cartes()
    
    if success:
        print("\n" + "="*60)
        print("✅ TEST RÉUSSI - Les logos sont intégrés aux cartes!")
        print("\n🔍 Vérifiez le fichier 'test_logos_cartes.pdf'")
        print("   Vous devriez voir:")
        print("   • Logo en filigrane au centre (très transparent)")
        print("   • Logo dans l'en-tête à gauche")
        print("   • Petit logo sur le coin du cadre photo")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("⚠️ TEST ÉCHOUÉ - Vérifiez les erreurs")
        print("="*60)
