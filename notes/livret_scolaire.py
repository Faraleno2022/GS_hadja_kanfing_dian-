"""
Livret Scolaire - Generation PDF du parcours complet d'un eleve.
Format officiel guineen : paysage A4, deux niveaux par page.

Primaire : Matieres | 1er Trim | 2eme Trim | 3eme Trim | Moy. Annuelle | Observations
College/Lycee : Matieres | Coef | 1er Sem (Moy Cours | Compo | Moy Sem) | 2eme Sem (idem)
"""

import io
import re
import logging
from decimal import Decimal
from datetime import datetime

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
#  CONSTANTES & COULEURS
# ==============================================================================

BLEU_FONCE = colors.HexColor('#003d82')
BLEU_CLAIR = colors.HexColor('#e8eef5')
GRIS_TEXTE = colors.HexColor('#333333')
GRIS_LIGNE = colors.HexColor('#555555')
GRIS_CLAIR = colors.HexColor('#f5f5f5')
GRIS_SEP   = colors.HexColor('#cccccc')

CYCLE_LABELS = {
    'MATERNELLE': 'Cycle Maternelle',
    'PRIMAIRE':   'Cycle Primaire',
    'COLLEGE':    'Cycle College',
    'LYCEE':      'Cycle Lycee / Terminale',
}


# ==============================================================================
#  UTILITAIRES
# ==============================================================================

def _s(val):
    """Convertit en string safe pour Helvetica (ASCII)."""
    if val is None:
        return ''
    return str(val)


def _get_logo_reader(ecole):
    """Retourne un ImageReader pour le logo de l'ecole, ou None."""
    try:
        if ecole.logo and hasattr(ecole.logo, 'path'):
            return ImageReader(ecole.logo.path)
    except Exception:
        pass
    return None


def _fmt(v):
    """Formate une note pour affichage."""
    if v is None:
        return ''
    try:
        return f'{float(v):.2f}'
    except (ValueError, TypeError):
        return ''


# ==============================================================================
#  DESSIN D'UNE DEMI-PAGE PRIMAIRE
#  Format exact : IRE/DEV ... DPE/DCE
#  Ecole Primaire de ...
#  Date d'entree / Venant de / References certificat
#  [Classe : X] [Annee scolaire]
#  Maitre : ...
#  Tableau sans Coef : Matieres | 1er Trim | 2eme Trim | 3eme Trim | Moy Ann | Obs
#  Moyenne Annuelle /20  Classement /eleves
#  Passe en classe superieure    Remis a ses parents
#  Appreciations Generales | Date | Signature du Directeur
# ==============================================================================

