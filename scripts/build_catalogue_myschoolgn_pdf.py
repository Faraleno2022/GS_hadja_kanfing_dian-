from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Catalogue_MySchoolGN_2026.pdf"
LOGO = ROOT / "static" / "logos" / "logo.png"
SCHOOL_PHOTO = ROOT / "static" / "images" / "carte2.jpg"

NAVY = colors.HexColor("#0E4A78")
BLUE = colors.HexColor("#2E74B5")
DARK_BLUE = colors.HexColor("#1F4D78")
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

PAGE_WIDTH, PAGE_HEIGHT = LETTER
LEFT = RIGHT = 1.0 * inch
TOP = 0.82 * inch
BOTTOM = 0.72 * inch
CONTENT_WIDTH = PAGE_WIDTH - LEFT - RIGHT


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


class NumberedCanvasMixin:
    pass


def on_page(canvas, doc):
    # A preceding table may leave a translated graphics state in some
    # ReportLab/renderer combinations. Restore absolute page coordinates.
    canvas.resetTransforms()
    canvas.saveState()
    canvas.setTitle("Catalogue MySchoolGN 2026")
    canvas.setAuthor("MySchoolGN")
    canvas.setSubject("Présentation commerciale du logiciel MySchoolGN")
    if doc.page == 1:
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, 31, PAGE_WIDTH - RIGHT, 31)
        canvas.setFont(FONT, 7.8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(
            PAGE_WIDTH / 2,
            18,
            "www.myschoolgn.space  |  +224 622 61 35 59  |  contact@myschoolgn.space",
        )
    elif doc.page == 6:
        # The final CTA page is designed as a closing cover and carries its
        # complete contact block inside the page body.
        pass
    else:
        canvas.setFont(FONT_BOLD, 7.8)
        canvas.setFillColor(NAVY)
        canvas.drawString(LEFT, PAGE_HEIGHT - 31, "MYSCHOOLGN")
        canvas.setFont(FONT_BOLD, 7.8)
        canvas.setFillColor(GRAY)
        canvas.drawRightString(PAGE_WIDTH - RIGHT, PAGE_HEIGHT - 31, "CATALOGUE 2026")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT, PAGE_HEIGHT - 37, PAGE_WIDTH - RIGHT, PAGE_HEIGHT - 37)
        canvas.line(LEFT, 31, PAGE_WIDTH - RIGHT, 31)
        canvas.setFont(FONT, 7.8)
        canvas.setFillColor(GRAY)
        canvas.drawString(LEFT, 18, "www.myschoolgn.space")
        canvas.drawRightString(PAGE_WIDTH - RIGHT, 18, f"Page {doc.page}")
    canvas.restoreState()


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.7,
            leading=10,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=31,
            leading=33,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=12.6,
            leading=15.5,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "kicker": ParagraphStyle(
            "kicker",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.6,
            leading=10,
            textColor=GREEN,
            spaceAfter=3,
        ),
        "title": ParagraphStyle(
            "title",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=24.5,
            leading=27,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "title_center": ParagraphStyle(
            "title_center",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=25.5,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=10.9,
            leading=14,
            textColor=GRAY,
            spaceAfter=9,
        ),
        "subtitle_center": ParagraphStyle(
            "subtitle_center",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=11,
            leading=14,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=13,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=9.4,
            leading=12,
            textColor=BLACK,
            spaceAfter=5,
        ),
        "body_center": ParagraphStyle(
            "body_center",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=9.6,
            leading=12.5,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=7,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=14.2,
            leading=16,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=5,
        ),
        "card_title": ParagraphStyle(
            "card_title",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=11.2,
            textColor=NAVY,
            spaceAfter=3,
        ),
        "card_body": ParagraphStyle(
            "card_body",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=8.4,
            leading=10.5,
            textColor=BLACK,
            spaceAfter=0,
        ),
        "card_detail": ParagraphStyle(
            "card_detail",
            parent=styles["Normal"],
            fontName=FONT_ITALIC,
            fontSize=7.35,
            leading=9,
            textColor=GRAY,
            spaceBefore=3,
            spaceAfter=0,
        ),
        "metric_label": ParagraphStyle(
            "metric_label",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.2,
            leading=9.5,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "metric_body": ParagraphStyle(
            "metric_body",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=7.7,
            leading=9.2,
            textColor=BLACK,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "small_note": ParagraphStyle(
            "small_note",
            parent=styles["Normal"],
            fontName=FONT_ITALIC,
            fontSize=7.2,
            leading=9,
            textColor=GRAY,
            spaceAfter=3,
        ),
        "small_note_center": ParagraphStyle(
            "small_note_center",
            parent=styles["Normal"],
            fontName=FONT_ITALIC,
            fontSize=7.2,
            leading=9,
            textColor=GRAY,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "list": ParagraphStyle(
            "list",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=8.8,
            leading=11.3,
            textColor=BLACK,
            leftIndent=15,
            firstLineIndent=-10,
            bulletIndent=0,
            spaceAfter=5,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=8.9,
            leading=11.4,
            textColor=BLACK,
            spaceAfter=0,
        ),
        "table_head": ParagraphStyle(
            "table_head",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.1,
            leading=9.5,
            textColor=WHITE,
            spaceAfter=0,
        ),
        "school": ParagraphStyle(
            "school",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.9,
            leading=10.8,
            textColor=INK,
            spaceAfter=0,
        ),
        "status_green": ParagraphStyle(
            "status_green",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=7.35,
            leading=8.8,
            textColor=GREEN,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "status_amber": ParagraphStyle(
            "status_amber",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=6.9,
            leading=8.4,
            textColor=AMBER,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "contact_label": ParagraphStyle(
            "contact_label",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8.2,
            leading=10,
            textColor=WHITE,
            spaceAfter=0,
        ),
        "contact_value": ParagraphStyle(
            "contact_value",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=9.2,
            leading=11,
            textColor=BLUE,
            spaceAfter=0,
        ),
    }


S = make_styles()


def p(text, style):
    return Paragraph(text, S[style])


def metric_strip(metrics):
    fills = [PALE_BLUE, PALE_GREEN, PALE_ORANGE]
    accents = [NAVY, GREEN, ORANGE]
    cells = []
    for label, text in metrics:
        cells.append([p(label.upper(), "metric_label"), p(text, "metric_body")])
    table = Table([cells], colWidths=[CONTENT_WIDTH / len(cells)] * len(cells), hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
    ]
    for idx in range(len(cells)):
        commands.extend(
            [
                ("BACKGROUND", (idx, 0), (idx, 0), fills[idx % 3]),
                ("LINEABOVE", (idx, 0), (idx, 0), 2.2, accents[idx % 3]),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def card_cell(title, body, detail=None, accent=NAVY):
    title_style = ParagraphStyle(
        f"card_title_{title}_{accent}",
        parent=S["card_title"],
        textColor=accent,
    )
    content = [Paragraph(title, title_style), p(body, "card_body")]
    if detail:
        content.append(p(detail, "card_detail"))
    return content


def cards_grid(cards, compact=False):
    rows = []
    for idx in range(0, len(cards), 2):
        row = []
        for card in cards[idx : idx + 2]:
            row.append(
                card_cell(
                    card["title"],
                    card["body"],
                    card.get("detail"),
                    card.get("accent", NAVY),
                )
            )
        if len(row) == 1:
            row.append("")
        rows.append(row)
    table = Table(rows, colWidths=[CONTENT_WIDTH / 2] * 2, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8 if compact else 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8 if compact else 9),
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
    ]
    for idx, card in enumerate(cards):
        row, col = divmod(idx, 2)
        commands.extend(
            [
                ("BACKGROUND", (col, row), (col, row), card.get("fill", WHITE)),
                ("LINEABOVE", (col, row), (col, row), 2.1, card.get("accent", NAVY)),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def callout(label, text, fill=PALE_BLUE, accent=BLUE):
    content = Paragraph(
        f'<font color="#{accent.hexval()[2:]}"><b>{label}</b></font>&nbsp;&nbsp;{text}',
        S["callout"],
    )
    table = Table([[content]], colWidths=[CONTENT_WIDTH], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3.2, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def list_item(text, lead, ordered=None):
    rest = text[len(lead) :] if text.startswith(lead) else text
    prefix = f"{ordered}." if ordered is not None else "•"
    return Paragraph(f"{prefix}&nbsp;&nbsp;<b>{lead}</b>{rest}", S["list"])


def school_table():
    data = [
        [p("N°", "table_head"), p("ÉTABLISSEMENT", "table_head"), p("STATUT", "table_head")],
        [p("01", "small_note_center"), p("Hadja Kanfing de Somayah", "school"), p("EN UTILISATION", "status_green")],
        [p("02", "small_note_center"), p("Kinder School Internationale", "school"), p("EN UTILISATION", "status_green")],
        [p("03", "small_note_center"), p("Les Écoles Naby Bakoro de Somayah", "school"), p("EN UTILISATION", "status_green")],
        [p("04", "small_note_center"), p("Hadja Kanfing de Sonfonia", "school"), p("EN UTILISATION", "status_green")],
        [
            p("05", "small_note_center"),
            p("Les Espoirs d'Afrique", "school"),
            p("CONTRACTUALISATION EN COURS", "status_amber"),
        ],
    ]
    table = Table(
        data,
        colWidths=[0.5 * inch, 3.72 * inch, 2.28 * inch],
        repeatRows=1,
        hAlign="LEFT",
    )
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BACKGROUND", (2, 1), (2, 4), PALE_GREEN),
        ("BACKGROUND", (2, 5), (2, 5), PALE_AMBER),
        ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    table.setStyle(TableStyle(commands))
    return table


def contact_table():
    data = [
        [
            p("SITE WEB", "contact_label"),
            Paragraph(
                '<link href="https://www.myschoolgn.space" color="#2E74B5">www.myschoolgn.space</link>',
                S["contact_value"],
            ),
        ],
        [
            p("TÉLÉPHONE", "contact_label"),
            Paragraph(
                '<link href="tel:+224622613559" color="#2E74B5">+224 622 61 35 59</link>',
                S["contact_value"],
            ),
        ],
        [
            p("EMAIL", "contact_label"),
            Paragraph(
                '<link href="mailto:contact@myschoolgn.space" color="#2E74B5">contact@myschoolgn.space</link>',
                S["contact_value"],
            ),
        ],
    ]
    table = Table(data, colWidths=[1.55 * inch, 4.95 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), NAVY),
                ("BACKGROUND", (1, 0), (1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def build_story():
    story = []

    # Page 1 — Cover
    story.extend(
        [
            Spacer(1, 2),
            Image(str(LOGO), width=1.1 * inch, height=1.1 * inch, hAlign="CENTER"),
            Spacer(1, 2),
            p("CATALOGUE DE SOLUTION · ÉDITION 2026", "cover_kicker"),
            p("MySchoolGN", "cover_title"),
            p(
                "Le pilotage scolaire, pédagogique et financier dans un seul environnement",
                "cover_subtitle",
            ),
            Image(str(SCHOOL_PHOTO), width=CONTENT_WIDTH, height=3.45 * inch, hAlign="CENTER"),
            Spacer(1, 8),
            p(
                "Une solution conçue pour les établissements guinéens, de la maternelle à la terminale, "
                "accessible en ligne et disponible en application Windows.",
                "body_center",
            ),
            metric_strip(
                [
                    ("Pédagogie", "Notes, bulletins et suivi des résultats"),
                    ("Administration", "Élèves, classes et documents scolaires"),
                    ("Finances", "Paiements, dépenses et pilotage"),
                ]
            ),
            Spacer(1, 6),
            p(
                "Centralisez l'information. Automatisez les tâches répétitives. Rapprochez l'école des familles.",
                "small_note_center",
            ),
            PageBreak(),
        ]
    )

    # Page 2 — Promise and benefits
    story.extend(
        [
            p("UNE ÉCOLE MIEUX ORGANISÉE", "kicker"),
            p("La gestion scolaire devient plus simple", "title"),
            p(
                "MySchoolGN réunit les opérations essentielles de l'établissement dans un système cohérent, "
                "sécurisé et facile à consulter.",
                "subtitle",
            ),
            cards_grid(
                [
                    {
                        "title": "CENTRALISER",
                        "body": "Dossiers élèves, classes, notes, paiements, personnel et services sont regroupés dans un même espace.",
                        "accent": NAVY,
                        "fill": PALE_BLUE,
                    },
                    {
                        "title": "AUTOMATISER",
                        "body": "Moyennes, classements, échéanciers et documents PDF sont calculés ou générés sans ressaisie inutile.",
                        "accent": GREEN,
                        "fill": PALE_GREEN,
                    },
                    {
                        "title": "PILOTER",
                        "body": "Les tableaux de bord donnent une vision claire des effectifs, des résultats, des recettes et des impayés.",
                        "accent": ORANGE,
                        "fill": PALE_ORANGE,
                    },
                    {
                        "title": "COMMUNIQUER",
                        "body": "Parents et responsables reçoivent plus facilement bulletins, reçus, rapports et rappels par les canaux prévus.",
                        "accent": BLUE,
                        "fill": LIGHT_GRAY,
                    },
                ]
            ),
            Spacer(1, 6),
            p("Une réponse pour chaque acteur", "h1"),
            list_item(
                "Direction : une vue d'ensemble pour suivre l'activité et prendre des décisions documentées.",
                "Direction :",
            ),
            list_item(
                "Enseignants : une saisie structurée des notes et des bulletins calculés automatiquement.",
                "Enseignants :",
            ),
            list_item(
                "Comptabilité : des échéanciers, reçus et états financiers mieux organisés.",
                "Comptabilité :",
            ),
            list_item(
                "Parents : un accès simple aux résultats et à la situation financière de leur enfant.",
                "Parents :",
            ),
            Spacer(1, 3),
            callout(
                "DEUX MODES D'UTILISATION",
                "Accès en ligne depuis un navigateur, ou application de bureau Windows pouvant fonctionner sans connexion Internet.",
                PALE_GREEN,
                GREEN,
            ),
            PageBreak(),
        ]
    )

    # Page 3 — Core modules
    story.extend(
        [
            p("FONCTIONNALITÉS", "kicker"),
            p("Les modules essentiels", "title"),
            p(
                "Du premier contact avec la famille jusqu'au bulletin et au suivi des paiements, "
                "MySchoolGN couvre le cycle de gestion quotidien.",
                "subtitle",
            ),
            cards_grid(
                [
                    {
                        "title": "1. GESTION DES ÉLÈVES",
                        "body": "Inscriptions, dossiers, responsables, photos, matricules automatiques, classes, transferts et nouvelle année scolaire.",
                        "detail": "Imports et exports Excel, cartes scolaires et fiches d'inscription PDF.",
                        "accent": NAVY,
                        "fill": PALE_BLUE,
                    },
                    {
                        "title": "2. NOTES & BULLETINS",
                        "body": "Saisie standard, guinéenne ou intelligente, calcul des moyennes, rangs, mentions et appréciations.",
                        "detail": "Bulletins primaire, secondaire et maternelle, individuels ou par classe.",
                        "accent": GREEN,
                        "fill": PALE_GREEN,
                    },
                    {
                        "title": "3. FINANCES & PAIEMENTS",
                        "body": "Grilles tarifaires, échéanciers, paiements partiels, remises, impayés, reçus et exports comptables.",
                        "detail": "Espèces, Mobile Money, chèque ou virement selon la configuration.",
                        "accent": ORANGE,
                        "fill": PALE_ORANGE,
                    },
                    {
                        "title": "4. ESPACE PARENTS",
                        "body": "Consultation sécurisée des notes, classements, activités, paiements et reçus depuis un téléphone ou un ordinateur.",
                        "detail": "Accès par matricule, numéro du responsable et classe.",
                        "accent": BLUE,
                        "fill": LIGHT_GRAY,
                    },
                    {
                        "title": "5. RAPPORTS & TABLEAUX DE BORD",
                        "body": "Synthèses pédagogiques, financières et administratives, graphiques interactifs et exports PDF ou Excel.",
                        "detail": "Suivi des effectifs, résultats, recettes, dépenses et taux de recouvrement.",
                        "accent": NAVY,
                        "fill": PALE_BLUE,
                    },
                    {
                        "title": "6. COMMUNICATION",
                        "body": "Envoi de bulletins, reçus et rappels de paiement par WhatsApp ou SMS selon les services activés.",
                        "detail": "Historique et suivi des envois disponibles dans le système.",
                        "accent": GREEN,
                        "fill": PALE_GREEN,
                    },
                ]
            ),
            Spacer(1, 8),
            callout(
                "DOCUMENTS GÉNÉRÉS",
                "Cartes scolaires, bulletins, livrets, reçus, notes de rappel, certificats, fiches de paie et rapports professionnels.",
                PALE_ORANGE,
                ORANGE,
            ),
            PageBreak(),
        ]
    )

    # Page 4 — Extended modules and implementation
    story.extend(
        [
            p("UNE PLATEFORME ÉVOLUTIVE", "kicker"),
            p("Pensée pour la réalité du terrain", "title"),
            p(
                "Les modules complémentaires permettent d'étendre MySchoolGN au rythme des priorités de l'établissement.",
                "subtitle",
            ),
            cards_grid(
                [
                    {
                        "title": "RESSOURCES HUMAINES",
                        "body": "Fiches enseignants, affectations, pointage, calcul des salaires et bulletins de paie PDF.",
                        "accent": NAVY,
                        "fill": PALE_BLUE,
                    },
                    {
                        "title": "DÉPENSES & FOURNISSEURS",
                        "body": "Catégories, pièces justificatives, workflow de validation, budget et suivi des engagements.",
                        "accent": GREEN,
                        "fill": PALE_GREEN,
                    },
                    {
                        "title": "TRANSPORT & CANTINE",
                        "body": "Abonnements, itinéraires, échéances, repas, restrictions alimentaires et présences.",
                        "accent": ORANGE,
                        "fill": PALE_ORANGE,
                    },
                    {
                        "title": "BIBLIOTHÈQUE & LOGISTIQUE",
                        "body": "Catalogue, emprunts, réservations, stocks, inventaires, biens et maintenance.",
                        "accent": BLUE,
                        "fill": LIGHT_GRAY,
                    },
                    {
                        "title": "SÉCURITÉ & PERMISSIONS",
                        "body": "Rôles, droits granulaires, validation des comptes, journal d'activité et accès contrôlés.",
                        "accent": NAVY,
                        "fill": PALE_BLUE,
                    },
                    {
                        "title": "ASSISTANT INTELLIGENT",
                        "body": "Aide interactive, ressources de cours et accompagnement des utilisateurs selon les fonctions activées.",
                        "accent": GREEN,
                        "fill": PALE_GREEN,
                    },
                ],
                compact=True,
            ),
            Spacer(1, 5),
            p("Un déploiement progressif", "h1"),
            list_item(
                "Cadrer les besoins : cycles, effectifs, utilisateurs, organisation financière et priorités.",
                "Cadrer les besoins :",
                1,
            ),
            list_item(
                "Configurer l'école : identité, classes, année scolaire, tarifs, rôles et permissions.",
                "Configurer l'école :",
                2,
            ),
            list_item(
                "Reprendre les données : importer les listes disponibles et contrôler les informations essentielles.",
                "Reprendre les données :",
                3,
            ),
            list_item(
                "Former et accompagner : démarrer par les modules prioritaires puis étendre l'usage.",
                "Former et accompagner :",
                4,
            ),
            PageBreak(),
        ]
    )

    # Page 5 — Schools
    story.extend(
        [
            p("RÉFÉRENCES", "kicker"),
            p("Établissements utilisateurs et déploiement en cours", "title"),
            p(
                "MySchoolGN accompagne déjà plusieurs communautés scolaires et poursuit son déploiement auprès de nouveaux établissements.",
                "subtitle",
            ),
            metric_strip(
                [
                    ("4 établissements", "utilisent MySchoolGN"),
                    ("1 établissement", "en contractualisation"),
                    ("1 même ambition", "mieux piloter l'école"),
                ]
            ),
            Spacer(1, 8),
            school_table(),
            Spacer(1, 4),
            p(
                "Liste communiquée pour ce catalogue en juillet 2026. Le statut « contractualisation en cours » ne correspond pas encore à une mise en production.",
                "small_note",
            ),
            callout(
                "UNE SOLUTION, PLUSIEURS CONTEXTES",
                "Chaque établissement peut configurer son identité, ses cycles, ses tarifs, ses rôles et les modules utiles à son organisation.",
                PALE_BLUE,
                NAVY,
            ),
            Spacer(1, 3),
            p("Ce que MySchoolGN structure au quotidien", "h1"),
            cards_grid(
                [
                    {
                        "title": "VIE SCOLAIRE",
                        "body": "Inscriptions, classes, élèves et familles.",
                        "accent": NAVY,
                        "fill": PALE_BLUE,
                    },
                    {
                        "title": "PÉDAGOGIE",
                        "body": "Notes, bulletins, classements et activités.",
                        "accent": GREEN,
                        "fill": PALE_GREEN,
                    },
                    {
                        "title": "GESTION",
                        "body": "Paiements, dépenses, salaires et services.",
                        "accent": ORANGE,
                        "fill": PALE_ORANGE,
                    },
                    {
                        "title": "RELATION PARENTS",
                        "body": "Rapports, reçus et communication ciblée.",
                        "accent": BLUE,
                        "fill": LIGHT_GRAY,
                    },
                ],
                compact=True,
            ),
            PageBreak(),
        ]
    )

    # Page 6 — CTA
    story.extend(
        [
            Spacer(1, 8),
            Image(str(LOGO), width=1.25 * inch, height=1.25 * inch, hAlign="CENTER"),
            Spacer(1, 7),
            p("PASSONS À L'ÉTAPE SUIVANTE", "cover_kicker"),
            p("Prêt à moderniser la gestion de votre école ?", "title_center"),
            p(
                "Demandez une présentation de MySchoolGN et identifiez les modules les plus utiles à votre établissement.",
                "subtitle_center",
            ),
            metric_strip(
                [
                    ("1. Démonstration", "Découvrir les parcours clés"),
                    ("2. Cadrage", "Prioriser les besoins de l'école"),
                    ("3. Déploiement", "Configurer, importer et former"),
                ]
            ),
            Spacer(1, 14),
            p("Contact MySchoolGN", "h1"),
            contact_table(),
            Spacer(1, 12),
            callout("MYSCHOOLGN", "Gérez votre école avec intelligence.", PALE_GREEN, GREEN),
            Spacer(1, 8),
            p("Préscolaire · Primaire · Collège · Lycée", "body_center"),
            p(
                "Les fonctionnalités disponibles dépendent des modules activés et de la configuration retenue par l'établissement.",
                "small_note_center",
            ),
        ]
    )
    return story


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP,
        bottomMargin=BOTTOM,
        title="Catalogue MySchoolGN 2026",
        author="MySchoolGN",
        subject="Présentation commerciale du logiciel MySchoolGN",
    )
    frame = Frame(
        LEFT,
        BOTTOM,
        CONTENT_WIDTH,
        PAGE_HEIGHT - TOP - BOTTOM,
        id="catalogue_frame",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    # Draw page furniture after flowables so a table/image graphics state can
    # never cover or clip the running header and footer.
    doc.addPageTemplates([PageTemplate(id="catalogue", frames=[frame], onPageEnd=on_page)])
    doc.build(build_story())
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
