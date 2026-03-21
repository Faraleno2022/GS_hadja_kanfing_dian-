"""
Livret Scolaire - Generation PDF du parcours complet d'un eleve.
Format officiel guineen : paysage A4, deux niveaux par page GAUCHE/DROITE.

College/Lycee : Matieres | Coef | 1er Sem (Moyenne Classe | Classement | Moy Semestre) | 2eme Sem (idem)
Primaire : Matieres | 1er Trim | 2eme Trim | 3eme Trim | Moy Annuelle | Observations
"""

import io
import re
import logging
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

from eleves.models import Eleve, Classe, Ecole, HistoriqueEleve
from .models import (
    ClasseNote, MatiereNote, Classement,
    NoteMensuelle, CompositionNote,
)
from .calculs_moyennes import detecter_niveau_scolaire
from utilisateurs.utils import filter_by_user_school, user_school

logger = logging.getLogger(__name__)

# ==============================================================================
#  CONSTANTES
# ==============================================================================

CYCLE_LABELS = {
    'MATERNELLE': 'Cycle Maternelle',
    'PRIMAIRE':   'Cycle Primaire',
    'COLLEGE':    'Cycle College',
    'LYCEE':      'Cycle Lycee / Terminale',
}


def _s(val):
    """Convertit en string safe."""
    if val is None:
        return ''
    return str(val)


def _fmt(v):
    """Formate une note."""
    if v is None:
        return ''
    try:
        return f'{float(v):.2f}'
    except (ValueError, TypeError):
        return ''


def _get_logo_reader(ecole):
    try:
        if ecole.logo and hasattr(ecole.logo, 'path'):
            return ImageReader(ecole.logo.path)
    except Exception:
        pass
    return None


# ==============================================================================
#  DESSIN D'UNE DEMI-PAGE (une colonne gauche ou droite)
# ==============================================================================

def _draw_half_college(c, x, y, w, h, ecole, entry, eleve, page_number):
    """
    Dessine UNE demi-page format College/Lycee (semestre).
    x, y = coin bas-gauche de la zone ; w, h = dimensions.
    Le contenu remplit toute la demi-page : tableau etire + pied ancre en bas.
    """
    classe_nom = entry['classe_nom']
    annee = entry['annee_scolaire']
    matieres = entry['matieres_data']
    sur = entry['sur']
    moy_ann = entry['moyenne_annuelle']
    rang = entry['rang']
    passe_en = entry['passe_en']

    # Cadre principal
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h)

    pad = 4
    lx = x + pad
    rx = x + w - pad
    top = y + h
    cy = top

    # ------------------------------------------------------------------
    # EN-TETE (haut)
    # ------------------------------------------------------------------
    cy -= 11
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    c.drawString(lx, cy, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, cy, f"DPE/DCE : {_s(ecole.dpe)}")

    cy -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, cy, f"College : {_s(ecole.nom)}")
    c.drawString(lx + w * 0.55, cy, "Venant de : ........................")

    cy -= 8
    c.drawString(lx, cy, "Date d'entree : ........................")

    cy -= 8
    c.drawString(lx, cy, "References : ........................")

    # Ligne separatrice
    cy -= 4
    c.setLineWidth(0.5)
    c.line(x, cy, x + w, cy)

    # Bande classe
    band_h = 14
    cy -= band_h
    c.setFillColor(colors.HexColor('#f0f0f0'))
    c.rect(x, cy, w, band_h, fill=1, stroke=1)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.black)
    c.drawString(lx + 5, cy + 3, f"Classe : {_s(classe_nom)}")
    c.drawRightString(rx - 5, cy + 3, f"Annee scolaire : {annee}")

    table_top = cy - 2  # Y ou le tableau commence

    # ------------------------------------------------------------------
    # PIED (ancre en BAS du cadre)
    # ------------------------------------------------------------------
    footer_h = 75  # hauteur totale reservee au pied
    page_num_h = 12
    footer_top = y + page_num_h + footer_h

    # Numero de page (tout en bas)
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")

    # Ligne separatrice appreciations
    sep_y = footer_top
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)
    c.line(x, sep_y, x + w, sep_y)

    # Appreciations (gauche) | Aux parents (droite)
    left_w = w * 0.50
    c.setLineWidth(0.3)
    c.line(x + left_w, sep_y, x + left_w, y + page_num_h)

    ay = sep_y - 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(lx, ay, "Appreciations Generales")
    ay -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ay, "..........................................................")
    ay -= 8
    c.drawString(lx, ay, "..........................................................")

    rstart_x = x + left_w + pad
    py = sep_y - 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Aux parents, Nom et Prenom de l'eleve")
    py -= 11
    c.setFont('Helvetica-Bold', 6)
    c.drawString(rstart_x, py, f"Eleve : {_s(eleve.nom)}")
    c.drawString(rstart_x + w * 0.22, py, f"Prenom : {_s(eleve.prenom)}")
    py -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Date :")
    py -= 11
    c.drawString(rstart_x, py, "Signature du Principal")

    # ------------------------------------------------------------------
    # TABLEAU DES NOTES (hauteur fixe par ligne, colle a l'en-tete)
    # ------------------------------------------------------------------
    header1 = ['Matieres', 'Coef', '1er Semestre', '', '', '2eme Semestre', '', '']
    header2 = ['', '', 'Moyenne\nClasse', 'Classement', 'Moyenne\nSemestre',
               'Moyenne\nClasse', 'Classement', 'Moyenne\nSemestre']

    col_ratios = [0.22, 0.05, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105]
    col_widths = [w * r for r in col_ratios]
    diff_w = w - sum(col_widths)
    col_widths[0] += diff_w

    data = [header1, header2]
    for m in matieres:
        data.append([
            _s(m['nom']),
            str(m.get('coef', '')),
            _fmt(m.get('sem1_moy')),
            _fmt(m.get('sem1_compo')),
            _fmt(m.get('sem1_moyenne')),
            _fmt(m.get('sem2_moy')),
            _fmt(m.get('sem2_compo')),
            _fmt(m.get('sem2_moyenne')),
        ])

    nb_rows = len(data)
    header_rh = 20
    data_rh = 20  # hauteur fixe raisonnable par ligne
    row_heights = [header_rh, header_rh] + [data_rh] * (nb_rows - 2)

    table = Table(data, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 1), 5.5),
        ('FONTSIZE', (0, 2), (-1, -1), 6.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#f0f0f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (4, 0)),
        ('SPAN', (5, 0), (7, 0)),
    ]))

    table_total_h = sum(row_heights)
    table_y = table_top - table_total_h
    table.wrapOn(c, w, table_total_h + 20)
    table.drawOn(c, x, table_y)

    # ------------------------------------------------------------------
    # MOYENNE ANNUELLE (collee juste sous le tableau)
    # ------------------------------------------------------------------
    fy = table_y - 11
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(colors.black)
    moy_txt2 = _fmt(moy_ann) if moy_ann else ''
    c.drawString(lx, fy, "Moyenne Annuelle")
    c.drawString(lx + w * 0.27, fy, f"{moy_txt2}")
    c.drawRightString(rx, fy, f"/{sur}")

    fy -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, fy, f"Passe en classe superieure /{sur}")
    rang_txt2 = _s(rang) if rang else ''
    c.drawString(lx + w * 0.40, fy, f"Classement : {rang_txt2}")
    c.drawString(lx + w * 0.68, fy, "Redoublant :")
    c.drawRightString(rx, fy, "eleves :")


