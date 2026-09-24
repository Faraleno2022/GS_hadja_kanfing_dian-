"""Génération du carnet annuel de paiement d'un élève."""

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ecole_moderne.pdf_utils import draw_logo_watermark
from ecole_moderne.branding import get_reportlab_palette

from .models import Paiement


MOIS_FR = (
    '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
)


def _decimal(valeur):
    return Decimal(str(valeur or 0))


def _montant(valeur):
    return f"{int(_decimal(valeur)):,}".replace(',', '\u00a0') + " GNF"


def _texte(valeur):
    return escape(str(valeur or ''))


def _logo_path(ecole):
    try:
        chemin = getattr(getattr(ecole, 'logo', None), 'path', None)
        if chemin:
            return chemin
    except Exception:
        pass
    return finders.find('logos/logo.jpeg')


def _lignes_carnet(paiement, echeancier):
    paiements = list(
        Paiement.objects.filter(
            eleve_id=paiement.eleve_id,
            annee_scolaire=paiement.annee_scolaire,
            statut='VALIDE',
        )
        .prefetch_related('remises')
        .order_by('date_paiement', 'date_validation', 'id')
    )
    total_du = _decimal(getattr(echeancier, 'total_du', 0))
    if total_du <= 0:
        total_du = sum((_decimal(item.montant) for item in paiements), Decimal('0'))

    cumul_encaisse = Decimal('0')
    cumul_remises = Decimal('0')
    lignes = []
    for item in paiements:
        cumul_encaisse += _decimal(item.montant)
        cumul_remises += sum(
            (_decimal(remise.montant_remise) for remise in item.remises.all()),
            Decimal('0'),
        )
        reste = max(Decimal('0'), total_du - cumul_encaisse - cumul_remises)
        lignes.append({
            'revision': item.frais_revision_inclus,
            'mois': MOIS_FR[item.date_paiement.month],
            'date': item.date_paiement.strftime('%d/%m/%Y'),
            'montant': item.montant,
            'reste': reste,
        })

    return lignes, total_du, cumul_encaisse, cumul_remises


