"""Construction du carnet annuel de paiement d'un élève."""

from decimal import Decimal
from io import BytesIO
import os

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ecole_moderne.pdf_utils import draw_logo_watermark

from .models import EcheancierPaiement, Paiement


MOIS_FR = (
    "",
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
)


def _decimal(value):
    return Decimal(str(value or 0))


def _gnf(value):
    return f"{int(_decimal(value)):,}".replace(",", " ") + " GNF"


def construire_donnees_carnet(paiement):
    """Retourne l'historique et le solde progressif du carnet.

    Le carnet est strictement limité à l'année scolaire du paiement de départ.
    Les remises validées réduisent le reste au même titre que sur l'échéancier,
    sans être confondues avec l'argent réellement encaissé.
    """
    paiements = list(
        Paiement.objects.filter(
            eleve=paiement.eleve,
            annee_scolaire=paiement.annee_scolaire,
            statut="VALIDE",
        )
        .select_related(
            "eleve",
            "eleve__classe",
            "eleve__classe__ecole",
            "type_paiement",
            "mode_paiement",
        )
        .prefetch_related("remises")
        .order_by("date_paiement", "date_creation", "pk")
    )

    echeancier = EcheancierPaiement.objects.filter(
        eleve=paiement.eleve,
        annee_scolaire=paiement.annee_scolaire,
    ).first()

    total_encaisse = sum((_decimal(item.montant) for item in paiements), Decimal("0"))
    total_remises = sum(
        (
            sum(
                (_decimal(remise.montant_remise) for remise in item.remises.all()),
                Decimal("0"),
            )
            for item in paiements
        ),
        Decimal("0"),
    )
    total_du = (
        _decimal(echeancier.total_du)
        if echeancier is not None
        else total_encaisse + total_remises
    )

    couverture_cumulee = Decimal("0")
    lignes = []
    for item in paiements:
        remise = sum(
            (_decimal(ligne.montant_remise) for ligne in item.remises.all()),
            Decimal("0"),
        )
        couverture_cumulee += _decimal(item.montant) + remise
        lignes.append(
            {
                "mois": f"{MOIS_FR[item.date_paiement.month]} {item.date_paiement.year}",
                "date": item.date_paiement,
                "montant": _decimal(item.montant),
                "remise": remise,
                "reste": max(Decimal("0"), total_du - couverture_cumulee),
                "numero_recu": item.numero_recu,
            }
        )

    return {
        "paiement": paiement,
        "eleve": paiement.eleve,
        "ecole": getattr(getattr(paiement.eleve, "classe", None), "ecole", None),
        "echeancier": echeancier,
        "annee_scolaire": paiement.annee_scolaire,
        "lignes": lignes,
        "total_du": total_du,
        "total_encaisse": total_encaisse,
        "total_remises": total_remises,
        "reste": max(Decimal("0"), total_du - total_encaisse - total_remises),
    }


def _logo_ecole(ecole):
    try:
        path = getattr(getattr(ecole, "logo", None), "path", None)
        return path if path and os.path.exists(path) else None
    except Exception:
        return None