def _draw_half_primaire(c, x, y, w, h, ecole, entry, eleve, page_number):
    """
    Dessine UNE demi-page format Primaire (trimestre).
    Le contenu remplit toute la demi-page.
    """
    classe_nom = entry['classe_nom']
    annee = entry['annee_scolaire']
    matieres = entry['matieres_data']
    sur = entry['sur']
    moy_ann = entry['moyenne_annuelle']
    rang = entry['rang']
    passe_en = entry['passe_en']

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h)

    pad = 4
    lx = x + pad
    rx = x + w - pad
    top = y + h
    cy = top

    # EN-TETE
    cy -= 11
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    c.drawString(lx, cy, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, cy, f"DPE/DCE : {_s(ecole.dpe)}")

    cy -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, cy, f"Ecole Primaire de : {_s(ecole.nom)}")
    if ecole.desee:
        c.drawRightString(rx, cy, f"DSEE : {_s(ecole.desee)}")

    cy -= 8
    c.drawString(lx, cy, "Date d'entree : ........................")
    c.drawString(lx + w * 0.45, cy, "Venant de : ........................")

    cy -= 8
    c.drawString(lx, cy, "References du Certificat de transfert : ........................")

    # BANDE CLASSE
    cy -= 4
    c.setLineWidth(0.5)
    c.line(x, cy, x + w, cy)

    band_h = 14
    cy -= band_h
    c.setFillColor(colors.HexColor('#f0f0f0'))
    c.rect(x, cy, w, band_h, fill=1, stroke=1)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.black)
    c.drawString(lx + 5, cy + 3, f"Classe : {_s(classe_nom)}")
    c.drawRightString(rx - 5, cy + 3, f"Annee scolaire : {annee}")

    # MAITRE
    cy -= 11
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(lx, cy, "Maitre : ................................................................")
    cy -= 3

    table_top = cy

    # ------------------------------------------------------------------
    # PIED (ancre en BAS)
    # ------------------------------------------------------------------
    footer_h = 75
    page_num_h = 12
    footer_top = y + page_num_h + footer_h

    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")

    sep_y = footer_top
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)
    c.line(x, sep_y, x + w, sep_y)

    # Appreciations (gauche) | Aux parents (droite)
    left_w = w * 0.50
    c.setLineWidth(0.3)
    c.line(x + left_w, sep_y, x + left_w, y + page_num_h)

    ay = sep_y - 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(lx, ay, "Appreciations Generales")
    ay -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ay, "..........................................................")
    ay -= 8
    c.drawString(lx, ay, "..........................................................")

    rstart_x = x + left_w + pad
    py = sep_y - 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Aux parents, Nom et Prenom de l'eleve")
    py -= 11
    c.setFont('Helvetica-Bold', 6)
    c.drawString(rstart_x, py, f"Eleve : {_s(eleve.nom)}")
    c.drawString(rstart_x + w * 0.22, py, f"Prenom : {_s(eleve.prenom)}")
    py -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Date :")
    py -= 11
    c.drawString(rstart_x, py, "Signature du Directeur")

    # ------------------------------------------------------------------
    # TABLEAU (hauteur fixe par ligne, colle a l'en-tete)
    # ------------------------------------------------------------------
    header = ['Matieres', '1er\nTrimestre', '2eme\nTrimestre', '3eme\nTrimestre',
              'Moyenne\nAnnuelle', 'Observations']
    col_ratios = [0.26, 0.13, 0.13, 0.13, 0.14, 0.21]
    col_widths = [w * r for r in col_ratios]
    diff_w = w - sum(col_widths)
    col_widths[-1] += diff_w

    data = [header]
    for m in matieres:
        t1 = m.get('t1_moy')
        t2 = m.get('t2_moy')
        t3 = m.get('t3_moy')
        vals = [v for v in [t1, t2, t3] if v is not None]
        m_ann = round(sum(float(v) for v in vals) / len(vals), 2) if vals else None

        seuil = 5.0 if sur == 10 else 10.0
        obs = ''
        if m_ann is not None:
            if sur == 10:
                obs = 'TB' if m_ann >= 8 else 'B' if m_ann >= 7 else 'AB' if m_ann >= 6 else 'P' if m_ann >= seuil else 'I'
            else:
                obs = 'TB' if m_ann >= 16 else 'B' if m_ann >= 14 else 'AB' if m_ann >= 12 else 'P' if m_ann >= seuil else 'I'
        data.append([_s(m['nom']), _fmt(t1), _fmt(t2), _fmt(t3), _fmt(m_ann), obs])

    nb_rows = len(data)
    header_rh = 20
    data_rh = 20  # hauteur fixe raisonnable
    row_heights = [header_rh] + [data_rh] * (nb_rows - 1)

    table = Table(data, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 5.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    table_total_h = sum(row_heights)
    table_y = table_top - table_total_h
    table.wrapOn(c, w, table_total_h + 20)
    table.drawOn(c, x, table_y)

    # ------------------------------------------------------------------
    # MOYENNE ANNUELLE (collee sous le tableau)
    # ------------------------------------------------------------------
    fy = table_y - 11
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(colors.black)
    moy_txt2 = _fmt(moy_ann) if moy_ann else ''
    c.drawString(lx, fy, "Moyenne Annuelle")
    c.drawString(lx + w * 0.27, fy, f"{moy_txt2}")
    c.drawRightString(rx, fy, f"/{sur}")

    fy -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, fy, f"Passe en classe superieure /{sur}")
    rang_txt2 = _s(rang) if rang else ''
    c.drawString(lx + w * 0.40, fy, f"Classement : {rang_txt2}")
    c.drawString(lx + w * 0.68, fy, "Redoublant :")
    c.drawRightString(rx, fy, "eleves :")


