"""Documents de paie reprenant le classeur Excel mensuel des salaires.

- État de salaire détaillé par section (Direction, Primaire, Secondaire) ;
- Masse salariale ;
- État des acomptes (bons) ;
- Fiche d'émargement des salaires (« Acquis ») ;
- Bulletins de paie individuels avec rubriques et montants en lettres.
"""

import os
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape

from ecole_moderne.branding import get_reportlab_palette
from ecole_moderne.security_decorators import require_school_object
from utilisateurs.utils import filter_by_user_school, user_school

from .forms import CalendrierPeriodeForm, ParametrePaieForm
from .models import CategoriePaie, EtatSalaire, ParametrePaie, PeriodeSalaire
from .montant_lettres import montant_en_lettres
from .services import acomptes_periode, etats_par_categorie, masse_salariale

MOIS = [
    '', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
    'août', 'septembre', 'octobre', 'novembre', 'décembre',
]


def gnf(montant):
    return f"{Decimal(montant or 0):,.0f}".replace(',', ' ')


def _periode_libelle(periode):
    return f"{MOIS[periode.mois].capitalize()} {periode.annee}"


def _annee_scolaire(periode):
    debut = periode.annee if periode.mois >= 9 else periode.annee - 1
    return f"{debut} - {debut + 1}"


def _etats_periode(periode):
    return (
        periode.etats_salaire
        .select_related('enseignant', 'enseignant__classe_principale')
        .prefetch_related('enseignant__affectations__classe')
        .order_by('enseignant__nom', 'enseignant__prenoms')
    )


def _fonction(enseignant):
    if enseignant.type_enseignant == 'ADMINISTRATEUR':
        return enseignant.fonction or 'Administration'
    if enseignant.utilise_classe_principale:
        classe = enseignant.classe_principale.nom if enseignant.classe_principale_id else ''
        return f"Chargé de cours ({classe})" if classe else enseignant.get_type_enseignant_display()
    matieres = sorted({
        affectation.matiere
        for affectation in enseignant.affectations.all()
        if affectation.actif and affectation.matiere
    })
    return ' / '.join(matieres) or 'Professeur'


class _Styles:
    def __init__(self, palette):
        base = getSampleStyleSheet()
        self.titre = ParagraphStyle(
            'PaieTitre', parent=base['Title'], fontSize=13, leading=16,
            textColor=palette['primary'], spaceAfter=2,
        )
        self.sous_titre = ParagraphStyle(
            'PaieSousTitre', parent=base['Normal'], fontSize=9.5, leading=12,
            alignment=1, fontName='Helvetica-Bold',
        )
        self.texte = ParagraphStyle(
            'PaieTexte', parent=base['Normal'], fontSize=8.5, leading=11,
        )
        self.cellule = ParagraphStyle(
            'PaieCellule', parent=base['Normal'], fontSize=7, leading=8.4,
        )
        self.cellule_centre = ParagraphStyle(
            'PaieCelluleCentre', parent=self.cellule, alignment=1,
        )
        self.entete = ParagraphStyle(
            'PaieEntete', parent=self.cellule_centre, fontName='Helvetica-Bold',
            textColor=palette['header_text'],
        )


def _p(texte, style):
    return Paragraph(escape(str(texte)), style)


def _logo_ecole(ecole):
    try:
        if ecole is not None and ecole.logo and os.path.exists(ecole.logo.path):
            return ecole.logo.path
    except Exception:
        return None
    return None


