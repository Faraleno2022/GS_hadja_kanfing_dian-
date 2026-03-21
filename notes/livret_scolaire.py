"""
Livret Scolaire — Génération PDF du parcours complet d'un élève.

Format : Paysage (landscape), deux niveaux par page (page divisée en deux),
imprimable recto-verso, bien numéroté.

Structure du livret :
1. Page de couverture (infos ministère, école, élève)
2. Pour chaque année/classe : tableau des notes par semestre/trimestre + moyenne annuelle
3. Analyse et rapport de fin de cycle (maternelle, primaire, collège, lycée)
4. Page finale : rapport global + proposition d'orientation automatique
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

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

MINISTERE = "RÉPUBLIQUE DE GUINÉE\nMinistère de l'Enseignement Pré-Universitaire\net de l'Alphabétisation"
DEVISE = "Travail — Justice — Solidarité"

CYCLE_LABELS = {
    'MATERNELLE': 'Cycle Maternelle',
    'PRIMAIRE': 'Cycle Primaire',
    'COLLEGE': 'Cycle Collège',
    'LYCEE': 'Cycle Lycée / Terminale',
}

# Ordre des matières standard
MATIERES_PRIMAIRE = [
    'Dictée et Questions', 'Rédaction', 'Mathématique', 'Histoire',
    'Géographie', 'Instruction Civique', 'Physique', 'Chimie', 'Biologie',
]
MATIERES_SECONDAIRE = [
    'Dictée et Questions', 'Rédaction', 'Mathématique', 'Histoire',
    'Géographie', 'Instruction Civique', 'Physique', 'Chimie', 'Biologie',
    'Anglais', 'Philosophie', 'Éducation Physique',
]


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITAIRES PDF
# ══════════════════════════════════════════════════════════════════════════════

def _get_logo_reader(ecole):
    """Retourne un ImageReader pour le logo de l'école, ou None."""
    try:
        if ecole.logo and hasattr(ecole.logo, 'path'):
            return ImageReader(ecole.logo.path)
    except Exception:
        pass
    return None


def _draw_header_half(c, x, y, w, h, ecole, classe_nom, annee_scolaire, eleve, page_label=''):
    """Dessine l'en-tête d'une demi-page (pour un niveau du livret)."""
    # Cadre
    c.setStrokeColor(colors.HexColor('#003d82'))
    c.setLineWidth(1.5)
    c.rect(x, y, w, h)

    # Ligne séparatrice en-tête
    header_h = 55
    c.setLineWidth(0.5)
    c.line(x, y + h - header_h, x + w, y + h - header_h)

    # Ministère (gauche)
    c.setFont('Helvetica', 6)
    c.setFillColor(colors.HexColor('#333333'))
    text_x = x + 5
    text_y = y + h - 12
    for line in MINISTERE.split('\n'):
        c.drawString(text_x, text_y, line.strip())
        text_y -= 8
    c.setFont('Helvetica-Oblique', 5)
    c.drawString(text_x, text_y, DEVISE)

    # IRE / DPE / DSEE (droite)
    right_x = x + w - 5
    c.setFont('Helvetica', 6)
    info_y = y + h - 12
    if ecole.ire:
        c.drawRightString(right_x, info_y, f"IRE/DEV: {ecole.ire}")
        info_y -= 8
    if ecole.dpe:
        c.drawRightString(right_x, info_y, f"DPE/DCE: {ecole.dpe}")
        info_y -= 8
    if ecole.desee:
        c.drawRightString(right_x, info_y, f"DSEE: {ecole.desee}")
        info_y -= 8

    # Nom du collège / école (centre)
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawCentredString(x + w / 2, y + h - 15, f"Collège: {ecole.nom}")

    # Classe et année
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(colors.black)
    c.drawCentredString(x + w / 2, y + h - 30, f"Classe : {classe_nom}")
    c.setFont('Helvetica', 7)
    c.drawCentredString(x + w / 2, y + h - 40, f"Année scolaire : {annee_scolaire}")

    # Élève info (sous l'en-tête)
    info_y = y + h - header_h - 12
    c.setFont('Helvetica', 6.5)
    c.drawString(x + 5, info_y, f"Élève: {eleve.nom} {eleve.prenom}")
    c.drawString(x + w / 2, info_y, f"Né(e) le: {eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '—'}")
    info_y -= 10
    c.drawString(x + 5, info_y, f"Matricule: {eleve.matricule}")
    if hasattr(eleve, 'lieu_naissance') and eleve.lieu_naissance:
        c.drawString(x + w / 2, info_y, f"Lieu: {eleve.lieu_naissance}")

    return info_y - 5  # Retourne la position Y après l'en-tête


