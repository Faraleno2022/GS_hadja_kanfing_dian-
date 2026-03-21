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
    Format exact du PDF officiel guineen.
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
    cy = top  # curseur Y descendant

    # ------------------------------------------------------------------
    # EN-TETE
    # ------------------------------------------------------------------
    cy -= 11
    c.setFont('Helvetica-Bold', 6)
    c.setFillColor(colors.black)
    c.drawString(lx, cy, f"IRE/DEV : {_s(ecole.ire)}")
    c.drawRightString(rx, cy, f"DPE/DCE : {_s(ecole.dpe)}")

    cy -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, cy, f"College : {_s(ecole.nom)}")
    c.drawString(lx + w * 0.55, cy, f"Venant de : ........................")

    cy -= 8
    c.drawString(lx, cy, "Date d'entree : ........................")

    cy -= 8
    c.drawString(lx, cy, "References : ........................")

    # ------------------------------------------------------------------
    # BANDE CLASSE / ANNEE SCOLAIRE
    # ------------------------------------------------------------------
    cy -= 4
    c.setLineWidth(0.5)
    c.line(x, cy, x + w, cy)

    band_h = 14
    cy -= band_h
    # Fond gris clair pour la bande
    c.setFillColor(colors.HexColor('#f0f0f0'))
    c.rect(x, cy, w, band_h, fill=1, stroke=1)

    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.black)
    c.drawString(lx + 5, cy + 3, f"Classe : {_s(classe_nom)}")
    c.drawRightString(rx - 5, cy + 3, f"Annee scolaire : {annee}")

    # ------------------------------------------------------------------
    # TABLEAU DES NOTES
    # ------------------------------------------------------------------
    # En-tete sur 2 lignes :
    # Ligne 1 : Matieres | Coef | 1er Semestre (span 3) | 2eme Semestre (span 3)
    # Ligne 2 :          |      | Moyenne | Classement | Moyenne | Moyenne | Classement | Moyenne
    #          |      | Classe  |            | Semestre | Classe  |            | Semestre
    cy -= 2

    header1 = ['Matieres', 'Coef', '1er Semestre', '', '', '2eme Semestre', '', '']
    header2 = ['', '', 'Moyenne\nClasse', 'Classement', 'Moyenne\nSemestre',
               'Moyenne\nClasse', 'Classement', 'Moyenne\nSemestre']

    # Proportions des colonnes
    col_ratios = [0.195, 0.05, 0.105, 0.105, 0.105, 0.105, 0.105, 0.105]
    col_widths = [w * r for r in col_ratios]
    # Ajuster le dernier
    diff_w = w - sum(col_widths)
    col_widths[0] += diff_w

    data = [header1, header2]
    for m in matieres:
        row = [
            _s(m['nom']),
            str(m.get('coef', '')),
            _fmt(m.get('sem1_moy')),       # Moyenne Classe (= moy cours)
            _fmt(m.get('sem1_compo')),      # Classement (= compo)
            _fmt(m.get('sem1_moyenne')),    # Moyenne Semestre
            _fmt(m.get('sem2_moy')),        # Moyenne Classe
            _fmt(m.get('sem2_compo')),      # Classement
            _fmt(m.get('sem2_moyenne')),    # Moyenne Semestre
        ]
        data.append(row)

    row_h = 13
    header_h = 20
    nb_rows = len(data)
    row_heights = [header_h, header_h] + [row_h] * (nb_rows - 2)

    table = Table(data, colWidths=col_widths, rowHeights=row_heights)

    style_cmds = [
        # Polices
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 1), 5),
        ('FONTSIZE', (0, 2), (-1, -1), 6),
        # Alignement
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Grille
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        # Fond en-tetes
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#f0f0f0')),
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        # SPAN en-tetes
        ('SPAN', (0, 0), (0, 1)),   # Matieres
        ('SPAN', (1, 0), (1, 1)),   # Coef
        ('SPAN', (2, 0), (4, 0)),   # 1er Semestre
        ('SPAN', (5, 0), (7, 0)),   # 2eme Semestre
    ]
    table.setStyle(TableStyle(style_cmds))

    table_total_h = sum(row_heights)
    table_y = cy - table_total_h
    table.wrapOn(c, w, table_total_h + 20)
    table.drawOn(c, x, table_y)

    # ------------------------------------------------------------------
    # PIED : Moyenne Annuelle / Passe en classe / Classement
    # ------------------------------------------------------------------
    fy = table_y - 11
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(colors.black)
    moy_txt = _fmt(moy_ann) if moy_ann else ''
    c.drawString(lx, fy, f"Moyenne Annuelle")
    c.drawString(lx + w * 0.27, fy, f"{moy_txt}")
    c.drawRightString(rx, fy, f"/20")

    fy -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, fy,
                 f"Passe en classe superieure /20")
    rang_txt = _s(rang) if rang else ''
    c.drawString(lx + w * 0.45, fy, f"Classement : {rang_txt}")
    c.drawString(lx + w * 0.72, fy, "Redoublant :")
    c.drawRightString(rx, fy, "eleves :")

    # Ligne separatrice avant appreciations
    fy -= 5
    c.setLineWidth(0.5)
    c.line(x, fy, x + w, fy)

    # ------------------------------------------------------------------
    # BAS : Appreciations (gauche) | Aux parents (droite)
    # ------------------------------------------------------------------
    left_w = w * 0.50
    right_w = w * 0.50

    # Ligne verticale separatrice
    c.setLineWidth(0.3)
    c.line(x + left_w, fy, x + left_w, y)

    # --- Cote GAUCHE : Appreciations Generales ---
    ay = fy - 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(lx, ay, "Appreciations Generales")
    ay -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ay, "..........................................................")
    ay -= 7
    c.drawString(lx, ay, "..........................................................")

    # --- Cote DROIT : Aux parents + signature ---
    rstart_x = x + left_w + pad
    py = fy - 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Aux parents, Nom et Prenom de l'eleve")

    py -= 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(rstart_x, py,
                 f"Eleve : {_s(eleve.nom)}")
    c.drawString(rstart_x + right_w * 0.45, py,
                 f"Prenom : {_s(eleve.prenom)}")

    py -= 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Date :")

    py -= 10
    c.drawString(rstart_x, py, "Signature du Principal")

    # ------------------------------------------------------------------
    # NUMERO DE PAGE (bas centre)
    # ------------------------------------------------------------------
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.black)
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")