def _entete_page(ecole, periode):
    """En-tête institutionnel identique sur toutes les pages des documents."""

    def dessiner(canvas, doc):
        largeur, hauteur = doc.pagesize
        canvas.saveState()
        logo = _logo_ecole(ecole)
        x_texte = doc.leftMargin
        if logo:
            try:
                canvas.drawImage(
                    logo, doc.leftMargin, hauteur - 2.3 * cm, width=1.6 * cm,
                    height=1.6 * cm, preserveAspectRatio=True, mask='auto',
                )
                x_texte += 1.9 * cm
            except Exception:
                pass
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(x_texte, hauteur - 1.1 * cm, getattr(ecole, 'nom', ''))
        canvas.setFont('Helvetica', 7.5)
        ligne = hauteur - 1.5 * cm
        for info in (
            getattr(ecole, 'adresse', ''),
            f"Tél : {ecole.telephone}" if getattr(ecole, 'telephone', '') else '',
        ):
            if info:
                canvas.drawString(x_texte, ligne, str(info)[:90])
                ligne -= 0.35 * cm

        droite = largeur - doc.rightMargin
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawRightString(droite, hauteur - 1.1 * cm, 'REPUBLIQUE DE GUINEE')
        canvas.setFont('Helvetica-Oblique', 7.5)
        canvas.drawRightString(droite, hauteur - 1.5 * cm, 'Travail - Justice - Solidarité')
        canvas.setFont('Helvetica', 7.5)
        canvas.drawRightString(
            droite, hauteur - 1.85 * cm, f"Année scolaire : {_annee_scolaire(periode)}"
        )
        canvas.setFont('Helvetica', 7)
        canvas.drawRightString(droite, 0.8 * cm, f"Page {doc.page}")
        canvas.restoreState()

    return dessiner


def _reponse_pdf(nom_fichier, inline=False):
    response = HttpResponse(content_type='application/pdf')
    disposition = 'inline' if inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{nom_fichier}"'
    return response


def _document(response, paysage=True):
    return SimpleDocTemplate(
        response,
        pagesize=landscape(A4) if paysage else A4,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=2.8 * cm, bottomMargin=1.4 * cm,
    )


def _style_tableau(palette, lignes_total=1):
    commandes = [
        ('BACKGROUND', (0, 0), (-1, 0), palette['header']),
        ('GRID', (0, 0), (-1, -1), 0.3, palette['border']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]
    if lignes_total:
        commandes += [
            ('BACKGROUND', (0, -lignes_total), (-1, -1), palette['table']),
            ('FONTNAME', (0, -lignes_total), (-1, -1), 'Helvetica-Bold'),
        ]
    return TableStyle(commandes)


def _arrete(texte_debut, montant, styles):
    return Paragraph(
        f"{escape(texte_debut)} <b>{escape(montant_en_lettres(montant))} "
        f"({gnf(montant)} GNF)</b>.",
        styles.texte,
    )


def _signatures(parametre, styles, largeur):
    lieu = parametre.lieu_signature or ''
    date_txt = timezone.localdate().strftime('%d/%m/%Y')
    elements = [
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"{escape(lieu + ', ' if lieu else '')}le {date_txt}",
            ParagraphStyle('PaieDate', parent=styles.texte, alignment=2),
        ),
        Spacer(1, 0.3 * cm),
    ]
    signataires = parametre.signataires
    if not signataires:
        return elements
    titres = [Paragraph(f"<b>{escape(t)}</b>", styles.cellule_centre) for t, _ in signataires]
    noms = [Paragraph(escape(n or ''), styles.cellule_centre) for _, n in signataires]
    table = Table(
        [titres, [''] * len(signataires), noms],
        colWidths=[largeur / len(signataires)] * len(signataires),
        rowHeights=[0.5 * cm, 1.6 * cm, 0.5 * cm],
    )
    table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(KeepTogether([table]))
    return elements


def _contexte(request, periode_id):
    periode = get_object_or_404(PeriodeSalaire.objects.select_related('ecole'), pk=periode_id)
    parametre = ParametrePaie.pour_ecole(periode.ecole)
    palette = get_reportlab_palette(periode.ecole)
    return periode, parametre, palette, _Styles(palette)


# ---------------------------------------------------------------------------
# Paramètres et page de synthèse
# ---------------------------------------------------------------------------