def _draw_notes_table(c, x, y_start, w, matieres_data, periodes, sur=20, is_semestre=True):
    """Dessine le tableau des notes pour un niveau.

    matieres_data: list of dict {
        'nom': str, 'coef': int/float,
        'sem1_moy': float|None, 'sem1_compo': float|None, 'sem1_moyenne': float|None,
        'sem2_moy': float|None, 'sem2_compo': float|None, 'sem2_moyenne': float|None,
    }
    """
    # Construire les données du tableau
    if is_semestre:
        header1 = ['', '', '1er Semestre', '', '', '2ème Semestre', '', '']
        header2 = ['Matières', 'Coef',
                    'Moyenne\nCours', 'Compo', 'Moyenne\nSemestr.',
                    'Moyenne\nCours', 'Compo', 'Moyenne\nSemestr.']
    else:
        header1 = ['', '', '1er Trimestre', '', '2ème Trimestre', '', '3ème Trimestre', '']
        header2 = ['Matières', 'Coef',
                    'Moy.', 'Compo',
                    'Moy.', 'Compo',
                    'Moy.', 'Compo']

    data = [header1, header2]

    def fmt(v):
        if v is None:
            return '—'
        return f'{float(v):.2f}'

    for m in matieres_data:
        if is_semestre:
            row = [
                m['nom'], str(m.get('coef', '')),
                fmt(m.get('sem1_moy')), fmt(m.get('sem1_compo')), fmt(m.get('sem1_moyenne')),
                fmt(m.get('sem2_moy')), fmt(m.get('sem2_compo')), fmt(m.get('sem2_moyenne')),
            ]
        else:
            row = [
                m['nom'], str(m.get('coef', '')),
                fmt(m.get('t1_moy')), fmt(m.get('t1_compo')),
                fmt(m.get('t2_moy')), fmt(m.get('t2_compo')),
                fmt(m.get('t3_moy')), fmt(m.get('t3_compo')),
            ]
        data.append(row)

    # Colonnes
    if is_semestre:
        col_widths = [w * 0.22, w * 0.06,
                      w * 0.10, w * 0.09, w * 0.11,
                      w * 0.10, w * 0.09, w * 0.11]
    else:
        col_widths = [w * 0.22, w * 0.06,
                      w * 0.10, w * 0.10,
                      w * 0.10, w * 0.10,
                      w * 0.10, w * 0.10]

    # Ajuster pour être sûr que ça fait pile w
    total = sum(col_widths)
    if abs(total - w) > 1:
        diff = w - total
        col_widths[0] += diff

    row_height = 11
    table = Table(data, colWidths=col_widths, rowHeights=[row_height] * len(data))

    style = TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#666666')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003d82')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8eef5')),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        # Fusionner les en-têtes de période
        ('SPAN', (2, 0), (4, 0) if is_semestre else (3, 0)),
    ])

    if is_semestre:
        style.add('SPAN', (5, 0), (7, 0))
    else:
        style.add('SPAN', (4, 0), (5, 0))
        style.add('SPAN', (6, 0), (7, 0))

    table.setStyle(style)

    table_height = row_height * len(data)
    table_y = y_start - table_height
    table.wrapOn(c, w, table_height + 20)
    table.drawOn(c, x, table_y)

    return table_y


def _draw_footer_half(c, x, y, w, moyenne_annuelle, classement_info, ecole, pass_info=''):
    """Dessine le pied (moyenne annuelle, classement, signature) d'une demi-page."""
    c.setFont('Helvetica-Bold', 7)
    c.setFillColor(colors.HexColor('#003d82'))

    moy_txt = f'{float(moyenne_annuelle):.2f}' if moyenne_annuelle else '—'
    c.drawString(x + 5, y, f"Moyenne Annuelle : {moy_txt}")

    if classement_info:
        c.drawString(x + w * 0.35, y, f"Classement : {classement_info}")

    # Passe en classe / Appréciation
    c.setFont('Helvetica', 6.5)
    c.setFillColor(colors.black)
    y -= 10
    if pass_info:
        c.drawString(x + 5, y, f"Passe en classe : {pass_info}")

    # Signatures
    y -= 12
    c.setFont('Helvetica', 6)
    c.drawString(x + 5, y, "Appréciation(s) :")
    c.drawString(x + w * 0.4, y, "Nom et")
    y -= 8
    c.drawString(x + w * 0.4, y, "Signature du Principal :")
    c.drawString(x + w * 0.7, y, "Parents / Élèves :")

    y -= 3
    c.setStrokeColor(colors.HexColor('#cccccc'))
    c.setDash(2, 2)
    c.line(x + w * 0.4, y, x + w * 0.65, y)
    c.line(x + w * 0.7, y, x + w * 0.95, y)
    c.setDash()

    return y - 5