def _draw_half_primaire(c, x, y, w, h, ecole, entry, eleve):
    """Dessine une demi-page format PRIMAIRE."""
    classe_nom = entry['classe_nom']
    annee = entry['annee_scolaire']
    matieres = entry['matieres_data']
    sur = entry['sur']
    moy_ann = entry['moyenne_annuelle']
    rang = entry['rang']
    passe_en = entry['passe_en']

    # Cadre principal
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.0)
    c.rect(x, y, w, h)

    top = y + h
    pad = 4
    lx = x + pad
    rx = x + w - pad

    # --- EN-TETE : IRE/DEV ........... DPE/DCE ........... ---
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    ey = top - 10
    c.drawString(lx, ey, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, ey, f"DPE/DCE : {_s(ecole.dpe)}")

    ey -= 9
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(lx, ey, f"Ecole Primaire de : {_s(ecole.nom)}")
    if ecole.desee:
        c.setFont('Helvetica', 5.5)
        c.drawRightString(rx, ey, f"DSEE : {_s(ecole.desee)}")

    ey -= 8
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ey, "Date d'entree : ........................")
    c.drawString(lx + w * 0.4, ey, "Venant de : ........................")

    ey -= 8
    c.drawString(lx, ey, "References du Certificat de transfert : ........................")

    # Ligne separatrice
    ey -= 4
    c.setLineWidth(0.5)
    c.line(x, ey, x + w, ey)

    # --- ENCADRE CLASSE / ANNEE SCOLAIRE ---
    ey -= 14
    # Cadre Classe
    cls_w = w * 0.45
    cls_h = 13
    c.setLineWidth(1.0)
    c.rect(lx, ey, cls_w, cls_h)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(lx + cls_w / 2, ey + 3, f"Classe : {_s(classe_nom)}")

    # Annee scolaire a droite
    c.setFont('Helvetica-Bold', 7)
    c.drawString(lx + cls_w + 10, ey + 3, f"Annee scolaire : {annee}")

    # --- MAITRE ---
    ey -= 12
    c.setFont('Helvetica-Bold', 6)
    c.drawString(lx, ey, "Maitre : ..................................................................")

    ey -= 5
    c.setLineWidth(0.3)
    c.line(x, ey, x + w, ey)

    # --- TABLEAU DES NOTES (SANS COEF) ---
    # Colonnes : Matieres | 1er Trim | 2eme Trim | 3eme Trim | Moy Annuelle | Observations
    header = ['Matieres', '1er\nTrimestre', '2eme\nTrimestre', '3eme\nTrimestre',
              'Moyenne\nAnnuelle', 'Observations']
    col_ratios = [0.26, 0.13, 0.13, 0.13, 0.14, 0.21]
    col_widths = [w * r for r in col_ratios]
    # Ajuster
    diff = w - sum(col_widths)
    col_widths[-1] += diff

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

        data.append([
            _s(m['nom']), _fmt(t1), _fmt(t2), _fmt(t3), _fmt(m_ann), obs
        ])

    row_h = 9
    nb_rows = len(data)
    table = Table(data, colWidths=col_widths, rowHeights=[row_h + 3] + [row_h] * (nb_rows - 1))

    style_cmds = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 5),
        ('FONTSIZE', (0, 1), (-1, -1), 5.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), BLEU_CLAIR),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]
    table.setStyle(TableStyle(style_cmds))

    table_h = (row_h + 3) + row_h * (nb_rows - 1)
    table_y = ey - table_h - 2
    table.wrapOn(c, w, table_h + 10)
    table.drawOn(c, x, table_y)

    # --- PIED : Moyenne Annuelle /20   Classement /eleves ---
    fy = table_y - 10
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    moy_txt = _fmt(moy_ann) if moy_ann else '......'
    c.drawString(lx, fy, f"Moyenne Annuelle : {moy_txt} /{sur}")
    c.drawString(lx + w * 0.4, fy, f"Classement : {_s(rang) if rang else '......'}")
    c.drawRightString(rx, fy, "eleves")

    fy -= 9
    c.setFont('Helvetica', 5.5)
    passe_txt = _s(passe_en) if passe_en else '..................'
    c.drawString(lx, fy, f"Passe en classe superieure : {passe_txt}")
    c.drawString(lx + w * 0.6, fy, "Remis a ses parents :")

    # --- APPRECIATIONS GENERALES | Date | Signature du Directeur ---
    fy -= 5
    c.setLineWidth(0.5)
    c.line(x, fy, x + w, fy)

    fy -= 10
    # 3 colonnes
    col1_w = w * 0.40
    col2_w = w * 0.20
    col3_w = w * 0.40
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(lx, fy, "Appreciations Generales :")
    c.drawString(lx + col1_w, fy, "Date :")
    c.drawString(lx + col1_w + col2_w, fy, "Prenoms, Nom et")
    fy -= 7
    c.drawString(lx + col1_w + col2_w, fy, "Signature du Directeur")

    # Lignes verticales separatrices
    c.setLineWidth(0.3)
    c.line(x + col1_w, fy + 17, x + col1_w, fy - 2)
    c.line(x + col1_w + col2_w, fy + 17, x + col1_w + col2_w, fy - 2)