@login_required
def parametres_paie(request):
    ecole = user_school(request.user)
    if ecole is None:
        messages.error(request, "Aucune école n'est associée à votre compte.")
        return redirect('salaires:tableau_bord')
    parametre = ParametrePaie.pour_ecole(ecole)
    if request.method == 'POST':
        form = ParametrePaieForm(request.POST, instance=parametre)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Barèmes de paie enregistrés. Ils s'appliquent aux prochains calculs de salaire.",
            )
            return redirect('salaires:parametres_paie')
    else:
        form = ParametrePaieForm(instance=parametre)
    return render(request, 'salaires/parametres_paie.html', {
        'form': form,
        'parametre': parametre,
        'ecole': ecole,
    })


@login_required
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def calendrier_periode(request, periode_id):
    """Nombre de lundis ... samedis travaillés (secondaire, emploi du temps)."""
    periode = get_object_or_404(PeriodeSalaire.objects.select_related('ecole'), pk=periode_id)
    if periode.cloturee:
        messages.error(request, "Une période clôturée ne peut plus être modifiée.")
        return redirect(f"{reverse('salaires:documents_paie')}?periode={periode.pk}")
    if request.method == 'POST':
        form = CalendrierPeriodeForm(request.POST, instance=periode)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Jours de cours enregistrés. Recalculez les salaires du secondaire "
                "pour appliquer ce calendrier.",
            )
            return redirect(f"{reverse('salaires:etats_salaire')}?periode={periode.pk}")
    else:
        form = CalendrierPeriodeForm(instance=periode)
    return render(request, 'salaires/calendrier_periode.html', {
        'form': form,
        'periode': periode,
        'total_jours': sum(periode.occurrences_jours_semaine()),
    })


@login_required
def documents_paie(request):
    """Masse salariale d'une période et accès aux documents imprimables."""
    periodes = filter_by_user_school(
        PeriodeSalaire.objects.select_related('ecole'), request.user
    ).order_by('-annee', '-mois')
    periode = None
    periode_id = request.GET.get('periode')
    if periode_id and str(periode_id).isdigit():
        periode = periodes.filter(pk=periode_id).first()
    if periode is None:
        periode = periodes.first()

    sections, totaux, acomptes, total_acomptes = [], {}, [], Decimal('0')
    if periode is not None:
        sections, totaux = masse_salariale(periode)
        acomptes, total_acomptes = acomptes_periode(periode)
    return render(request, 'salaires/documents_paie.html', {
        'periodes': periodes,
        'periode': periode,
        'sections': sections,
        'totaux': totaux,
        'total_en_lettres': montant_en_lettres(totaux.get('total_net', 0)) if periode else '',
        'acomptes': acomptes,
        'total_acomptes': total_acomptes,
    })


# ---------------------------------------------------------------------------
# État de salaire détaillé
# ---------------------------------------------------------------------------

def _tableau_section_fixe(section, parametre, styles, palette, largeur):
    entetes = [
        'N°', 'Prénoms et Nom', 'Matri.', 'Embauche', 'Ancien.', 'Charge ou Fonction',
        'Jours', 'Salaire de base', 'Fonct.', 'Craie', 'Ancien.', 'Éloign.',
        'Perform.', 'Except.', 'Salaire brut', 'Acompte', 'Retenues', 'Net à payer',
    ]
    data = [[_p(t, styles.entete) for t in entetes]]
    for index, etat in enumerate(section['etats'], start=1):
        e = etat.enseignant
        data.append([
            index,
            _p(f"{e.prenoms} {e.nom}", styles.cellule),
            _p(e.matricule, styles.cellule_centre),
            e.date_embauche.year if e.date_embauche else '',
            e.anciennete_annees(etat.periode.annee),
            _p(_fonction(e), styles.cellule),
            etat.jours_travailles(parametre.jours_ouvrables),
            gnf(etat.salaire_base),
            gnf(etat.prime_fonction), gnf(etat.prime_craie), gnf(etat.prime_anciennete),
            gnf(etat.prime_eloignement), gnf(etat.prime_performance),
            gnf(etat.prime_exceptionnelle),
            gnf(etat.salaire_brut), gnf(etat.avances_deduites), gnf(etat.retenues_hors_avances),
            gnf(etat.salaire_net),
        ])
    r = section['totaux_rubriques']
    data.append([
        '', 'TOTAL', '', '', '', '', '', gnf(section['total_base']),
        gnf(r['prime_fonction']), gnf(r['prime_craie']), gnf(r['prime_anciennete']),
        gnf(r['prime_eloignement']), gnf(r['prime_performance']),
        gnf(r['prime_exceptionnelle']), gnf(section['total_brut']),
        gnf(section['total_avances']), gnf(section['total_deductions']),
        gnf(section['total_net']),
    ])
    largeurs = [0.7, 3.4, 1.4, 1.55, 1.35, 2.8, 0.9, 1.7, 1.35, 1.3, 1.3, 1.3, 1.35, 1.35, 1.8, 1.5, 1.4, 1.8]
    facteur = largeur / (sum(largeurs) * cm)
    table = Table(data, repeatRows=1, colWidths=[w * cm * facteur for w in largeurs])
    style = _style_tableau(palette)
    style.add('ALIGN', (6, 1), (-1, -1), 'RIGHT')
    style.add('ALIGN', (0, 1), (0, -1), 'CENTER')
    style.add('ALIGN', (3, 1), (4, -1), 'CENTER')
    table.setStyle(style)
    return table