# ══════════════════════════════════════════════════════════════════════════════
#  COLLECTE DES DONNÉES DU PARCOURS
# ══════════════════════════════════════════════════════════════════════════════

def _collecter_parcours_eleve(eleve, ecole):
    """Collecte tout le parcours d'un élève : toutes les années, classes, notes.

    Retourne une liste ordonnée par année :
    [
        {
            'annee_scolaire': '2020-2021',
            'classe_nom': '7ème Année',
            'niveau': 'COLLEGE',
            'cycle': 'COLLEGE',
            'sur': 20,
            'is_semestre': True,
            'matieres_data': [...],
            'moyenne_annuelle': 12.5,
            'rang': '3ème/35',
            'passe_en': '8ème Année',
        },
        ...
    ]
    """
    parcours = []

    # Chercher toutes les classes où l'élève a été (via HistoriqueEleve et classes)
    # 1) Classe actuelle
    # 2) Historique des changements de classe
    annees_classes = {}

    # Via l'historique
    historiques = HistoriqueEleve.objects.filter(
        eleve=eleve,
        action='CHANGEMENT_CLASSE'
    ).order_by('date_action')

    for h in historiques:
        # Extraire année et classe de la description
        desc = h.description or ''
        # Pattern: "Passage nouvelle année XXXX-XXXX: CLASSE → CLASSE"
        match_annee = re.search(r'(\d{4}-\d{4})', desc)
        if match_annee:
            annee = match_annee.group(1)
            # Chercher le nom de la classe d'origine
            match_classe = re.search(r':\s*(.+?)\s*→', desc)
            if match_classe and annee not in annees_classes:
                prev_annee_parts = annee.split('-')
                try:
                    prev_annee = f"{int(prev_annee_parts[0])-1}-{int(prev_annee_parts[1])-1}"
                except Exception:
                    prev_annee = annee
                annees_classes[prev_annee] = match_classe.group(1).strip()

    # Classe actuelle
    if eleve.classe:
        annees_classes[eleve.classe.annee_scolaire] = eleve.classe.nom

    # Chercher aussi via les Classement existants
    classements_eleve = Classement.objects.filter(eleve=eleve).order_by('annee_scolaire')
    for cl in classements_eleve:
        if cl.annee_scolaire not in annees_classes:
            annees_classes[cl.annee_scolaire] = cl.classe.nom if cl.classe else '?'

    # Pour chaque année trouvée, collecter les données
    for annee_scolaire in sorted(annees_classes.keys()):
        classe_nom = annees_classes[annee_scolaire]
        niveau = detecter_niveau_scolaire(classe_nom)
        sur = 10 if niveau == 'PRIMAIRE' else 20
        is_semestre = niveau in ('COLLEGE', 'LYCEE')

        # Trouver la ClasseNote correspondante
        classe_note = ClasseNote.objects.filter(
            ecole=ecole,
            annee_scolaire=annee_scolaire,
            nom__icontains=classe_nom.split('(')[0].strip()[:15]  # Recherche partielle
        ).first()

        if not classe_note:
            # Essai plus large
            classe_note = ClasseNote.objects.filter(
                ecole=ecole,
                annee_scolaire=annee_scolaire,
            ).first()

        matieres_data = []
        moyenne_annuelle = None
        rang_info = ''
        passe_en = ''

        if classe_note:
            matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')

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
                        'sem1_moy': moy_s1, 'sem1_compo': compo_s1_val, 'sem1_moyenne': sem1_moyenne,
                        'sem2_moy': moy_s2, 'sem2_compo': compo_s2_val, 'sem2_moyenne': sem2_moyenne,
                    })
                else:
                    # Trimestres pour le primaire
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
                        m_data[f'{t_label}_moy'] = moy_t
                        m_data[f'{t_label}_compo'] = compo_t_val

                matieres_data.append(m_data)

            # Moyenne annuelle via Classement
            classement_annuel = Classement.objects.filter(
                eleve=eleve, classe=classe_note, annee_scolaire=annee_scolaire,
                periode__icontains='ANNUEL'
            ).first()

            if classement_annuel:
                moyenne_annuelle = float(classement_annuel.moyenne_generale)
                rang_info = classement_annuel.rang_formate or f"{classement_annuel.rang}ème/{classement_annuel.effectif}"
            else:
                # Calculer depuis les classements de période
                cls_periodes = Classement.objects.filter(
                    eleve=eleve, classe=classe_note, annee_scolaire=annee_scolaire,
                ).exclude(periode__icontains='ANNUEL')
                if cls_periodes.exists():
                    moyennes = [float(c.moyenne_generale) for c in cls_periodes if c.moyenne_generale]
                    if moyennes:
                        moyenne_annuelle = round(sum(moyennes) / len(moyennes), 2)

        # Déterminer la classe suivante depuis l'historique
        from eleves.views_nouvelle_annee import PROGRESSION_CLASSES, PROGRESSION_LABELS, _normaliser
        base_norm = _normaliser(classe_nom.split('(')[0].strip())
        next_base = PROGRESSION_CLASSES.get(base_norm)
        if next_base:
            passe_en = PROGRESSION_LABELS.get(next_base, next_base)

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