# ==============================================================================
#  DESSIN D'UNE DEMI-PAGE COLLEGE / LYCEE
#  Format exact : IRE/DEV ... DPE/DCE
#  College ...
#  Date d'entree / Venant de / Reference
#  [Classe : X] [Annee scolaire]
#  Tableau avec Coef : Matieres | Coef | 1er Sem (Moy Cours|Compo|Moy Sem) | 2eme Sem (idem)
#  Moyenne Annuelle /20  Classement /eleves
#  Passe en classe superieure    Remis a ses parents
#  Appreciations | Prenoms, Nom et Signature du Principal
# ==============================================================================

def _draw_half_college(c, x, y, w, h, ecole, entry, eleve):
    """Dessine une demi-page format COLLEGE/LYCEE (semestre)."""
    classe_nom = entry['classe_nom']
    annee = entry['annee_scolaire']
    matieres = entry['matieres_data']
    sur = entry['sur']
    moy_ann = entry['moyenne_annuelle']
    rang = entry['rang']
    passe_en = entry['passe_en']

    # Cadre principal
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.0)
    c.rect(x, y, w, h)

    top = y + h
    pad = 4
    lx = x + pad
    rx = x + w - pad

    # --- EN-TETE ---
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    ey = top - 10
    c.drawString(lx, ey, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, ey, f"DPE/DCE : {_s(ecole.dpe)}")

    ey -= 9
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(lx, ey, f"College : {_s(ecole.nom)}")
    if ecole.desee:
        c.setFont('Helvetica', 5.5)
        c.drawRightString(rx, ey, f"DSEE : {_s(ecole.desee)}")

    ey -= 8
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ey, "Date d'entree : .................")
    c.drawString(lx + w * 0.35, ey, "Venant de : .................")
    ey -= 8
    c.drawString(lx, ey, "Reference : .................")

    # Ligne separatrice
    ey -= 4
    c.setLineWidth(0.5)
    c.line(x, ey, x + w, ey)

    # --- ENCADRE CLASSE / ANNEE SCOLAIRE ---
    ey -= 14
    cls_w = w * 0.40
    cls_h = 13
    c.setLineWidth(1.0)
    c.rect(lx, ey, cls_w, cls_h)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(lx + cls_w / 2, ey + 3, f"Classe : {_s(classe_nom)}")

    c.setFont('Helvetica-Bold', 7)
    c.drawString(lx + cls_w + 10, ey + 3, f"Annee scolaire : {annee}")

    ey -= 5
    c.setLineWidth(0.3)
    c.line(x, ey, x + w, ey)

    # --- TABLEAU DES NOTES (AVEC COEF, SEMESTRES) ---
    # En-tete sur 2 lignes :
    # Ligne 1 : Matieres | Coef | 1er Semestre (span 3) | 2eme Semestre (span 3)
    # Ligne 2 : (vide)  | (vide)| Moy Cours | Compo | Moy Sem | Moy Cours | Compo | Moy Sem
    header1 = ['Matieres', 'Coef', '1er Semestre', '', '', '2eme Semestre', '', '']
    header2 = ['', '', 'Moyenne\nCours', 'Compo', 'Moyenne\nSemestre',
               'Moyenne\nCours', 'Compo', 'Moyenne\nSemestre']

    col_ratios = [0.20, 0.05, 0.11, 0.09, 0.11, 0.11, 0.09, 0.11]
    col_widths = [w * r for r in col_ratios]
    # Ajuster le reste
    diff_w = w - sum(col_widths)
    col_widths[0] += diff_w

    data = [header1, header2]
    for m in matieres:
        row = [
            _s(m['nom']),
            str(m.get('coef', '')),
            _fmt(m.get('sem1_moy')),
            _fmt(m.get('sem1_compo')),
            _fmt(m.get('sem1_moyenne')),
            _fmt(m.get('sem2_moy')),
            _fmt(m.get('sem2_compo')),
            _fmt(m.get('sem2_moyenne')),
        ]
        data.append(row)

    row_h = 9
    nb_rows = len(data)
    row_heights = [row_h + 2, row_h + 2] + [row_h] * (nb_rows - 2)
    table = Table(data, colWidths=col_widths, rowHeights=row_heights)

    style_cmds = [
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 1), BLEU_CLAIR),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        # SPAN pour fusionner les en-tetes de semestre (ligne 0)
        ('SPAN', (0, 0), (0, 1)),   # Matieres
        ('SPAN', (1, 0), (1, 1)),   # Coef
        ('SPAN', (2, 0), (4, 0)),   # 1er Semestre
        ('SPAN', (5, 0), (7, 0)),   # 2eme Semestre
    ]
    table.setStyle(TableStyle(style_cmds))

    table_h = sum(row_heights)
    table_y = ey - table_h - 2
    table.wrapOn(c, w, table_h + 10)
    table.drawOn(c, x, table_y)

    # --- PIED ---
    fy = table_y - 10
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    moy_txt = _fmt(moy_ann) if moy_ann else '......'
    c.drawString(lx, fy, f"Moyenne Annuelle : {moy_txt} /{sur}")
    c.drawString(lx + w * 0.4, fy, f"Classement : {_s(rang) if rang else '......'}")
    c.drawRightString(rx, fy, "eleves")

    fy -= 9
    c.setFont('Helvetica', 5.5)
    passe_txt = _s(passe_en) if passe_en else '..................'
    c.drawString(lx, fy, f"Passe en classe superieure : {passe_txt}")
    c.drawString(lx + w * 0.6, fy, "Remis a ses parents :")

    # --- APPRECIATIONS | Signature du Principal ---
    fy -= 5
    c.setLineWidth(0.5)
    c.line(x, fy, x + w, fy)

    fy -= 10
    col1_w = w * 0.40
    col2_w = w * 0.20
    col3_w = w * 0.40
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(lx, fy, "Appreciations :")
    c.drawString(lx + col1_w, fy, "Date :")
    c.drawString(lx + col1_w + col2_w, fy, "Prenoms, Nom et")
    fy -= 7
    c.drawString(lx + col1_w + col2_w, fy, "Signature du Principal")

    c.setLineWidth(0.3)
    c.line(x + col1_w, fy + 17, x + col1_w, fy - 2)
    c.line(x + col1_w + col2_w, fy + 17, x + col1_w + col2_w, fy - 2)


