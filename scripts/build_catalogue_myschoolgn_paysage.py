"""Catalogue commercial MySchoolGN - 4 pages A4 paysage, chaque page divisee en deux."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_LECTURE = OUTPUT_DIR / "Catalogue_MySchoolGN_2026_paysage.pdf"
OUTPUT_LIVRET = OUTPUT_DIR / "Catalogue_MySchoolGN_2026_livret_recto_verso.pdf"
LOGO = ROOT / "static" / "logos" / "logo.png"
SCHOOL_PHOTO = ROOT / "static" / "images" / "carte2.jpg"

NAVY = colors.HexColor("#0E4A78")
BLUE = colors.HexColor("#2E74B5")
GREEN = colors.HexColor("#278A68")
ORANGE = colors.HexColor("#F28C28")
INK = colors.HexColor("#17324D")
GRAY = colors.HexColor("#667085")
LIGHT_GRAY = colors.HexColor("#F2F4F7")
PALE_BLUE = colors.HexColor("#EAF2F8")
PALE_GREEN = colors.HexColor("#EAF6F1")
PALE_ORANGE = colors.HexColor("#FFF3E5")
BORDER = colors.HexColor("#D8E1EA")
WHITE = colors.white
BLACK = colors.HexColor("#111827")
AMBER = colors.HexColor("#A76700")
PALE_AMBER = colors.HexColor("#FFF4D6")

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
MARGIN_X = 34
TOP = 44
BOTTOM = 32
GUTTER = 30
COL_WIDTH = (PAGE_WIDTH - 2 * MARGIN_X - GUTTER) / 2.0
COL_HEIGHT = PAGE_HEIGHT - TOP - BOTTOM
COL1_X = MARGIN_X
COL2_X = MARGIN_X + COL_WIDTH + GUTTER
GUTTER_CENTER = MARGIN_X + COL_WIDTH + GUTTER / 2.0

TOTAL_VOLETS = 8  # 4 feuilles paysage x 2 volets = 8 pages de livret
TOTAL_FEUILLES = 4

# Ordre de lecture : les volets se suivent de gauche a droite.
IMPOSITION_LECTURE = [(1, 2), (3, 4), (5, 6), (7, 8)]
# Imposition cahier : 2 feuilles imprimees recto verso, pliees et agrafees.
IMPOSITION_LIVRET = [(8, 1), (2, 7), (6, 3), (4, 5)]


def register_fonts():
    font_dir = Path(r"C:\Windows\Fonts")
    font_files = {
        "Arial": font_dir / "arial.ttf",
        "Arial-Bold": font_dir / "arialbd.ttf",
        "Arial-Italic": font_dir / "ariali.ttf",
        "Arial-BoldItalic": font_dir / "arialbi.ttf",
    }
    if all(path.exists() for path in font_files.values()):
        for name, path in font_files.items():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        pdfmetrics.registerFontFamily(
            "Arial",
            normal="Arial",
            bold="Arial-Bold",
            italic="Arial-Italic",
            boldItalic="Arial-BoldItalic",
        )
        return "Arial", "Arial-Bold", "Arial-Italic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


FONT, FONT_BOLD, FONT_ITALIC = register_fonts()


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.4,
            leading=10, textColor=GREEN, alignment=TA_CENTER, spaceAfter=3,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=styles["Title"], fontName=FONT_BOLD, fontSize=30,
            leading=32, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", parent=styles["Normal"], fontName=FONT, fontSize=10.6,
            leading=13.4, textColor=GRAY, alignment=TA_CENTER, spaceAfter=9,
        ),
        "kicker": ParagraphStyle(
            "kicker", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.2,
            leading=9.6, textColor=GREEN, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "title", parent=styles["Title"], fontName=FONT_BOLD, fontSize=18.5,
            leading=21, textColor=NAVY, alignment=TA_LEFT, spaceAfter=4,
        ),
        "title_center": ParagraphStyle(
            "title_center", parent=styles["Title"], fontName=FONT_BOLD, fontSize=19.5,
            leading=22, textColor=NAVY, alignment=TA_CENTER, spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=styles["Normal"], fontName=FONT, fontSize=9.2,
            leading=11.8, textColor=GRAY, spaceAfter=7,
        ),
        "subtitle_center": ParagraphStyle(
            "subtitle_center", parent=styles["Normal"], fontName=FONT, fontSize=9.4,
            leading=12, textColor=GRAY, alignment=TA_CENTER, spaceAfter=9,
        ),
        "body_center": ParagraphStyle(
            "body_center", parent=styles["Normal"], fontName=FONT, fontSize=8.8,
            leading=11.4, textColor=INK, alignment=TA_CENTER, spaceAfter=5,
        ),
        "h1": ParagraphStyle(
            "h1", parent=styles["Heading1"], fontName=FONT_BOLD, fontSize=11.6,
            leading=13.4, textColor=BLUE, spaceBefore=5, spaceAfter=4,
        ),
        "card_title": ParagraphStyle(
            "card_title", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9.2,
            leading=10.8, textColor=NAVY, spaceAfter=2.5,
        ),
        "card_body": ParagraphStyle(
            "card_body", parent=styles["Normal"], fontName=FONT, fontSize=8.1,
            leading=10.2, textColor=BLACK, spaceAfter=0,
        ),
        "card_detail": ParagraphStyle(
            "card_detail", parent=styles["Normal"], fontName=FONT_ITALIC, fontSize=7.2,
            leading=8.8, textColor=GRAY, spaceBefore=2.5, spaceAfter=0,
        ),
        "metric_label": ParagraphStyle(
            "metric_label", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=7.9,
            leading=9.2, textColor=NAVY, alignment=TA_CENTER, spaceAfter=1.5,
        ),
        "metric_body": ParagraphStyle(
            "metric_body", parent=styles["Normal"], fontName=FONT, fontSize=7.2,
            leading=8.7, textColor=BLACK, alignment=TA_CENTER, spaceAfter=0,
        ),
        "small_note": ParagraphStyle(
            "small_note", parent=styles["Normal"], fontName=FONT_ITALIC, fontSize=6.9,
            leading=8.6, textColor=GRAY, spaceAfter=3,
        ),
        "small_note_center": ParagraphStyle(
            "small_note_center", parent=styles["Normal"], fontName=FONT_ITALIC, fontSize=6.9,
            leading=8.6, textColor=GRAY, alignment=TA_CENTER, spaceAfter=3,
        ),
        "list": ParagraphStyle(
            "list", parent=styles["Normal"], fontName=FONT, fontSize=8.3,
            leading=10.6, textColor=BLACK, leftIndent=14, firstLineIndent=-10,
            bulletIndent=0, spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "callout", parent=styles["Normal"], fontName=FONT, fontSize=8.3,
            leading=10.6, textColor=BLACK, spaceAfter=0,
        ),
        "table_head": ParagraphStyle(
            "table_head", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=7.6,
            leading=9, textColor=WHITE, spaceAfter=0,
        ),
        "cell": ParagraphStyle(
            "cell", parent=styles["Normal"], fontName=FONT, fontSize=7.8,
            leading=9.6, textColor=BLACK, spaceAfter=0,
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=7.8,
            leading=9.6, textColor=INK, spaceAfter=0,
        ),
        "school": ParagraphStyle(
            "school", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.3,
            leading=10.2, textColor=INK, spaceAfter=0,
        ),
        "status_green": ParagraphStyle(
            "status_green", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=6.9,
            leading=8.4, textColor=GREEN, alignment=TA_CENTER, spaceAfter=0,
        ),
        "status_amber": ParagraphStyle(
            "status_amber", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=6.5,
            leading=8, textColor=AMBER, alignment=TA_CENTER, spaceAfter=0,
        ),
        "contact_label": ParagraphStyle(
            "contact_label", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=7.8,
            leading=9.6, textColor=WHITE, spaceAfter=0,
        ),
        "contact_value": ParagraphStyle(
            "contact_value", parent=styles["Normal"], fontName=FONT, fontSize=8.8,
            leading=10.6, textColor=BLUE, spaceAfter=0,
        ),
    }


S = make_styles()


def p(text, style):
    return Paragraph(text, S[style])


def draw_volet_furniture(canvas, x0, numero):
    """Entete, pied de page et numero propres a un volet (une page du livret)."""
    x1 = x0 + COL_WIDTH
    couverture = numero in (1, TOTAL_VOLETS)
    if not couverture:
        canvas.setFont(FONT_BOLD, 7.4)
        canvas.setFillColor(NAVY)
        canvas.drawString(x0, PAGE_HEIGHT - 28, "MYSCHOOLGN")
        canvas.setFillColor(GRAY)
        canvas.drawRightString(x1, PAGE_HEIGHT - 28, "CATALOGUE 2026")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(x0, PAGE_HEIGHT - 34, x1, PAGE_HEIGHT - 34)
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(x0, 23, x1, 23)
    canvas.setFont(FONT, 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(x0, 12, "www.myschoolgn.space  |  +224 622 61 35 59")
    canvas.setFont(FONT_BOLD, 7.6)
    canvas.setFillColor(NAVY)
    canvas.drawRightString(x1, 12, f"{numero} / {TOTAL_VOLETS}")


def on_page(canvas, doc):
    canvas.resetTransforms()
    canvas.saveState()
    gauche, droite = doc.imposition[doc.page - 1]
    # Ligne mediane : trait de pliage du livret.
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    if doc.mode_livret:
        canvas.setDash(2, 3)
    canvas.line(GUTTER_CENTER, 16, GUTTER_CENTER, PAGE_HEIGHT - 20)
    canvas.setDash()
    if doc.mode_livret:
        canvas.setFont(FONT, 5.8)
        canvas.setFillColor(GRAY)
        canvas.saveState()
        canvas.translate(GUTTER_CENTER - 3, PAGE_HEIGHT / 2 - 14)
        canvas.rotate(90)
        canvas.drawString(0, 0, "PLI")
        canvas.restoreState()
    draw_volet_furniture(canvas, COL1_X, gauche)
    draw_volet_furniture(canvas, COL2_X, droite)
    canvas.restoreState()


def metric_strip(metrics, width=COL_WIDTH):
    fills = [PALE_BLUE, PALE_GREEN, PALE_ORANGE]
    accents = [NAVY, GREEN, ORANGE]
    cells = [[p(label.upper(), "metric_label"), p(text, "metric_body")] for label, text in metrics]
    table = Table([cells], colWidths=[width / len(cells)] * len(cells), hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
    ]
    for idx in range(len(cells)):
        commands.append(("BACKGROUND", (idx, 0), (idx, 0), fills[idx % 3]))
        commands.append(("LINEABOVE", (idx, 0), (idx, 0), 2.0, accents[idx % 3]))
    table.setStyle(TableStyle(commands))
    return table


def feature_card(title, body, detail=None, accent=NAVY, fill=WHITE, width=COL_WIDTH):
    """Fiche pleine largeur de colonne : titre, description, precision."""
    title_style = ParagraphStyle(
        f"ft_{abs(hash((title, accent.hexval())))}", parent=S["card_title"], textColor=accent
    )
    content = [Paragraph(title, title_style), p(body, "card_body")]
    if detail:
        content.append(p(detail, "card_detail"))
    table = Table([[content]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 2.6, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def cards_grid(cards, width=COL_WIDTH):
    """Grille 2 colonnes a l'interieur d'un volet."""
    rows = []
    for idx in range(0, len(cards), 2):
        row = []
        for card in cards[idx : idx + 2]:
            title_style = ParagraphStyle(
                f"cg_{abs(hash((card['title'], card.get('accent', NAVY).hexval())))}",
                parent=S["card_title"],
                textColor=card.get("accent", NAVY),
            )
            cell = [Paragraph(card["title"], title_style), p(card["body"], "card_body")]
            if card.get("detail"):
                cell.append(p(card["detail"], "card_detail"))
            row.append(cell)
        if len(row) == 1:
            row.append("")
        rows.append(row)
    table = Table(rows, colWidths=[width / 2] * 2, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
    ]
    for idx, card in enumerate(cards):
        row, col = divmod(idx, 2)
        commands.append(("BACKGROUND", (col, row), (col, row), card.get("fill", WHITE)))
        commands.append(("LINEABOVE", (col, row), (col, row), 2.0, card.get("accent", NAVY)))
    table.setStyle(TableStyle(commands))
    return table


def callout(label, text, fill=PALE_BLUE, accent=BLUE, width=COL_WIDTH):
    content = Paragraph(
        f'<font color="#{accent.hexval()[2:]}"><b>{label}</b></font>&nbsp;&nbsp;{text}',
        S["callout"],
    )
    table = Table([[content]], colWidths=[width], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def list_item(text, lead, ordered=None):
    rest = text[len(lead):] if text.startswith(lead) else text
    prefix = f"{ordered}." if ordered is not None else "•"
    return Paragraph(f"{prefix}&nbsp;&nbsp;<b>{lead}</b>{rest}", S["list"])


def two_col_table(rows, head, widths, head_fill=NAVY):
    data = [[p(head[0], "table_head"), p(head[1], "table_head")]]
    for left, right in rows:
        data.append([p(left, "cell_bold"), p(right, "cell")])
    table = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), head_fill),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
    return table


def school_table():
    data = [
        [p("N°", "table_head"), p("ÉTABLISSEMENT", "table_head"), p("STATUT", "table_head")],
        [p("01", "small_note_center"), p("Hadja Kanfing de Somayah", "school"), p("EN UTILISATION", "status_green")],
        [p("02", "small_note_center"), p("Kinder School Internationale", "school"), p("EN UTILISATION", "status_green")],
        [p("03", "small_note_center"), p("Les Écoles Naby Bakoro de Somayah", "school"), p("EN UTILISATION", "status_green")],
        [p("04", "small_note_center"), p("Hadja Kanfing de Sonfonia", "school"), p("EN UTILISATION", "status_green")],
        [p("05", "small_note_center"), p("Les Espoirs d'Afrique", "school"), p("CONTRACTUALISATION EN COURS", "status_amber")],
    ]
    table = Table(data, colWidths=[26, COL_WIDTH - 26 - 118, 118], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (2, 1), (2, 4), PALE_GREEN),
                ("BACKGROUND", (2, 5), (2, 5), PALE_AMBER),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
            ]
        )
    )
    return table


def contact_table():
    data = [
        [p("SITE WEB", "contact_label"),
         Paragraph('<link href="https://www.myschoolgn.space" color="#2E74B5">www.myschoolgn.space</link>', S["contact_value"])],
        [p("TÉLÉPHONE", "contact_label"),
         Paragraph('<link href="tel:+224622613559" color="#2E74B5">+224 622 61 35 59</link>', S["contact_value"])],
        [p("EMAIL", "contact_label"),
         Paragraph('<link href="mailto:contact@myschoolgn.space" color="#2E74B5">contact@myschoolgn.space</link>', S["contact_value"])],
    ]
    table = Table(data, colWidths=[96, COL_WIDTH - 96], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), NAVY),
                ("BACKGROUND", (1, 0), (1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


# ---------------------------------------------------------------- volets (8)

def volet_1a():
    """Page 1 - volet gauche : couverture."""
    return [
        Spacer(1, 2),
        Image(str(LOGO), width=68, height=68, hAlign="CENTER"),
        Spacer(1, 4),
        p("CATALOGUE DE SOLUTION · ÉDITION 2026", "cover_kicker"),
        p("MySchoolGN", "cover_title"),
        p("Le pilotage scolaire, pédagogique et financier dans un seul environnement", "cover_subtitle"),
        Image(str(SCHOOL_PHOTO), width=COL_WIDTH, height=165, hAlign="CENTER"),
        Spacer(1, 8),
        p(
            "Une solution conçue pour les établissements guinéens, de la maternelle à la terminale, "
            "accessible en ligne et disponible en application Windows.",
            "body_center",
        ),
        Spacer(1, 2),
        metric_strip(
            [
                ("Pédagogie", "Notes, bulletins, résultats"),
                ("Administration", "Élèves, classes, documents"),
                ("Finances", "Paiements, dépenses, pilotage"),
            ]
        ),
        Spacer(1, 10),
        two_col_table(
            [
                ("Destinataires", "Écoles privées et publiques, groupes scolaires multi-sites"),
                ("Cycles couverts", "Maternelle, primaire, collège et lycée"),
                ("Utilisation", "Application web et application Windows hors ligne"),
                ("Utilisateurs", "Direction, secrétariat, comptabilité, enseignants, parents"),
                ("Langue", "Français, adapté au système éducatif guinéen"),
            ],
            ("EN BREF", "CE QU'IL FAUT RETENIR"),
            [96, COL_WIDTH - 96],
        ),
        Spacer(1, 8),
        p("Préscolaire · Primaire · Collège · Lycée", "small_note_center"),
    ]


def volet_1b():
    """Page 1 - volet droit : la promesse."""
    return [
        p("UNE ÉCOLE MIEUX ORGANISÉE", "kicker"),
        p("La gestion scolaire devient plus simple", "title"),
        p(
            "MySchoolGN réunit les opérations essentielles de l'établissement dans un système "
            "cohérent, sécurisé et facile à consulter.",
            "subtitle",
        ),
        cards_grid(
            [
                {
                    "title": "CENTRALISER",
                    "body": "Dossiers élèves, classes, notes, paiements, personnel et services regroupés dans un même espace.",
                    "accent": NAVY, "fill": PALE_BLUE,
                },
                {
                    "title": "AUTOMATISER",
                    "body": "Moyennes, classements, échéanciers et documents PDF calculés ou générés sans ressaisie.",
                    "accent": GREEN, "fill": PALE_GREEN,
                },
                {
                    "title": "PILOTER",
                    "body": "Tableaux de bord clairs : effectifs, résultats, recettes, dépenses et impayés.",
                    "accent": ORANGE, "fill": PALE_ORANGE,
                },
                {
                    "title": "COMMUNIQUER",
                    "body": "Bulletins, reçus, rapports et rappels transmis plus facilement aux familles.",
                    "accent": BLUE, "fill": LIGHT_GRAY,
                },
            ]
        ),
        p("Une réponse pour chaque acteur", "h1"),
        list_item("Direction : une vue d'ensemble pour suivre l'activité et décider sur des chiffres fiables.", "Direction :"),
        list_item("Enseignants : saisie structurée des notes, bulletins et appréciations calculés automatiquement.", "Enseignants :"),
        list_item("Comptabilité : échéanciers, reçus numérotés et états financiers toujours à jour.", "Comptabilité :"),
        list_item("Parents : accès simple aux résultats et à la situation financière de leur enfant.", "Parents :"),
        Spacer(1, 2),
        p("Ce que l'école gagne concrètement", "h1"),
        two_col_table(
            [
                ("Bulletins", "Moyennes, rangs et mentions calculés, puis édition PDF par classe"),
                ("Encaissements", "Reçu numéroté remis immédiatement, situation de l'élève à jour"),
                ("Impayés", "Liste des élèves en retard disponible à tout moment"),
                ("Archives", "Dossiers, notes et paiements conservés d'une année à l'autre"),
                ("Contrôle", "Journal d'activité : qui a fait quoi, quand et sur quel dossier"),
            ],
            ("BESOIN", "RÉPONSE APPORTÉE PAR MYSCHOOLGN"),
            [88, COL_WIDTH - 88],
        ),
        Spacer(1, 8),
        callout(
            "DEUX MODES D'UTILISATION",
            "Accès en ligne depuis un navigateur, ou application de bureau Windows fonctionnant sans connexion Internet.",
            PALE_GREEN, GREEN,
        ),
        Spacer(1, 6),
        callout(
            "MISE EN ROUTE",
            "Reprise des listes existantes par import Excel, formation des équipes et accompagnement après le démarrage.",
            PALE_ORANGE, ORANGE,
        ),
    ]


def volet_2a():
    """Page 2 - volet gauche : modules essentiels 1 a 3."""
    return [
        p("FONCTIONNALITÉS · 1", "kicker"),
        p("Les modules essentiels", "title"),
        p(
            "De l'inscription de l'élève jusqu'au bulletin et au reçu de paiement, MySchoolGN "
            "couvre le cycle de gestion quotidien de l'établissement.",
            "subtitle",
        ),
        feature_card(
            "1. GESTION DES ÉLÈVES",
            "Inscriptions et dossiers complets, responsables et contacts, photos, matricules générés "
            "automatiquement, affectation aux classes, transferts, archivage et passage à la nouvelle année scolaire.",
            "Import et export Excel des listes · cartes scolaires et fiches d'inscription PDF · recherche multicritère.",
            NAVY, PALE_BLUE,
        ),
        Spacer(1, 5),
        feature_card(
            "2. NOTES, BULLETINS & PÉDAGOGIE",
            "Saisie des notes par matière, évaluation et trimestre, calcul des moyennes pondérées, rangs, "
            "mentions et appréciations, emploi du temps par classe et calendrier des professeurs.",
            "Bulletins maternelle, primaire et secondaire · édition individuelle ou par classe · analyse des résultats.",
            GREEN, PALE_GREEN,
        ),
        Spacer(1, 5),
        feature_card(
            "3. PAIEMENTS & SCOLARITÉ",
            "Grilles tarifaires par école et par classe, échéanciers, paiements partiels avec allocation "
            "intelligente, remises, suivi des impayés et relances, reçus numérotés automatiquement.",
            "Espèces, Mobile Money, chèque ou virement · exports comptables · tableau de recouvrement.",
            ORANGE, PALE_ORANGE,
        ),
        Spacer(1, 6),
        p("Détails qui font la différence", "h1"),
        list_item("Matricule automatique : chaque élève reçoit un identifiant unique, sans doublon.", "Matricule automatique :"),
        list_item("Paiement partiel intelligent : le versement est réparti automatiquement sur les échéances dues.", "Paiement partiel intelligent :"),
        list_item("Reçus numérotés : numérotation continue par année, traçable et vérifiable.", "Reçus numérotés :"),
        list_item("Matière non notée : comptée comme telle dans la moyenne, pour un classement équitable.", "Matière non notée :"),
        Spacer(1, 4),
        two_col_table(
            [
                ("Inscription", "Frais d'inscription ou de réinscription par classe"),
                ("Scolarité", "Mensualités ou tranches, avec échéancier par élève"),
                ("Services", "Transport scolaire et cantine facturés séparément"),
                ("Remises", "Bourses, réductions fratrie et cas particuliers"),
                ("Encaissement", "Espèces, Mobile Money, chèque ou virement"),
            ],
            ("TARIFICATION", "CE QUE LA GRILLE PERMET DE GÉRER"),
            [92, COL_WIDTH - 92],
        ),
        Spacer(1, 6),
        callout(
            "DOCUMENTS GÉNÉRÉS",
            "Cartes scolaires, bulletins et livrets, reçus, notes de rappel, certificats, fiches de paie et rapports.",
            PALE_BLUE, NAVY,
        ),
    ]


def volet_2b():
    """Page 2 - volet droit : modules essentiels 4 a 6."""
    return [
        p("FONCTIONNALITÉS · 2", "kicker"),
        p("Suivi, pilotage et relation familles", "title"),
        p(
            "Les données saisies une seule fois alimentent les tableaux de bord, les rapports "
            "et les informations transmises aux parents.",
            "subtitle",
        ),
        feature_card(
            "4. ESPACE PARENTS",
            "Consultation sécurisée des notes, du classement, des activités et de la situation financière "
            "de l'élève depuis un téléphone ou un ordinateur, avec téléchargement des reçus.",
            "Accès identifié par matricule, numéro du responsable et classe.",
            BLUE, LIGHT_GRAY,
        ),
        Spacer(1, 5),
        feature_card(
            "5. RAPPORTS & TABLEAUX DE BORD",
            "Synthèses pédagogiques, financières et administratives : effectifs par classe et par cycle, "
            "résultats, recettes, dépenses, taux de recouvrement et évolution mensuelle.",
            "Graphiques interactifs · exports PDF et Excel · filtres par école, classe et période.",
            NAVY, PALE_BLUE,
        ),
        Spacer(1, 5),
        feature_card(
            "6. COMMUNICATION",
            "Envoi des bulletins, reçus et rappels de paiement aux responsables par WhatsApp ou SMS, "
            "avec historique des envois consultable dans le système.",
            "Services de messagerie activables selon le choix de l'établissement.",
            GREEN, PALE_GREEN,
        ),
        Spacer(1, 6),
        p("Le parcours type d'une année scolaire", "h1"),
        list_item("Inscrire : créer les dossiers élèves, affecter les classes, éditer les cartes scolaires.", "Inscrire :", 1),
        list_item("Encaisser : appliquer la grille tarifaire, enregistrer les paiements, remettre les reçus.", "Encaisser :", 2),
        list_item("Évaluer : saisir les notes, contrôler les moyennes, publier les bulletins par trimestre.", "Évaluer :", 3),
        list_item("Analyser : suivre résultats, impayés et dépenses depuis les tableaux de bord.", "Analyser :", 4),
        list_item("Clôturer : archiver l'année, faire passer les élèves et ouvrir la rentrée suivante.", "Clôturer :", 5),
        Spacer(1, 4),
        two_col_table(
            [
                ("Effectifs", "Élèves par classe, par cycle et par école, à la date choisie"),
                ("Résultats", "Moyennes de classe, taux de réussite et élèves en difficulté"),
                ("Recettes", "Encaissements du jour, du mois et de la période scolaire"),
                ("Impayés", "Montant restant dû et taux de recouvrement par classe"),
                ("Dépenses", "Dépenses validées, en attente et rejetées, par catégorie"),
            ],
            ("INDICATEUR", "CE QUE LE TABLEAU DE BORD AFFICHE"),
            [86, COL_WIDTH - 86],
        ),
        Spacer(1, 6),
        callout(
            "UNE SEULE SAISIE",
            "L'information entrée dans un module alimente les bulletins, les reçus, les rapports et l'espace parents.",
            PALE_ORANGE, ORANGE,
        ),
    ]


def volet_3a():
    """Page 3 - volet gauche : modules complementaires."""
    return [
        p("UNE PLATEFORME ÉVOLUTIVE", "kicker"),
        p("Les modules complémentaires", "title"),
        p(
            "L'établissement active les modules utiles à son organisation et étend l'usage "
            "au rythme de ses priorités.",
            "subtitle",
        ),
        cards_grid(
            [
                {
                    "title": "RESSOURCES HUMAINES",
                    "body": "Fiches enseignants et personnel, taux horaire ou forfait, pointage, calcul des salaires et bulletins de paie PDF.",
                    "accent": NAVY, "fill": PALE_BLUE,
                },
                {
                    "title": "DÉPENSES & FOURNISSEURS",
                    "body": "Catégories de dépenses, fournisseurs (NIF/RCCM), pièces justificatives, workflow de validation et suivi des impayées.",
                    "accent": GREEN, "fill": PALE_GREEN,
                },
                {
                    "title": "TRANSPORT & CANTINE",
                    "body": "Abonnements bus par zone et itinéraire, cantine (déjeuner, goûter, complet), échéances et présences.",
                    "accent": ORANGE, "fill": PALE_ORANGE,
                },
                {
                    "title": "BIBLIOTHÈQUE",
                    "body": "Catalogue et catégories de livres, emprunts et retours, retards, pénalités cumulatives et statistiques.",
                    "accent": BLUE, "fill": LIGHT_GRAY,
                },
                {
                    "title": "ASSIDUITÉ & DISCIPLINE",
                    "body": "Pointage des présences et absences, retards, justificatifs et suivi par classe sur la période choisie.",
                    "accent": NAVY, "fill": PALE_BLUE,
                },
                {
                    "title": "ASSISTANT INTELLIGENT",
                    "body": "Chatbot d'aide intégré pour guider les utilisateurs dans les écrans et les procédures courantes.",
                    "accent": GREEN, "fill": PALE_GREEN,
                },
                {
                    "title": "COMPTABILITÉ",
                    "body": "Suivi des recettes et des dépenses, soldes par période, états et exports pour la tenue des comptes.",
                    "accent": ORANGE, "fill": PALE_ORANGE,
                },
                {
                    "title": "SAUVEGARDE & DONNÉES",
                    "body": "Sauvegardes de la base, restauration, imports et exports Excel, synchronisation entre postes.",
                    "accent": BLUE, "fill": LIGHT_GRAY,
                },
            ]
        ),
        Spacer(1, 6),
        p("Chaque module produit ses documents", "h1"),
        list_item("Élèves : carte scolaire, fiche d'inscription, liste de classe, certificat de scolarité.", "Élèves :"),
        list_item("Notes : bulletin trimestriel, livret annuel, procès-verbal et palmarès de classe.", "Notes :"),
        list_item("Paiements : reçu, échéancier, état des impayés et journal de caisse.", "Paiements :"),
        list_item("Personnel : fiche de paie, état de pointage et récapitulatif mensuel.", "Personnel :"),
        Spacer(1, 4),
        metric_strip(
            [
                ("Activation", "Modules ouverts à la demande"),
                ("Progressif", "Au rythme de l'établissement"),
                ("Sans rupture", "Les données restent liées"),
            ]
        ),
        Spacer(1, 6),
        callout(
            "MULTI-ÉCOLES",
            "Une même installation peut gérer plusieurs établissements, chacun avec son identité, ses classes, "
            "ses tarifs et ses utilisateurs.",
            PALE_ORANGE, ORANGE,
        ),
    ]


def volet_3b():
    """Page 3 - volet droit : securite, technique, deploiement."""
    return [
        p("SÉCURITÉ & MISE EN ŒUVRE", "kicker"),
        p("Des accès maîtrisés, un déploiement encadré", "title"),
        p(
            "Chaque utilisateur ne voit que ce qui le concerne. Les actions sensibles sont tracées "
            "dans un journal d'activité consultable par la direction.",
            "subtitle",
        ),
        two_col_table(
            [
                ("Administrateur", "Accès complet à tous les modules et à la configuration"),
                ("Directeur", "Lecture et écriture sur l'ensemble de l'activité scolaire"),
                ("Comptable", "Paiements, dépenses, salaires et rapports financiers"),
                ("Secrétaire", "Élèves, inscriptions et saisie des paiements"),
                ("Enseignant", "Saisie des notes pour ses classes uniquement"),
                ("Consultation", "Mode lecture seule, sans action possible"),
            ],
            ("PROFIL", "PÉRIMÈTRE D'ACCÈS"),
            [96, COL_WIDTH - 96],
        ),
        Spacer(1, 6),
        p("Deux modes de déploiement", "h1"),
        cards_grid(
            [
                {
                    "title": "EN LIGNE",
                    "body": "Application web accessible depuis un navigateur, sur ordinateur, tablette ou téléphone. Sauvegardes centralisées.",
                    "accent": BLUE, "fill": PALE_BLUE,
                },
                {
                    "title": "SUR POSTE (WINDOWS)",
                    "body": "Application de bureau installable, utilisable sans Internet, protégée par une licence propre à l'établissement.",
                    "accent": GREEN, "fill": PALE_GREEN,
                },
            ]
        ),
        Spacer(1, 6),
        p("Un déploiement progressif", "h1"),
        list_item("Cadrer les besoins : cycles, effectifs, utilisateurs et organisation financière.", "Cadrer les besoins :", 1),
        list_item("Configurer l'école : identité, classes, année scolaire, tarifs, rôles et permissions.", "Configurer l'école :", 2),
        list_item("Reprendre les données : importer les listes existantes et contrôler les informations clés.", "Reprendre les données :", 3),
        list_item("Former et accompagner : démarrer par les modules prioritaires puis étendre l'usage.", "Former et accompagner :", 4),
        Spacer(1, 5),
        two_col_table(
            [
                ("Poste de travail", "Windows, navigateur récent ; tablette et téléphone pour la consultation"),
                ("Installation", "Programme d'installation guidé, licence propre à l'établissement"),
                ("Échanges", "Génération PDF intégrée, imports et exports Excel des listes"),
            ],
            ("PRÉ-REQUIS", "CE QU'IL FAUT PRÉVOIR"),
            [96, COL_WIDTH - 96],
        ),
        Spacer(1, 6),
        callout(
            "PROTECTION DES DONNÉES",
            "Comptes nominatifs, mots de passe individuels, journal d'activité et sauvegardes régulières de la base.",
            PALE_BLUE, NAVY,
        ),
    ]


def volet_4a():
    """Page 4 - volet gauche : references."""
    return [
        p("RÉFÉRENCES", "kicker"),
        p("Ils utilisent déjà MySchoolGN", "title"),
        p(
            "MySchoolGN accompagne plusieurs communautés scolaires et poursuit son déploiement "
            "auprès de nouveaux établissements.",
            "subtitle",
        ),
        metric_strip(
            [
                ("4 établissements", "utilisent MySchoolGN"),
                ("1 établissement", "en contractualisation"),
                ("1 ambition", "mieux piloter l'école"),
            ]
        ),
        Spacer(1, 8),
        school_table(),
        Spacer(1, 3),
        p(
            "Liste communiquée pour ce catalogue en juillet 2026. Le statut « contractualisation en cours » "
            "ne correspond pas encore à une mise en production.",
            "small_note",
        ),
        Spacer(1, 4),
        p("Ce que MySchoolGN structure au quotidien", "h1"),
        cards_grid(
            [
                {"title": "VIE SCOLAIRE", "body": "Inscriptions, classes, élèves et familles.", "accent": NAVY, "fill": PALE_BLUE},
                {"title": "PÉDAGOGIE", "body": "Notes, bulletins, classements et activités.", "accent": GREEN, "fill": PALE_GREEN},
                {"title": "GESTION", "body": "Paiements, dépenses, salaires et services.", "accent": ORANGE, "fill": PALE_ORANGE},
                {"title": "RELATION PARENTS", "body": "Rapports, reçus et communication ciblée.", "accent": BLUE, "fill": LIGHT_GRAY},
            ]
        ),
        Spacer(1, 8),
        p("Questions fréquentes", "h1"),
        list_item("Faut-il Internet ? Non : l'application Windows fonctionne hors ligne, la version web nécessite une connexion.", "Faut-il Internet ?"),
        list_item("Et nos données actuelles ? Les listes d'élèves et de classes sont reprises par import Excel.", "Et nos données actuelles ?"),
        list_item("Plusieurs écoles ? Oui : chaque établissement garde son identité, ses tarifs et ses utilisateurs.", "Plusieurs écoles ?"),
        list_item("Combien d'utilisateurs ? Autant que nécessaire, chacun avec son rôle et ses droits.", "Combien d'utilisateurs ?"),
        Spacer(1, 3),
        callout(
            "ACCOMPAGNEMENT",
            "Installation, configuration de l'école, reprise des listes, formation des utilisateurs et assistance après le démarrage.",
            PALE_GREEN, GREEN,
        ),
    ]


def volet_4b():
    """Page 4 - volet droit : appel a l'action et contact."""
    return [
        Spacer(1, 6),
        Image(str(LOGO), width=74, height=74, hAlign="CENTER"),
        Spacer(1, 6),
        p("PASSONS À L'ÉTAPE SUIVANTE", "cover_kicker"),
        p("Prêt à moderniser la gestion de votre école ?", "title_center"),
        p(
            "Demandez une présentation de MySchoolGN et identifiez ensemble les modules "
            "les plus utiles à votre établissement.",
            "subtitle_center",
        ),
        metric_strip(
            [
                ("1. Démonstration", "Découvrir les parcours clés"),
                ("2. Cadrage", "Prioriser les besoins de l'école"),
                ("3. Déploiement", "Configurer, importer et former"),
            ]
        ),
        Spacer(1, 10),
        p("Ce que comprend une mise en place", "h1"),
        list_item("Paramétrage de l'école : cycles, classes, année scolaire, grille tarifaire et rôles.", "Paramétrage de l'école :"),
        list_item("Reprise des données : import des listes d'élèves, du personnel et des soldes en cours.", "Reprise des données :"),
        list_item("Formation : prise en main par métier, secrétariat, comptabilité et enseignants.", "Formation :"),
        list_item("Suivi : assistance après le démarrage et mises à jour de l'application.", "Suivi :"),
        Spacer(1, 8),
        p("Contact MySchoolGN", "h1"),
        contact_table(),
        Spacer(1, 12),
        callout("MYSCHOOLGN", "Gérez votre école avec intelligence.", PALE_GREEN, GREEN),
        Spacer(1, 10),
        p("Préscolaire · Primaire · Collège · Lycée", "body_center"),
        p(
            "Les fonctionnalités disponibles dépendent des modules activés et de la configuration "
            "retenue par l'établissement.",
            "small_note_center",
        ),
    ]