def _draw_half_maternelle(c, x, y, w, h, ecole, entry, eleve, page_number):
    """Demi-page Maternelle avec contenu remplissant la page."""
    classe_nom = entry['classe_nom']
    annee = entry['annee_scolaire']

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h)

    pad = 4
    lx = x + pad
    rx = x + w - pad
    top = y + h
    cy = top

    # En-tete
    cy -= 11
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    c.drawString(lx, cy, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, cy, f"DPE/DCE : {_s(ecole.dpe)}")

    cy -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, cy, f"Ecole Maternelle : {_s(ecole.nom)}")

    cy -= 4
    c.setLineWidth(0.5)
    c.line(x, cy, x + w, cy)

    band_h = 14
    cy -= band_h
    c.setFillColor(colors.HexColor('#f0f0f0'))
    c.rect(x, cy, w, band_h, fill=1, stroke=1)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.black)
    c.drawString(lx + 5, cy + 3, f"Classe : {_s(classe_nom)}")
    c.drawRightString(rx - 5, cy + 3, f"Annee scolaire : {annee}")

    cy -= 14
    c.setFont('Helvetica', 6)
    c.drawString(lx, cy, f"Eleve: {_s(eleve.nom)} {_s(eleve.prenom)}")
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else ''
    c.drawString(lx + w * 0.45, cy, f"Ne(e) le: {dn}")

    # Zone centrale
    cy -= 20
    c.setFont('Helvetica-Oblique', 7)
    c.drawString(lx, cy, "Evaluation qualitative (appreciations) - Voir bulletins trimestriels")

    # Tableau simplifie avec domaines d'evaluation
    cy -= 15
    domains = [
        "Langage / Communication",
        "Graphisme / Ecriture",
        "Mathematiques / Logique",
        "Decouverte du monde",
        "Arts plastiques / Dessin",
        "Education physique",
        "Socialisation / Autonomie",
        "Comportement general",
    ]
    header = ['Domaines', '1er Trim.', '2eme Trim.', '3eme Trim.', 'Appreciation']
    col_ratios_m = [0.32, 0.14, 0.14, 0.14, 0.26]
    col_widths_m = [w * r for r in col_ratios_m]
    diff_m = w - sum(col_widths_m)
    col_widths_m[-1] += diff_m

    data_m = [header]
    for d in domains:
        data_m.append([d, '', '', '', ''])

    # Pied ancre en bas
    footer_h = 75
    page_num_h = 12
    footer_top = y + page_num_h + footer_h

    nb_rows_m = len(data_m)
    header_rh_m = 20
    data_rh_m = 20  # hauteur fixe
    row_heights_m = [header_rh_m] + [data_rh_m] * (nb_rows_m - 1)

    table_m = Table(data_m, colWidths=col_widths_m, rowHeights=row_heights_m)
    table_m.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 5.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    table_total_h_m = sum(row_heights_m)
    table_y_m = cy - table_total_h_m
    table_m.wrapOn(c, w, table_total_h_m + 20)
    table_m.drawOn(c, x, table_y_m)

    # Pied
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")

    sep_y = footer_top
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)
    c.line(x, sep_y, x + w, sep_y)

    fy = footer_top + 12
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(colors.black)
    c.drawString(lx, fy, "Appreciation globale du trimestre")

    left_w = w * 0.50
    c.setLineWidth(0.3)
    c.line(x + left_w, sep_y, x + left_w, y + page_num_h)

    ay = sep_y - 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(lx, ay, "Appreciations Generales")
    ay -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ay, "..........................................................")
    ay -= 8
    c.drawString(lx, ay, "..........................................................")

    rstart_x = x + left_w + pad
    py = sep_y - 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Aux parents, Nom et Prenom de l'eleve")
    py -= 11
    c.setFont('Helvetica-Bold', 6)
    c.drawString(rstart_x, py, f"Eleve : {_s(eleve.nom)}")
    c.drawString(rstart_x + w * 0.22, py, f"Prenom : {_s(eleve.prenom)}")
    py -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Date :")
    py -= 11
    c.drawString(rstart_x, py, "Signature du Directeur")


def _draw_half_page(c, x, y, w, h, ecole, entry, eleve, page_number):
    """Dispatch vers le bon format selon le niveau."""
    niveau = entry['niveau']
    if niveau == 'MATERNELLE':
        _draw_half_maternelle(c, x, y, w, h, ecole, entry, eleve, page_number)
    elif niveau in ('COLLEGE', 'LYCEE'):
        _draw_half_college(c, x, y, w, h, ecole, entry, eleve, page_number)
    else:
        _draw_half_primaire(c, x, y, w, h, ecole, entry, eleve, page_number)


# ==============================================================================
#  PAGES SPECIALES DU DEPLIANT
# ==============================================================================

def _draw_guinea_flag(c, cx, y_top, flag_w=60, flag_h=40):
    """Dessine le drapeau de la Guinee (3 bandes verticales : rouge, jaune, vert)."""
    stripe_w = flag_w / 3
    fx = cx - flag_w / 2

    # Rouge
    c.setFillColor(colors.HexColor('#CE1126'))
    c.rect(fx, y_top - flag_h, stripe_w, flag_h, fill=1, stroke=0)
    # Jaune
    c.setFillColor(colors.HexColor('#FCD116'))
    c.rect(fx + stripe_w, y_top - flag_h, stripe_w, flag_h, fill=1, stroke=0)
    # Vert
    c.setFillColor(colors.HexColor('#009460'))
    c.rect(fx + 2 * stripe_w, y_top - flag_h, stripe_w, flag_h, fill=1, stroke=0)

    # Bordure fine
    c.setStrokeColor(colors.HexColor('#333333'))
    c.setLineWidth(0.5)
    c.rect(fx, y_top - flag_h, flag_w, flag_h, fill=0, stroke=1)


def _draw_mont_nimba(c, cx, y_top, size=50):
    """Dessine le Mont Nimba (sommet de Guinee) en vectoriel."""
    mw = size * 1.2
    mh = size * 0.85
    base_y = y_top - mh

    # Ciel degrade bleu clair (fond)
    c.setFillColor(colors.HexColor('#D6EAF8'))
    c.rect(cx - mw / 2, base_y, mw, mh, fill=1, stroke=0)

    # Montagne principale (pic central)
    p = c.beginPath()
    p.moveTo(cx - mw / 2, base_y)           # base gauche
    p.lineTo(cx - mw * 0.12, y_top)         # sommet principal
    p.lineTo(cx + mw / 2, base_y)           # base droite
    p.close()
    c.setFillColor(colors.HexColor('#2E7D32'))
    c.drawPath(p, fill=1, stroke=0)

    # Montagne secondaire (gauche, plus petite)
    p2 = c.beginPath()
    p2.moveTo(cx - mw / 2, base_y)
    p2.lineTo(cx - mw * 0.28, y_top - mh * 0.30)
    p2.lineTo(cx - mw * 0.05, base_y)
    p2.close()
    c.setFillColor(colors.HexColor('#388E3C'))
    c.drawPath(p2, fill=1, stroke=0)

    # Montagne secondaire (droite)
    p3 = c.beginPath()
    p3.moveTo(cx + mw * 0.05, base_y)
    p3.lineTo(cx + mw * 0.30, y_top - mh * 0.35)
    p3.lineTo(cx + mw / 2, base_y)
    p3.close()
    c.setFillColor(colors.HexColor('#43A047'))
    c.drawPath(p3, fill=1, stroke=0)

    # Neige / nuage au sommet
    c.setFillColor(colors.HexColor('#E8F5E9'))
    peak_x = cx - mw * 0.12
    peak_y = y_top
    p4 = c.beginPath()
    p4.moveTo(peak_x - mw * 0.08, peak_y - mh * 0.12)
    p4.lineTo(peak_x, peak_y)
    p4.lineTo(peak_x + mw * 0.08, peak_y - mh * 0.12)
    p4.close()
    c.drawPath(p4, fill=1, stroke=0)

    # Soleil
    sun_x = cx + mw * 0.30
    sun_y = y_top - mh * 0.12
    c.setFillColor(colors.HexColor('#FCD116'))
    c.circle(sun_x, sun_y, size * 0.09, fill=1, stroke=0)

    # Bordure
    c.setStrokeColor(colors.HexColor('#333333'))
    c.setLineWidth(0.5)
    c.rect(cx - mw / 2, base_y, mw, mh, fill=0, stroke=1)

    # Texte
    c.setFont('Helvetica-Bold', 4)
    c.setFillColor(colors.HexColor('#333333'))
    c.drawCentredString(cx, base_y - 8, "MONT NIMBA")