# ==============================================================================
#  DESSIN D'UNE DEMI-PAGE MATERNELLE
# ==============================================================================

def _draw_half_maternelle(c, x, y, w, h, ecole, entry, eleve):
    """Dessine une demi-page format MATERNELLE."""
    classe_nom = entry['classe_nom']
    annee = entry['annee_scolaire']

    c.setStrokeColor(colors.black)
    c.setLineWidth(1.0)
    c.rect(x, y, w, h)

    top = y + h
    pad = 4
    lx = x + pad
    rx = x + w - pad

    # En-tete
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    ey = top - 10
    c.drawString(lx, ey, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, ey, f"DPE/DCE : {_s(ecole.dpe)}")

    ey -= 9
    c.setFont('Helvetica-Bold', 6.5)
    c.drawString(lx, ey, f"Ecole Maternelle : {_s(ecole.nom)}")

    ey -= 4
    c.setLineWidth(0.5)
    c.line(x, ey, x + w, ey)

    # Classe / Annee
    ey -= 14
    cls_w = w * 0.45
    cls_h = 13
    c.setLineWidth(1.0)
    c.rect(lx, ey, cls_w, cls_h)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(lx + cls_w / 2, ey + 3, f"Classe : {_s(classe_nom)}")
    c.setFont('Helvetica-Bold', 7)
    c.drawString(lx + cls_w + 10, ey + 3, f"Annee scolaire : {annee}")

    # Info eleve
    ey -= 14
    c.setFont('Helvetica', 6)
    c.drawString(lx, ey, f"Eleve: {_s(eleve.nom)} {_s(eleve.prenom)}")
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else ''
    c.drawString(lx + w * 0.45, ey, f"Ne(e) le: {dn}")

    ey -= 14
    c.setFont('Helvetica-Oblique', 6.5)
    c.drawString(lx, ey, "Evaluation qualitative (appreciations) - Voir bulletins trimestriels")

    # Signature
    ey -= 25
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(lx, ey, "Appreciations Generales :")
    c.drawString(lx + w * 0.5, ey, "Signature du Directeur :")