def _tableau_section_horaire(section, parametre, styles, palette, largeur):
    entetes = [
        'N°', 'Prénoms et Nom', 'Matri.', 'Matière(s)', 'Jours', 'Heures prestées',
        'Heures révision', 'Taux', 'Valeur des heures', 'Primes', 'Salaire brut',
        'Acompte', 'Retenues', 'Net à payer',
    ]
    data = [[_p(t, styles.entete) for t in entetes]]
    total_heures = Decimal('0')
    total_revision = Decimal('0')
    for index, etat in enumerate(section['etats'], start=1):
        e = etat.enseignant
        total_heures += etat.total_heures or Decimal('0')
        total_revision += etat.heures_revision or Decimal('0')
        data.append([
            index,
            _p(f"{e.prenoms} {e.nom}", styles.cellule),
            _p(e.matricule, styles.cellule_centre),
            _p(_fonction(e), styles.cellule),
            etat.jours_travailles(parametre.jours_ouvrables),
            f"{etat.total_heures or 0:g}",
            f"{etat.heures_revision or 0:g}",
            gnf(etat.taux_horaire_applique),
            gnf(etat.salaire_base),
            gnf(etat.primes),
            gnf(etat.salaire_brut),
            gnf(etat.avances_deduites),
            gnf(etat.retenues_hors_avances),
            gnf(etat.salaire_net),
        ])
    data.append([
        '', 'TOTAL', '', '', '', f"{total_heures:g}", f"{total_revision:g}", '',
        gnf(section['total_base']), gnf(section['total_primes']),
        gnf(section['total_brut']), gnf(section['total_avances']),
        gnf(section['total_deductions']), gnf(section['total_net']),
    ])
    largeurs = [0.7, 4.2, 1.5, 3.2, 1.0, 1.5, 1.5, 1.5, 2.1, 1.9, 2.2, 1.9, 1.7, 2.2]
    facteur = largeur / (sum(largeurs) * cm)
    table = Table(data, repeatRows=1, colWidths=[w * cm * facteur for w in largeurs])
    style = _style_tableau(palette)
    style.add('ALIGN', (4, 1), (-1, -1), 'RIGHT')
    style.add('ALIGN', (0, 1), (0, -1), 'CENTER')
    table.setStyle(style)
    return table