def _draw_half_primaire(c, x, y, w, h, ecole, entry, eleve, page_number):
    """
    Dessine UNE demi-page format Primaire (trimestre).
    Matieres | 1er Trim | 2eme Trim | 3eme Trim | Moy Annuelle | Observations
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

    # TABLEAU : Matieres | 1er Trim | 2eme Trim | 3eme Trim | Moy Annuelle | Observations
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

    row_h = 13
    header_rh = 18
    nb_rows = len(data)
    row_heights = [header_rh] + [row_h] * (nb_rows - 1)

    table = Table(data, colWidths=col_widths, rowHeights=row_heights)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 5),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    table_total_h = sum(row_heights)
    table_y = cy - table_total_h
    table.wrapOn(c, w, table_total_h + 20)
    table.drawOn(c, x, table_y)

    # PIED
    fy = table_y - 11
    c.setFont('Helvetica-Bold', 6.5)
    c.setFillColor(colors.black)
    moy_txt = _fmt(moy_ann) if moy_ann else ''
    c.drawString(lx, fy, f"Moyenne Annuelle")
    c.drawString(lx + w * 0.27, fy, f"{moy_txt}")
    c.drawRightString(rx, fy, f"/{sur}")

    fy -= 11
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, fy, f"Passe en classe superieure /{sur}")
    rang_txt = _s(rang) if rang else ''
    c.drawString(lx + w * 0.45, fy, f"Classement : {rang_txt}")
    c.drawString(lx + w * 0.72, fy, "Redoublant :")
    c.drawRightString(rx, fy, "eleves :")

    fy -= 5
    c.setLineWidth(0.5)
    c.line(x, fy, x + w, fy)

    # Appreciations / Aux parents
    left_w = w * 0.50
    c.setLineWidth(0.3)
    c.line(x + left_w, fy, x + left_w, y)

    ay = fy - 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(lx, ay, "Appreciations Generales")
    ay -= 9
    c.setFont('Helvetica', 5.5)
    c.drawString(lx, ay, "..........................................................")
    ay -= 7
    c.drawString(lx, ay, "..........................................................")

    rstart_x = x + left_w + pad
    py = fy - 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Aux parents, Nom et Prenom de l'eleve")
    py -= 10
    c.setFont('Helvetica-Bold', 6)
    c.drawString(rstart_x, py, f"Eleve : {_s(eleve.nom)}")
    c.drawString(rstart_x + w * 0.22, py, f"Prenom : {_s(eleve.prenom)}")
    py -= 10
    c.setFont('Helvetica', 5.5)
    c.drawString(rstart_x, py, "Date :")
    py -= 10
    c.drawString(rstart_x, py, "Signature du Directeur")

    # Numero de page
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")


def _draw_half_maternelle(c, x, y, w, h, ecole, entry, eleve, page_number):
    """Demi-page Maternelle."""
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

    cy -= 14
    c.setFont('Helvetica-Oblique', 6.5)
    c.drawString(lx, cy, "Evaluation qualitative (appreciations) - Voir bulletins trimestriels")

    cy -= 25
    c.setFont('Helvetica-Bold', 5.5)
    c.drawString(lx, cy, "Appreciations Generales :")
    c.drawString(lx + w * 0.5, cy, "Signature du Directeur :")

    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + 3, f"-{page_number}-")


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

def _generer_livret_pdf(eleve, ecole, parcours):
    """Genere le PDF du livret scolaire complet.
    Format: Paysage A4, deux niveaux par page GAUCHE/DROITE, numerotation par demi-page.
    """
    buffer = io.BytesIO()
    width, height = landscape(A4)  # 842 x 595
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle(f"Livret Scolaire - {_s(eleve.nom)} {_s(eleve.prenom)}")

    margin = 10
    gap = 6  # Espace entre les deux moities
    half_w = (width - 2 * margin - gap) / 2
    usable_h = height - 2 * margin

    page_counter = 0  # Numerotation des demi-pages

    # === PAGE DE COUVERTURE ===
    page_counter += 1
    c.setFillColor(colors.HexColor('#003d82'))
    c.rect(0, 0, width, height, fill=1)

    logo = _get_logo_reader(ecole)
    if logo:
        try:
            c.drawImage(logo, width / 2 - 40, height - 150, 80, 80,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(width / 2, height - 185, "LIVRET SCOLAIRE")

    c.setFont('Helvetica', 11)
    y = height - 215
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
    for label, val in [
        ("IRE/DEV", ecole.ire), ("DPE/DCE", ecole.dpe),
        ("DSEE", ecole.desee), ("Adresse", ecole.adresse),
        ("Tel", ecole.telephone),
    ]:
        if val:
            c.drawCentredString(width / 2, y, f"{label}: {_s(val)}")
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
    c.drawCentredString(width / 2, box_y + box_h - 45, f"Matricule: {eleve.matricule}")
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '-'
    lieu = _s(getattr(eleve, 'lieu_naissance', '') or '')
    c.drawCentredString(width / 2, box_y + box_h - 60, f"Ne(e) le {dn}  a {lieu}")
    sexe_txt = 'Masculin' if getattr(eleve, 'sexe', '') == 'M' else 'Feminin'
    c.drawCentredString(width / 2, box_y + box_h - 75, f"Sexe: {sexe_txt}")
    c.setFont('Helvetica', 9)
    c.drawCentredString(width / 2, box_y + box_h - 92,
                        f"Parcours : {len(parcours)} annee(s)")

    c.setFont('Helvetica', 8)
    c.drawCentredString(width / 2, 15, f"-{page_counter}-")
    c.showPage()

    # === PAGES DU PARCOURS (2 niveaux par page : GAUCHE / DROITE) ===
    i = 0
    while i < len(parcours):
        # Demi-page GAUCHE
        page_counter += 1
        left_x = margin
        _draw_half_page(c, left_x, margin, half_w, usable_h,
                        ecole, parcours[i], eleve, page_counter)

        # Demi-page DROITE
        i += 1
        if i < len(parcours):
            page_counter += 1
            right_x = margin + half_w + gap
            _draw_half_page(c, right_x, margin, half_w, usable_h,
                            ecole, parcours[i], eleve, page_counter)
            i += 1
        else:
            # Droite vide : cadre pointille
            right_x = margin + half_w + gap
            c.setStrokeColor(colors.HexColor('#cccccc'))
            c.setDash(3, 3)
            c.rect(right_x, margin, half_w, usable_h)
            c.setDash()

        c.showPage()

    # === PAGE DE SYNTHESE / RAPPORT FINAL ===
    page_counter += 1
    c.setFont('Helvetica-Bold', 14)
    c.setFillColor(colors.HexColor('#003d82'))
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

    usable_w = width - 2 * margin
    y = height - 75
    for cycle_key, cycle_entries in cycles_data.items():
        cycle_label = CYCLE_LABELS.get(cycle_key, cycle_key)
        c.setFont('Helvetica-Bold', 10)
        c.setFillColor(colors.HexColor('#003d82'))
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
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#555555')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003d82')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eef5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        th = rh * len(synth_data)
        table.wrapOn(c, usable_w, th + 10)
        table.drawOn(c, margin + 10, y - th)
        y -= th + 18

        if y < 120:
            c.setFont('Helvetica', 8)
            c.drawCentredString(width / 2, 5, f"-{page_counter}-")
            c.showPage()
            page_counter += 1
            y = height - 40

    # ORIENTATION
    y -= 8
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(colors.HexColor('#003d82'))
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
    c.setFillColor(colors.HexColor('#333333'))
    c.drawCentredString(width / 2, 5, f"-{page_counter}-")

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
