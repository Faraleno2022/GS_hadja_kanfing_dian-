"""
Rapport Scolaire Public — Accessible aux parents sans authentification.
Le parent renseigne le matricule de l'élève, son numéro de téléphone
et la classe. Le système vérifie que les informations correspondent
et génère un PDF complet : situation scolaire, notes, activités journalières.
"""
import io
import os
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace

from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Q, Avg
from django.utils.html import escape
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader
from PIL import Image

from eleves.models import Eleve, Classe, Ecole
from notes.models import (
    ClasseNote, MatiereNote, NoteEleve, NoteMensuelle,
    CompositionNote, AppreciationMaternelle,
    ActiviteJournaliere, PieceJointeActivite, Classement, NoteSuivi,
)
from notes.charte_graphique import (
    couleur_document,
    document_avec_charte,
    get_charte_reportlab,
)
from paiements.models import Paiement, EcheancierPaiement

from django.utils.crypto import get_random_string
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired


# ────────────────────────────────────────────────────────────────
# UTILITAIRE : Token signé pour sécuriser l'accès
# ────────────────────────────────────────────────────────────────
_signer = TimestampSigner(salt='rapport-scolaire')


def _make_token(eleve_id):
    return _signer.sign(str(eleve_id))


def _verify_token(token, max_age=1800):
    """Vérifie le token et retourne l'eleve_id. Expire après 30 min."""
    try:
        return int(_signer.unsign(token, max_age=max_age))
    except (BadSignature, SignatureExpired, ValueError):
        return None


def _eleve_parent_depuis_token(request):
    """Retourne uniquement l'élève désigné par le token temporaire du parent."""
    eleve_id = _verify_token(request.GET.get('token', ''))
    if not eleve_id:
        raise Http404("Lien parent invalide ou expiré.")
    try:
        return Eleve.objects.select_related(
            'classe', 'classe__ecole',
            'responsable_principal', 'responsable_secondaire',
        ).get(pk=eleve_id, statut='ACTIF')
    except Eleve.DoesNotExist:
        raise Http404("Élève introuvable.")


def _bulletins_disponibles(eleve, classe_note, annee):
    """Liste les périodes réellement renseignées et signe chaque bulletin."""
    if not classe_note:
        return []

    periodes = set(
        NoteMensuelle.objects.filter(
            eleve=eleve,
            matiere__classe=classe_note,
            annee_scolaire=annee,
        ).filter(Q(note__isnull=False) | Q(absent=True)).values_list('mois', flat=True)
    )
    periodes.update(
        CompositionNote.objects.filter(
            eleve=eleve,
            matiere__classe=classe_note,
            annee_scolaire=annee,
        ).filter(Q(note__isnull=False) | Q(absent=True)).values_list('periode', flat=True)
    )
    periodes.update(
        AppreciationMaternelle.objects.filter(
            eleve=eleve,
            matiere__classe=classe_note,
            annee_scolaire=annee,
        ).values_list('trimestre', flat=True)
    )

    labels = dict(NoteMensuelle.MOIS_CHOICES)
    labels.update(dict(CompositionNote.PERIODE_CHOICES))
    labels.update(dict(AppreciationMaternelle.TRIMESTRE_CHOICES))
    ordre = {
        'OCTOBRE': 1, 'NOVEMBRE': 2, 'DECEMBRE': 3,
        'TRIMESTRE_1': 4, 'JANVIER': 5, 'FEVRIER': 6, 'MARS': 7,
        'TRIMESTRE_2': 8, 'SEMESTRE_1': 9, 'AVRIL': 10, 'MAI': 11,
        'JUIN': 12, 'TRIMESTRE_3': 13, 'SEMESTRE_2': 14,
    }
    from .bulletin_public import generer_token_bulletin

    return [
        {
            'periode': periode,
            'libelle': labels.get(periode, periode.replace('_', ' ').title()),
            'token': generer_token_bulletin(
                eleve.pk, classe_note.pk, periode, duree_validite_jours=1,
            ),
        }
        for periode in sorted(periodes, key=lambda item: ordre.get(item, 999))
    ]


class ClassementList(list):
    def last(self):
        return self[-1] if self else None


def _classements_courants(eleve, classe_note, annee):
    """Construit les classements depuis le calcul central, pas depuis un snapshot."""
    if not classe_note:
        return []

    from .calculs_moyennes import (
        detecter_niveau_scolaire,
        obtenir_appreciation_intelligente,
        obtenir_mention_intelligente,
    )
    from .utils_rangs import calculer_rangs_classe_periode

    periodes = []
    periodes.extend(
        NoteMensuelle.objects.filter(
            eleve=eleve,
            matiere__classe=classe_note,
            annee_scolaire=annee,
            note__isnull=False,
        ).values_list('mois', flat=True).distinct()
    )
    periodes.extend(
        CompositionNote.objects.filter(
            eleve=eleve,
            matiere__classe=classe_note,
            annee_scolaire=annee,
            note__isnull=False,
        ).values_list('periode', flat=True).distinct()
    )

    ordre = {
        'OCTOBRE': 1, 'NOVEMBRE': 2, 'DECEMBRE': 3,
        'TRIMESTRE_1': 4, 'JANVIER': 5, 'FEVRIER': 6, 'MARS': 7,
        'TRIMESTRE_2': 8, 'SEMESTRE_1': 9, 'AVRIL': 10, 'MAI': 11,
        'JUIN': 12, 'TRIMESTRE_3': 13, 'SEMESTRE_2': 14,
    }
    resultats = []
    niveau = detecter_niveau_scolaire(classe_note.nom)
    for periode in sorted(set(periodes), key=lambda p: ordre.get(p, 999)):
        rangs = calculer_rangs_classe_periode(classe_note, periode, use_cache=False)
        info = rangs.get(eleve.id)
        if not info:
            continue
        moyenne = Decimal(str(info['moyenne']))
        total_eleves = info.get('total_eleves') or 0
        rang = info.get('rang_num') or info.get('rang')
        resultats.append(SimpleNamespace(
            periode=periode,
            moyenne_generale=moyenne,
            rang=rang,
            rang_formate=f"{info['rang']}/{total_eleves}" if total_eleves else str(info['rang']),
            effectif=total_eleves,
            mention=obtenir_mention_intelligente(moyenne, niveau),
            appreciation=obtenir_appreciation_intelligente(moyenne, eleve.prenom, niveau),
        ))
    return ClassementList(resultats)