@login_required
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def etat_salaire_detaille_pdf(request, periode_id):
    periode, parametre, palette, styles = _contexte(request, periode_id)
    sections = etats_par_categorie(_etats_periode(periode))
    categorie = request.GET.get('section')
    if categorie:
        sections = [s for s in sections if s['categorie'] == categorie]

    response = _reponse_pdf(f"etat_salaire_{periode.annee}_{periode.mois:02d}.pdf")
    doc = _document(response)
    largeur = doc.width
    elements = []
    if not sections:
        elements.append(Paragraph("Aucun état de salaire pour cette période.", styles.texte))
    for numero, section in enumerate(sections):
        if numero:
            elements.append(PageBreak())
        elements.append(Paragraph(
            f"ÉTAT DE SALAIRE À PAYER : PERSONNEL {section['libelle'].upper()}",
            styles.titre,
        ))
        elements.append(Paragraph(f"Mois de : {_periode_libelle(periode)}", styles.sous_titre))
        elements.append(Spacer(1, 0.35 * cm))
        if section['categorie'] == CategoriePaie.SECONDAIRE:
            elements.append(_tableau_section_horaire(section, parametre, styles, palette, largeur))
        else:
            elements.append(_tableau_section_fixe(section, parametre, styles, palette, largeur))
        elements.append(Spacer(1, 0.35 * cm))
        elements.append(_arrete(
            f"Arrêté le présent état de salaire du mois de {_periode_libelle(periode)} "
            "à la somme de :",
            section['total_net'],
            styles,
        ))
        elements.extend(_signatures(parametre, styles, largeur))

    entete = _entete_page(periode.ecole, periode)
    doc.build(elements, onFirstPage=entete, onLaterPages=entete)
    return response


# ---------------------------------------------------------------------------
# Masse salariale
# ---------------------------------------------------------------------------

@login_required
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def masse_salariale_pdf(request, periode_id):
    periode, parametre, palette, styles = _contexte(request, periode_id)
    sections, totaux = masse_salariale(periode)

    response = _reponse_pdf(f"masse_salariale_{periode.annee}_{periode.mois:02d}.pdf")
    doc = _document(response, paysage=False)
    elements = [
        Paragraph("MASSE SALARIALE", styles.titre),
        Paragraph(f"Mois de : {_periode_libelle(periode)}", styles.sous_titre),
        Spacer(1, 0.5 * cm),
    ]
    entetes = ['N°', 'Section', 'Effectif', 'Montant brut', 'Acompte', 'Retenues', 'Net à payer']
    data = [[_p(t, styles.entete) for t in entetes]]
    for index, section in enumerate(sections, start=1):
        data.append([
            index, section['libelle'], section['effectif'], gnf(section['total_brut']),
            gnf(section['total_avances']), gnf(section['total_deductions']),
            gnf(section['total_net']),
        ])
    data.append([
        '', 'TOTAL', totaux.get('effectif', 0), gnf(totaux.get('total_brut')),
        gnf(totaux.get('total_avances')), gnf(totaux.get('total_deductions')),
        gnf(totaux.get('total_net')),
    ])
    table = Table(data, colWidths=[1 * cm, 4 * cm, 1.8 * cm, 3 * cm, 2.6 * cm, 2.4 * cm, 3 * cm])
    style = _style_tableau(palette)
    style.add('ALIGN', (2, 1), (-1, -1), 'RIGHT')
    style.add('FONTSIZE', (0, 0), (-1, -1), 9)
    style.add('TOPPADDING', (0, 0), (-1, -1), 5)
    style.add('BOTTOMPADDING', (0, 0), (-1, -1), 5)
    table.setStyle(style)
    elements += [table, Spacer(1, 0.5 * cm)]
    elements.append(_arrete(
        f"Arrêtée la présente masse salariale du mois de {_periode_libelle(periode)} "
        "à la somme de :",
        totaux.get('total_net', 0),
        styles,
    ))
    elements.extend(_signatures(parametre, styles, doc.width))
    entete = _entete_page(periode.ecole, periode)
    doc.build(elements, onFirstPage=entete, onLaterPages=entete)
    return response


# ---------------------------------------------------------------------------
# Acomptes (bons)
# ---------------------------------------------------------------------------