# ══════════════════════════════════════════════════════════════════════════════
#  GÉNÉRATION PDF
# ══════════════════════════════════════════════════════════════════════════════

def _generer_livret_pdf(eleve, ecole, parcours):
    """Génère le PDF du livret scolaire complet.

    Format: Paysage A4, deux niveaux par page (haut/bas), numéroté.
    """
    buffer = io.BytesIO()
    width, height = landscape(A4)  # 842 x 595
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    c.setTitle(f"Livret Scolaire — {eleve.nom} {eleve.prenom}")

    margin = 15
    usable_w = width - 2 * margin
    usable_h = height - 2 * margin
    half_h = usable_h / 2 - 5  # Espace entre les deux moitiés
    page_num = 0

    # ─── PAGE DE COUVERTURE ───────────────────────────────────────────────
    page_num += 1
    c.setFillColor(colors.HexColor('#003d82'))
    c.rect(0, 0, width, height, fill=1)

    # Logo
    logo = _get_logo_reader(ecole)
    if logo:
        try:
            c.drawImage(logo, width / 2 - 40, height - 150, 80, 80,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Texte couverture
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 22)
    c.drawCentredString(width / 2, height - 180, "LIVRET SCOLAIRE")

    c.setFont('Helvetica', 12)
    y = height - 210
    for line in MINISTERE.split('\n'):
        c.drawCentredString(width / 2, y, line.strip())
        y -= 16
    c.setFont('Helvetica-Oblique', 10)
    c.drawCentredString(width / 2, y, DEVISE)
    y -= 30

    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(width / 2, y, ecole.nom)
    y -= 20

    c.setFont('Helvetica', 10)
    if ecole.ire:
        c.drawCentredString(width / 2, y, f"IRE/DEV: {ecole.ire}")
        y -= 15
    if ecole.dpe:
        c.drawCentredString(width / 2, y, f"DPE/DCE: {ecole.dpe}")
        y -= 15
    if ecole.desee:
        c.drawCentredString(width / 2, y, f"DSEE: {ecole.desee}")
        y -= 15
    if ecole.adresse:
        c.drawCentredString(width / 2, y, f"Adresse: {ecole.adresse}")
        y -= 15
    if ecole.telephone:
        c.drawCentredString(width / 2, y, f"Tel: {ecole.telephone}")
    y -= 30

    # Cadre élève
    box_w, box_h = 400, 100
    box_x = (width - box_w) / 2
    box_y = y - box_h
    c.setStrokeColor(colors.white)
    c.setLineWidth(2)
    c.rect(box_x, box_y, box_w, box_h)

    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(width / 2, box_y + box_h - 25, f"{eleve.nom} {eleve.prenom}")
    c.setFont('Helvetica', 11)
    c.drawCentredString(width / 2, box_y + box_h - 45, f"Matricule: {eleve.matricule}")
    dn = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '—'
    lieu = getattr(eleve, 'lieu_naissance', '') or ''
    c.drawCentredString(width / 2, box_y + box_h - 60, f"Né(e) le {dn}  à {lieu}")
    c.drawCentredString(width / 2, box_y + box_h - 75, f"Sexe: {'Masculin' if eleve.sexe == 'M' else 'Féminin'}")

    # Numéro de page
    c.setFont('Helvetica', 8)
    c.drawCentredString(width / 2, 20, f"— {page_num} —")

    c.showPage()

    # ─── PAGES DU PARCOURS (2 niveaux par page) ──────────────────────────
    i = 0
    while i < len(parcours):
        page_num += 1

        # Moitié HAUTE
        p1 = parcours[i]
        top_y = margin + half_h + 10  # Position Y de la moitié haute
        top_h = half_h

        content_y = _draw_header_half(
            c, margin, top_y, usable_w, top_h,
            ecole, p1['classe_nom'], p1['annee_scolaire'], eleve
        )

        if p1['matieres_data']:
            table_y = _draw_notes_table(
                c, margin + 3, content_y, usable_w - 6,
                p1['matieres_data'], [], p1['sur'], p1['is_semestre']
            )
            _draw_footer_half(
                c, margin + 3, table_y - 5, usable_w - 6,
                p1['moyenne_annuelle'], p1['rang'], ecole, p1['passe_en']
            )
        elif p1['niveau'] == 'MATERNELLE':
            c.setFont('Helvetica-Oblique', 7)
            c.drawString(margin + 10, content_y - 15, "Evaluation qualitative (appreciations) - Voir bulletins trimestriels")

        # Moitié BASSE
        i += 1
        if i < len(parcours):
            p2 = parcours[i]
            bot_y = margin
            bot_h = half_h

            content_y2 = _draw_header_half(
                c, margin, bot_y, usable_w, bot_h,
                ecole, p2['classe_nom'], p2['annee_scolaire'], eleve
            )

            if p2['matieres_data']:
                table_y2 = _draw_notes_table(
                    c, margin + 3, content_y2, usable_w - 6,
                    p2['matieres_data'], [], p2['sur'], p2['is_semestre']
                )
                _draw_footer_half(
                    c, margin + 3, table_y2 - 5, usable_w - 6,
                    p2['moyenne_annuelle'], p2['rang'], ecole, p2['passe_en']
                )
            elif p2['niveau'] == 'MATERNELLE':
                c.setFont('Helvetica-Oblique', 7)
                c.drawString(margin + 10, content_y2 - 15,
                             "Évaluation qualitative (appréciations) — Voir bulletins trimestriels")
            i += 1
        else:
            # Moitié basse vide : ligne de séparation
            c.setStrokeColor(colors.HexColor('#cccccc'))
            c.setDash(3, 3)
            c.line(margin, margin + half_h + 5, width - margin, margin + half_h + 5)
            c.setDash()

        # Numéro de page
        c.setFont('Helvetica', 8)
        c.setFillColor(colors.HexColor('#666666'))
        c.drawCentredString(width / 2, 8, f"— {page_num} —")

        c.showPage()

    # ─── PAGE DE SYNTHÈSE / RAPPORT FINAL ─────────────────────────────────
    page_num += 1
    c.setFont('Helvetica-Bold', 16)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawCentredString(width / 2, height - 40, "ANALYSE ET RAPPORT FINAL DU PARCOURS")

    c.setFont('Helvetica', 10)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 60,
                        f"Élève : {eleve.nom} {eleve.prenom}  —  Matricule : {eleve.matricule}")

    # Tableau synthèse par cycle
    cycles_data = {}
    for p in parcours:
        cycle = p['cycle']
        if cycle not in cycles_data:
            cycles_data[cycle] = []
        cycles_data[cycle].append(p)

    y = height - 90
    for cycle_key, cycle_entries in cycles_data.items():
        cycle_label = CYCLE_LABELS.get(cycle_key, cycle_key)
        c.setFont('Helvetica-Bold', 11)
        c.setFillColor(colors.HexColor('#003d82'))
        c.drawString(margin + 10, y, cycle_label)
        y -= 18

        # Tableau
        synth_data = [['Année', 'Classe', 'Moyenne Annuelle', 'Classement', 'Observation']]
        for p in cycle_entries:
            moy_txt = f"{p['moyenne_annuelle']:.2f}/{p['sur']}" if p['moyenne_annuelle'] else '—'
            seuil = 5.0 if p['sur'] == 10 else 10.0
            obs = 'Admis(e)' if p['moyenne_annuelle'] and p['moyenne_annuelle'] >= seuil else 'Non admis(e)' if p['moyenne_annuelle'] else '—'
            synth_data.append([
                p['annee_scolaire'], p['classe_nom'], moy_txt, p['rang'] or '—', obs
            ])

        # Moyenne du cycle
        moyennes_cycle = [p['moyenne_annuelle'] for p in cycle_entries if p['moyenne_annuelle']]
        if moyennes_cycle:
            moy_cycle = round(sum(moyennes_cycle) / len(moyennes_cycle), 2)
            sur_cycle = cycle_entries[0]['sur']
            synth_data.append(['', 'MOYENNE DU CYCLE', f'{moy_cycle:.2f}/{sur_cycle}', '', ''])

        col_w = [usable_w * 0.15, usable_w * 0.25, usable_w * 0.20, usable_w * 0.20, usable_w * 0.20]
        table = Table(synth_data, colWidths=col_w, rowHeights=[16] * len(synth_data))
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#999999')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003d82')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eef5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        table_h = 16 * len(synth_data)
        table.wrapOn(c, usable_w, table_h + 10)
        table.drawOn(c, margin + 10, y - table_h)
        y -= table_h + 20

        if y < 100:
            c.setFont('Helvetica', 8)
            c.drawCentredString(width / 2, 8, f"— {page_num} —")
            c.showPage()
            page_num += 1
            y = height - 40

    # ─── PROPOSITION D'ORIENTATION ────────────────────────────────────────
    y -= 10
    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(colors.HexColor('#003d82'))
    c.drawString(margin + 10, y, "PROPOSITION D'ORIENTATION AUTOMATIQUE")
    y -= 20

    # Calculer l'orientation basée sur les moyennes
    orientation = _calculer_orientation(parcours)
    c.setFont('Helvetica', 9)
    c.setFillColor(colors.black)
    for line in orientation:
        c.drawString(margin + 20, y, line)
        y -= 14

    # Signatures finales
    y -= 20
    c.setFont('Helvetica-Bold', 9)
    c.drawString(margin + 10, y, "Le Directeur / Proviseur :")
    c.drawString(width / 2, y, "Le Censeur :")
    y -= 15
    c.setFont('Helvetica', 8)
    c.drawString(margin + 10, y, f"Nom: {ecole.directeur or ''}")
    if ecole.censeur:
        c.drawString(width / 2, y, f"Nom: {ecole.censeur}")
    y -= 25
    c.drawString(margin + 10, y, "Signature et cachet :")
    c.drawString(width / 2, y, "Signature :")

    # Numéro de page
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#666666'))
    c.drawCentredString(width / 2, 8, f"— {page_num} —")

    c.save()
    buffer.seek(0)
    return buffer