# ────────────────────────────────────────────────────────────────
# UTILITAIRE : Collecter toutes les données scolaires
# ────────────────────────────────────────────────────────────────

def _collecter_donnees_scolaires(eleve):
    """Collecte toutes les données scolaires d'un élève pour le template et le PDF."""
    annee = eleve.classe.annee_scolaire if eleve.classe else ''
    ecole = eleve.classe.ecole if eleve.classe else None

    # ─── Classe Note ───
    classe_note = ClasseNote.objects.filter(
        nom=eleve.classe.nom,
        ecole=eleve.classe.ecole,
        annee_scolaire=annee,
        actif=True,
    ).first() if eleve.classe else None

    # ─── Notes mensuelles ───
    MOIS_ORDRE = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 'MARS', 'AVRIL', 'MAI', 'JUIN']
    MOIS_LABELS = ['Oct', 'Nov', 'Déc', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin']

    matieres = []
    matieres_data = []
    compo_periodes = []

    if classe_note:
        matieres_qs = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
        matieres = list(matieres_qs)
        from .calculs_moyennes import calculer_moyenne_annuelle_matiere, calculer_moyenne_generale_annuelle

        # Collecter les périodes de composition existantes
        compo_periodes_set = set()
        for mat in matieres:
            compos = CompositionNote.objects.filter(
                eleve=eleve, matiere=mat, annee_scolaire=annee
            )
            for c in compos:
                compo_periodes_set.add((c.periode, c.get_periode_display()))
        compo_periodes = sorted(compo_periodes_set, key=lambda x: x[0])
        compo_codes = {p[0] for p in compo_periodes}
        annual_system = None
        if any(p.startswith('TRIMESTRE') for p in compo_codes):
            annual_system = 'annuel_trimestriel'
        elif any(p.startswith('SEMESTRE') for p in compo_codes):
            annual_system = 'annuel_semestriel'

        for mat in matieres:
            # Notes mensuelles
            notes_m = NoteMensuelle.objects.filter(eleve=eleve, matiere=mat, annee_scolaire=annee)
            mois_dict = {n.mois: n for n in notes_m}
            notes_par_mois = []
            total_notes = 0
            count_notes = 0
            for m in MOIS_ORDRE:
                n = mois_dict.get(m)
                if n:
                    if n.absent:
                        notes_par_mois.append('ABS')
                    elif n.note is not None:
                        notes_par_mois.append(str(n.note))
                        total_notes += float(n.note)
                        count_notes += 1
                    else:
                        notes_par_mois.append('—')
                else:
                    notes_par_mois.append('—')

            # Compositions
            compos = CompositionNote.objects.filter(
                eleve=eleve, matiere=mat, annee_scolaire=annee
            ).order_by('periode')
            compo_dict = {c.periode: ('ABS' if c.absent else str(c.note or '—')) for c in compos}
            notes_compo = [compo_dict.get(p[0], '—') for p in compo_periodes]

            moyenne_matiere = round(total_notes / count_notes, 2) if count_notes > 0 else None
            if annual_system:
                moyenne_centrale = calculer_moyenne_annuelle_matiere(eleve, mat, annual_system).get('moyenne_annuelle')
                if moyenne_centrale is not None:
                    moyenne_matiere = moyenne_centrale

            matieres_data.append({
                'nom': mat.nom,
                'coefficient': mat.coefficient,
                'notes_mensuelles': notes_par_mois,
                'notes_compo': notes_compo,
                'moyenne': moyenne_matiere,
            })

    # ─── Classements ───
    classements = _classements_courants(eleve, classe_note, annee)

    # ─── Forces et faiblesses (déduit des notes) ───
    forces = []
    faiblesses = []
    for md in matieres_data:
        if md['moyenne'] is not None:
            if md['moyenne'] >= 14:
                forces.append({'matiere': md['nom'], 'moyenne': md['moyenne']})
            elif md['moyenne'] < 10:
                faiblesses.append({'matiere': md['nom'], 'moyenne': md['moyenne']})
    forces.sort(key=lambda x: x['moyenne'], reverse=True)
    faiblesses.sort(key=lambda x: x['moyenne'])

    # ─── Conseils personnalisés ───
    conseils = []
    if faiblesses:
        for f in faiblesses[:3]:
            conseils.append(f"Renforcer les efforts en {f['matiere']} (moyenne actuelle : {f['moyenne']}/20)")
    if forces:
        conseils.append(f"Continuer les excellents résultats en {forces[0]['matiere']}")
    if not forces and not faiblesses:
        conseils.append("Continuer les efforts pour maintenir un bon niveau général")

    # Moyenne générale
    moyenne_generale = None
    if classe_note and matieres and 'annual_system' in locals() and annual_system:
        moyenne_generale = calculer_moyenne_generale_annuelle(eleve, matieres_qs, annual_system).get('moyenne_generale')
    if moyenne_generale is None:
        moyennes_valides = [md['moyenne'] for md in matieres_data if md['moyenne'] is not None]
        moyenne_generale = round(sum(moyennes_valides) / len(moyennes_valides), 2) if moyennes_valides else None

    # ─── Activités journalières ───
    activites = ActiviteJournaliere.objects.filter(
        eleve=eleve
    ).select_related('classe').prefetch_related('pieces_jointes').order_by('-date')[:50]

    return {
        'eleve': eleve,
        'ecole': ecole,
        'annee': annee,
        'classe_note': classe_note,
        'mois_labels': MOIS_LABELS,
        'compo_periodes': compo_periodes,
        'matieres_data': matieres_data,
        'classements': classements,
        'forces': forces,
        'faiblesses': faiblesses,
        'conseils': conseils,
        'moyenne_generale': moyenne_generale,
        'activites': activites,
    }


# ────────────────────────────────────────────────────────────────
# VUE : Formulaire de recherche (public, pas de login_required)
# ────────────────────────────────────────────────────────────────

def rapport_scolaire_recherche(request):
    """Affiche le formulaire de recherche et traite la soumission."""
    erreur = None
    eleve = None

    if request.method == 'POST':
        matricule = request.POST.get('matricule', '').strip().upper()
        telephone = request.POST.get('telephone', '').strip()
        classe_id = request.POST.get('classe', '').strip()

        if not matricule or not telephone or not classe_id:
            erreur = "Veuillez remplir tous les champs."
        else:
            # Normaliser le téléphone : accepter avec ou sans +224
            tel_normalise = re.sub(r'[\s\-\.]', '', telephone)
            if not tel_normalise.startswith('+'):
                tel_normalise = '+224' + tel_normalise.lstrip('0')

            # Chercher l'élève
            try:
                eleve = Eleve.objects.select_related(
                    'classe', 'classe__ecole',
                    'responsable_principal', 'responsable_secondaire'
                ).get(matricule=matricule, statut='ACTIF')
            except Eleve.DoesNotExist:
                erreur = "Aucun élève actif trouvé avec ce matricule."

            if eleve and not erreur:
                # Vérifier la classe (par ID ou par nom)
                try:
                    cid = int(classe_id)
                    if eleve.classe_id != cid:
                        erreur = "La classe ne correspond pas à cet élève."
                except (ValueError, TypeError):
                    if classe_id.lower() not in eleve.classe.nom.lower():
                        erreur = "La classe ne correspond pas à cet élève."

                # Vérifier le téléphone du responsable
                if not erreur:
                    tel_match = False
                    for resp in [eleve.responsable_principal, eleve.responsable_secondaire]:
                        if resp and resp.telephone:
                            resp_tel = re.sub(r'[\s\-\.]', '', resp.telephone)
                            if not resp_tel.startswith('+'):
                                resp_tel = '+224' + resp_tel.lstrip('0')
                            if resp_tel == tel_normalise:
                                tel_match = True
                                break
                    if not tel_match:
                        erreur = "Le numéro de téléphone ne correspond à aucun responsable de cet élève."

        if eleve and not erreur:
            # Tout est valide — rediriger vers la page détail
            token = _make_token(eleve.pk)
            return redirect(f'/rapport-scolaire/detail/?token={token}')

    # GET ou erreur — PAS de liste de classes (sécurité : ne pas exposer les écoles/classes)
    return render(request, 'rapport_scolaire/recherche.html', {
        'erreur': erreur,
    })


# ────────────────────────────────────────────────────────────────
# VUE AJAX : Charger les classes après validation matricule+téléphone
# ────────────────────────────────────────────────────────────────

@require_POST
def rapport_scolaire_classes_ajax(request):
    """Retourne la liste des classes pour un élève après validation du matricule et téléphone."""
    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Requête invalide.'}, status=400)

    matricule = (data.get('matricule') or '').strip().upper()
    telephone = (data.get('telephone') or '').strip()

    if not matricule or not telephone:
        return JsonResponse({'error': 'Matricule et téléphone requis.'}, status=400)

    # Normaliser le téléphone
    tel_normalise = re.sub(r'[\s\-\.]', '', telephone)
    if not tel_normalise.startswith('+'):
        tel_normalise = '+224' + tel_normalise.lstrip('0')

    # Chercher l'élève
    try:
        eleve = Eleve.objects.select_related(
            'classe', 'classe__ecole',
            'responsable_principal', 'responsable_secondaire'
        ).get(matricule=matricule, statut='ACTIF')
    except Eleve.DoesNotExist:
        return JsonResponse({'error': 'Aucun élève actif trouvé avec ce matricule.'}, status=404)

    # Vérifier le téléphone du responsable
    tel_match = False
    for resp in [eleve.responsable_principal, eleve.responsable_secondaire]:
        if resp and resp.telephone:
            resp_tel = re.sub(r'[\s\-\.]', '', resp.telephone)
            if not resp_tel.startswith('+'):
                resp_tel = '+224' + resp_tel.lstrip('0')
            if resp_tel == tel_normalise:
                tel_match = True
                break

    if not tel_match:
        return JsonResponse({'error': 'Le numéro de téléphone ne correspond pas.'}, status=403)

    # Retourner uniquement la classe de cet élève (pas toute la base)
    classe = eleve.classe
    return JsonResponse({
        'classes': [{
            'id': classe.id,
            'nom': classe.nom,
            'ecole': classe.ecole.nom if classe.ecole else '',
        }]
    })


# ────────────────────────────────────────────────────────────────
# VUE : Page détail complète (public, sécurisé par token signé)
# ────────────────────────────────────────────────────────────────

def rapport_scolaire_detail(request):
    """Affiche le rapport scolaire complet en HTML pour les parents."""
    token = request.GET.get('token', '')
    eleve_id = _verify_token(token)
    if not eleve_id:
        return render(request, 'rapport_scolaire/recherche.html', {
            'erreur': "Lien expiré ou invalide. Veuillez relancer la recherche.",
        })

    try:
        eleve = Eleve.objects.select_related(
            'classe', 'classe__ecole',
            'responsable_principal', 'responsable_secondaire'
        ).get(pk=eleve_id, statut='ACTIF')
    except Eleve.DoesNotExist:
        raise Http404

    donnees = _collecter_donnees_scolaires(eleve)
    donnees['token'] = token

    # ─── Paiements validés de l'élève ───
    paiements = Paiement.objects.filter(
        eleve=eleve, statut='VALIDE'
    ).select_related('type_paiement', 'mode_paiement').order_by('-date_paiement')
    donnees['paiements'] = paiements

    # ─── Centre de documents du parent ───
    classe_note = donnees.get('classe_note')
    annee = donnees.get('annee') or ''
    donnees['bulletins_disponibles'] = _bulletins_disponibles(
        eleve, classe_note, annee,
    )
    notes_suivi = NoteSuivi.objects.filter(eleve=eleve, annee_scolaire=annee)
    if classe_note:
        notes_suivi = notes_suivi.filter(matiere__classe=classe_note)
    donnees['notes_suivi_count'] = notes_suivi.count()
    donnees['participations_count'] = notes_suivi.filter(
        type_note='PARTICIPATION',
    ).count()
    vie_scolaire = ActiviteJournaliere.objects.filter(
        eleve=eleve,
        type_activite__in=['ABSENCE', 'RETARD', 'DISCIPLINE', 'CONVOCATION'],
    )
    if classe_note:
        vie_scolaire = vie_scolaire.filter(classe=classe_note)
    donnees['vie_scolaire_count'] = vie_scolaire.count()
    donnees['emploi_du_temps_disponible'] = bool(
        classe_note and classe_note.creneaux_edt.exists()
    )
    donnees['carnet_disponible'] = paiements.filter(
        annee_scolaire=annee,
    ).exists()

    # ─── Situation financière (échéancier) ───
    try:
        ech = eleve.echeancier
        donnees['echeancier'] = (
            {
                'total_du': ech.total_du,
                'total_paye': ech.total_paye,
                'solde_restant': ech.solde_restant,
                'pourcentage_paye': ech.pourcentage_paye,
            }
            if ech else None
        )
    except EcheancierPaiement.DoesNotExist:
        donnees['echeancier'] = None

    return render(request, 'rapport_scolaire/detail.html', donnees)


# ────────────────────────────────────────────────────────────────
# VUE : Téléchargement PDF (public, sécurisé par token signé)
# ────────────────────────────────────────────────────────────────

def rapport_scolaire_pdf(request):
    """Télécharge le rapport scolaire en PDF."""
    token = request.GET.get('token', '')
    eleve_id = _verify_token(token)
    if not eleve_id:
        return render(request, 'rapport_scolaire/recherche.html', {
            'erreur': "Lien expiré ou invalide. Veuillez relancer la recherche.",
        })

    try:
        eleve = Eleve.objects.select_related(
            'classe', 'classe__ecole',
            'responsable_principal', 'responsable_secondaire'
        ).get(pk=eleve_id, statut='ACTIF')
    except Eleve.DoesNotExist:
        raise Http404

    return _generer_rapport_pdf(eleve)


# ────────────────────────────────────────────────────────────────
# VUE : Téléchargement d'un reçu de paiement (public, token signé)
# ────────────────────────────────────────────────────────────────

def rapport_scolaire_recu_pdf(request, paiement_id):
    """Télécharge le reçu PDF d'un paiement, sécurisé par le token rapport-scolaire."""
    token = request.GET.get('token', '')
    eleve_id = _verify_token(token)
    if not eleve_id:
        return render(request, 'rapport_scolaire/recherche.html', {
            'erreur': "Lien expiré ou invalide. Veuillez relancer la recherche.",
        })

    # Vérifier que le paiement appartient bien à cet élève
    try:
        paiement = Paiement.objects.select_related(
            'eleve', 'type_paiement', 'mode_paiement',
            'eleve__classe', 'eleve__classe__ecole'
        ).get(pk=paiement_id, eleve_id=eleve_id, statut='VALIDE')
    except Paiement.DoesNotExist:
        raise Http404

    return _generer_recu_paiement_pdf(paiement)


def _reponse_pdf_parent(eleve, titre, introduction, entetes=None, lignes=None,
                        nom_fichier='document', paysage=False, paragraphes=None,
                        signature=False):
    """Construit un document parent professionnel selon la charte de l'école."""
    ecole = eleve.classe.ecole if eleve.classe else None
    annee = eleve.classe.annee_scolaire if eleve.classe else ''
    palette = get_charte_reportlab(ecole)
    page_size = landscape(A4) if paysage else A4
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=1.25 * cm,
        rightMargin=1.25 * cm,
        topMargin=1.25 * cm,
        bottomMargin=1.35 * cm,
        title=titre,
        author=getattr(ecole, 'nom', 'MySchoolGN') or 'MySchoolGN',
    )
    styles = getSampleStyleSheet()
    titre_style = ParagraphStyle(
        'ParentDocumentTitle', parent=styles['Title'], fontSize=17, leading=20,
        alignment=TA_CENTER, textColor=palette['couleur_primaire'], spaceAfter=6,
    )
    sous_titre_style = ParagraphStyle(
        'ParentDocumentSubtitle', parent=styles['Normal'], fontSize=9,
        leading=12, alignment=TA_CENTER,
        textColor=palette['couleur_texte_secondaire'], spaceAfter=12,
    )
    corps_style = ParagraphStyle(
        'ParentDocumentBody', parent=styles['BodyText'], fontSize=10,
        leading=15, alignment=TA_JUSTIFY, spaceAfter=10,
    )
    cellule_style = ParagraphStyle(
        'ParentDocumentCell', parent=styles['Normal'], fontSize=7.5,
        leading=9, alignment=TA_CENTER,
    )

    nom_ecole = getattr(ecole, 'nom', 'Établissement scolaire') or 'Établissement scolaire'
    elements = [
        Paragraph(escape(nom_ecole.upper()), titre_style),
        Paragraph(escape(titre.upper()), titre_style),
        Paragraph(
            f"Élève : <b>{escape(eleve.nom_complet)}</b> &nbsp; | &nbsp; "
            f"Matricule : <b>{escape(eleve.matricule or '—')}</b> &nbsp; | &nbsp; "
            f"Classe : <b>{escape(eleve.classe.nom if eleve.classe else '—')}</b> &nbsp; | &nbsp; "
            f"Année : <b>{escape(annee or '—')}</b>",
            sous_titre_style,
        ),
    ]
    if introduction:
        elements.append(Paragraph(escape(introduction), corps_style))
    for paragraphe in paragraphes or []:
        elements.append(Paragraph(escape(paragraphe), corps_style))

    lignes = list(lignes or [])
    if entetes:
        donnees_tableau = [
            [Paragraph(f"<b>{escape(str(valeur))}</b>", cellule_style) for valeur in entetes]
        ]
        for ligne in lignes:
            donnees_tableau.append([
                Paragraph(escape(str(valeur if valeur not in (None, '') else '—')), cellule_style)
                for valeur in ligne
            ])
        if not lignes:
            donnees_tableau.append([
                Paragraph("Aucune donnée enregistrée pour cette période.", cellule_style)
            ] + [''] * (len(entetes) - 1))

        largeur_disponible = page_size[0] - doc.leftMargin - doc.rightMargin
        tableau = Table(
            donnees_tableau,
            colWidths=[largeur_disponible / len(entetes)] * len(entetes),
            repeatRows=1,
        )
        tableau.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), palette['couleur_fond_header']),
            ('TEXTCOLOR', (0, 0), (-1, 0), palette['texte_sur_header']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, palette['couleur_fond_tableau']]),
            ('GRID', (0, 0), (-1, -1), 0.5, palette['couleur_bordure']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.extend([Spacer(1, 0.2 * cm), tableau])

    if signature:
        elements.extend([
            Spacer(1, 1.2 * cm),
            Paragraph(
                "Document à faire viser par la direction de l'établissement",
                sous_titre_style,
            ),
            Paragraph("Signature et cachet : ______________________________", sous_titre_style),
        ])

    def dessiner_page(canvas_pdf, document):
        canvas_pdf.saveState()
        try:
            from ecole_moderne.pdf_utils import draw_logo_watermark
            draw_logo_watermark(canvas_pdf, page_size[0], page_size[1], ecole=ecole)
        except Exception:
            pass
        canvas_pdf.setStrokeColor(palette['couleur_bordure'])
        canvas_pdf.line(
            document.leftMargin, 0.8 * cm,
            page_size[0] - document.rightMargin, 0.8 * cm,
        )
        canvas_pdf.setFillColor(palette['couleur_texte_secondaire'])
        canvas_pdf.setFont('Helvetica', 7)
        canvas_pdf.drawString(
            document.leftMargin, 0.5 * cm,
            f"{titre} — généré le {datetime.now():%d/%m/%Y}",
        )
        canvas_pdf.drawRightString(
            page_size[0] - document.rightMargin, 0.5 * cm,
            f"Page {document.page}",
        )
        canvas_pdf.restoreState()

    doc.build(elements, onFirstPage=dessiner_page, onLaterPages=dessiner_page)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    suffixe = slugify(f"{eleve.matricule}-{eleve.nom}") or str(eleve.pk)
    response['Content-Disposition'] = (
        f'attachment; filename="{nom_fichier}_{suffixe}.pdf"'
    )
    return response


def _lettre_recommandation_parent(eleve):
    donnees = _collecter_donnees_scolaires(eleve)
    moyenne = donnees.get('moyenne_generale')
    if moyenne is None:
        niveau = "son sérieux et son implication dans la vie de la classe"
    elif moyenne >= 14:
        niveau = f"ses très bons résultats scolaires, avec une moyenne générale de {moyenne}/20"
    elif moyenne >= 10:
        niveau = f"ses résultats satisfaisants, avec une moyenne générale de {moyenne}/20"
    else:
        niveau = f"les efforts fournis dans sa progression scolaire, avec une moyenne actuelle de {moyenne}/20"

    forces = ', '.join(item['matiere'] for item in donnees.get('forces', [])[:3])
    texte_forces = (
        f"Ses principaux points forts ressortent notamment en {forces}."
        if forces else
        "Son parcours témoigne d'une volonté de progresser et de consolider ses acquis."
    )
    participation = NoteSuivi.objects.filter(
        eleve=eleve,
        annee_scolaire=donnees.get('annee') or '',
        type_note='PARTICIPATION',
    ).aggregate(moyenne=Avg('note'))['moyenne']
    texte_participation = (
        f"Sa participation en classe est évaluée en moyenne à {participation:.2f}/20."
        if participation is not None else
        "L'élève est encouragé à poursuivre une participation régulière en classe."
    )
    paragraphes = [
        "À qui de droit,",
        (
            f"La direction atteste que {eleve.nom_complet}, matricule {eleve.matricule}, "
            f"est régulièrement inscrit(e) en {eleve.classe.nom if eleve.classe else 'classe non précisée'} "
            f"au titre de l'année scolaire {donnees.get('annee') or 'en cours'}."
        ),
        f"Nous recommandons cet(te) élève pour {niveau}. {texte_forces}",
        texte_participation,
        (
            "La présente lettre est établie à la demande de la famille sur la base des "
            "informations enregistrées dans le dossier scolaire de l'élève."
        ),
    ]
    return _reponse_pdf_parent(
        eleve,
        "Lettre de recommandation",
        "Recommandation scolaire individuelle",
        nom_fichier='lettre_recommandation',
        paragraphes=paragraphes,
        signature=True,
    )


def rapport_scolaire_document(request, document_type, format_document='pdf'):
    """Télécharge un document de l'enfant, exclusivement via le token du parent."""
    eleve = _eleve_parent_depuis_token(request)
    classe_note = ClasseNote.objects.filter(
        nom=eleve.classe.nom,
        ecole=eleve.classe.ecole,
        annee_scolaire=eleve.classe.annee_scolaire,
        actif=True,
    ).first() if eleve.classe else None
    annee = eleve.classe.annee_scolaire if eleve.classe else ''

    if document_type == 'carnet-paiement' and format_document == 'pdf':
        paiement = Paiement.objects.filter(
            eleve=eleve,
            annee_scolaire=annee,
            statut='VALIDE',
        ).select_related('eleve__classe', 'eleve__classe__ecole').order_by(
            '-date_paiement', '-pk',
        ).first()
        if not paiement:
            raise Http404("Aucun paiement validé pour cette année scolaire.")
        from paiements.carnet_paiement import generer_carnet_paiement_pdf
        contenu = generer_carnet_paiement_pdf(paiement)
        response = HttpResponse(contenu, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="carnet_paiement_{slugify(eleve.matricule)}.pdf"'
        )
        return response

    if document_type == 'lettre-recommandation' and format_document == 'pdf':
        return _lettre_recommandation_parent(eleve)

    if document_type in ('participation-classe', 'notes-suivi') and format_document == 'pdf':
        suivis = NoteSuivi.objects.filter(
            eleve=eleve,
            annee_scolaire=annee,
        ).select_related('matiere').order_by('date', 'mois', 'matiere__nom')
        if classe_note:
            suivis = suivis.filter(matiere__classe=classe_note)
        if document_type == 'participation-classe':
            suivis = suivis.filter(type_note='PARTICIPATION')
            titre = "Participation en classe"
            introduction = "Relevé des évaluations de participation enregistrées par les enseignants."
            nom_fichier = 'participation_classe'
        else:
            titre = "Notes de suivi"
            introduction = "Relevé des contrôles continus, devoirs, évaluations et participations."
            nom_fichier = 'notes_suivi'
        lignes = [
            (
                suivi.date.strftime('%d/%m/%Y') if suivi.date else '—',
                suivi.get_mois_display(),
                suivi.matiere.nom,
                suivi.get_type_note_display(),
                f"{suivi.note}/20",
                suivi.observation or '—',
            )
            for suivi in suivis
        ]
        return _reponse_pdf_parent(
            eleve, titre, introduction,
            entetes=['Date', 'Mois', 'Matière', 'Type', 'Note', 'Observation'],
            lignes=lignes,
            nom_fichier=nom_fichier,
            paysage=True,
        )

    if document_type == 'vie-scolaire' and format_document == 'pdf':
        activites = ActiviteJournaliere.objects.filter(
            eleve=eleve,
            type_activite__in=['ABSENCE', 'RETARD', 'DISCIPLINE', 'CONVOCATION'],
        ).select_related('classe').order_by('-date')
        if classe_note:
            activites = activites.filter(classe=classe_note)
        lignes = [
            (
                activite.date.strftime('%d/%m/%Y'),
                activite.get_type_activite_display(),
                activite.titre,
                activite.appreciation or '—',
                activite.description or '—',
            )
            for activite in activites
        ]
        return _reponse_pdf_parent(
            eleve,
            "Vie scolaire",
            "Relevé des absences, retards, faits disciplinaires et convocations.",
            entetes=['Date', 'Type', 'Intitulé', 'Appréciation', 'Observation'],
            lignes=lignes,
            nom_fichier='vie_scolaire',
            paysage=True,
        )

    if document_type == 'livret-scolaire' and format_document == 'pdf':
        from .livret_scolaire import _collecter_parcours_eleve, _generer_livret_pdf
        ecole = eleve.classe.ecole if eleve.classe else None
        parcours = _collecter_parcours_eleve(eleve, ecole) if ecole else []
        if parcours:
            pdf_buffer = _generer_livret_pdf(eleve, ecole, parcours)
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="livret_scolaire_{slugify(eleve.matricule)}.pdf"'
            )
            return response
        return _reponse_pdf_parent(
            eleve,
            "Livret scolaire",
            "Aucun historique scolaire détaillé n'est encore enregistré pour cet élève.",
            nom_fichier='livret_scolaire',
        )

    if document_type == 'emploi-du-temps' and format_document in ('pdf', 'excel'):
        if not classe_note:
            raise Http404("Aucun emploi du temps associé à la classe de cet élève.")
        from .views_edt import (
            _generer_emploi_du_temps_excel,
            _generer_emploi_du_temps_pdf,
        )
        if format_document == 'excel':
            return _generer_emploi_du_temps_excel(classe_note)
        return _generer_emploi_du_temps_pdf(classe_note)

    raise Http404("Document non disponible.")


