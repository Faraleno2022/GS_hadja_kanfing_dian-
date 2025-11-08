"""
Génération d'une carte scolaire unique au format PVC CR80
avec filigrane renforcé et optimisations pour impression PVC
"""

import os
import sys
import django
from reportlab.lib.units import mm

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from eleves.models import Eleve
from eleves.carte_scolaire_generator import _dessiner_carte_simple
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generer_carte_pvc_unique(eleve_id, output_file='carte_pvc_unique.pdf'):
    """
    Génère une carte unique au format PVC CR80 exact
    avec marques de coupe et filigrane renforcé
    """
    
    # Récupérer l'élève
    eleve = Eleve.objects.get(id=eleve_id)
    
    # Dimensions exactes format PVC CR80
    CARD_WIDTH = 85.6 * mm   # Largeur standard carte bancaire
    CARD_HEIGHT = 53.98 * mm  # Hauteur standard carte bancaire
    
    # Marges pour centrer sur A4
    page_width, page_height = A4
    margin_x = (page_width - CARD_WIDTH) / 2
    margin_y = (page_height - CARD_HEIGHT) / 2
    
    # Créer le PDF
    c = canvas.Canvas(output_file, pagesize=A4)
    
    # Enregistrement des polices
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        main_font = 'Arial'
        bold_font = 'Arial-Bold'
    except:
        main_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'
    
    # Dessiner les marques de coupe (pour découpe précise)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    mark_length = 10*mm
    
    # Marques horizontales
    c.line(margin_x - mark_length - 2*mm, margin_y, margin_x - 2*mm, margin_y)
    c.line(margin_x - mark_length - 2*mm, margin_y + CARD_HEIGHT, margin_x - 2*mm, margin_y + CARD_HEIGHT)
    c.line(margin_x + CARD_WIDTH + 2*mm, margin_y, margin_x + CARD_WIDTH + mark_length + 2*mm, margin_y)
    c.line(margin_x + CARD_WIDTH + 2*mm, margin_y + CARD_HEIGHT, margin_x + CARD_WIDTH + mark_length + 2*mm, margin_y + CARD_HEIGHT)
    
    # Marques verticales
    c.line(margin_x, margin_y - mark_length - 2*mm, margin_x, margin_y - 2*mm)
    c.line(margin_x + CARD_WIDTH, margin_y - mark_length - 2*mm, margin_x + CARD_WIDTH, margin_y - 2*mm)
    c.line(margin_x, margin_y + CARD_HEIGHT + 2*mm, margin_x, margin_y + CARD_HEIGHT + mark_length + 2*mm)
    c.line(margin_x + CARD_WIDTH, margin_y + CARD_HEIGHT + 2*mm, margin_x + CARD_WIDTH, margin_y + CARD_HEIGHT + mark_length + 2*mm)
    
    # Dessiner la carte
    _dessiner_carte_simple(c, eleve, margin_x, margin_y, CARD_WIDTH, CARD_HEIGHT, main_font, bold_font)
    
    # Ajouter les informations techniques pour l'impression PVC
    c.setFont(main_font, 6)
    c.setFillColor(colors.gray)
    c.drawString(margin_x, margin_y - 15*mm, "Format: CR80 (85.6 × 53.98 mm)")
    c.drawString(margin_x, margin_y - 18*mm, "Compatible: Evolis, Fargo, Zebra, Magicard")
    c.drawString(margin_x, margin_y - 21*mm, "Résolution recommandée: 300 DPI")
    c.drawString(margin_x, margin_y - 24*mm, f"Filigrane: 15% opacité, 25mm")
    
    # Zone de sécurité (3mm du bord)
    if False:  # Mettre True pour afficher la zone de sécurité
        c.setStrokeColor(colors.red)
        c.setLineWidth(0.2)
        c.setDash([2, 2])
        c.rect(margin_x + 3*mm, margin_y + 3*mm, CARD_WIDTH - 6*mm, CARD_HEIGHT - 6*mm, stroke=1, fill=0)
    
    c.showPage()
    c.save()
    
    print(f"✅ Carte PVC générée: {output_file}")
    print(f"   Format: CR80 (85.6 × 53.98 mm)")
    print(f"   Élève: {eleve.prenom} {eleve.nom}")
    print(f"   Matricule: {eleve.matricule}")
    print(f"   Filigrane: 15% opacité (renforcé)")
    
    return output_file

def test_carte_pvc():
    """Test de génération d'une carte PVC unique"""
    print("=" * 70)
    print("GÉNÉRATION CARTE PVC CR80 AVEC FILIGRANE RENFORCÉ")
    print("=" * 70)
    
    try:
        # Prendre le premier élève de la classe 19
        from eleves.models import Classe
        classe = Classe.objects.get(id=19)
        eleve = classe.eleves.first()
        
        if eleve:
            print(f"\n📇 Élève sélectionné:")
            print(f"   Nom: {eleve.prenom} {eleve.nom}")
            print(f"   Classe: {eleve.classe.nom}")
            print(f"   École: {eleve.classe.ecole.nom}")
            
            print("\n🎨 Caractéristiques PVC:")
            print("   • Format CR80 exact (85.6 × 53.98 mm)")
            print("   • Filigrane renforcé (15% opacité)")
            print("   • Marques de coupe pour découpe")
            print("   • Compatible toutes imprimantes PVC")
            
            # Générer la carte
            output_file = f"carte_pvc_{eleve.id}.pdf"
            generer_carte_pvc_unique(eleve.id, output_file)
            
            print("\n📊 SPÉCIFICATIONS TECHNIQUES:")
            print("   ┌─────────────────────────────┐")
            print("   │ Format: CR80 (ISO/IEC 7810) │")
            print("   │ Largeur: 85.6 mm            │")
            print("   │ Hauteur: 53.98 mm           │")
            print("   │ Épaisseur: 0.76 mm (30 mil) │")
            print("   │ Coins: Rayon 3.18 mm        │")
            print("   └─────────────────────────────┘")
            
            print("\n🖨️ COMPATIBILITÉ IMPRIMANTES:")
            print("   • Evolis Primacy, Zenius")
            print("   • Fargo HDP5000, DTC1250e")
            print("   • Zebra ZXP Series 3, 7, 9")
            print("   • Magicard Pronto, Enduro")
            print("   • DataCard SD260, SD460")
            
            print("\n💎 MATÉRIAUX PVC:")
            print("   • PVC blanc standard (recommandé)")
            print("   • PVC composite (plus durable)")
            print("   • PVC avec overlay holographique")
            print("   • Bande magnétique (optionnel)")
            print("   • Puce RFID (optionnel)")
            
            print("\n✅ Carte prête pour impression PVC professionnelle!")
            
            return True
        else:
            print("❌ Aucun élève trouvé dans la classe")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_carte_pvc()