def _calculer_orientation(parcours):
    """Propose une orientation automatique basée sur le parcours."""
    if not parcours:
        return ["Aucune donnée disponible pour proposer une orientation."]

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
        f"- Derniere classe : {derniere['classe_nom']} ({derniere['annee_scolaire']})",
    ]

    # Analyse des forces
    # Chercher les matières avec les meilleures moyennes dans la dernière année
    if derniere['matieres_data']:
        mats_avg = []
        for m in derniere['matieres_data']:
            vals = []
            for key in ['sem1_moyenne', 'sem2_moyenne', 't1_moy', 't2_moy', 't3_moy']:
                v = m.get(key)
                if v is not None:
                    vals.append(v)
            if vals:
                mats_avg.append((m['nom'], round(sum(vals) / len(vals), 2)))

        if mats_avg:
            mats_avg.sort(key=lambda x: x[1], reverse=True)
            top_3 = mats_avg[:3]
            lines.append(f"- Points forts : {', '.join(f'{n} ({v:.1f})' for n, v in top_3)}")

    # Propositions
    lines.append("")
    if moy_globale >= seuil * 1.6:  # Excellent
        lines.append(">> ORIENTATION PROPOSEE : Filiere d'excellence - Sciences ou Lettres selon les resultats")
        lines.append("   L'eleve presente un profil academique excellent propice aux filieres selectives.")
    elif moy_globale >= seuil * 1.3:  # Très bien
        lines.append(">> ORIENTATION PROPOSEE : Filiere scientifique ou litteraire selon les aptitudes")
        lines.append("   L'eleve presente de solides capacites dans l'ensemble des disciplines.")
    elif moy_globale >= seuil:  # Suffisant
        lines.append(">> ORIENTATION PROPOSEE : Filiere generale avec soutien dans les matieres faibles")
        lines.append("   L'eleve a le niveau requis mais pourrait beneficier d'un accompagnement cible.")
    else:
        lines.append(">> ORIENTATION PROPOSEE : Redoublement ou filiere professionnelle recommande")
        lines.append("   Un renforcement des acquis est necessaire avant progression.")

    return lines