def _draw_half_page(c, x, y, w, h, ecole, entry, eleve):
    """Dispatch vers le bon format selon le niveau."""
    niveau = entry['niveau']
    if niveau == 'MATERNELLE':
        _draw_half_maternelle(c, x, y, w, h, ecole, entry, eleve)
    elif niveau in ('COLLEGE', 'LYCEE'):
        _draw_half_college(c, x, y, w, h, ecole, entry, eleve)
    else:
        _draw_half_primaire(c, x, y, w, h, ecole, entry, eleve)


# ==============================================================================
#  COLLECTE DES DONNEES DU PARCOURS
# ==============================================================================

def _collecter_parcours_eleve(eleve, ecole):
    """Collecte tout le parcours d'un eleve : toutes les annees, classes, notes."""
    parcours = []
    annees_classes = {}

    # Via l'historique
    try:
        historiques = HistoriqueEleve.objects.filter(
            eleve=eleve,
            action='CHANGEMENT_CLASSE'
        ).order_by('date_action')

        for h in historiques:
            desc = h.description or ''
            match_annee = re.search(r'(\d{4}-\d{4})', desc)
            if match_annee:
                annee = match_annee.group(1)
                # Chercher le nom de la classe d'origine (fleche ASCII ou Unicode)
                match_classe = re.search(r':\s*(.+?)\s*(?:->|\u2192)', desc)
                if match_classe and annee not in annees_classes:
                    prev_annee_parts = annee.split('-')
                    try:
                        prev_annee = f"{int(prev_annee_parts[0])-1}-{int(prev_annee_parts[1])-1}"
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
        classements_eleve = Classement.objects.filter(eleve=eleve).order_by('annee_scolaire')
        for cl in classements_eleve:
            if cl.annee_scolaire not in annees_classes:
                annees_classes[cl.annee_scolaire] = cl.classe.nom if cl.classe else '?'
    except Exception as e:
        logger.warning(f"Erreur lecture classements eleve {eleve.pk}: {e}")

    # Pour chaque annee, collecter les donnees
    for annee_scolaire in sorted(annees_classes.keys()):
        classe_nom = annees_classes[annee_scolaire]
        niveau = detecter_niveau_scolaire(classe_nom)
        sur = 10 if niveau == 'PRIMAIRE' else 20
        is_semestre = niveau in ('COLLEGE', 'LYCEE')

        # Trouver la ClasseNote
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
                    # Semestre 1
                    notes_s1 = NoteMensuelle.objects.filter(
                        eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                        mois__in=['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER']
                    )
                    compo_s1 = CompositionNote.objects.filter(
                        eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                        periode='SEMESTRE_1'
                    ).first()

                    moy_s1 = None
                    if notes_s1.exists():
                        vals = [float(n.note) for n in notes_s1 if n.note is not None]
                        moy_s1 = round(sum(vals) / len(vals), 2) if vals else None

                    compo_s1_val = float(compo_s1.note) if compo_s1 and compo_s1.note is not None else None
                    sem1_moyenne = None
                    if moy_s1 is not None and compo_s1_val is not None:
                        sem1_moyenne = round(moy_s1 * 0.4 + compo_s1_val * 0.6, 2)
                    elif moy_s1 is not None:
                        sem1_moyenne = moy_s1
                    elif compo_s1_val is not None:
                        sem1_moyenne = compo_s1_val

                    # Semestre 2
                    notes_s2 = NoteMensuelle.objects.filter(
                        eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                        mois__in=['MARS', 'AVRIL', 'MAI', 'JUIN']
                    )
                    compo_s2 = CompositionNote.objects.filter(
                        eleve=eleve, matiere=mat, annee_scolaire=annee_scolaire,
                        periode='SEMESTRE_2'
                    ).first()

                    moy_s2 = None
                    if notes_s2.exists():
                        vals = [float(n.note) for n in notes_s2 if n.note is not None]
                        moy_s2 = round(sum(vals) / len(vals), 2) if vals else None

                    compo_s2_val = float(compo_s2.note) if compo_s2 and compo_s2.note is not None else None
                    sem2_moyenne = None
                    if moy_s2 is not None and compo_s2_val is not None:
                        sem2_moyenne = round(moy_s2 * 0.4 + compo_s2_val * 0.6, 2)
                    elif moy_s2 is not None:
                        sem2_moyenne = moy_s2
                    elif compo_s2_val is not None:
                        sem2_moyenne = compo_s2_val

                    m_data.update({
                        'sem1_moy': moy_s1, 'sem1_compo': compo_s1_val,
                        'sem1_moyenne': sem1_moyenne,
                        'sem2_moy': moy_s2, 'sem2_compo': compo_s2_val,
                        'sem2_moyenne': sem2_moyenne,
                    })
                else:
                    # Trimestres
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
            classement_annuel = Classement.objects.filter(
                eleve=eleve, classe=classe_note, annee_scolaire=annee_scolaire,
                periode__icontains='ANNUEL'
            ).first()

            if classement_annuel:
                moyenne_annuelle = float(classement_annuel.moyenne_generale)
                rang_info = classement_annuel.rang_formate or f"{classement_annuel.rang}eme/{classement_annuel.effectif}"
            else:
                cls_periodes = Classement.objects.filter(
                    eleve=eleve, classe=classe_note, annee_scolaire=annee_scolaire,
                ).exclude(periode__icontains='ANNUEL')
                if cls_periodes.exists():
                    moyennes = [float(cp.moyenne_generale) for cp in cls_periodes if cp.moyenne_generale]
                    if moyennes:
                        moyenne_annuelle = round(sum(moyennes) / len(moyennes), 2)

        # Classe suivante
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

