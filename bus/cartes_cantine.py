"""Cartes d'abonnement cantine (format PVC CR80, 8 par feuille A4)."""

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from eleves.cartes_layout import (
    CARTE_HAUTEUR,
    CARTE_LARGEUR,
    dessiner_carte_eleve,
    dessiner_planche_cartes,
    enregistrer_polices,
)

ACCENT_CANTINE = '#b45309'
LIGHT_CANTINE = '#fef3c7'


def _lignes_carte(abonnement):
    eleve = abonnement.eleve
    validite = '-'
    if abonnement.date_debut and abonnement.date_expiration:
        validite = f"{abonnement.date_debut.strftime('%d/%m')} - {abonnement.date_expiration.strftime('%d/%m/%Y')}"

    regime = abonnement.regime_alimentaire or abonnement.allergies or 'Aucun'

    return [
        ('Matricule', getattr(eleve, 'matricule', None)),
        ('Classe', getattr(getattr(eleve, 'classe', None), 'nom', None)),
        ('Repas', abonnement.get_type_repas_display()),
        ('Validite', validite),
        ('Regime', regime),
    ]


def dessiner_carte_cantine(c, abonnement, x, y, width, height, main_font, main_font_bold):
    dessiner_carte_eleve(
        c, abonnement.eleve, x, y, width, height, main_font, main_font_bold,
        'CARTE CANTINE', ACCENT_CANTINE, LIGHT_CANTINE,
        _lignes_carte(abonnement), 'CANTINE',
    )


def generer_carte_cantine_pdf(abonnement, response):
    """Une seule carte, sur une page a la taille exacte de la carte."""
    main_font, main_font_bold = enregistrer_polices()
    c = canvas.Canvas(response, pagesize=(CARTE_LARGEUR, CARTE_HAUTEUR))
    dessiner_carte_cantine(c, abonnement, 0, 0, CARTE_LARGEUR, CARTE_HAUTEUR, main_font, main_font_bold)
    c.showPage()
    c.save()
    return response


def generer_planche_cartes_cantine_pdf(abonnements, response):
    """Planche A4 : 8 cartes cantine par feuille."""
    main_font, main_font_bold = enregistrer_polices()
    c = canvas.Canvas(response, pagesize=A4)

    def _dessiner(canvas_pdf, abonnement, x, y, width, height):
        dessiner_carte_cantine(canvas_pdf, abonnement, x, y, width, height, main_font, main_font_bold)

    dessiner_planche_cartes(c, abonnements, _dessiner)

    c.showPage()
    c.save()
    return response