def construire_carnet_paiement_pdf(paiement, echeancier):
    """Retourne le carnet PDF et son résumé financier."""
    ecole = getattr(getattr(paiement.eleve, 'classe', None), 'ecole', None)
    palette = get_reportlab_palette(ecole)
    lignes, total_du, total_encaisse, total_remises = _lignes_carnet(
        paiement, echeancier
    )
    reste_global = max(Decimal('0'), total_du - total_encaisse - total_remises)

    buffer = BytesIO()
    largeur, hauteur = landscape(A4)
    document = SimpleDocTemplate(
        buffer,
        pagesize=(largeur, hauteur),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=12 * mm,
        title=f"Carnet de paiement - {paiement.eleve.nom_complet}",
        author=getattr(ecole, 'nom', 'MySchoolGN'),
    )

    styles = getSampleStyleSheet()
    titre = ParagraphStyle(
        'CarnetTitre',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=21,
        textColor=palette['primary'],
        alignment=TA_LEFT,
        spaceAfter=2,
    )
    sous_titre = ParagraphStyle(
        'CarnetSousTitre',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=palette['muted'],
    )
    petit = ParagraphStyle(
        'CarnetPetit',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=palette['text'],
    )
    cellule = ParagraphStyle(
        'CarnetCellule',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=9,
        alignment=TA_CENTER,
    )
    entete = ParagraphStyle(
        'CarnetEntete',
        parent=cellule,
        fontName='Helvetica-Bold',
        textColor=palette['header_text'],
    )

    logo = _logo_path(ecole)
    bloc_logo = ''
    if logo:
        try:
            bloc_logo = Image(logo, width=24 * mm, height=24 * mm, kind='proportional')
        except Exception:
            bloc_logo = ''
    identite = [
        Paragraph('CARNET DE PAIEMENT', titre),
        Paragraph(
            f"{_texte(getattr(ecole, 'nom', 'Établissement scolaire'))}<br/>"
            f"Année scolaire : <b>{_texte(paiement.annee_scolaire)}</b>",
            sous_titre,
        ),
    ]
    header = Table([[bloc_logo, identite]], colWidths=[30 * mm, 230 * mm])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    eleve = paiement.eleve
    classe = getattr(eleve, 'classe', None)
    infos = Table([
        [
            Paragraph(f"<b>Élève</b><br/>{_texte(eleve.nom_complet)}", petit),
            Paragraph(f"<b>Matricule</b><br/>{_texte(eleve.matricule)}", petit),
            Paragraph(f"<b>Classe</b><br/>{_texte(getattr(classe, 'nom', ''))}", petit),
            Paragraph(f"<b>Année</b><br/>{_texte(paiement.annee_scolaire)}", petit),
        ]
    ], colWidths=[76 * mm, 47 * mm, 82 * mm, 47 * mm])
    infos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), palette['primary_soft']),
        ('BOX', (0, 0), (-1, -1), 0.6, palette['border']),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, palette['table']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    resume = Table([
        [
            Paragraph(f"<b>Total dû</b><br/>{_montant(total_du)}", cellule),
            Paragraph(f"<b>Total encaissé</b><br/>{_montant(total_encaisse)}", cellule),
            Paragraph(f"<b>Total remises</b><br/>{_montant(total_remises)}", cellule),
            Paragraph(f"<b>Reste à payer</b><br/>{_montant(reste_global)}", cellule),
        ]
    ], colWidths=[63 * mm] * 4)
    resume.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#F7FAFC')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#FFF4E5')),
        ('BOX', (0, 0), (-1, -1), 0.6, palette['border']),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, palette['table']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    tableau = [[
        Paragraph('Mois', entete),
        Paragraph('Date', entete),
        Paragraph('Montant', entete),
        Paragraph('Reste à payer', entete),
        Paragraph('Signature comptable', entete),
        Paragraph('Signature fondateur', entete),
        Paragraph('Signature parent', entete),
    ]]
    for ligne in lignes:
        tableau.append([
            Paragraph(_texte(ligne['mois']), cellule),
            Paragraph(_texte(ligne['date']), cellule),
            Paragraph(_montant(ligne['montant']) + ('<br/>Révision : -20 000 GNF' if ligne['revision'] else ''), cellule),
            Paragraph(_montant(ligne['reste']), cellule),
            '', '', '',
        ])
    while len(tableau) < 11:
        tableau.append(['', '', '', '', '', '', ''])

    grille = Table(
        tableau,
        colWidths=[24 * mm, 25 * mm, 31 * mm, 35 * mm, 47 * mm, 47 * mm, 43 * mm],
        rowHeights=[10 * mm] + [(14 if ligne['revision'] else 10) * mm for ligne in lignes] + [10 * mm] * (len(tableau) - 1 - len(lignes)),
        repeatRows=1,
    )
    grille.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), palette['header']),
        ('TEXTCOLOR', (0, 0), (-1, 0), palette['header_text']),
        ('GRID', (0, 0), (-1, -1), 0.55, palette['border']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, palette['table_alt']]),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    contenu = [
        header,
        Spacer(1, 4 * mm),
        infos,
        Spacer(1, 3 * mm),
        resume,
        Spacer(1, 4 * mm),
        Paragraph('Révision : 20 000 GNF déduits de la scolarité pour les lignes marquées, sans diminuer le versement encaissé.', cellule),
        Spacer(1, 2 * mm),
        grille,
        Spacer(1, 2 * mm),
        Paragraph(
            "Les montants et soldes ci-dessus tiennent compte uniquement des "
            "paiements validés et des remises enregistrées pour cette année scolaire.",
            sous_titre,
        ),
    ]

    def _page(canvas, doc):
        draw_logo_watermark(
            canvas, largeur, hauteur, ecole=ecole, opacity=0.025, rotate=0, scale=0.75
        )
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#718096'))
        canvas.drawRightString(
            largeur - 12 * mm,
            6 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    document.build(contenu, onFirstPage=_page, onLaterPages=_page)
    donnees = buffer.getvalue()
    buffer.close()
    return donnees, {
        'total_du': total_du,
        'total_encaisse': total_encaisse,
        'total_remises': total_remises,
        'reste_global': reste_global,
        'nombre_paiements': len(lignes),
    }