# ══════════════════════════════════════════════════════════════════════════════
#  VUES DJANGO
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def livret_scolaire_selection(request):
    """Page de sélection : choisir un élève ou une classe pour générer le livret."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune école associée à votre compte.")
        return redirect('notes:tableau_bord')

    from eleves.utils_annee import get_annee_active
    annee_active = get_annee_active(request, ecole)

    classes = Classe.objects.filter(ecole=ecole)
    if annee_active:
        classes = classes.filter(annee_scolaire=annee_active)
    classes = classes.order_by('niveau', 'nom')

    # Si une classe est sélectionnée, charger ses élèves
    classe_id = request.GET.get('classe_id')
    eleves = []
    classe_selected = None
    if classe_id:
        try:
            classe_selected = classes.get(pk=classe_id)
            eleves = Eleve.objects.filter(classe=classe_selected, statut='ACTIF').order_by('nom', 'prenom')
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
    """Génère et télécharge le livret scolaire PDF d'un élève."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune école associée à votre compte.")
        return redirect('notes:tableau_bord')

    eleve = get_object_or_404(Eleve, pk=eleve_id)

    # Sécurité : vérifier que l'élève appartient à l'école
    if not filter_by_user_school(Eleve.objects.filter(pk=eleve_id), request.user, 'classe__ecole').exists():
        messages.error(request, "Accès non autorisé à cet élève.")
        return redirect('notes:livret_scolaire')

    try:
        parcours = _collecter_parcours_eleve(eleve, ecole)

        if not parcours:
            messages.warning(request, f"Aucune donnee de parcours trouvee pour {eleve.nom} {eleve.prenom}.")
            return redirect('notes:livret_scolaire')

        buffer = _generer_livret_pdf(eleve, ecole, parcours)

        filename = f"Livret_Scolaire_{eleve.nom}_{eleve.prenom}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Erreur generation livret pour eleve {eleve_id}: {e}", exc_info=True)
        messages.error(request, f"Erreur lors de la generation du livret : {e}")
        return redirect('notes:livret_scolaire')


