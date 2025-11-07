"""
Générateur de cartes scolaires modernes avec design amélioré
"""
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as ReportlabImage
from PIL import Image, ImageDraw, ImageOps
import io
import os
from django.utils import timezone
from datetime import timedelta


def generer_carte_scolaire_moderne(eleve, response):
    """
    Génère une carte scolaire moderne avec le design spécifié:
    - Haut: Logo + nom de l'établissement
    - Gauche: Photo (35-40% de la hauteur)
    - Droite: Informations alignées
    """
    # Configuration des dimensions (format carte de crédit standard)
    width, height = 86*mm, 54*mm
    c = canvas.Canvas(response, pagesize=(width, height))
    
    # Enregistrement des polices
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Italic', 'C:/Windows/Fonts/ariali.ttf'))
        main_font = 'Arial'
        bold_font = 'Arial-Bold'
        italic_font = 'Arial-Italic'
    except:
        main_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'
        italic_font = 'Helvetica-Oblique'
    
    # Couleurs du thème
    primary_blue = '#1e40af'
    secondary_blue = '#3b82f6'
    accent_green = '#10b981'
    text_dark = '#1f2937'
    text_gray = '#6b7280'
    light_gray = '#f3f4f6'
    border_color = '#e5e7eb'
    
    # 1. FOND BLANC ET BORDURE
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    
    # Bordure externe avec coins arrondis
    c.setStrokeColor(colors.HexColor(primary_blue))
    c.setLineWidth(1.5)
    c.roundRect(1, 1, width-2, height-2, 6, stroke=1, fill=0)
    
    # 2. EN-TÊTE (Logo + Nom de l'école)
    header_height = 14*mm
    
    # Fond dégradé pour l'en-tête
    c.setFillColor(colors.HexColor(primary_blue))
    c.roundRect(2, height - header_height - 1, width-4, header_height, 5, stroke=0, fill=1)
    
    # Logo de l'école
    logo_size = 10*mm
    logo_x = 4*mm
    logo_y = height - 12*mm
    
    # Cercle blanc pour le logo
    c.setFillColor(colors.white)
    c.circle(logo_x + logo_size/2, logo_y + logo_size/2, logo_size/2, stroke=0, fill=1)
    
    # Insérer le logo ou les initiales
    try:
        if eleve.classe.ecole.logo and hasattr(eleve.classe.ecole.logo, 'path'):
            if os.path.exists(eleve.classe.ecole.logo.path):
                # Charger et traiter le logo
                c.drawImage(eleve.classe.ecole.logo.path, logo_x + 0.5, logo_y + 0.5, 
                          width=logo_size-1, height=logo_size-1, preserveAspectRatio=True, mask='auto')
    except:
        # Si pas de logo, afficher les initiales
        c.setFillColor(colors.HexColor(primary_blue))
        c.setFont(bold_font, 14)
        initiales = eleve.classe.ecole.nom[:2].upper()
        c.drawCentredString(logo_x + logo_size/2, logo_y + logo_size/2 - 2, initiales)
    
    # Nom de l'école
    c.setFillColor(colors.white)
    c.setFont(bold_font, 11)
    school_name = eleve.classe.ecole.nom.upper()
    if len(school_name) > 30:
        school_name = school_name[:30] + "..."
    c.drawString(logo_x + logo_size + 3*mm, logo_y + logo_size - 3*mm, school_name)
    
    # Sous-titre
    c.setFont(italic_font, 7)
    c.drawString(logo_x + logo_size + 3*mm, logo_y + logo_size - 6*mm, "CARTE D'ÉTUDIANT")
    
    # 3. SECTION PHOTO (Gauche - 35% de la largeur)
    photo_section_width = width * 0.35
    photo_x = 4*mm
    photo_y = 8*mm
    photo_width = 24*mm
    photo_height = 30*mm
    
    # Cadre photo avec ombre
    c.setFillColor(colors.HexColor(light_gray))
    c.roundRect(photo_x + 0.5, photo_y - 0.5, photo_width, photo_height, 3, stroke=0, fill=1)
    
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor(border_color))
    c.setLineWidth(1)
    c.roundRect(photo_x, photo_y, photo_width, photo_height, 3, stroke=1, fill=1)
    
    # Insérer la photo de l'élève
    photo_inserted = False
    if eleve.photo:
        try:
            if hasattr(eleve.photo, 'path') and os.path.exists(eleve.photo.path):
                img = Image.open(eleve.photo.path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Redimensionner en gardant le ratio
                img.thumbnail((int(photo_width*2.83-10), int(photo_height*2.83-10)), Image.Resampling.LANCZOS)
                
                # Sauvegarder temporairement
                temp_buffer = io.BytesIO()
                img.save(temp_buffer, format='JPEG', quality=95)
                temp_buffer.seek(0)
                
                # Centrer la photo dans le cadre
                img_width = (photo_width - 2*mm)
                img_height = (photo_height - 2*mm)
                img_x = photo_x + 1*mm
                img_y = photo_y + 1*mm
                
                c.drawImage(temp_buffer, img_x, img_y, 
                          width=img_width, height=img_height, 
                          preserveAspectRatio=True)
                photo_inserted = True
        except Exception as e:
            print(f"Erreur lors du chargement de la photo: {e}")
    
    # Si pas de photo, afficher un placeholder
    if not photo_inserted:
        c.setFillColor(colors.HexColor(light_gray))
        c.rect(photo_x + 1, photo_y + 1, photo_width - 2, photo_height - 2, stroke=0, fill=1)
        
        # Icône utilisateur
        c.setFillColor(colors.HexColor(text_gray))
        c.setFont(bold_font, 24)
        c.drawCentredString(photo_x + photo_width/2, photo_y + photo_height/2 + 3, 
                          f"{eleve.prenom[0]}{eleve.nom[0]}".upper())
        
        c.setFont(main_font, 8)
        c.drawCentredString(photo_x + photo_width/2, photo_y + photo_height/2 - 5, "PHOTO")
    
    # 4. SECTION INFORMATIONS (Droite - 65% de la largeur)
    info_x = photo_x + photo_width + 4*mm
    info_y_start = height - header_height - 8*mm
    line_height = 5*mm
    
    # Nom complet (en gras et plus grand)
    c.setFillColor(colors.HexColor(text_dark))
    c.setFont(bold_font, 11)
    nom_complet = f"{eleve.prenom} {eleve.nom}".upper()
    if len(nom_complet) > 25:
        nom_complet = nom_complet[:22] + "..."
    c.drawString(info_x, info_y_start, nom_complet)
    
    # Ligne de séparation subtile
    c.setStrokeColor(colors.HexColor(border_color))
    c.setLineWidth(0.5)
    c.line(info_x, info_y_start - 2*mm, width - 4*mm, info_y_start - 2*mm)
    
    # Informations détaillées
    info_y = info_y_start - 6*mm
    
    # Matricule
    c.setFont(bold_font, 8)
    c.setFillColor(colors.HexColor(text_gray))
    c.drawString(info_x, info_y, "Matricule:")
    c.setFont(main_font, 8)
    c.setFillColor(colors.HexColor(text_dark))
    c.drawString(info_x + 18*mm, info_y, eleve.matricule)
    
    # Classe
    info_y -= 4*mm
    c.setFont(bold_font, 8)
    c.setFillColor(colors.HexColor(text_gray))
    c.drawString(info_x, info_y, "Classe:")
    c.setFont(main_font, 8)
    c.setFillColor(colors.HexColor(text_dark))
    c.drawString(info_x + 18*mm, info_y, eleve.classe.nom)
    
    # Niveau
    info_y -= 4*mm
    c.setFont(bold_font, 8)
    c.setFillColor(colors.HexColor(text_gray))
    c.drawString(info_x, info_y, "Niveau:")
    c.setFont(main_font, 8)
    c.setFillColor(colors.HexColor(text_dark))
    c.drawString(info_x + 18*mm, info_y, eleve.classe.niveau)
    
    # Année scolaire avec badge de validité
    info_y -= 5*mm
    c.setFillColor(colors.HexColor('#fef3c7'))
    c.roundRect(info_x - 1, info_y - 1, 45*mm, 5*mm, 2, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor('#fbbf24'))
    c.setLineWidth(0.5)
    c.roundRect(info_x - 1, info_y - 1, 45*mm, 5*mm, 2, stroke=1, fill=0)
    
    c.setFont(bold_font, 7)
    c.setFillColor(colors.HexColor('#92400e'))
    annee_scolaire = eleve.classe.annee_scolaire
    date_fin = timezone.now().date() + timedelta(days=365)
    c.drawString(info_x + 1, info_y + 1, f"Valide jusqu'au {date_fin.strftime('%d/%m/%Y')}")
    
    # 5. CONTACT D'URGENCE (en bas)
    contact_y = 4*mm
    
    # Ligne de séparation
    c.setStrokeColor(colors.HexColor(border_color))
    c.setLineWidth(0.3)
    c.setDash(1, 2)
    c.line(info_x, contact_y + 6*mm, width - 4*mm, contact_y + 6*mm)
    c.setDash()
    
    # Titre contact d'urgence
    c.setFont(bold_font, 6)
    c.setFillColor(colors.HexColor('#ef4444'))
    c.drawString(info_x, contact_y + 3.5*mm, "CONTACT D'URGENCE:")
    
    # Informations du contact
    if eleve.responsable_principal:
        c.setFont(main_font, 6)
        c.setFillColor(colors.HexColor(text_dark))
        
        # Nom du responsable
        resp_nom = eleve.responsable_principal.nom_complet[:30]
        c.drawString(info_x, contact_y + 1*mm, resp_nom)
        
        # Téléphone et adresse sur la même ligne
        contact_info = ""
        if eleve.responsable_principal.telephone:
            contact_info = f"📞 {eleve.responsable_principal.telephone}"
        
        if eleve.responsable_principal.adresse:
            adresse_courte = eleve.responsable_principal.adresse[:25]
            if contact_info:
                contact_info += f" | {adresse_courte}"
            else:
                contact_info = adresse_courte
        
        c.setFont(main_font, 5.5)
        c.setFillColor(colors.HexColor(text_gray))
        c.drawString(info_x, contact_y - 1*mm, contact_info[:50])
    
    # 6. BANDE DÉCORATIVE EN BAS
    c.setFillColor(colors.HexColor(accent_green))
    c.rect(2, 1, width-4, 2, stroke=0, fill=1)
    
    # 7. Numéro de série (optionnel)
    c.setFont(main_font, 5)
    c.setFillColor(colors.HexColor('#d1d5db'))
    c.drawRightString(width - 3*mm, 2*mm, f"#{eleve.id:06d}")
    
    c.showPage()
    c.save()
    return response


def generer_cartes_classe_moderne(classe, eleves, response):
    """
    Génère plusieurs cartes par page pour une classe entière
    Format: 2 cartes par page A4
    """
    from reportlab.lib.pagesizes import A4
    
    card_width, card_height = 86*mm, 54*mm
    margin = 15*mm
    spacing = 10*mm
    
    c = canvas.Canvas(response, pagesize=A4)
    page_width, page_height = A4
    
    # Positions des cartes sur la page (2 cartes par page)
    positions = [
        (margin, page_height - margin - card_height),
        (margin + card_width + spacing, page_height - margin - card_height),
        (margin, page_height - margin - (2 * card_height) - spacing),
        (margin + card_width + spacing, page_height - margin - (2 * card_height) - spacing),
    ]
    
    # Enregistrement des polices
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        main_font = 'Arial'
        bold_font = 'Arial-Bold'
    except:
        main_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'
    
    card_count = 0
    
    for eleve in eleves:
        pos_index = card_count % 4
        x, y = positions[pos_index]
        
        # Dessiner la carte à la position donnée
        _dessiner_carte_simple(c, eleve, x, y, card_width, card_height, main_font, bold_font)
        
        card_count += 1
        
        # Nouvelle page après 4 cartes
        if card_count % 4 == 0 and card_count < len(eleves):
            c.showPage()
    
    c.showPage()
    c.save()
    return response


def _dessiner_carte_simple(c, eleve, x, y, width, height, main_font, bold_font):
    """
    Dessine une carte simplifiée pour l'impression en masse
    """
    # Couleurs
    primary_blue = '#1e40af'
    text_dark = '#1f2937'
    text_gray = '#6b7280'
    border_color = '#e5e7eb'
    
    # Bordure de la carte
    c.setStrokeColor(colors.HexColor(primary_blue))
    c.setLineWidth(1)
    c.roundRect(x, y, width, height, 4, stroke=1, fill=0)
    
    # En-tête
    header_height = 12*mm
    c.setFillColor(colors.HexColor(primary_blue))
    c.roundRect(x+1, y+height-header_height-1, width-2, header_height, 3, stroke=0, fill=1)
    
    # Nom de l'école
    c.setFillColor(colors.white)
    c.setFont(bold_font, 9)
    c.drawString(x+3*mm, y+height-8*mm, eleve.classe.ecole.nom.upper()[:35])
    
    # Photo (simplifiée)
    photo_size = 20*mm
    photo_x = x + 3*mm
    photo_y = y + 10*mm
    
    c.setFillColor(colors.HexColor('#f3f4f6'))
    c.rect(photo_x, photo_y, photo_size, photo_size, stroke=1, fill=1)
    
    if eleve.photo:
        try:
            if hasattr(eleve.photo, 'path') and os.path.exists(eleve.photo.path):
                from PIL import Image
                img = Image.open(eleve.photo.path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.thumbnail((int(photo_size*2.83), int(photo_size*2.83)), Image.Resampling.LANCZOS)
                temp_buffer = io.BytesIO()
                img.save(temp_buffer, format='JPEG', quality=90)
                temp_buffer.seek(0)
                c.drawImage(temp_buffer, photo_x, photo_y, 
                          width=photo_size, height=photo_size, preserveAspectRatio=True)
        except:
            pass
    
    # Si pas de photo, initiales
    if not eleve.photo or not os.path.exists(eleve.photo.path) if hasattr(eleve.photo, 'path') else True:
        c.setFillColor(colors.HexColor(text_gray))
        c.setFont(bold_font, 14)
        c.drawCentredString(photo_x + photo_size/2, photo_y + photo_size/2 - 2, 
                          f"{eleve.prenom[0]}{eleve.nom[0]}".upper())
    
    # Informations de l'élève
    info_x = photo_x + photo_size + 3*mm
    info_y = y + height - header_height - 8*mm
    
    # Nom
    c.setFillColor(colors.HexColor(text_dark))
    c.setFont(bold_font, 9)
    c.drawString(info_x, info_y, f"{eleve.prenom} {eleve.nom}".upper()[:25])
    
    # Matricule
    info_y -= 5*mm
    c.setFont(main_font, 7)
    c.setFillColor(colors.HexColor(text_gray))
    c.drawString(info_x, info_y, f"Mat: {eleve.matricule}")
    
    # Classe
    info_y -= 4*mm
    c.drawString(info_x, info_y, f"Classe: {eleve.classe.nom}")
    
    # Contact
    if eleve.responsable_principal and eleve.responsable_principal.telephone:
        info_y -= 4*mm
        c.setFont(main_font, 6)
        c.drawString(info_x, info_y, f"Urgence: {eleve.responsable_principal.telephone}")
