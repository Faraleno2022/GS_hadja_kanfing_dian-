"""Documents de paie au format du classeur de l'école.

Chaque fonction reproduit une feuille du classeur mensuel :

- ``etat_salaire_groupe_pdf``  : « ETAT DE SALAIRE A PAYER » par rubrique
  (Direction, Maternelle et primaire, Secondaire, Personnel d'appui) ;
- ``masse_salariale_pdf``      : « MASSE SALARIALE » (totaux par rubrique) ;
- ``acomptes_pdf``             : « ACOMPTE PERSONNEL » (bons 1 à 5) ;
- ``emargement_pdf``           : « FICHE D'EMARGEMENT DES SALAIRES POUR ACQUIS » ;
- ``bulletin_paie_pdf``        : « BULLETIN DE PAIE » individuel.
"""

import os
from calendar import monthrange
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

from .models import AvanceSalaire, EtatSalaire, GroupePaie
from .montant_lettres import formater_gnf, montant_en_lettres
from .services import charge_ou_fonction

MOIS = [
    '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet',
    'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]
ORDRE_GROUPES = [
    GroupePaie.DIRECTION, GroupePaie.PRIMAIRE, GroupePaie.SECONDAIRE,
    GroupePaie.APPUI,
]
ZERO = Decimal('0')

_styles = getSampleStyleSheet()
STYLE_CELLULE = ParagraphStyle(
    'cellule', parent=_styles['Normal'], fontSize=7.5, leading=9,
)
STYLE_ENTETE_CELLULE = ParagraphStyle(
    'entete_cellule', parent=STYLE_CELLULE, fontName='Helvetica-Bold',
    fontSize=7, leading=8.5, alignment=TA_CENTER,
)
STYLE_TITRE = ParagraphStyle(
    'titre_paie', parent=_styles['Title'], fontSize=14, spaceAfter=2,
)
STYLE_SOUS_TITRE = ParagraphStyle(
    'sous_titre_paie', parent=_styles['Normal'], fontSize=10,
    alignment=TA_CENTER, fontName='Helvetica-Bold',
)
STYLE_TEXTE = ParagraphStyle(
    'texte_paie', parent=_styles['Normal'], fontSize=9, leading=12,
)
STYLE_ENTETE = ParagraphStyle(
    'entete_paie', parent=_styles['Normal'], fontSize=9, leading=11,
)


# --------------------------------------------------------------------------
# Outils communs
# --------------------------------------------------------------------------

def libelle_mois(periode):
    return f"{MOIS[periode.mois]} {periode.annee}"


def nom_document(enseignant):
    """« Prénoms et Nom » comme sur le classeur."""
    return f"{enseignant.prenoms} {enseignant.nom}".strip()


def date_edition(periode):
    dernier_jour = monthrange(periode.annee, periode.mois)[1]
    date_txt = f"{dernier_jour} {MOIS[periode.mois].lower()} {periode.annee}"
    if periode.lieu_edition:
        return f"{periode.lieu_edition}, le {date_txt}."
    return f"Le {date_txt}."


def etats_de_la_periode(periode, groupe=None):
    etats = (
        EtatSalaire.objects.filter(periode=periode)
        .select_related('enseignant', 'periode', 'periode__ecole')
        .order_by('enseignant__nom', 'enseignant__prenoms')
    )
    if groupe:
        etats = [etat for etat in etats if etat.enseignant.groupe_paie == groupe]
    return list(etats)


def _p(texte, style=STYLE_CELLULE):
    # Les noms et observations sont des saisies : pas de balisage ReportLab.
    return Paragraph(escape(str(texte)), style)


def _m(montant):
    return formater_gnf(montant)


def _chemin_logo(ecole):
    try:
        chemin = getattr(getattr(ecole, 'logo', None), 'path', None)
        if chemin and os.path.exists(chemin):
            return chemin
    except (ValueError, OSError):
        pass
    return None


def entete_ecole(periode, largeur):
    """Bloc école à gauche, République de Guinée à droite."""
    ecole = periode.ecole
    telephones = ' / '.join(
        tel for tel in (
            getattr(ecole, 'telephone', ''),
            getattr(ecole, 'telephone2', ''),
            getattr(ecole, 'telephone3', ''),
        ) if tel
    )
    gauche = [f"<b>{escape(ecole.nom)}</b>"]
    if ecole.adresse:
        gauche.append(escape(str(ecole.adresse)).replace('\n', '<br/>'))
    if telephones:
        gauche.append(f"Tél : {escape(telephones)}")
    droite = [
        '<b>RÉPUBLIQUE DE GUINÉE</b>',
        'Travail - Justice - Solidarité',
        f"Année scolaire : {periode.annee_scolaire}",
    ]
    bloc_gauche = Paragraph('<br/>'.join(gauche), STYLE_ENTETE)
    bloc_droite = Paragraph(
        '<br/>'.join(droite),
        ParagraphStyle('droite', parent=STYLE_ENTETE, alignment=TA_CENTER),
    )
    logo = _chemin_logo(ecole)
    if logo:
        cellules = [[Image(logo, width=1.6 * cm, height=1.6 * cm), bloc_gauche, bloc_droite]]
        largeurs = [1.9 * cm, largeur * 0.55 - 1.9 * cm, largeur * 0.45]
    else:
        cellules = [[bloc_gauche, bloc_droite]]
        largeurs = [largeur * 0.55, largeur * 0.45]
    table = Table(cellules, colWidths=largeurs)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return table


def titre_document(titre, periode, sous_titre=None):
    elements = [
        Spacer(1, 0.3 * cm),
        Paragraph(titre, STYLE_TITRE),
    ]
    if sous_titre:
        elements.append(Paragraph(sous_titre, STYLE_SOUS_TITRE))
    elements.append(Paragraph(f"Mois de : {libelle_mois(periode)}", STYLE_SOUS_TITRE))
    elements.append(Spacer(1, 0.3 * cm))
    return elements


def avertissement_brouillon(etats):
    non_valides = sum(1 for etat in etats if not etat.valide)
    if not non_valides:
        return []
    return [
        Paragraph(
            f"<font color='#b45309'><b>Document provisoire :</b> {non_valides} "
            f"état(s) de salaire non encore validé(s).</font>",
            STYLE_TEXTE,
        ),
        Spacer(1, 0.2 * cm),
    ]


def arrete(libelle, montant):
    return Paragraph(
        f"{libelle} à la somme de : <b>{montant_en_lettres(montant)} "
        f"({_m(montant)} GNF)</b>.",
        STYLE_TEXTE,
    )


def bloc_signatures(periode, largeur, signataires=None):
    signataires = signataires if signataires is not None else periode.liste_signataires
    elements = [
        Spacer(1, 0.3 * cm),
        Paragraph(
            escape(date_edition(periode)),
            ParagraphStyle('date', parent=STYLE_TEXTE, alignment=2),
        ),
        Spacer(1, 0.3 * cm),
    ]
    if not signataires:
        return elements
    titres = [Paragraph(f"<b>{escape(titre)}</b>", STYLE_SOUS_TITRE) for titre, _ in signataires]
    noms = [Paragraph(escape(nom), STYLE_SOUS_TITRE) for _, nom in signataires]
    table = Table(
        [titres, [''] * len(signataires), noms],
        colWidths=[largeur / len(signataires)] * len(signataires),
        rowHeights=[None, 1.6 * cm, None],
    )
    table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(KeepTogether([table]))
    return elements


def style_tableau(nb_lignes_entete=1, ligne_total=True, colonnes_montants=None):
    commandes = [
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (-1, nb_lignes_entete - 1), colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, 0), (-1, nb_lignes_entete - 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, nb_lignes_entete - 1), 'CENTER'),
        ('ALIGN', (0, nb_lignes_entete), (0, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]
    for colonne in colonnes_montants or []:
        commandes.append(('ALIGN', (colonne, nb_lignes_entete), (colonne, -1), 'RIGHT'))
    if ligne_total:
        commandes += [
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ]
    return TableStyle(commandes)


def _document(reponse, paysage=True):
    taille = landscape(A4) if paysage else A4
    doc = SimpleDocTemplate(
        reponse, pagesize=taille,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1 * cm, bottomMargin=1 * cm,
    )
    return doc, taille[0] - doc.leftMargin - doc.rightMargin


# --------------------------------------------------------------------------
# État de salaire par rubrique
# --------------------------------------------------------------------------

def _colonne_retenues(etats):
    return any(etat.deductions for etat in etats)


def _tableau_forfait(etats, periode, largeur):
    retenues = _colonne_retenues(etats)
    entete_1 = [
        'N°', 'Prénoms et Nom', 'Matri.', 'Charge ou Fonct.', 'Jours trav.',
        'Salaire de base', 'PRIMES', '', '', '', '', '',
        'Salaire brut', 'Acompte payé',
    ] + (['Retenues'] if retenues else []) + ['Net à payer', 'Émarg.']
    entete_2 = [
        '', '', '', '', '', '',
        'Fonct.', 'Craie / Révis.', 'Ancien.', 'Éloign.', 'Perform.', 'Except.',
        '', '',
    ] + ([''] if retenues else []) + ['', '']
    lignes = [[_p(c, STYLE_ENTETE_CELLULE) if c else '' for c in entete_1],
              [_p(c, STYLE_ENTETE_CELLULE) if c else '' for c in entete_2]]

    champs = ['salaire_base', *EtatSalaire.CHAMPS_PRIMES]
    totaux = {champ: ZERO for champ in champs}
    total_brut = total_avances = total_retenues = total_net = ZERO
    for index, etat in enumerate(etats, start=1):
        for champ in champs:
            totaux[champ] += getattr(etat, champ) or ZERO
        total_brut += etat.salaire_brut
        total_avances += etat.avances or ZERO
        total_retenues += etat.deductions or ZERO
        total_net += etat.salaire_net or ZERO
        lignes.append([
            index,
            _p(nom_document(etat.enseignant)),
            etat.enseignant.matricule,
            _p(charge_ou_fonction(etat.enseignant, periode)),
            etat.jours_travailles,
            *[_m(getattr(etat, champ)) for champ in champs],
            _m(etat.salaire_brut),
            _m(etat.avances),
        ] + ([_m(etat.deductions)] if retenues else []) + [
            _m(etat.salaire_net), '',
        ])
    lignes.append(
        ['', 'TOTAL', '', '', '']
        + [_m(totaux[champ]) for champ in champs]
        + [_m(total_brut), _m(total_avances)]
        + ([_m(total_retenues)] if retenues else [])
        + [_m(total_net), '']
    )

    fixes = [0.8, 4.1, 1.5, 3.0, 1.1]
    montants = [1.7] + [1.45] * 6 + [1.8, 1.7] + ([1.5] if retenues else []) + [1.8]
    largeurs = [x * cm for x in fixes + montants]
    reste = largeur - sum(largeurs)
    largeurs.append(max(reste, 1.2 * cm))
    table = Table(lignes, colWidths=largeurs, repeatRows=2)
    style = style_tableau(
        nb_lignes_entete=2,
        colonnes_montants=list(range(5, 5 + len(montants))),
    )
    for colonne in range(len(entete_1)):
        if colonne < 6 or colonne > 11:
            style.add('SPAN', (colonne, 0), (colonne, 1))
    style.add('SPAN', (6, 0), (11, 0))
    style.add('ALIGN', (4, 2), (4, -1), 'CENTER')
    table.setStyle(style)
    return table, total_brut


def _tableau_secondaire(etats, periode, largeur):
    retenues = _colonne_retenues(etats)
    entete = [
        'N°', 'Prénoms et Nom', 'Matri.', 'Charge ou Fonction', 'Jours trav.',
        'Heures prestées', 'Heures révision', 'Taux', 'Valeur des heures',
        'Primes', 'Salaire brut', 'Acompte payé',
    ] + (['Retenues'] if retenues else []) + ['Net à payer', 'Émarg.']
    lignes = [[_p(c, STYLE_ENTETE_CELLULE) for c in entete]]
    heures = revision = base = primes = brut = avances = deductions = net = ZERO
    for index, etat in enumerate(etats, start=1):
        heures += etat.total_heures or ZERO
        revision += etat.heures_revision or ZERO
        base += etat.salaire_base or ZERO
        primes += etat.primes or ZERO
        brut += etat.salaire_brut
        avances += etat.avances or ZERO
        deductions += etat.deductions or ZERO
        net += etat.salaire_net or ZERO
        lignes.append([
            index,
            _p(nom_document(etat.enseignant)),
            etat.enseignant.matricule,
            _p(charge_ou_fonction(etat.enseignant, periode)),
            etat.jours_travailles,
            f"{(etat.total_heures or ZERO).normalize():f}",
            f"{(etat.heures_revision or ZERO).normalize():f}",
            _m(etat.taux_horaire_applique),
            _m(etat.salaire_base),
            _m(etat.primes),
            _m(etat.salaire_brut),
            _m(etat.avances),
        ] + ([_m(etat.deductions)] if retenues else []) + [
            _m(etat.salaire_net), '',
        ])
    lignes.append(
        ['', 'TOTAL', '', '', '',
         f"{heures.normalize():f}", f"{revision.normalize():f}", '',
         _m(base), _m(primes), _m(brut), _m(avances)]
        + ([_m(deductions)] if retenues else [])
        + [_m(net), '']
    )
    fixes = [0.8, 4.5, 1.6, 3.4, 1.2, 1.5, 1.5]
    montants = [1.5, 2.0, 1.8, 2.0, 1.8] + ([1.6] if retenues else []) + [2.0]
    largeurs = [x * cm for x in fixes + montants]
    largeurs.append(max(largeur - sum(largeurs), 1.2 * cm))
    table = Table(lignes, colWidths=largeurs, repeatRows=1)
    style = style_tableau(colonnes_montants=list(range(7, 7 + len(montants))))
    style.add('ALIGN', (4, 1), (6, -1), 'CENTER')
    table.setStyle(style)
    return table, brut


def etat_salaire_groupe_pdf(reponse, periode, groupe):
    doc, largeur = _document(reponse)
    etats = etats_de_la_periode(periode, groupe)
    libelle_groupe = GroupePaie(groupe).label
    elements = [entete_ecole(periode, largeur)]
    elements += titre_document(
        'ETAT DE SALAIRE A PAYER',
        periode,
        sous_titre=f"Personnel : {libelle_groupe}",
    )
    elements += avertissement_brouillon(etats)
    if groupe == GroupePaie.SECONDAIRE:
        table, total = _tableau_secondaire(etats, periode, largeur)
    else:
        table, total = _tableau_forfait(etats, periode, largeur)
    elements.append(table)
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(arrete(
        f"Arrêté le présent état de salaire du mois de {libelle_mois(periode)}",
        total,
    ))
    elements += bloc_signatures(periode, largeur)
    doc.build(elements)


# --------------------------------------------------------------------------
# Masse salariale
# --------------------------------------------------------------------------

def totaux_par_groupe(periode):
    totaux = []
    etats = etats_de_la_periode(periode)
    for groupe in ORDRE_GROUPES:
        du_groupe = [etat for etat in etats if etat.enseignant.groupe_paie == groupe]
        if not du_groupe:
            continue
        totaux.append({
            'groupe': groupe,
            'libelle': GroupePaie(groupe).label,
            'effectif': len(du_groupe),
            'brut': sum((etat.salaire_brut for etat in du_groupe), ZERO),
            'avances': sum((etat.avances or ZERO for etat in du_groupe), ZERO),
            'retenues': sum((etat.deductions or ZERO for etat in du_groupe), ZERO),
            'net': sum((etat.salaire_net or ZERO for etat in du_groupe), ZERO),
        })
    return totaux, etats


def masse_salariale_pdf(reponse, periode):
    doc, largeur = _document(reponse, paysage=False)
    lignes_groupes, etats = totaux_par_groupe(periode)
    retenues = any(ligne['retenues'] for ligne in lignes_groupes)
    entete = ['N°', 'Rubrique', 'Effectif', 'Montant', 'Acompte'] + (
        ['Retenues'] if retenues else []
    ) + ['Net à payer', 'Observation']
    lignes = [[_p(c, STYLE_ENTETE_CELLULE) for c in entete]]
    for index, ligne in enumerate(lignes_groupes, start=1):
        lignes.append(
            [index, ligne['libelle'], ligne['effectif'], _m(ligne['brut']), _m(ligne['avances'])]
            + ([_m(ligne['retenues'])] if retenues else [])
            + [_m(ligne['net']), '']
        )
    total = {cle: sum((ligne[cle] for ligne in lignes_groupes), ZERO)
             for cle in ('brut', 'avances', 'retenues', 'net')}
    effectif = sum(ligne['effectif'] for ligne in lignes_groupes)
    lignes.append(
        ['', 'TOTAL', effectif, _m(total['brut']), _m(total['avances'])]
        + ([_m(total['retenues'])] if retenues else [])
        + [_m(total['net']), '']
    )
    fixes = [1.0, 4.5, 1.8, 2.6, 2.4] + ([2.2] if retenues else []) + [2.6]
    largeurs = [x * cm for x in fixes]
    largeurs.append(max(largeur - sum(largeurs), 2 * cm))
    table = Table(lignes, colWidths=largeurs, repeatRows=1)
    style = style_tableau(colonnes_montants=list(range(3, len(entete) - 1)))
    style.add('ALIGN', (2, 1), (2, -1), 'CENTER')
    table.setStyle(style)

    elements = [entete_ecole(periode, largeur)]
    elements += titre_document('MASSE SALARIALE', periode)
    elements += avertissement_brouillon(etats)
    elements += [
        table,
        Spacer(1, 0.4 * cm),
        arrete(
            f"Arrêtée la présente masse salariale du mois de {libelle_mois(periode)}",
            total['brut'],
        ),
    ]
    elements += bloc_signatures(periode, largeur)
    doc.build(elements)


# --------------------------------------------------------------------------
# Acomptes
# --------------------------------------------------------------------------

NOMBRE_BONS = 5


def lignes_acomptes(periode):
    """Une ligne par travailleur : bons 1 à 5 (les bons au-delà du 5e sont cumulés)."""
    avances_par_enseignant = {}
    for avance in (
        AvanceSalaire.objects.filter(periode=periode)
        .select_related('enseignant')
        .order_by('date_avance', 'date_creation', 'pk')
    ):
        avances_par_enseignant.setdefault(avance.enseignant_id, []).append(avance)

    enseignants = {etat.enseignant_id: etat.enseignant for etat in etats_de_la_periode(periode)}
    for avances in avances_par_enseignant.values():
        enseignants.setdefault(avances[0].enseignant_id, avances[0].enseignant)

    lignes = []
    for enseignant in sorted(
        enseignants.values(),
        key=lambda e: (ORDRE_GROUPES.index(e.groupe_paie), e.nom, e.prenoms),
    ):
        montants = [avance.montant for avance in avances_par_enseignant.get(enseignant.pk, [])]
        bons = montants[:NOMBRE_BONS - 1] + (
            [sum(montants[NOMBRE_BONS - 1:], ZERO)] if len(montants) >= NOMBRE_BONS else []
        )
        bons += [None] * (NOMBRE_BONS - len(bons))
        lignes.append({
            'enseignant': enseignant,
            'bons': bons,
            'total': sum(montants, ZERO),
            'observation': (
                f"{len(montants)} bons" if len(montants) > NOMBRE_BONS else ''
            ),
        })
    return lignes


def acomptes_pdf(reponse, periode):
    doc, largeur = _document(reponse)
    lignes_data = lignes_acomptes(periode)
    entete = ['N°', 'Prénoms et Nom', 'Matri.', 'Site', 'Charge ou Fonction'] + [
        f"Bon {numero}" for numero in range(1, NOMBRE_BONS + 1)
    ] + ['Acompte payé', 'Observation']
    lignes = [[_p(c, STYLE_ENTETE_CELLULE) for c in entete]]
    totaux_bons = [ZERO] * NOMBRE_BONS
    total = ZERO
    for index, ligne in enumerate(lignes_data, start=1):
        enseignant = ligne['enseignant']
        for position, bon in enumerate(ligne['bons']):
            totaux_bons[position] += bon or ZERO
        total += ligne['total']
        lignes.append(
            [
                index,
                _p(nom_document(enseignant)),
                enseignant.matricule,
                _p(GroupePaie(enseignant.groupe_paie).label),
                _p(charge_ou_fonction(enseignant, periode)),
            ]
            + [_m(bon) if bon else '' for bon in ligne['bons']]
            + [_m(ligne['total']), _p(ligne['observation'])]
        )
    lignes.append(
        ['', 'TOTAL', '', '', '']
        + [_m(montant) for montant in totaux_bons]
        + [_m(total), '']
    )
    fixes = [0.8, 5.0, 1.8, 3.2, 4.0] + [1.9] * NOMBRE_BONS + [2.2]
    largeurs = [x * cm for x in fixes]
    largeurs.append(max(largeur - sum(largeurs), 2 * cm))
    table = Table(lignes, colWidths=largeurs, repeatRows=1)
    table.setStyle(style_tableau(
        colonnes_montants=list(range(5, 5 + NOMBRE_BONS + 1)),
    ))

    elements = [entete_ecole(periode, largeur)]
    elements += titre_document('ACOMPTE PERSONNEL', periode)
    elements += [
        table,
        Spacer(1, 0.4 * cm),
        arrete("Arrêté le présent état des acomptes", total),
    ]
    elements += bloc_signatures(periode, largeur)
    doc.build(elements)


# --------------------------------------------------------------------------
# Fiche d'émargement
# --------------------------------------------------------------------------

def emargement_pdf(reponse, periode, groupes=None):
    doc, largeur = _document(reponse, paysage=False)
    etats = etats_de_la_periode(periode)
    if groupes:
        etats = [etat for etat in etats if etat.enseignant.groupe_paie in groupes]
    etats.sort(key=lambda etat: (
        ORDRE_GROUPES.index(etat.enseignant.groupe_paie),
        etat.enseignant.nom, etat.enseignant.prenoms,
    ))
    entete = ['N°', 'Prénoms et Nom', 'Matri.', 'Site', 'Charge ou Fonction',
              'Émargement', 'Observation']
    lignes = [[_p(c, STYLE_ENTETE_CELLULE) for c in entete]]
    for index, etat in enumerate(etats, start=1):
        enseignant = etat.enseignant
        lignes.append([
            index,
            _p(nom_document(enseignant)),
            enseignant.matricule,
            _p(GroupePaie(enseignant.groupe_paie).label),
            _p(charge_ou_fonction(enseignant, periode)),
            '', '',
        ])
    largeurs = [x * cm for x in (0.8, 4.6, 1.8, 2.6, 3.4, 3.0)]
    largeurs.append(max(largeur - sum(largeurs), 1.5 * cm))
    table = Table(
        lignes, colWidths=largeurs, repeatRows=1,
        rowHeights=[None] + [0.9 * cm] * len(etats),
    )
    table.setStyle(style_tableau(ligne_total=False))

    sous_titre = None
    if groupes:
        sous_titre = 'Personnel : ' + ', '.join(GroupePaie(g).label for g in groupes)
    elements = [entete_ecole(periode, largeur)]
    elements += titre_document(
        "FICHE D'ÉMARGEMENT DES SALAIRES POUR ACQUIT", periode, sous_titre,
    )
    elements += [
        Paragraph(
            "1- En émargeant la présente fiche, vous attestez avoir perçu votre "
            f"salaire du mois que vous doit {escape(periode.ecole.nom)}.",
            STYLE_TEXTE,
        ),
        Paragraph(
            "2- Le bulletin de paie fournit tous les détails relatifs à votre "
            "salaire ; ce bulletin est personnel !",
            STYLE_TEXTE,
        ),
        Spacer(1, 0.3 * cm),
        table,
    ]
    elements += bloc_signatures(periode, largeur)
    doc.build(elements)


# --------------------------------------------------------------------------
# Bulletin de paie individuel
# --------------------------------------------------------------------------

MOTS_SIGNATAIRE_PAIE = ('gestion', 'compta', 'financ', 'caiss')


def signataire_bulletin(periode):
    signataires = periode.liste_signataires
    for titre, nom in signataires:
        if any(mot in titre.lower() for mot in MOTS_SIGNATAIRE_PAIE):
            return titre, nom
    if signataires:
        return signataires[-1]
    return 'La Comptabilité', ''


def bulletin_paie_pdf(reponse, etat):
    periode = etat.periode
    enseignant = etat.enseignant
    doc, largeur = _document(reponse, paysage=False)

    infos = [
        ['Prénoms et nom :', nom_document(enseignant), 'Matricule :', enseignant.matricule or '-'],
        ["Date d'embauche :", enseignant.date_embauche.strftime('%d/%m/%Y'),
         'Ancienneté :', f"{enseignant.anciennete_annees(periode.annee)} an(s)"],
        ['Fonction :', _p(charge_ou_fonction(enseignant, periode)),
         'Jours travaillés :', etat.jours_travailles],
        ['Site :', GroupePaie(enseignant.groupe_paie).label, '', ''],
    ]
    table_infos = Table(infos, colWidths=[3.2 * cm, 7 * cm, 3.2 * cm, largeur - 13.4 * cm])
    table_infos.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    rubriques = [('Salaire de base', etat.salaire_base, None, None)]
    if enseignant.est_taux_horaire and etat.total_heures is not None:
        rubriques[0] = (
            f"Salaire de base ({etat.total_heures.normalize():f} h × "
            f"{_m(etat.taux_horaire_applique)} GNF)",
            etat.salaire_base, None, None,
        )
    libelles_primes = {
        'prime_fonction': 'Prime de fonction',
        'prime_craie': 'Prime de craie / révision',
        'prime_anciennete': "Prime d'ancienneté",
        'prime_eloignement': "Prime d'éloignement",
        'prime_performance': 'Prime de performance',
        'prime_exceptionnelle': 'Prime exceptionnelle',
    }
    for champ in EtatSalaire.CHAMPS_PRIMES:
        rubriques.append((libelles_primes[champ], None, getattr(etat, champ), None))
    prelevements = (etat.avances or ZERO) + (etat.deductions or ZERO)
    rubriques.append(('Avance sur salaire et autre prélèvement', None, None, prelevements))

    lignes = [[_p(c, STYLE_ENTETE_CELLULE) for c in ('N°', 'Rubriques', 'Base', 'Primes', 'Acompte', 'Solde')]]
    solde = ZERO
    for index, (libelle, base, prime, retenue) in enumerate(rubriques, start=1):
        solde += (base or ZERO) + (prime or ZERO) - (retenue or ZERO)
        lignes.append([
            index, _p(libelle),
            _m(base) if base is not None else '',
            _m(prime) if prime is not None else '',
            _m(retenue) if retenue is not None else '',
            _m(solde),
        ])
    lignes.append(['', 'TOTAL', _m(etat.salaire_base), _m(etat.primes), _m(prelevements), _m(etat.salaire_net)])
    table = Table(
        lignes,
        colWidths=[1 * cm, largeur - 11 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm],
        repeatRows=1,
    )
    table.setStyle(style_tableau(colonnes_montants=[2, 3, 4, 5]))

    resume = Table(
        [
            [Paragraph('<b>Salaire brut :</b>', STYLE_TEXTE), Paragraph(f"<b>{_m(etat.salaire_brut)} GNF</b>", STYLE_TEXTE),
             Paragraph(montant_en_lettres(etat.salaire_brut), STYLE_TEXTE)],
            [Paragraph('<b>Net à payer :</b>', STYLE_TEXTE), Paragraph(f"<b>{_m(etat.salaire_net)} GNF</b>", STYLE_TEXTE),
             Paragraph(montant_en_lettres(etat.salaire_net), STYLE_TEXTE)],
        ],
        colWidths=[3 * cm, 3.5 * cm, largeur - 6.5 * cm],
    )
    resume.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 1), (-1, 1), 0.8, colors.black),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f3f4f6')),
    ]))

    statut = 'Payé' if etat.paye else ('Validé' if etat.valide else 'Provisoire (non validé)')
    elements = [entete_ecole(periode, largeur)]
    elements += titre_document('BULLETIN DE PAIE', periode)
    elements += [
        table_infos,
        Spacer(1, 0.4 * cm),
        table,
        Spacer(1, 0.4 * cm),
        resume,
        Spacer(1, 0.2 * cm),
        Paragraph(f"Statut : {statut}", STYLE_TEXTE),
    ]
    if etat.observations:
        elements.append(Paragraph(f"Observations : {escape(etat.observations)}", STYLE_TEXTE))
    titre, nom = signataire_bulletin(periode)
    elements += bloc_signatures(
        periode, largeur,
        signataires=[('Le travailleur', nom_document(enseignant)), (titre, nom)],
    )
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph(
        '<i>Ce bulletin est personnel et confidentiel.</i>',
        ParagraphStyle('pied', parent=STYLE_TEXTE, alignment=TA_LEFT, fontSize=8),
    ))
    doc.build(elements)