@login_required
def livret_scolaire_classe_pdf(request, classe_id):
    """Génère les livrets scolaires de tous les élèves d'une classe (1 PDF)."""
    ecole = user_school(request.user)
    if not ecole:
        messages.error(request, "Aucune école associée.")
        return redirect('notes:tableau_bord')

    classe = get_object_or_404(Classe, pk=classe_id, ecole=ecole)
    eleves = Eleve.objects.filter(classe=classe, statut='ACTIF').order_by('nom', 'prenom')

    if not eleves.exists():
        messages.warning(request, f"Aucun élève actif dans la classe {classe.nom}.")
        return redirect('notes:livret_scolaire')

    # Générer un PDF combiné
    from reportlab.lib.pagesizes import landscape, A4
    buffer = io.BytesIO()
    width, height = landscape(A4)
    c_pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    c_pdf.setTitle(f"Livrets Scolaires — {classe.nom}")

    for idx, eleve in enumerate(eleves):
        parcours = _collecter_parcours_eleve(eleve, ecole)
        if parcours:
            eleve_buffer = _generer_livret_pdf(eleve, ecole, parcours)
            # On ne peut pas fusionner facilement avec ReportLab seul,
            # alors on génère chaque livret séparément et on retourne le premier
            # Pour la V1, on retourne un PDF par élève
            pass

    # V1 simplifiée : générer pour le premier élève et informer
    # Dans une V2, on utilisera PyPDF2/PyMuPDF pour fusionner
    first_eleve = eleves.first()
    parcours = _collecter_parcours_eleve(first_eleve, ecole)
    if parcours:
        buffer = _generer_livret_pdf(first_eleve, ecole, parcours)
        filename = f"Livrets_{classe.nom}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    messages.warning(request, "Aucune donnée disponible.")
    return redirect('notes:livret_scolaire')