def generer_carnet_paiement_pdf(paiement):
    """Génère un carnet de paiement PDF prêt à être imprimé."""
    donnees = construire_donnees_carnet(paiement)
    ecole = donnees["ecole"]
    eleve = donnees["eleve"]
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.5 * cm,
        title=f"Carnet de paiement - {eleve.nom_complet}",
        author=getattr(ecole, "nom", "MySchoolGN") or "MySchoolGN",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CarnetTitre",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=colors.HexColor("#123B5D"),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CarnetSousTitre",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#52606D"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CarnetInfo",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#243B53"),
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CarnetCell",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=10,
            alignment=TA_CENTER,
        )
    )

    elements = []
    logo_path = _logo_ecole(ecole)
    school_name = getattr(ecole, "nom", "Établissement scolaire") or "Établissement scolaire"
    school_details = [school_name]
    for label, value in (
        ("Adresse", getattr(ecole, "adresse", "") if ecole else ""),
        ("Téléphone", getattr(ecole, "telephone", "") if ecole else ""),
        ("Email", getattr(ecole, "email", "") if ecole else ""),
    ):
        if value:
            school_details.append(f"{label} : {value}")

    if logo_path:
        logo = Image(logo_path, width=1.8 * cm, height=1.8 * cm)
        header = Table(
            [
                [
                    logo,
                    Paragraph(
                        "<b>" + "</b><br/>".join(school_details[:1]) + "</b><br/>"
                        + "<br/>".join(school_details[1:]),
                        styles["CarnetInfo"],
                    ),
                    Paragraph("CARNET DE<br/>PAIEMENT", styles["CarnetTitre"]),
                ]
            ],
            colWidths=[2.2 * cm, 8.1 * cm, 7.1 * cm],
        )
    else:
        header = Table(
            [
                [
                    Paragraph("<b>" + school_name + "</b><br/>" + "<br/>".join(school_details[1:]), styles["CarnetInfo"]),
                    Paragraph("CARNET DE<br/>PAIEMENT", styles["CarnetTitre"]),
                ]
            ],
            colWidths=[10.3 * cm, 7.1 * cm],
        )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#123B5D")),
                ("LINEBELOW", (0, 0), (-1, -1), 3, colors.HexColor("#D4A72C")),
                ("BACKGROUND", (-1, 0), (-1, 0), colors.HexColor("#F0F4F8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.extend([header, Spacer(1, 0.35 * cm)])

    classe = getattr(eleve, "classe", None)
    info_data = [
        [
            Paragraph(f"<b>Élève :</b> {eleve.nom_complet}", styles["CarnetInfo"]),
            Paragraph(f"<b>Matricule :</b> {getattr(eleve, 'matricule', '') or '—'}", styles["CarnetInfo"]),
        ],
        [
            Paragraph(f"<b>Classe :</b> {getattr(classe, 'nom', classe) or '—'}", styles["CarnetInfo"]),
            Paragraph(f"<b>Année scolaire :</b> {donnees['annee_scolaire']}", styles["CarnetInfo"]),
        ],
    ]
    info_table = Table(info_data, colWidths=[9.2 * cm, 8.2 * cm])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#BCCCDC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2EC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.extend([info_table, Spacer(1, 0.35 * cm)])

    summary = Table(
        [
            [
                Paragraph(f"<b>Montant annuel</b><br/>{_gnf(donnees['total_du'])}", styles["CarnetCell"]),
                Paragraph(f"<b>Total versé</b><br/>{_gnf(donnees['total_encaisse'])}", styles["CarnetCell"]),
                Paragraph(f"<b>Remises</b><br/>{_gnf(donnees['total_remises'])}", styles["CarnetCell"]),
                Paragraph(f"<b>Reste à payer</b><br/>{_gnf(donnees['reste'])}", styles["CarnetCell"]),
            ]
        ],
        colWidths=[4.35 * cm] * 4,
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF2F8")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#123B5D")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9FB3C8")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elements.extend([summary, Spacer(1, 0.45 * cm)])

    table_data = [
        [
            Paragraph("<b>Mois</b>", styles["CarnetCell"]),
            Paragraph("<b>Date</b>", styles["CarnetCell"]),
            Paragraph("<b>Montant</b>", styles["CarnetCell"]),
            Paragraph("<b>Reste à payer</b>", styles["CarnetCell"]),
            Paragraph("<b>Signature comptable</b>", styles["CarnetCell"]),
        ]
    ]
    for ligne in donnees["lignes"]:
        table_data.append(
            [
                Paragraph(ligne["mois"], styles["CarnetCell"]),
                Paragraph(ligne["date"].strftime("%d/%m/%Y"), styles["CarnetCell"]),
                Paragraph(_gnf(ligne["montant"]), styles["CarnetCell"]),
                Paragraph(_gnf(ligne["reste"]), styles["CarnetCell"]),
                Paragraph("<br/>________________", styles["CarnetCell"]),
            ]
        )

    payment_table = Table(
        table_data,
        colWidths=[3.1 * cm, 2.5 * cm, 3.4 * cm, 3.8 * cm, 4.6 * cm],
        repeatRows=1,
        rowHeights=[0.75 * cm] + [1.05 * cm] * (len(table_data) - 1),
    )
    payment_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B5D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#123B5D")),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#9FB3C8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.extend([payment_table, Spacer(1, 0.35 * cm)])
    elements.append(
        Paragraph(
            "Ce carnet récapitule uniquement les paiements validés. Le reste à payer tient compte des remises enregistrées. "
            "Chaque ligne doit être visée par le service comptable.",
            styles["CarnetSousTitre"],
        )
    )

    def _page(canvas, document):
        canvas.saveState()
        try:
            draw_logo_watermark(canvas, A4[0], A4[1], ecole=ecole)
        except Exception:
            pass
        canvas.setStrokeColor(colors.HexColor("#BCCCDC"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 0.85 * cm, A4[0] - doc.rightMargin, 0.85 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#52606D"))
        canvas.drawString(doc.leftMargin, 0.55 * cm, f"Carnet de paiement - {donnees['annee_scolaire']}")
        canvas.drawRightString(
            A4[0] - doc.rightMargin,
            0.55 * cm,
            f"Page {document.page} - Généré le {timezone.localtime().strftime('%d/%m/%Y %H:%M')}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=_page, onLaterPages=_page)
    return buffer.getvalue()
