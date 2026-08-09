"""Mise en page commune des cartes (scolaire, retrait, bus, cantine).

Toutes les planches de cartes sont imprimees au format A4 avec 8 cartes par
feuille (2 colonnes x 4 lignes) au format PVC standard CR80 (85.6 x 53.98 mm).
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Format PVC standard CR80
CARTE_LARGEUR = 85.6 * mm
CARTE_HAUTEUR = 53.98 * mm

# Planche A4 : 2 colonnes x 4 lignes = 8 cartes
CARTES_COLONNES = 2
CARTES_LIGNES = 4
CARTES_PAR_PAGE = CARTES_COLONNES * CARTES_LIGNES

ESPACEMENT_H = 5 * mm
ESPACEMENT_V = 5 * mm


def positions_cartes_a4():
    """Retourne les 8 positions (x, y) des cartes d'une planche A4, centrees."""
    page_width, page_height = A4

    total_w = CARTES_COLONNES * CARTE_LARGEUR + (CARTES_COLONNES - 1) * ESPACEMENT_H
    total_h = CARTES_LIGNES * CARTE_HAUTEUR + (CARTES_LIGNES - 1) * ESPACEMENT_V

    margin_x = (page_width - total_w) / 2
    margin_y = (page_height - total_h) / 2

    positions = []
    for row in range(CARTES_LIGNES):
        for col in range(CARTES_COLONNES):
            x = margin_x + col * (CARTE_LARGEUR + ESPACEMENT_H)
            y = page_height - margin_y - (row + 1) * CARTE_HAUTEUR - row * ESPACEMENT_V
            positions.append((x, y))
    return positions


def enregistrer_polices():
    """Charge Arial si disponible, sinon retombe sur Helvetica."""
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
        return 'Arial', 'Arial-Bold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'


def dessiner_planche_cartes(c, elements, dessiner):
    """Dessine `elements` sur des planches A4 de 8 cartes.

    `dessiner` est appele avec (canvas, element, x, y, largeur, hauteur).
    Le canvas n'est ni ferme ni sauvegarde ici.
    """
    positions = positions_cartes_a4()
    elements = list(elements)
    total = len(elements)

    for index, element in enumerate(elements):
        x, y = positions[index % CARTES_PAR_PAGE]
        dessiner(c, element, x, y, CARTE_LARGEUR, CARTE_HAUTEUR)

        if (index + 1) % CARTES_PAR_PAGE == 0 and (index + 1) < total:
            c.showPage()

    return total


def texte_sur(value, default='-'):
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def texte_ajuste(c, text, x, y, max_width, font_name, max_size, min_size=5, color=None):
    text = texte_sur(text)
    size = max_size
    while size > min_size and pdfmetrics.stringWidth(text, font_name, size) > max_width:
        size -= 0.5

    if pdfmetrics.stringWidth(text, font_name, size) > max_width:
        while text and pdfmetrics.stringWidth(text + '...', font_name, size) > max_width:
            text = text[:-1]
        text = text + '...' if text else '...'

    if color:
        c.setFillColor(colors.HexColor(color))
    c.setFont(font_name, size)
    c.drawString(x, y, text)