@login_required
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def acomptes_pdf(request, periode_id):
    periode, parametre, palette, styles = _contexte(request, periode_id)
    lignes, total = acomptes_periode(periode)

    response = _reponse_pdf(f"acomptes_{periode.annee}_{periode.mois:02d}.pdf")
    doc = _document(response)
    elements = [
        Paragraph("ACOMPTES DU PERSONNEL", styles.titre),
        Paragraph(f"Mois de : {_periode_libelle(periode)}", styles.sous_titre),
        Spacer(1, 0.4 * cm),
    ]
    entetes = [
        'N°', 'Prénoms et Nom', 'Matri.', 'Site', 'Charge ou Fonction',
        'Bon 1', 'Bon 2', 'Bon 3', 'Bon 4', 'Bon 5', 'Acompte payé', 'Observation',
    ]
    data = [[_p(t, styles.entete) for t in entetes]]
    for index, ligne in enumerate(lignes, start=1):
        e = ligne['enseignant']
        data.append([
            index,
            _p(f"{e.prenoms} {e.nom}", styles.cellule),
            _p(e.matricule, styles.cellule_centre),
            ligne['section'],
            _p(_fonction(e), styles.cellule),
            *[gnf(bon) if bon is not None else '' for bon in ligne['bons']],
            gnf(ligne['total']),
            _p(', '.join(ligne['references']), styles.cellule),
        ])
    data.append(['', 'TOTAL', '', '', '', '', '', '', '', '', gnf(total), ''])
    largeurs = [0.8, 4.4, 1.6, 2.0, 3.6, 1.8, 1.8, 1.8, 1.8, 1.8, 2.3, 3.4]
    facteur = doc.width / (sum(largeurs) * cm)
    table = Table(data, repeatRows=1, colWidths=[w * cm * facteur for w in largeurs])
    style = _style_tableau(palette)
    style.add('ALIGN', (5, 1), (10, -1), 'RIGHT')
    table.setStyle(style)
    elements += [table, Spacer(1, 0.4 * cm)]
    elements.append(_arrete("Arrêté le présent état des acomptes à la somme de :", total, styles))
    elements.extend(_signatures(parametre, styles, doc.width))
    entete = _entete_page(periode.ecole, periode)
    doc.build(elements, onFirstPage=entete, onLaterPages=entete)
    return response


# ---------------------------------------------------------------------------
# Fiche d'émargement (Acquis)
# ---------------------------------------------------------------------------

@login_required
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def emargement_pdf(request, periode_id):
    periode, parametre, palette, styles = _contexte(request, periode_id)
    sections = etats_par_categorie(_etats_periode(periode))
    categorie = request.GET.get('section')
    if categorie:
        sections = [s for s in sections if s['categorie'] == categorie]

    response = _reponse_pdf(f"emargement_salaires_{periode.annee}_{periode.mois:02d}.pdf")
    doc = _document(response, paysage=False)
    elements = [
        Paragraph("FICHE D'ÉMARGEMENT DES SALAIRES POUR ACQUIS", styles.titre),
        Paragraph(f"Mois de : {_periode_libelle(periode)}", styles.sous_titre),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"1- En émargeant la présente fiche, vous attestez avoir perçu votre salaire "
            f"du mois que vous doit {escape(periode.ecole.nom)}.",
            styles.texte,
        ),
        Paragraph(
            "2- Le bulletin de paie fournit tous les détails relatifs à votre salaire ; "
            "ce bulletin est personnel.",
            styles.texte,
        ),
        Spacer(1, 0.4 * cm),
    ]
    entetes = ['N°', 'Prénoms et Nom', 'Matri.', 'Site', 'Charge ou Fonction', 'Net perçu', 'Émargement', 'Observation']
    data = [[_p(t, styles.entete) for t in entetes]]
    index = 0
    for section in sections:
        for etat in section['etats']:
            index += 1
            e = etat.enseignant
            data.append([
                index,
                _p(f"{e.prenoms} {e.nom}", styles.cellule),
                _p(e.matricule, styles.cellule_centre),
                section['libelle'],
                _p(_fonction(e), styles.cellule),
                gnf(etat.salaire_net),
                '', '',
            ])
    table = Table(
        data, repeatRows=1,
        colWidths=[0.8 * cm, 4.2 * cm, 1.6 * cm, 1.9 * cm, 3.4 * cm, 2.0 * cm, 2.6 * cm, 2.1 * cm],
    )
    style = _style_tableau(palette, lignes_total=0)
    style.add('ALIGN', (5, 1), (5, -1), 'RIGHT')
    style.add('TOPPADDING', (0, 1), (-1, -1), 8)
    style.add('BOTTOMPADDING', (0, 1), (-1, -1), 8)
    table.setStyle(style)
    elements.append(table)
    elements.extend(_signatures(parametre, styles, doc.width))
    entete = _entete_page(periode.ecole, periode)
    doc.build(elements, onFirstPage=entete, onLaterPages=entete)
    return response