def _draw_cover_half(c, x, y, w, h, ecole, eleve, parcours, logo, page_number):
    """Dessine la couverture (page 1) sur une demi-page GAUCHE."""
    c.setStrokeColor(colors.HexColor('#555555'))
    c.setLineWidth(1.5)
    c.rect(x, y, w, h)

    # Fond gris
    c.setFillColor(colors.HexColor('#E8E8E8'))
    c.rect(x + 1, y + 1, w - 2, h - 2, fill=1, stroke=0)

    pad = 10
    cx = x + w / 2
    top = y + h

    # --- IMAGES ALIGNEES : Drapeau (gauche) | Logo (centre) | Photo eleve (droite) ---
    img_row_y = top - 12          # haut de la rangee d'images
    img_h = 42                    # hauteur des images
    img_spacing = w * 0.28        # espacement depuis le centre

    # Drapeau de la Guinee (GAUCHE)
    _draw_guinea_flag(c, cx - img_spacing, img_row_y, flag_w=55, flag_h=img_h)

    # Logo de l'ecole (CENTRE)
    logo_size = img_h + 4
    if logo:
        try:
            c.drawImage(logo, cx - logo_size / 2, img_row_y - logo_size,
                        logo_size, logo_size,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    else:
        # Placeholder si pas de logo
        c.setStrokeColor(colors.HexColor('#999999'))
        c.setDash(2, 2)
        c.rect(cx - logo_size / 2, img_row_y - logo_size, logo_size, logo_size, stroke=1, fill=0)
        c.setDash()
        c.setFont('Helvetica', 5)
        c.setFillColor(colors.HexColor('#999999'))
        c.drawCentredString(cx, img_row_y - logo_size / 2, 'Logo')

    # Photo de l'eleve (DROITE)
    photo_w = img_h * 0.8
    photo_h = img_h
    photo_x = cx + img_spacing - photo_w / 2
    photo_y = img_row_y - photo_h
    photo_drawn = False
    try:
        if eleve.photo and hasattr(eleve.photo, 'path'):
            photo_reader = ImageReader(eleve.photo.path)
            c.drawImage(photo_reader, photo_x, photo_y, photo_w, photo_h,
                        preserveAspectRatio=True, mask='auto')
            photo_drawn = True
    except Exception:
        pass
    if not photo_drawn:
        # Placeholder si pas de photo
        c.setFillColor(colors.HexColor('#F0F0F0'))
        c.setStrokeColor(colors.HexColor('#888888'))
        c.setLineWidth(0.5)
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
        c.setFont('Helvetica', 5)
        c.setFillColor(colors.HexColor('#999999'))
        c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, 'Photo')
    # Bordure de la photo
    c.setStrokeColor(colors.HexColor('#555555'))
    c.setLineWidth(0.6)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)

    # Titre sous les images
    title_y = img_row_y - img_h - 18
    c.setFillColor(colors.HexColor('#222222'))
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(cx, title_y, "LIVRET SCOLAIRE")

    # Ligne decorative tricolore sous le titre
    line_y = title_y - 6
    c.setStrokeColor(colors.HexColor('#CE1126'))
    c.setLineWidth(1.5)
    c.line(cx - 80, line_y, cx + 80, line_y)
    c.setStrokeColor(colors.HexColor('#FCD116'))
    c.line(cx - 60, line_y - 3, cx + 60, line_y - 3)
    c.setStrokeColor(colors.HexColor('#009460'))
    c.setLineWidth(1.5)
    c.line(cx - 80, line_y - 6, cx + 80, line_y - 6)

    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#222222'))
    ty = line_y - 18
    c.drawCentredString(cx, ty, "REPUBLIQUE DE GUINEE")
    ty -= 11
    c.setFont('Helvetica', 7)
    c.drawCentredString(cx, ty, "Ministere de l'Enseignement Pre-Universitaire")
    ty -= 9
    c.drawCentredString(cx, ty, "et de l'Alphabetisation")
    ty -= 10
    c.setFont('Helvetica-Oblique', 6.5)
    c.setFillColor(colors.HexColor('#555555'))
    c.drawCentredString(cx, ty, "Travail - Justice - Solidarite")
    ty -= 16

    # Ligne separatrice
    c.setStrokeColor(colors.HexColor('#999999'))
    c.setLineWidth(0.5)
    c.line(x + pad, ty + 5, x + w - pad, ty + 5)

    # Ecole
    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(colors.HexColor('#222222'))
    c.drawCentredString(cx, ty - 6, _s(ecole.nom))
    ty -= 20

    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#333333'))
    for label, val in [
        ("IRE/DEV", ecole.ire), ("DPE/DCE", ecole.dpe),
        ("DSEE", ecole.desee), ("Adresse", ecole.adresse),
        ("Tel", ecole.telephone),
    ]:
        if val:
            c.drawCentredString(cx, ty, f"{label}: {_s(val)}")
            ty -= 10
    ty -= 8

    # Cadre eleve (fond blanc avec bordure)
    box_w = w - 2 * pad
    box_h = 95
    box_x = x + pad
    box_y = ty - box_h
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor('#888888'))
    c.setLineWidth(1)
    c.rect(box_x, box_y, box_w, box_h, fill=1, stroke=1)

    # Bande de titre du cadre eleve
    c.setFillColor(colors.HexColor('#555555'))
    c.rect(box_x, box_y + box_h - 16, box_w, 16, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(colors.white)
    c.drawCentredString(cx, box_y + box_h - 13, "IDENTIFICATION DE L'ELEVE")

    c.setFillColor(colors.HexColor('#222222'))
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(cx, box_y + box_h - 32,
                        f"{_s(eleve.nom)} {_s(eleve.prenom)}")
    c.setFont('Helvetica', 8)
    c.drawCentredString(cx, box_y + box_h - 46, f"Matricule: {eleve.matricule}")
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '-'
    lieu = _s(getattr(eleve, 'lieu_naissance', '') or '')
    c.drawCentredString(cx, box_y + box_h - 58, f"Ne(e) le {dn}  a {lieu}")
    sexe_txt = 'Masculin' if getattr(eleve, 'sexe', '') == 'M' else 'Feminin'
    c.drawCentredString(cx, box_y + box_h - 70, f"Sexe: {sexe_txt}")
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#555555'))
    c.drawCentredString(cx, box_y + box_h - 84,
                        f"Parcours : {len(parcours)} annee(s)")

    # Numero de page
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#555555'))
    c.drawCentredString(cx, y + 5, f"-{page_number}-")


def _draw_fiche_sante_half(c, x, y, w, h, eleve, page_number):
    """Dessine la fiche de sante (derniere page du depliant) sur une demi-page DROITE."""
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h)

    pad = 6
    lx = x + pad
    rx = x + w - pad
    cx = x + w / 2
    top = y + h

    # Titre
    cy = top - 15
    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawCentredString(cx, cy, "FICHE DE SANTE DE L'ELEVE")

    cy -= 5
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor('#003d82'))
    c.line(lx, cy, rx, cy)

    # Infos generales
    cy -= 16
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(colors.black)
    c.drawString(lx, cy, f"Nom et Prenom : {_s(eleve.nom)} {_s(eleve.prenom)}")

    cy -= 14
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else ''
    c.drawString(lx, cy, f"Date de naissance : {dn}")
    c.drawString(lx + w * 0.5, cy, f"Sexe : {'M' if getattr(eleve, 'sexe', '') == 'M' else 'F'}")

    # Tableau de sante
    cy -= 18
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "Etat de sante general")

    cy -= 5
    fields = [
        ("Groupe sanguin", "............"),
        ("Allergies connues", "............................................"),
        ("Maladies chroniques", "............................................"),
        ("Traitements en cours", "............................................"),
        ("Vaccinations a jour", "Oui ......    Non ......"),
        ("Handicap / Deficience", "............................................"),
        ("Porte des lunettes", "Oui ......    Non ......"),
        ("Observations medicales", "............................................"),
    ]
    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    for label, val in fields:
        cy -= 14
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(lx, cy, f"{label} :")
        c.setFont('Helvetica', 6.5)
        c.drawString(lx + w * 0.35, cy, val)

    # Personne a contacter en cas d'urgence
    cy -= 22
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "Personne a contacter en cas d'urgence")

    urgence_fields = [
        ("Nom et Prenom", "............................................"),
        ("Lien de parente", "............................................"),
        ("Telephone", "............................................"),
        ("Adresse", "............................................"),
    ]
    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    for label, val in urgence_fields:
        cy -= 14
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(lx, cy, f"{label} :")
        c.setFont('Helvetica', 6.5)
        c.drawString(lx + w * 0.30, cy, val)

    # Tableau suivi annuel
    cy -= 22
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "Suivi medical annuel")

    cy -= 5
    suivi_header = ['Annee', 'Taille', 'Poids', 'Observations', 'Visa Medical']
    suivi_data = [suivi_header]
    for _ in range(4):
        suivi_data.append(['', '', '', '', ''])

    col_w_s = [w * 0.15, w * 0.12, w * 0.12, w * 0.35, w * 0.20]
    diff_s = w - 2 * pad - sum(col_w_s)
    col_w_s[-1] += diff_s
    rh_s = 16
    table_s = Table(suivi_data, colWidths=col_w_s, rowHeights=[rh_s] * len(suivi_data))
    table_s.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
    ]))
    th_s = rh_s * len(suivi_data)
    table_s.wrapOn(c, w - 2 * pad, th_s + 10)
    table_s.drawOn(c, lx, cy - th_s)

    # Numero de page
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(cx, y + 3, f"-{page_number}-")