# Les 8 pages du livret, dans l'ordre de lecture (page 1 = couverture).
PAGES = [
    volet_1a,  # 1 - couverture
    volet_1b,  # 2 - la promesse
    volet_2a,  # 3 - modules essentiels 1 a 3
    volet_2b,  # 4 - suivi, pilotage, familles
    volet_3a,  # 5 - modules complementaires
    volet_3b,  # 6 - securite et mise en oeuvre
    volet_4a,  # 7 - references
    volet_4b,  # 8 - contact (dos de couverture)
]


def build_story(imposition):
    story = []
    for index, (gauche, droite) in enumerate(imposition):
        story.extend(PAGES[gauche - 1]())
        story.append(FrameBreak())
        story.extend(PAGES[droite - 1]())
        if index < len(imposition) - 1:
            story.append(PageBreak())
    return story


def measure():
    """Controle de debordement : hauteur reelle de chaque page du livret."""
    report = []
    for numero, builder in enumerate(PAGES, start=1):
        total = 0.0
        previous_after = 0.0
        for flowable in builder():
            _, height = flowable.wrap(COL_WIDTH, COL_HEIGHT)
            before = getattr(flowable, "getSpaceBefore", lambda: 0)()
            after = getattr(flowable, "getSpaceAfter", lambda: 0)()
            # ReportLab garde le maximum entre spaceAfter et spaceBefore.
            total += max(previous_after, before) + height
            previous_after = after
        total += previous_after
        report.append((numero, total, COL_HEIGHT))
    return report