# ---------------------------------------------------------------------------
# Bulletins de paie
# ---------------------------------------------------------------------------

def _bulletin(etat, parametre, styles, palette, largeur):
    e = etat.enseignant
    periode = etat.periode
    elements = [
        Paragraph("BULLETIN DE PAIE", styles.titre),
        Paragraph(f"Mois de : {_periode_libelle(periode)}", styles.sous_titre),
        Spacer(1, 0.4 * cm),
    ]
    infos = [
        ['Prénoms et nom :', f"{e.prenoms} {e.nom}", 'Matricule :', e.matricule or '-'],
        ["Date d'embauche :", e.date_embauche.strftime('%d/%m/%Y') if e.date_embauche else '-',
         'Ancienneté :', f"{e.anciennete_annees(periode.annee)} an(s)"],
        ['Fonction :', _fonction(e), 'Jours travaillés :', etat.jours_travailles(parametre.jours_ouvrables)],
        ['Site :', e.categorie_paie.label, 'Brut / Net :', f"{gnf(etat.salaire_brut)} / {gnf(etat.salaire_net)} GNF"],
    ]
    table_infos = Table(
        [[_p(c, styles.texte) if isinstance(c, str) else c for c in ligne] for ligne in infos],
        colWidths=[largeur * 0.18, largeur * 0.37, largeur * 0.17, largeur * 0.28],
    )
    table_infos.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOX', (0, 0), (-1, -1), 0.4, palette['border']),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements += [table_infos, Spacer(1, 0.4 * cm)]

    entetes = ['N°', 'Rubriques', 'Base', 'Primes', 'Acompte / retenue', 'Solde']
    data = [[_p(t, styles.entete) for t in entetes]]
    solde = etat.salaire_base or Decimal('0')
    libelle_base = 'Salaire de base'
    if e.est_taux_horaire:
        libelle_base = (
            f"Salaire de base ({etat.total_heures or 0:g} h × {gnf(etat.taux_horaire_applique)})"
        )
    data.append([1, _p(libelle_base, styles.cellule), gnf(etat.salaire_base), '', '', gnf(solde)])
    numero = 1
    for libelle, montant in etat.rubriques_primes:
        numero += 1
        solde += montant
        data.append([numero, _p(libelle, styles.cellule), '', gnf(montant), '', gnf(solde)])
    numero += 1
    solde -= etat.avances_deduites or Decimal('0')
    data.append([
        numero, _p('Avance sur salaire (acompte)', styles.cellule), '', '',
        gnf(etat.avances_deduites), gnf(solde),
    ])
    if etat.imputation_sanctions:
        numero += 1
        solde -= etat.imputation_sanctions
        data.append([
            numero,
            _p(f"Imputation liée aux sanctions ({etat.jours_chomes} jour(s) chômé(s))", styles.cellule),
            '', '', gnf(etat.imputation_sanctions), gnf(solde),
        ])
    numero += 1
    solde -= etat.deductions or Decimal('0')
    data.append([
        numero, _p('Retenues et autres prélèvements', styles.cellule), '', '',
        gnf(etat.deductions), gnf(solde),
    ])
    data.append([
        '', 'TOTAL', gnf(etat.salaire_base), gnf(etat.primes),
        gnf(etat.retenues_totales), gnf(etat.salaire_net),
    ])
    table = Table(
        data,
        colWidths=[largeur * 0.06, largeur * 0.40, largeur * 0.13, largeur * 0.13, largeur * 0.14, largeur * 0.14],
    )
    style = _style_tableau(palette)
    style.add('ALIGN', (2, 1), (-1, -1), 'RIGHT')
    style.add('FONTSIZE', (0, 0), (-1, -1), 8.5)
    style.add('TOPPADDING', (0, 0), (-1, -1), 4)
    style.add('BOTTOMPADDING', (0, 0), (-1, -1), 4)
    table.setStyle(style)
    elements += [table, Spacer(1, 0.4 * cm)]

    elements.append(Paragraph(
        f"<b>Salaire brut :</b> {gnf(etat.salaire_brut)} GNF — "
        f"{escape(montant_en_lettres(etat.salaire_brut))}",
        styles.texte,
    ))
    elements.append(Paragraph(
        f"<b>Net à payer :</b> {gnf(etat.salaire_net)} GNF — "
        f"{escape(montant_en_lettres(etat.salaire_net))}",
        styles.texte,
    ))
    if etat.observations:
        elements.append(Paragraph(f"<b>Observations :</b> {escape(etat.observations)}", styles.texte))
    statut = 'Payé' if etat.paye else ('Validé' if etat.valide else 'Brouillon (non validé)')
    elements.append(Paragraph(f"<b>Statut :</b> {statut}", styles.texte))

    signatures = Table(
        [[
            Paragraph("<b>L'intéressé(e)</b>", styles.cellule_centre),
            Paragraph(f"<b>{escape(parametre.signataire_3_titre or 'La Gestion')}</b>", styles.cellule_centre),
        ], ['', ''], [
            Paragraph(escape(f"{e.prenoms} {e.nom}"), styles.cellule_centre),
            Paragraph(escape(parametre.signataire_3_nom or ''), styles.cellule_centre),
        ]],
        colWidths=[largeur / 2, largeur / 2],
        rowHeights=[0.6 * cm, 1.8 * cm, 0.5 * cm],
    )
    elements += [Spacer(1, 0.6 * cm), KeepTogether([signatures])]
    return elements