def _draw_renseignements_parents_half(c, x, y, w, h, eleve, page_number):
    """Dessine les renseignements des parents (page 2 du depliant)."""
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h)

    pad = 6
    lx = x + pad
    rx = x + w - pad
    cx = x + w / 2
    top = y + h

    # Titre
    cy = top - 15
    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawCentredString(cx, cy, "RENSEIGNEMENTS SUR LES PARENTS")

    cy -= 5
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.HexColor('#003d82'))
    c.line(lx, cy, rx, cy)

    # Infos eleve recap
    cy -= 16
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(colors.black)
    c.drawString(lx, cy, f"Eleve : {_s(eleve.nom)} {_s(eleve.prenom)}")
    c.drawString(lx + w * 0.5, cy, f"Matricule : {eleve.matricule}")

    # ------- PERE / Responsable principal -------
    cy -= 22
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "PERE / RESPONSABLE PRINCIPAL")
    cy -= 3
    c.setLineWidth(0.3)
    c.line(lx, cy, rx, cy)

    resp1 = getattr(eleve, 'responsable_principal', None)

    pere_fields = [
        ("Nom et Prenom", f"{_s(resp1.nom)} {_s(resp1.prenom)}" if resp1 else "............................................"),
        ("Lien de parente", _s(resp1.get_relation_display()) if resp1 else "............................................"),
        ("Profession", _s(resp1.profession) if resp1 and resp1.profession else "............................................"),
        ("Telephone", _s(resp1.telephone) if resp1 else "............................................"),
        ("Adresse", _s(resp1.adresse) if resp1 else "............................................"),
        ("Email", _s(resp1.email) if resp1 and resp1.email else "............................................"),
    ]

    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    for label, val in pere_fields:
        cy -= 14
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(lx, cy, f"{label} :")
        c.setFont('Helvetica', 6.5)
        c.drawString(lx + w * 0.28, cy, val)

    # ------- MERE / Responsable secondaire -------
    cy -= 22
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "MERE / RESPONSABLE SECONDAIRE")
    cy -= 3
    c.setLineWidth(0.3)
    c.setStrokeColor(colors.HexColor('#003d82'))
    c.line(lx, cy, rx, cy)

    resp2 = getattr(eleve, 'responsable_secondaire', None)

    mere_fields = [
        ("Nom et Prenom", f"{_s(resp2.nom)} {_s(resp2.prenom)}" if resp2 else "............................................"),
        ("Lien de parente", _s(resp2.get_relation_display()) if resp2 else "............................................"),
        ("Profession", _s(resp2.profession) if resp2 and resp2.profession else "............................................"),
        ("Telephone", _s(resp2.telephone) if resp2 else "............................................"),
        ("Adresse", _s(resp2.adresse) if resp2 else "............................................"),
    ]

    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    for label, val in mere_fields:
        cy -= 14
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(lx, cy, f"{label} :")
        c.setFont('Helvetica', 6.5)
        c.drawString(lx + w * 0.28, cy, val)

    # ------- SITUATION FAMILIALE -------
    cy -= 22
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "ADRESSE ET SITUATION FAMILIALE")
    cy -= 3
    c.setLineWidth(0.3)
    c.line(lx, cy, rx, cy)

    sit_fields = [
        ("Adresse de l'eleve", "............................................"),
        ("Quartier / Secteur", "............................................"),
        ("Ville", "............................................"),
        ("Nombre de freres/soeurs", "............................................"),
        ("Rang dans la fratrie", "............................................"),
        ("Vit avec", "Pere ......  Mere ......  Tuteur ......"),
        ("Observations", "............................................"),
    ]

    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    for label, val in sit_fields:
        cy -= 14
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(lx, cy, f"{label} :")
        c.setFont('Helvetica', 6.5)
        c.drawString(lx + w * 0.35, cy, val)

    # Numero de page
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(cx, y + 3, f"-{page_number}-")


# ==============================================================================
#  COLLECTE DES DONNEES DU PARCOURS
# ==============================================================================