def build_pdf(output, imposition, mode_livret):
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(output),
        pagesize=landscape(A4),
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=TOP,
        bottomMargin=BOTTOM,
        title="Catalogue MySchoolGN 2026",
        author="MySchoolGN",
        subject="Presentation commerciale du logiciel MySchoolGN",
    )
    # Lus par on_page pour numeroter chaque volet selon sa page de livret.
    doc.imposition = imposition
    doc.mode_livret = mode_livret
    frames = [
        Frame(COL1_X, BOTTOM, COL_WIDTH, COL_HEIGHT, id="gauche",
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(COL2_X, BOTTOM, COL_WIDTH, COL_HEIGHT, id="droite",
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
    ]
    doc.addPageTemplates([PageTemplate(id="deux_volets", frames=frames, onPageEnd=on_page)])
    doc.build(build_story(imposition))
    return output


if __name__ == "__main__":
    for numero, used, avail in measure():
        flag = "OK " if used <= avail else "DEBORDE"
        print(f"{flag} page {numero}/{TOTAL_VOLETS} : {used:6.1f} / {avail:6.1f} pt")
    print(f"\n{TOTAL_VOLETS} pages sur {TOTAL_FEUILLES} faces = {TOTAL_FEUILLES // 2} feuilles recto verso")
    print("Lecture :", build_pdf(OUTPUT_LECTURE, IMPOSITION_LECTURE, mode_livret=False))
    print("Livret  :", build_pdf(OUTPUT_LIVRET, IMPOSITION_LIVRET, mode_livret=True))