def _generer_livret_pdf(eleve, ecole, parcours):
    """Genere le PDF du livret scolaire complet."""
    buffer = io.BytesIO()
    width, height = landscape(A4)  # 842 x 595
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle(f"Livret Scolaire - {_s(eleve.nom)} {_s(eleve.prenom)}")

    margin = 12
    usable_w = width - 2 * margin
    usable_h = height - 2 * margin
    half_h = usable_h / 2 - 4
    page_num = 0

    # === PAGE DE COUVERTURE ===
    page_num += 1
    c.setFillColor(BLEU_FONCE)
    c.rect(0, 0, width, height, fill=1)

    # Logo
    logo = _get_logo_reader(ecole)
    if logo:
        try:
            c.drawImage(logo, width / 2 - 40, height - 150, 80, 80,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(width / 2, height - 180, "LIVRET SCOLAIRE")

    c.setFont('Helvetica', 11)
    y = height - 210
    c.drawCentredString(width / 2, y, "REPUBLIQUE DE GUINEE")
    y -= 15
    c.drawCentredString(width / 2, y, "Ministere de l'Enseignement Pre-Universitaire")
    y -= 15
    c.drawCentredString(width / 2, y, "et de l'Alphabetisation")
    y -= 15
    c.setFont('Helvetica-Oblique', 10)
    c.drawCentredString(width / 2, y, "Travail - Justice - Solidarite")
    y -= 30

    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(width / 2, y, _s(ecole.nom))
    y -= 20

    c.setFont('Helvetica', 10)
    if ecole.ire:
        c.drawCentredString(width / 2, y, f"IRE/DEV: {_s(ecole.ire)}")
        y -= 15
    if ecole.dpe:
        c.drawCentredString(width / 2, y, f"DPE/DCE: {_s(ecole.dpe)}")
        y -= 15
    if ecole.desee:
        c.drawCentredString(width / 2, y, f"DSEE: {_s(ecole.desee)}")
        y -= 15
    if ecole.adresse:
        c.drawCentredString(width / 2, y, f"Adresse: {_s(ecole.adresse)}")
        y -= 15
    if ecole.telephone:
        c.drawCentredString(width / 2, y, f"Tel: {ecole.telephone}")
        y -= 15
    y -= 15

    # Cadre eleve
    box_w, box_h = 400, 110
    box_x = (width - box_w) / 2
    box_y = y - box_h
    c.setStrokeColor(colors.white)
    c.setLineWidth(2)
    c.rect(box_x, box_y, box_w, box_h)

    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(width / 2, box_y + box_h - 25,
                        f"{_s(eleve.nom)} {_s(eleve.prenom)}")
    c.setFont('Helvetica', 11)
    c.drawCentredString(width / 2, box_y + box_h - 45,
                        f"Matricule: {eleve.matricule}")
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '-'
    lieu = _s(getattr(eleve, 'lieu_naissance', '') or '')
    c.drawCentredString(width / 2, box_y + box_h - 60,
                        f"Ne(e) le {dn}  a {lieu}")
    sexe_txt = 'Masculin' if getattr(eleve, 'sexe', '') == 'M' else 'Feminin'
    c.drawCentredString(width / 2, box_y + box_h - 75, f"Sexe: {sexe_txt}")
    c.setFont('Helvetica', 9)
    c.drawCentredString(width / 2, box_y + box_h - 92,
                        f"Parcours : {len(parcours)} annee(s)")

    c.setFont('Helvetica', 8)
    c.drawCentredString(width / 2, 20, f"- {page_num} -")
    c.showPage()

    # === PAGES DU PARCOURS (2 niveaux par page) ===
    i = 0
    while i < len(parcours):
        page_num += 1

        # Moitie HAUTE
        top_y = margin + half_h + 8
        _draw_half_page(c, margin, top_y, usable_w, half_h, ecole, parcours[i], eleve)

        # Moitie BASSE
        i += 1
        if i < len(parcours):
            _draw_half_page(c, margin, margin, usable_w, half_h, ecole, parcours[i], eleve)
            i += 1
        else:
            # Ligne de separation pointillee
            c.setStrokeColor(GRIS_SEP)
            c.setDash(3, 3)
            mid_y = margin + half_h + 4
            c.line(margin, mid_y, width - margin, mid_y)
            c.setDash()

        # Numero de page
        c.setFont('Helvetica', 8)
        c.setFillColor(GRIS_TEXTE)
        c.drawCentredString(width / 2, 5, f"- {page_num} -")
        c.showPage()

    # === PAGE DE SYNTHESE ===
    page_num += 1
    c.setFont('Helvetica-Bold', 14)
    c.setFillColor(BLEU_FONCE)
    c.drawCentredString(width / 2, height - 35, "ANALYSE ET RAPPORT FINAL DU PARCOURS")

    c.setFont('Helvetica', 9)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 52,
                        f"Eleve : {_s(eleve.nom)} {_s(eleve.prenom)}"
                        f"  -  Matricule : {eleve.matricule}")

    # Synthese par cycle
    cycles_data = {}
    for p in parcours:
        cycle = p['cycle']
        if cycle not in cycles_data:
            cycles_data[cycle] = []
        cycles_data[cycle].append(p)

    y = height - 75
    for cycle_key, cycle_entries in cycles_data.items():
        cycle_label = CYCLE_LABELS.get(cycle_key, cycle_key)
        c.setFont('Helvetica-Bold', 10)
        c.setFillColor(BLEU_FONCE)
        c.drawString(margin + 10, y, cycle_label)
        y -= 16

        synth_data = [['Annee', 'Classe', 'Moyenne Annuelle', 'Classement', 'Observation']]
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
            synth_data.append(['', 'MOYENNE DU CYCLE', f'{moy_cycle:.2f}/{sur_cycle}', '', ''])

        col_w = [usable_w * 0.15, usable_w * 0.25, usable_w * 0.20,
                 usable_w * 0.20, usable_w * 0.20]
        rh = 15
        table = Table(synth_data, colWidths=col_w, rowHeights=[rh] * len(synth_data))
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, GRIS_LIGNE),
            ('BACKGROUND', (0, 0), (-1, 0), BLEU_FONCE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), BLEU_CLAIR),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        th = rh * len(synth_data)
        table.wrapOn(c, usable_w, th + 10)
        table.drawOn(c, margin + 10, y - th)
        y -= th + 18

        if y < 120:
            c.setFont('Helvetica', 8)
            c.drawCentredString(width / 2, 5, f"- {page_num} -")
            c.showPage()
            page_num += 1
            y = height - 40

    # === ORIENTATION ===
    y -= 8
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(BLEU_FONCE)
    c.drawString(margin + 10, y, "PROPOSITION D'ORIENTATION AUTOMATIQUE")
    y -= 18

    orientation = _calculer_orientation(parcours)
    c.setFont('Helvetica', 8.5)
    c.setFillColor(colors.black)
    for line in orientation:
        c.drawString(margin + 20, y, line)
        y -= 13

    # Signatures finales
    y -= 18
    c.setFont('Helvetica-Bold', 9)
    c.drawString(margin + 10, y, "Le Directeur / Proviseur :")
    c.drawString(width / 2, y, "Le Censeur :")
    y -= 14
    c.setFont('Helvetica', 8)
    c.drawString(margin + 10, y, f"Nom: {_s(ecole.directeur) if ecole.directeur else ''}")
    if ecole.censeur:
        c.drawString(width / 2, y, f"Nom: {_s(ecole.censeur)}")
    y -= 20
    c.drawString(margin + 10, y, "Signature et cachet :")
    c.drawString(width / 2, y, "Signature :")

    c.setFont('Helvetica', 8)
    c.setFillColor(GRIS_TEXTE)
    c.drawCentredString(width / 2, 5, f"- {page_num} -")

    c.save()
    buffer.seek(0)
    return buffer


def _calculer_orientation(parcours):
    """Propose une orientation automatique basee sur le parcours."""
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
    """Page de selection : choisir un eleve ou une classe pour generer le livret."""
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
    """Genere et telecharge le livret scolaire PDF d'un eleve."""
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
            messages.warning(
                request,
                f"Aucune donnee de parcours trouvee pour {eleve.nom} {eleve.prenom}."
            )
            return redirect('notes:livret_scolaire')

        buffer = _generer_livret_pdf(eleve, ecole, parcours)

        filename = f"Livret_Scolaire_{_s(eleve.nom)}_{_s(eleve.prenom)}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Erreur generation livret pour eleve {eleve_id}: {e}", exc_info=True)
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
                buffer = _generer_livret_pdf(eleve, ecole, parcours)
                filename = f"Livret_{_s(classe.nom)}_{_s(eleve.nom)}.pdf"
                response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
        except Exception as e:
            logger.error(f"Erreur livret classe pour eleve {eleve.pk}: {e}", exc_info=True)
            continue

    messages.warning(request, "Aucune donnee disponible.")
    return redirect('notes:livret_scolaire')