@document_avec_charte(ecole_position=0)
def _generer_recu_paiement_pdf(paiement):
    """Génère le reçu PDF pour un paiement (version publique rapport-scolaire)."""
    from django.db.models import Sum

    buf = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buf, pagesize=A4)

    # Filigrane
    try:
        from ecole_moderne.pdf_utils import draw_logo_watermark
        ecole_obj = paiement.eleve.classe.ecole if paiement.eleve.classe else None
        draw_logo_watermark(c, width, height, ecole=ecole_obj)
    except Exception:
        pass

    left = 40
    top = height - 40
    line_h = 18

    # ── En-tête ──
    c.setFont('Helvetica-Bold', 18)
    c.drawString(left, top, "REÇU DE PAIEMENT")
    top -= 25

    ecole_obj = paiement.eleve.classe.ecole if paiement.eleve.classe else None
    if ecole_obj:
        c.setFont('Helvetica-Bold', 12)
        c.drawString(left, top, ecole_obj.nom)
        top -= 15
        c.setFont('Helvetica', 9)
        if getattr(ecole_obj, 'telephone', None):
            c.drawString(left, top, f"Tél: {ecole_obj.telephone}")
            top -= 12
        if getattr(ecole_obj, 'email', None):
            c.drawString(left, top, f"Email: {ecole_obj.email}")
            top -= 12
    top -= 20

    # ── Informations du reçu ──
    c.setFont('Helvetica-Bold', 11)
    c.drawString(left, top, f"Numéro de reçu: {paiement.numero_recu or 'N/A'}")
    top -= line_h
    c.drawString(left, top, f"Date: {paiement.date_paiement.strftime('%d/%m/%Y')}")
    top -= line_h * 2

    # ── Informations élève ──
    c.setFont('Helvetica-Bold', 12)
    c.drawString(left, top, "ÉLÈVE")
    top -= line_h
    c.setFont('Helvetica', 11)
    c.drawString(left, top, f"Nom: {paiement.eleve.prenom or ''} {paiement.eleve.nom or ''}")
    top -= line_h
    c.drawString(left, top, f"Matricule: {paiement.eleve.matricule or 'N/A'}")
    top -= line_h
    if paiement.eleve.classe:
        c.drawString(left, top, f"Classe: {paiement.eleve.classe.nom}")
        top -= line_h
    top -= line_h

    # ── Détails du paiement ──
    remises_total = paiement.remises.aggregate(total=Sum('montant_remise')).get('total') or 0
    montant_net = paiement.montant - remises_total if remises_total > 0 else paiement.montant

    c.setFont('Helvetica-Bold', 12)
    c.drawString(left, top, "DÉTAILS DU PAIEMENT")
    top -= line_h
    c.setFont('Helvetica', 11)
    c.drawString(left, top, f"Type: {paiement.type_paiement.nom if paiement.type_paiement else 'N/A'}")
    top -= line_h
    c.drawString(left, top, f"Mode: {paiement.mode_paiement.nom if paiement.mode_paiement else 'N/A'}")
    top -= line_h
    c.drawString(left, top, f"Montant: {paiement.montant:,.0f} GNF".replace(",", " "))
    top -= line_h

    if remises_total > 0:
        c.drawString(left, top, f"Remises: -{remises_total:,.0f} GNF".replace(",", " "))
        top -= line_h
        c.setFont('Helvetica-Bold', 11)
        c.drawString(left, top, f"Net payé: {montant_net:,.0f} GNF".replace(",", " "))
        c.setFont('Helvetica', 11)
        top -= line_h

    top -= 10

    # ── Situation financière ──
    try:
        ech = paiement.eleve.echeancier
        total_du = ech.total_du
        total_paye = ech.total_paye
        solde_restant = ech.solde_restant
    except EcheancierPaiement.DoesNotExist:
        total_du = total_paye = solde_restant = Decimal('0')

    if total_du > 0:
        c.setFont('Helvetica-Bold', 12)
        c.drawString(left, top, "SITUATION FINANCIÈRE")
        top -= line_h
        c.setFont('Helvetica', 11)
        c.drawString(left, top, f"Total frais de scolarité: {total_du:,.0f} GNF".replace(",", " "))
        top -= line_h
        c.drawString(left, top, f"Total déjà payé: {total_paye:,.0f} GNF".replace(",", " "))
        top -= line_h
        c.setFont('Helvetica-Bold', 11)
        if solde_restant > 0:
            c.setFillColorRGB(0.8, 0, 0)
            c.drawString(left, top, f"Reste à payer: {solde_restant:,.0f} GNF".replace(",", " "))
            c.setFillColorRGB(0, 0, 0)
        else:
            c.setFillColorRGB(0, 0.5, 0)
            c.drawString(left, top, "Scolarité entièrement payée")
            c.setFillColorRGB(0, 0, 0)
        top -= line_h

    top -= 10
    c.setFont('Helvetica-Bold', 11)
    c.drawString(left, top, f"Statut: {paiement.get_statut_display()}")

    c.showPage()
    c.save()

    buf.seek(0)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    filename = f"recu_{paiement.numero_recu}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ────────────────────────────────────────────────────────────────