def dessiner_carte_eleve(c, eleve, x, y, width, height, main_font, main_font_bold,
                         title, accent_color, light_color, rows, serial_label):
    """Dessine une carte eleve (retrait, bus, cantine...) dans le rectangle donne."""
    c.saveState()

    ecole = eleve.classe.ecole if getattr(eleve, 'classe', None) else None
    primary = '#1746a2'
    accent = accent_color or '#0f766e'
    dark = '#0f172a'
    muted = '#64748b'
    line = '#dbe3ef'
    soft = '#f5f8fc'
    footer_soft = '#eef4fb'

    margin = 2.2 * mm
    header_h = 10.5 * mm
    footer_h = 6.2 * mm
    radius = 4.5

    school_name = texte_sur(getattr(ecole, 'nom', '')).upper()
    full_name = f"{texte_sur(eleve.prenom, '')} {texte_sur(eleve.nom, '')}".strip().upper()

    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor(line))
    c.setLineWidth(0.7)
    c.roundRect(x, y, width, height, radius, stroke=1, fill=1)

    c.setFillColor(colors.HexColor(primary))
    c.roundRect(x + 0.8, y + height - header_h - 0.8, width - 1.6, header_h, radius, stroke=0, fill=1)
    c.rect(x + 0.8, y + height - header_h - 0.8, width - 1.6, header_h / 2, stroke=0, fill=1)

    logo_size = 7.2 * mm
    logo_x = x + margin
    logo_y = y + height - header_h + 1.1 * mm
    c.setFillColor(colors.white)
    c.circle(logo_x + logo_size / 2, logo_y + logo_size / 2, logo_size / 2, stroke=0, fill=1)
    try:
        if ecole and ecole.logo and hasattr(ecole.logo, 'path') and os.path.exists(ecole.logo.path):
            c.drawImage(
                ecole.logo.path,
                logo_x + 0.6,
                logo_y + 0.6,
                width=logo_size - 1.2,
                height=logo_size - 1.2,
                preserveAspectRatio=True,
                mask='auto',
            )
        else:
            raise ValueError('No logo')
    except Exception:
        c.setFillColor(colors.HexColor(primary))
        c.setFont(main_font_bold, 7)
        c.drawCentredString(logo_x + logo_size / 2, logo_y + logo_size / 2 - 2, school_name[:2] or 'EC')

    title_x = logo_x + logo_size + 2 * mm
    title_w = width - (title_x - x) - margin
    texte_ajuste(c, school_name, title_x, y + height - 5.1 * mm, title_w, main_font_bold, 7.6, 4.8, '#ffffff')
    texte_ajuste(c, title, title_x, y + height - 8.2 * mm, title_w, main_font, 5.2, 4.2, '#dbeafe')

    try:
        c.saveState()
        c.setFillAlpha(0.06)
        if ecole and ecole.logo and hasattr(ecole.logo, 'path') and os.path.exists(ecole.logo.path):
            mark = 30 * mm
            c.drawImage(
                ecole.logo.path,
                x + width - mark - 4 * mm,
                y + footer_h + 5 * mm,
                width=mark,
                height=mark,
                preserveAspectRatio=True,
                mask='auto',
            )
        else:
            c.setFillColor(colors.HexColor(primary))
            c.setFont(main_font_bold, 28)
            c.drawCentredString(x + width * 0.70, y + height * 0.46, school_name[:3])
        c.restoreState()
    except Exception:
        try:
            c.restoreState()
        except Exception:
            pass

    photo_w = 22.5 * mm
    photo_h = 27.5 * mm
    photo_x = x + margin
    photo_y = y + footer_h + 3.2 * mm
    c.setFillColor(colors.HexColor(soft))
    c.setStrokeColor(colors.HexColor(line))
    c.setLineWidth(0.7)
    c.roundRect(photo_x, photo_y, photo_w, photo_h, 3.2, stroke=1, fill=1)

    photo_drawn = False
    try:
        if eleve.photo and hasattr(eleve.photo, 'path') and eleve.photo.name and os.path.exists(eleve.photo.path):
            c.drawImage(eleve.photo.path, photo_x + 1, photo_y + 1, photo_w - 2, photo_h - 2,
                        preserveAspectRatio=True, anchor='c', mask='auto')
            photo_drawn = True
    except Exception:
        photo_drawn = False

    if not photo_drawn:
        initials = (texte_sur(getattr(eleve, 'prenom', 'E'), 'E')[:1] + texte_sur(getattr(eleve, 'nom', 'L'), 'L')[:1]).upper()
        c.setFillColor(colors.HexColor('#e8eef8'))
        c.roundRect(photo_x + 1, photo_y + 1, photo_w - 2, photo_h - 2, 2.5, stroke=0, fill=1)
        c.setFillColor(colors.HexColor(primary))
        c.setFont(main_font_bold, 17)
        c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2 - 4, initials or 'EL')

    info_x = photo_x + photo_w + 3 * mm
    info_w = x + width - margin - info_x
    name_y = y + height - header_h - 4.4 * mm
    texte_ajuste(c, full_name, info_x, name_y, info_w, main_font_bold, 8.7, 5.8, dark)

    c.setStrokeColor(colors.HexColor(accent))
    c.setLineWidth(1.0)
    c.line(info_x, name_y - 1.7 * mm, info_x + info_w, name_y - 1.7 * mm)

    row_y = name_y - 5.3 * mm
    label_w = 14 * mm
    value_w = info_w - label_w
    for label, value in rows[:5]:
        c.setFillColor(colors.HexColor(muted))
        c.setFont(main_font_bold, 5.6)
        c.drawString(info_x, row_y, texte_sur(label).upper())
        texte_ajuste(c, value, info_x + label_w, row_y, value_w, main_font, 6.6, 4.7, dark)
        row_y -= 4.2 * mm

    c.setFillColor(colors.HexColor(footer_soft))
    c.rect(x + 0.8, y + 0.8, width - 1.6, footer_h, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor(line))
    c.setLineWidth(0.5)
    c.line(x + 0.8, y + footer_h + 0.8, x + width - 0.8, y + footer_h + 0.8)

    annee = texte_sur(getattr(getattr(eleve, 'classe', None), 'annee_scolaire', ''))
    texte_ajuste(c, f'ANNEE SCOLAIRE {annee}', x + margin, y + 2.4 * mm, width * 0.55, main_font_bold, 5.8, 4.2, primary)
    c.setFillColor(colors.HexColor(muted))
    c.setFont(main_font, 4.6)
    c.drawRightString(x + width - margin, y + 2.4 * mm, f'{serial_label} #{getattr(eleve, "id", 0):06d}')

    c.setStrokeColor(colors.HexColor(primary))
    c.setLineWidth(0.9)
    c.roundRect(x, y, width, height, radius, stroke=1, fill=0)
    c.restoreState()