def _bulletins_pdf(etats, periode, nom_fichier):
    parametre = ParametrePaie.pour_ecole(periode.ecole)
    palette = get_reportlab_palette(periode.ecole)
    styles = _Styles(palette)
    response = _reponse_pdf(nom_fichier)
    doc = _document(response, paysage=False)
    elements = []
    for index, etat in enumerate(etats):
        if index:
            elements.append(PageBreak())
        elements.extend(_bulletin(etat, parametre, styles, palette, doc.width))
    if not elements:
        elements.append(Paragraph("Aucun état de salaire pour cette période.", styles.texte))
    entete = _entete_page(periode.ecole, periode)
    doc.build(elements, onFirstPage=entete, onLaterPages=entete)
    return response


@login_required
@require_school_object(model=EtatSalaire, pk_kwarg='etat_id', field_path='periode__ecole')
def bulletin_paie_pdf(request, etat_id):
    etat = get_object_or_404(
        EtatSalaire.objects.select_related(
            'enseignant', 'enseignant__classe_principale', 'periode', 'periode__ecole'
        ),
        pk=etat_id,
    )
    return _bulletins_pdf(
        [etat],
        etat.periode,
        f"bulletin_paie_{etat.enseignant.nom}_{etat.periode.mois:02d}_{etat.periode.annee}.pdf",
    )


@login_required
@require_school_object(model=PeriodeSalaire, pk_kwarg='periode_id', field_path='ecole')
def bulletins_paie_periode_pdf(request, periode_id):
    periode = get_object_or_404(PeriodeSalaire.objects.select_related('ecole'), pk=periode_id)
    etats = []
    for section in etats_par_categorie(_etats_periode(periode)):
        etats.extend(section['etats'])
    return _bulletins_pdf(
        etats, periode, f"bulletins_paie_{periode.annee}_{periode.mois:02d}.pdf"
    )