def _collecter_parcours_eleve(eleve, ecole):
    """Collecte tout le parcours d'un eleve."""
    parcours = []
    annees_classes = {}

    # Via l'historique
    try:
        historiques = HistoriqueEleve.objects.filter(
            eleve=eleve, action='CHANGEMENT_CLASSE'
        ).order_by('date_action')

        for h in historiques:
            desc = h.description or ''
            match_annee = re.search(r'(\d{4}-\d{4})', desc)
            if match_annee:
                annee = match_annee.group(1)
                match_classe = re.search(r':\s*(.+?)\s*(?:->|\u2192)', desc)
                if match_classe and annee not in annees_classes:
                    parts = annee.split('-')
                    try:
                        prev_annee = f"{int(parts[0])-1}-{int(parts[1])-1}"
                    except Exception:
                        prev_annee = annee
                    annees_classes[prev_annee] = match_classe.group(1).strip()
    except Exception as e:
        logger.warning(f"Erreur lecture historique eleve {eleve.pk}: {e}")

    # Classe actuelle
    if eleve.classe:
        annees_classes[eleve.classe.annee_scolaire] = eleve.classe.nom

    # Via les Classements
    try:
        for cl in Classement.objects.filter(eleve=eleve).order_by('annee_scolaire'):
            if cl.annee_scolaire not in annees_classes:
                annees_classes[cl.annee_scolaire] = cl.classe.nom if cl.classe else '?'
    except Exception as e:
        logger.warning(f"Erreur lecture classements eleve {eleve.pk}: {e}")

    for annee_scolaire in sorted(annees_classes.keys()):
        classe_nom = annees_classes[annee_scolaire]
        niveau = detecter_niveau_scolaire(classe_nom)
        sur = 10 if niveau == 'PRIMAIRE' else 20
        is_semestre = niveau in ('COLLEGE', 'LYCEE')

        search_nom = classe_nom.split('(')[0].strip()[:15]
        classe_note = ClasseNote.objects.filter(
            ecole=ecole, annee_scolaire=annee_scolaire,
            nom__icontains=search_nom
        ).first()
        if not classe_note:
            classe_note = ClasseNote.objects.filter(
                ecole=ecole, annee_scolaire=annee_scolaire,
            ).first()

        matieres_data = []
        moyenne_annuelle = None
        rang_info = ''
        passe_en = ''

        if classe_note:
            matieres = MatiereNote.objects.filter(
                classe=classe_note, actif=True
            ).order_by('nom')

            for mat in matieres:
                m_data = {'nom': mat.nom, 'coef': float(mat.coefficient)}

                if is_semestre:
                    for sem_num, mois_list, prefix in [
                        (1, ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER'], 'sem1'),
                        (2, ['MARS', 'AVRIL', 'MAI', 'JUIN'], 'sem2'),
                    ]:
                        notes = NoteMensuelle.objects.filter(
                            eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                            mois__in=mois_list
                        )
                        compo = CompositionNote.objects.filter(
                            eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                            periode=f'SEMESTRE_{sem_num}'
                        ).first()

                        moy = None
                        if notes.exists():
                            vals = [float(n.note) for n in notes if n.note is not None]
                            moy = round(sum(vals) / len(vals), 2) if vals else None

                        compo_val = float(compo.note) if compo and compo.note is not None else None
                        sem_moy = None
                        if moy is not None and compo_val is not None:
                            sem_moy = round(moy * 0.4 + compo_val * 0.6, 2)
                        elif moy is not None:
                            sem_moy = moy
                        elif compo_val is not None:
                            sem_moy = compo_val

                        m_data[f'{prefix}_moy'] = moy
                        m_data[f'{prefix}_compo'] = compo_val
                        m_data[f'{prefix}_moyenne'] = sem_moy
                else:
                    for i, (t_label, mois_list) in enumerate([
                        ('t1', ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE']),
                        ('t2', ['JANVIER', 'FEVRIER', 'MARS']),
                        ('t3', ['AVRIL', 'MAI', 'JUIN']),
                    ], 1):
                        notes_t = NoteMensuelle.objects.filter(
                            eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                            mois__in=mois_list
                        )
                        compo_t = CompositionNote.objects.filter(
                            eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                            periode=f'TRIMESTRE_{i}'
                        ).first()

                        moy_t = None
                        if notes_t.exists():
                            vals = [float(n.note) for n in notes_t if n.note is not None]
                            moy_t = round(sum(vals) / len(vals), 2) if vals else None

                        compo_t_val = float(compo_t.note) if compo_t and compo_t.note is not None else None
                        final_t = None
                        if moy_t is not None and compo_t_val is not None:
                            final_t = round(moy_t * 0.4 + compo_t_val * 0.6, 2)
                        elif moy_t is not None:
                            final_t = moy_t
                        elif compo_t_val is not None:
                            final_t = compo_t_val

                        m_data[f'{t_label}_moy'] = final_t
                        m_data[f'{t_label}_compo'] = compo_t_val

                matieres_data.append(m_data)

            # Moyenne annuelle via Classement
            cl_ann = Classement.objects.filter(
                eleve=eleve, classe=classe_note, annee_scolaire=annee_scolaire,
                periode__icontains='ANNUEL'
            ).first()

            if cl_ann:
                moyenne_annuelle = float(cl_ann.moyenne_generale)
                rang_info = cl_ann.rang_formate or f"{cl_ann.rang}eme/{cl_ann.effectif}"
            else:
                cls_p = Classement.objects.filter(
                    eleve=eleve, classe=classe_note, annee_scolaire=annee_scolaire,
                ).exclude(periode__icontains='ANNUEL')
                if cls_p.exists():
                    moyennes = [float(cp.moyenne_generale) for cp in cls_p if cp.moyenne_generale]
                    if moyennes:
                        moyenne_annuelle = round(sum(moyennes) / len(moyennes), 2)

        try:
            from eleves.views_nouvelle_annee import PROGRESSION_CLASSES, PROGRESSION_LABELS, _normaliser
            base_norm = _normaliser(classe_nom.split('(')[0].strip())
            next_base = PROGRESSION_CLASSES.get(base_norm)
            if next_base:
                passe_en = PROGRESSION_LABELS.get(next_base, next_base)
        except Exception:
            pass

        parcours.append({
            'annee_scolaire': annee_scolaire,
            'classe_nom': classe_nom,
            'niveau': niveau,
            'cycle': niveau,
            'sur': sur,
            'is_semestre': is_semestre,
            'matieres_data': matieres_data,
            'moyenne_annuelle': moyenne_annuelle,
            'rang': rang_info,
            'passe_en': passe_en,
        })

    return parcours


# ==============================================================================
#  GENERATION PDF COMPLETE
# ==============================================================================

def _draw_synthese_half(c, x, y_base, w, h, ecole, eleve, parcours, page_number):
    """Dessine la page de synthese/rapport final sur une demi-page."""
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y_base, w, h)

    pad = 6
    lx = x + pad
    cx = x + w / 2
    top = y_base + h
    usable_w = w - 2 * pad

    # Titre
    cy = top - 15
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawCentredString(cx, cy, "ANALYSE ET RAPPORT FINAL")

    cy -= 12
    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    c.drawCentredString(cx, cy,
                        f"Eleve : {_s(eleve.nom)} {_s(eleve.prenom)}"
                        f"  -  Matricule : {eleve.matricule}")

    # Synthese par cycle
    cycles_data = {}
    for p in parcours:
        cycle = p['cycle']
        if cycle not in cycles_data:
            cycles_data[cycle] = []
        cycles_data[cycle].append(p)

    cy -= 14
    for cycle_key, cycle_entries in cycles_data.items():
        cycle_label = CYCLE_LABELS.get(cycle_key, cycle_key)
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(colors.HexColor('#003d82'))
        c.drawString(lx, cy, cycle_label)
        cy -= 10

        synth_data = [['Annee', 'Classe', 'Moy. Ann.', 'Classement', 'Obs.']]
        for p in cycle_entries:
            moy_txt = f"{p['moyenne_annuelle']:.2f}/{p['sur']}" if p['moyenne_annuelle'] else '-'
            seuil = 5.0 if p['sur'] == 10 else 10.0
            if p['moyenne_annuelle'] and p['moyenne_annuelle'] >= seuil:
                obs = 'Admis(e)'
            elif p['moyenne_annuelle']:
                obs = 'Non admis(e)'
            else:
                obs = '-'
            synth_data.append([
                p['annee_scolaire'], _s(p['classe_nom']),
                moy_txt, p['rang'] or '-', obs
            ])

        moyennes_cycle = [p['moyenne_annuelle'] for p in cycle_entries if p['moyenne_annuelle']]
        if moyennes_cycle:
            moy_cycle = round(sum(moyennes_cycle) / len(moyennes_cycle), 2)
            sur_cycle = cycle_entries[0]['sur']
            synth_data.append(['', 'MOY. CYCLE', f'{moy_cycle:.2f}/{sur_cycle}', '', ''])

        col_w = [usable_w * 0.16, usable_w * 0.24, usable_w * 0.20,
                 usable_w * 0.20, usable_w * 0.20]
        rh = 13
        table = Table(synth_data, colWidths=col_w, rowHeights=[rh] * len(synth_data))
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#555555')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003d82')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eef5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        th = rh * len(synth_data)
        table.wrapOn(c, usable_w, th + 5)
        table.drawOn(c, lx, cy - th)
        cy -= th + 10

    # ORIENTATION
    cy -= 4
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(lx, cy, "PROPOSITION D'ORIENTATION")
    cy -= 10

    orientation = _calculer_orientation(parcours)
    c.setFont('Helvetica', 5.5)
    c.setFillColor(colors.black)
    for line in orientation:
        if cy < y_base + 55:
            break
        c.drawString(lx + 4, cy, line)
        cy -= 9

    # Signatures
    sig_y = y_base + 30
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(colors.black)
    c.drawString(lx, sig_y, "Le Directeur / Proviseur :")
    c.drawString(cx, sig_y, "Le Censeur :")
    sig_y -= 10
    c.setFont('Helvetica', 6)
    c.drawString(lx, sig_y, f"Nom: {_s(ecole.directeur) if ecole.directeur else ''}")
    if ecole.censeur:
        c.drawString(cx, sig_y, f"Nom: {_s(ecole.censeur)}")
    sig_y -= 12
    c.drawString(lx, sig_y, "Signature et cachet :")
    c.drawString(cx, sig_y, "Signature :")

    # Numero de page
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(cx, y_base + 3, f"-{page_number}-")


def _draw_blank_half(c, x, y, w, h, page_number):
    """Dessine une demi-page vide (remplissage pour multiple de 4)."""
    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.setDash(3, 3)
    c.rect(x, y, w, h)
    c.setDash()
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#999999'))
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")


def _generer_livret_pdf(eleve, ecole, parcours):
    """Genere le PDF du livret scolaire en IMPOSITION CAHIER (booklet).

    Le PDF est genere pour impression recto-verso et agrafage au milieu.
    Quand on plie les feuilles et qu'on agrafe, les pages se suivent dans
    l'ordre de lecture : 1, 2, 3, 4, ..., N.

    Ordre de lecture des demi-pages :
      Page 1 : Couverture (face avant)
      Page 2 : Renseignements parents
      Pages 3..N-2 : Niveaux scolaires du parcours
      Page N-1 : Analyse et rapport final
      Page N : Fiche de sante (face arriere / dos du livret)

    Imposition cahier (N pages, multiple de 4) :
      Feuille 1 recto : page N (gauche) | page 1 (droite)
      Feuille 1 verso : page 2 (gauche) | page N-1 (droite)
      Feuille 2 recto : page N-2 (gauche) | page 3 (droite)
      Feuille 2 verso : page 4 (gauche) | page N-3 (droite)
      ...
    """
    buffer = io.BytesIO()
    width, height = landscape(A4)  # 842 x 595
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle(f"Livret Scolaire - {_s(eleve.nom)} {_s(eleve.prenom)}")

    margin = 10
    gap = 6
    half_w = (width - 2 * margin - gap) / 2
    usable_h = height - 2 * margin
    left_x = margin
    right_x = margin + half_w + gap
    logo = _get_logo_reader(ecole)

    # =====================================================================
    # 1) Construire la liste des demi-pages dans l'ORDRE DE LECTURE
    #    Chaque element est un callable : fn(c, x, y, w, h, page_number)
    #    ou None pour une page vide (remplissage)
    # =====================================================================
    logical_pages = []

    # Page 1 : Couverture
    logical_pages.append(
        lambda c, x, y, w, h, pn: _draw_cover_half(
            c, x, y, w, h, ecole, eleve, parcours, logo, pn))

    # Page 2 : Renseignements parents
    logical_pages.append(
        lambda c, x, y, w, h, pn: _draw_renseignements_parents_half(
            c, x, y, w, h, eleve, pn))

    # Pages 3+ : Niveaux scolaires du parcours
    for entry in parcours:
        logical_pages.append(
            lambda c, x, y, w, h, pn, e=entry: _draw_half_page(
                c, x, y, w, h, ecole, e, eleve, pn))

    # Avant-derniere page : Synthese / rapport final
    logical_pages.append(
        lambda c, x, y, w, h, pn: _draw_synthese_half(
            c, x, y, w, h, ecole, eleve, parcours, pn))

    # Derniere page : Fiche de sante (dos du livret)
    logical_pages.append(
        lambda c, x, y, w, h, pn: _draw_fiche_sante_half(
            c, x, y, w, h, eleve, pn))

    # =====================================================================
    # 2) Completer a un multiple de 4 (necessaire pour l'imposition cahier)
    # =====================================================================
    while len(logical_pages) % 4 != 0:
        logical_pages.append(None)  # page vide

    N = len(logical_pages)

    # =====================================================================
    # 3) Generer le PDF en IMPOSITION CAHIER
    #    Pour chaque feuille k (0-indexed) :
    #      Recto : page[N-1 - 2k] a gauche | page[2k] a droite
    #      Verso : page[2k + 1] a gauche   | page[N-2 - 2k] a droite
    # =====================================================================
    num_sheets = N // 4

    for k in range(num_sheets):
        # --- RECTO de la feuille k ---
        li = N - 1 - 2 * k   # index page gauche
        ri = 2 * k            # index page droite

        # Gauche
        pn = li + 1
        if logical_pages[li] is not None:
            logical_pages[li](c, left_x, margin, half_w, usable_h, pn)
        else:
            _draw_blank_half(c, left_x, margin, half_w, usable_h, pn)

        # Droite
        pn = ri + 1
        if logical_pages[ri] is not None:
            logical_pages[ri](c, right_x, margin, half_w, usable_h, pn)
        else:
            _draw_blank_half(c, right_x, margin, half_w, usable_h, pn)

        c.showPage()

        # --- VERSO de la feuille k ---
        li = 2 * k + 1        # index page gauche
        ri = N - 2 - 2 * k    # index page droite

        # Gauche
        pn = li + 1
        if logical_pages[li] is not None:
            logical_pages[li](c, left_x, margin, half_w, usable_h, pn)
        else:
            _draw_blank_half(c, left_x, margin, half_w, usable_h, pn)

        # Droite
        pn = ri + 1
        if logical_pages[ri] is not None:
            logical_pages[ri](c, right_x, margin, half_w, usable_h, pn)
        else:
            _draw_blank_half(c, right_x, margin, half_w, usable_h, pn)

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


def _calculer_orientation(parcours):
    """Propose une orientation automatique."""
    if not parcours:
        return ["Aucune donnee disponible pour proposer une orientation."]

    derniere = parcours[-1]
    moyennes_all = [p['moyenne_annuelle'] for p in parcours if p['moyenne_annuelle']]
    if not moyennes_all:
        return ["Aucune moyenne disponible pour proposer une orientation."]

    moy_globale = round(sum(moyennes_all) / len(moyennes_all), 2)
    sur = derniere['sur']
    seuil = 5.0 if sur == 10 else 10.0

    lines = [
        f"- Moyenne generale du parcours : {moy_globale:.2f}/{sur}",
        f"- Nombre d'annees evaluees : {len(moyennes_all)}",
        f"- Derniere classe : {_s(derniere['classe_nom'])} ({derniere['annee_scolaire']})",
    ]

    if derniere['matieres_data']:
        mats_avg = []
        for m in derniere['matieres_data']:
            vals = []
            for key in ['sem1_moyenne', 'sem2_moyenne', 't1_moy', 't2_moy', 't3_moy']:
                v = m.get(key)
                if v is not None:
                    vals.append(float(v))
            if vals:
                mats_avg.append((_s(m['nom']), round(sum(vals) / len(vals), 2)))
        if mats_avg:
            mats_avg.sort(key=lambda x: x[1], reverse=True)
            top_3 = mats_avg[:3]
            lines.append(f"- Points forts : {', '.join(f'{n} ({v:.1f})' for n, v in top_3)}")

    lines.append("")
    if moy_globale >= seuil * 1.6:
        lines.append(">> ORIENTATION PROPOSEE : Filiere d'excellence - Sciences ou Lettres")
        lines.append("   Profil academique excellent propice aux filieres selectives.")
    elif moy_globale >= seuil * 1.3:
        lines.append(">> ORIENTATION PROPOSEE : Filiere scientifique ou litteraire")
        lines.append("   Solides capacites dans l'ensemble des disciplines.")
    elif moy_globale >= seuil:
        lines.append(">> ORIENTATION PROPOSEE : Filiere generale avec soutien cible")
        lines.append("   Niveau requis atteint, accompagnement recommande.")
    else:
        lines.append(">> ORIENTATION PROPOSEE : Redoublement ou filiere professionnelle")
        lines.append("   Renforcement des acquis necessaire avant progression.")

    return lines


# ==============================================================================
#  VUES DJANGO
# ==============================================================================

@login_required
def livret_scolaire_selection(request):
    """Page de selection."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune ecole associee a votre compte.")
        return redirect('notes:tableau_bord')

    from eleves.utils_annee import get_annee_active
    annee_active = get_annee_active(request, ecole)

    classes = Classe.objects.filter(ecole=ecole)
    if annee_active:
        classes = classes.filter(annee_scolaire=annee_active)
    classes = classes.order_by('niveau', 'nom')

    classe_id = request.GET.get('classe_id')
    eleves = []
    classe_selected = None
    if classe_id:
        try:
            classe_selected = classes.get(pk=classe_id)
            eleves = Eleve.objects.filter(
                classe=classe_selected, statut='ACTIF'
            ).order_by('nom', 'prenom')
        except Classe.DoesNotExist:
            pass

    context = {
        'ecole': ecole,
        'classes': classes,
        'classe_selected': classe_selected,
        'eleves': eleves,
        'annee_active': annee_active,
        'titre_page': 'Livrets Scolaires',
    }
    return render(request, 'notes/livret_scolaire_selection.html', context)


@login_required
def livret_scolaire_pdf(request, eleve_id):
    """Genere le livret scolaire PDF d'un eleve."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune ecole associee a votre compte.")
        return redirect('notes:tableau_bord')

    eleve = get_object_or_404(Eleve, pk=eleve_id)

    if not filter_by_user_school(
        Eleve.objects.filter(pk=eleve_id), request.user, 'classe__ecole'
    ).exists():
        messages.error(request, "Acces non autorise a cet eleve.")
        return redirect('notes:livret_scolaire')

    try:
        parcours = _collecter_parcours_eleve(eleve, ecole)
        if not parcours:
            messages.warning(request,
                             f"Aucune donnee de parcours trouvee pour {eleve.nom} {eleve.prenom}.")
            return redirect('notes:livret_scolaire')

        pdf_buffer = _generer_livret_pdf(eleve, ecole, parcours)
        filename = f"Livret_Scolaire_{_s(eleve.nom)}_{_s(eleve.prenom)}.pdf"
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Erreur generation livret eleve {eleve_id}: {e}", exc_info=True)
        messages.error(request, f"Erreur lors de la generation du livret : {e}")
        return redirect('notes:livret_scolaire')


@login_required
def livret_scolaire_classe_pdf(request, classe_id):
    """Genere les livrets scolaires de tous les eleves d'une classe."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune ecole associee.")
        return redirect('notes:tableau_bord')

    classe = get_object_or_404(Classe, pk=classe_id, ecole=ecole)
    eleves_qs = Eleve.objects.filter(
        classe=classe, statut='ACTIF'
    ).order_by('nom', 'prenom')

    if not eleves_qs.exists():
        messages.warning(request, f"Aucun eleve actif dans la classe {classe.nom}.")
        return redirect('notes:livret_scolaire')

    for eleve in eleves_qs:
        try:
            parcours = _collecter_parcours_eleve(eleve, ecole)
            if parcours:
                pdf_buffer = _generer_livret_pdf(eleve, ecole, parcours)
                filename = f"Livret_{_s(classe.nom)}_{_s(eleve.nom)}.pdf"
                response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            logger.error(f"Erreur livret classe eleve {eleve.pk}: {e}", exc_info=True)
            continue

    messages.warning(request, "Aucune donnee disponible.")
    return redirect('notes:livret_scolaire')