# GÉNÉRATION PDF COMPLÈTE
# ────────────────────────────────────────────────────────────────

@document_avec_charte(ecole_position=0)
def _generer_rapport_pdf(eleve):
    """Génère le PDF complet du rapport scolaire pour un élève."""
    buf = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buf, pagesize=A4)
    margin = 1.5 * cm
    col_width = width - 2 * margin

    ecole = eleve.classe.ecole if eleve.classe else None
    annee = eleve.classe.annee_scolaire if eleve.classe else ''

    # ── Filigrane ─────────────────────────────────────────────
    try:
        from ecole_moderne.pdf_utils import draw_logo_watermark
        _watermark = lambda c, w, h: draw_logo_watermark(c, w, h, opacity=0.04, rotate=30, scale=1.5, ecole=ecole)
    except ImportError:
        _watermark = lambda c, w, h: None

    def new_page():
        c.showPage()
        _watermark(c, width, height)
        return height - margin

    _watermark(c, width, height)
    y = height - margin

    # ══════════════════════════════════════════════════════════
    # PAGE 1 : EN-TÊTE + INFORMATIONS ÉLÈVE
    # ══════════════════════════════════════════════════════════
    y = _draw_report_header(c, ecole, eleve, annee, y, margin, width)

    # ── Informations de l'élève ──
    y -= 15
    y = _draw_section_title(c, "INFORMATIONS DE L'ÉLÈVE", y, margin, col_width)
    y -= 5

    infos = [
        ("Matricule", eleve.matricule),
        ("Nom complet", f"{eleve.prenom} {eleve.nom}"),
        ("Sexe", eleve.get_sexe_display()),
        ("Date de naissance", eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else '—'),
        ("Lieu de naissance", eleve.lieu_naissance or '—'),
        ("Classe", eleve.classe.nom if eleve.classe else '—'),
        ("Statut", eleve.get_statut_display()),
    ]
    # Responsables
    for label, resp in [("Responsable principal", eleve.responsable_principal),
                        ("Responsable secondaire", eleve.responsable_secondaire)]:
        if resp:
            infos.append((label, f"{resp.nom_complet} ({resp.get_relation_display()}) — Tél: {resp.telephone}"))

    for label, val in infos:
        if y < margin + 30:
            y = new_page()
        c.setFont('Helvetica-Bold', 9)
        c.drawString(margin, y, f"{label} :")
        c.setFont('Helvetica', 9)
        c.drawString(margin + 140, y, str(val))
        y -= 14

    # ══════════════════════════════════════════════════════════
    # SECTION NOTES – notes mensuelles & compositions
    # ══════════════════════════════════════════════════════════
    y -= 10
    if y < margin + 60:
        y = new_page()
    y = _draw_section_title(c, "NOTES ET RÉSULTATS SCOLAIRES", y, margin, col_width)
    y -= 5

    # Trouver la ClasseNote correspondante
    classe_note = ClasseNote.objects.filter(
        nom=eleve.classe.nom,
        ecole=eleve.classe.ecole,
        annee_scolaire=annee,
        actif=True,
    ).first()

    if classe_note:
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True).order_by('nom')
        if matieres.exists():
            y = _draw_notes_table(c, eleve, classe_note, matieres, y, margin, col_width, new_page)
        else:
            c.setFont('Helvetica-Oblique', 9)
            c.drawString(margin, y, "Aucune matière configurée pour cette classe.")
            y -= 14
    else:
        c.setFont('Helvetica-Oblique', 9)
        c.drawString(margin, y, "Aucune donnée de notes trouvée pour cette classe.")
        y -= 14

    # ── Classements courants ──
    classements = _classements_courants(eleve, classe_note, annee)
    if classements:
        y -= 10
        if y < margin + 60:
            y = new_page()
        y = _draw_section_title(c, "CLASSEMENTS", y, margin, col_width)
        y -= 5
        y = _draw_classements(c, classements, y, margin, col_width, new_page)

    # ══════════════════════════════════════════════════════════
    # SECTION ACTIVITÉS JOURNALIÈRES
    # ══════════════════════════════════════════════════════════
    activites = ActiviteJournaliere.objects.filter(
        eleve=eleve
    ).select_related('classe').prefetch_related('pieces_jointes').order_by('-date')[:50]

    if activites.exists():
        y -= 10
        if y < margin + 60:
            y = new_page()
        y = _draw_section_title(c, "ACTIVITÉS JOURNALIÈRES", y, margin, col_width)
        y -= 5
        y = _draw_activites(c, activites, y, margin, col_width, new_page)

    # ══════════════════════════════════════════════════════════
    # PIED DE PAGE
    # ══════════════════════════════════════════════════════════
    y -= 20
    if y < margin + 40:
        y = new_page()
    c.setFont('Helvetica-Oblique', 7)
    c.setFillColor(colors.grey)
    c.drawString(margin, margin, f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — MySchoolGN")
    c.setFillColor(colors.black)

    c.save()
    buf.seek(0)

    response = HttpResponse(buf, content_type='application/pdf')
    filename = f"rapport_scolaire_{eleve.nom}_{eleve.prenom}_{annee}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ────────────────────────────────────────────────────────────────
# FONCTIONS UTILITAIRES PDF
# ────────────────────────────────────────────────────────────────

def _draw_report_header(c, ecole, eleve, annee, y, margin, page_width):
    """En-tête officiel du rapport."""
    center = page_width / 2

    # Ligne République
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(center, y, "République de Guinée")
    y -= 13
    c.setFont('Helvetica-Oblique', 9)
    c.drawCentredString(center, y, "Travail - Justice - Solidarité")
    y -= 18

    # Nom de l'école
    if ecole:
        c.setFont('Helvetica-Bold', 13)
        c.drawCentredString(center, y, ecole.nom.upper())
        y -= 14
        if ecole.adresse:
            c.setFont('Helvetica', 8)
            c.drawCentredString(center, y, ecole.adresse)
            y -= 11
        if ecole.telephone:
            c.setFont('Helvetica', 8)
            c.drawCentredString(center, y, f"Tél: {ecole.telephone}")
            y -= 11

    # Logo
    if ecole and hasattr(ecole, 'logo') and ecole.logo:
        try:
            logo_path = ecole.logo.path
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                aspect = img.width / img.height
                logo_h = 50
                logo_w = logo_h * aspect
                c.drawImage(ImageReader(logo_path), margin, y, width=logo_w, height=logo_h,
                            preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Titre du document
    y -= 10
    c.setFillColor(couleur_document('couleur_primaire'))
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(center, y, "RAPPORT SCOLAIRE COMPLET")
    y -= 14
    c.setFont('Helvetica', 10)
    c.drawCentredString(center, y, f"Année scolaire : {annee}")
    c.setFillColor(colors.black)
    y -= 6

    # Ligne séparatrice
    c.setStrokeColor(couleur_document('couleur_primaire'))
    c.setLineWidth(1.5)
    c.line(margin, y, page_width - margin, y)
    y -= 6
    return y


def _draw_section_title(c, title, y, margin, col_width):
    """Dessine un titre de section avec fond coloré."""
    c.setFillColor(couleur_document('couleur_primaire'))
    c.roundRect(margin, y - 4, col_width, 18, 3, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(margin + 8, y, title)
    c.setFillColor(colors.black)
    return y - 20


def _draw_notes_table(c, eleve, classe_note, matieres, y, margin, col_width, new_page):
    """Dessine le tableau des notes mensuelles et compositions."""

    # Collecter les données
    MOIS = ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 'MARS', 'AVRIL', 'MAI', 'JUIN']
    MOIS_COURT = ['Oct', 'Nov', 'Déc', 'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin']

    annee = classe_note.annee_scolaire

    rows_data = []
    for mat in matieres:
        row = {'matiere': mat.nom, 'coeff': str(mat.coefficient or ''), 'mois': [], 'compo': []}

        # Notes mensuelles
        notes_m = NoteMensuelle.objects.filter(
            eleve=eleve, matiere=mat, annee_scolaire=annee
        )
        mois_dict = {n.mois: n for n in notes_m}
        for m in MOIS:
            note_obj = mois_dict.get(m)
            if note_obj:
                row['mois'].append('ABS' if note_obj.absent else (str(note_obj.note) if note_obj.note is not None else '—'))
            else:
                row['mois'].append('—')

        # Compositions
        compos = CompositionNote.objects.filter(
            eleve=eleve, matiere=mat, annee_scolaire=annee
        ).order_by('periode')
        for comp in compos:
            row['compo'].append((comp.get_periode_display(), 'ABS' if comp.absent else str(comp.note or '—')))

        rows_data.append(row)

    if not rows_data:
        c.setFont('Helvetica-Oblique', 9)
        c.drawString(margin, y, "Aucune note enregistrée.")
        return y - 14

    # Dessiner un tableau compact
    # En-tête
    header = ['Matière', 'Coeff'] + MOIS_COURT
    # Trouver les périodes de compo qui existent
    compo_periodes = set()
    for rd in rows_data:
        for p, _ in rd['compo']:
            compo_periodes.add(p)
    compo_periodes = sorted(compo_periodes)
    header += [p[:6] for p in compo_periodes]  # Trim to 6 chars

    num_cols = len(header)
    # Calculer largeurs de colonnes
    mat_w = 90
    coeff_w = 30
    note_w = (col_width - mat_w - coeff_w) / max((num_cols - 2), 1)
    col_widths = [mat_w, coeff_w] + [note_w] * (num_cols - 2)

    data = [header]
    for rd in rows_data:
        row_vals = [rd['matiere'][:18], rd['coeff']] + rd['mois']
        # Ajouter les compos dans l'ordre des périodes
        compo_dict = dict(rd['compo'])
        for p in compo_periodes:
            row_vals.append(compo_dict.get(p, '—'))
        data.append(row_vals)

    # Vérifier l'espace disponible
    table_height = len(data) * 14 + 10
    if y - table_height < margin:
        y = new_page()

    # Créer table ReportLab
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BACKGROUND', (0, 0), (-1, 0), couleur_document('couleur_primaire')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, couleur_document('couleur_fond_tableau')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ])
    table.setStyle(style)

    tw, th = table.wrap(col_width, 0)
    if y - th < margin:
        y = new_page()
    table.drawOn(c, margin, y - th)
    y -= th + 5

    return y


def _draw_classements(c, classements, y, margin, col_width, new_page):
    """Dessine le tableau des classements."""
    header = ['Période', 'Moyenne', 'Rang', 'Mention', 'Appréciation']
    data = [header]
    for cl in classements:
        data.append([
            cl.periode.replace('_', ' '),
            str(cl.moyenne_generale),
            cl.rang_formate,
            cl.mention or '—',
            (cl.appreciation or '—')[:40],
        ])

    col_widths = [100, 60, 70, 80, col_width - 310]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), couleur_document('couleur_primaire')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, couleur_document('couleur_fond_tableau')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    tw, th = table.wrap(col_width, 0)
    if y - th < margin:
        y = new_page()
    table.drawOn(c, margin, y - th)
    return y - th - 5


def _draw_activites(c, activites, y, margin, col_width, new_page):
    """Dessine le tableau des activités journalières."""
    TYPE_COLORS = {
        'EVALUATION': couleur_document('couleur_secondaire'),
        'SPORTIVE': colors.HexColor('#388e3c'),
        'CULTURELLE': colors.HexColor('#f57c00'),
        'ARTISTIQUE': colors.HexColor('#7b1fa2'),
        'SORTIE': colors.HexColor('#00838f'),
        'AUTRE': colors.HexColor('#546e7a'),
    }

    header = ['Date', 'Type', 'Titre', 'Appréciation', 'PJ']
    data = [header]
    type_cells = []  # (row, type) pour coloriser

    for i, act in enumerate(activites):
        pj_count = act.pieces_jointes.count()
        data.append([
            act.date.strftime('%d/%m/%Y'),
            act.get_type_activite_display(),
            act.titre[:35],
            act.appreciation[:25] if act.appreciation else '—',
            str(pj_count) if pj_count else '—',
        ])
        type_cells.append((i + 1, act.type_activite))

    col_widths = [65, 75, col_width - 260, 80, 40]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    base_style = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('BACKGROUND', (0, 0), (-1, 0), couleur_document('couleur_accent')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, couleur_document('accent_clair')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]

    # Coloriser les cellules "Type" par type d'activité
    for row_idx, type_act in type_cells:
        color = TYPE_COLORS.get(type_act, colors.grey)
        base_style.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), color))

    table.setStyle(TableStyle(base_style))

    tw, th = table.wrap(col_width, 0)
    if y - th < margin:
        y = new_page()
    table.drawOn(c, margin, y - th)
    return y - th - 5
