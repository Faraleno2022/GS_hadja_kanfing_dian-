"""
Bulletin semestriel amélioré avec statistiques, analyse et recommandations
pour les classes du secondaire (Collège/Lycée).
"""

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import statistics
from datetime import datetime

from eleves.models import Eleve, Classe
from notes.models import MatiereClasse
from notes.views import (
    semester_avg, semester_course_avg, semester_compo_avg, 
    monthly_avg, _draw_school_header
)
from ecole_moderne.security_decorators import require_school_object
from utilisateurs.utils import filter_by_user_school


def analyser_performance_eleve(eleve, matieres, lignes, moyenne_generale, classe, semestre, annee_scolaire):
    """
    Analyse les performances d'un élève et génère des statistiques, points forts/faibles et recommandations.
    
    Args:
        eleve: Instance Eleve
        matieres: QuerySet des matières de la classe
        lignes: Liste des dictionnaires contenant les moyennes par matière
        moyenne_generale: Decimal de la moyenne générale de l'élève
        classe: Instance Classe
        semestre: int (1 ou 2)
        annee_scolaire: str
    
    Returns:
        dict contenant:
            - statistiques: dict avec rang, moyenne_classe, ecart_type, percentile
            - points_forts: list de dict {matiere, moyenne, ecart}
            - points_faibles: list de dict {matiere, moyenne, ecart}
            - recommandations: list de str
    """
    
    # 1. Calculer les moyennes de tous les élèves de la classe
    eleves_classe = Eleve.objects.filter(classe=classe, statut='actif')
    moyennes_classe = []
    
    for e in eleves_classe:
        somme_moyennes_coef = Decimal('0')
        somme_coef_matieres = Decimal('0')
        
        for mat in matieres:
            moy_sem = semester_avg(e, mat, annee_scolaire, semestre, mode='weighted')
            if moy_sem is not None:
                somme_moyennes_coef += moy_sem * Decimal(mat.coefficient or 1)
                somme_coef_matieres += Decimal(mat.coefficient or 1)
        
        if somme_coef_matieres > 0:
            mg = (somme_moyennes_coef / somme_coef_matieres).quantize(Decimal('0.01'))
            moyennes_classe.append({'eleve_id': e.id, 'moyenne': float(mg)})
    
    # 2. Calculer les statistiques de classe
    moyennes_values = [m['moyenne'] for m in moyennes_classe]
    
    statistiques = {
        'rang': None,
        'total_eleves': len(moyennes_classe),
        'moyenne_classe': None,
        'ecart_type': None,
        'percentile': None,
        'meilleure_moyenne': None,
        'plus_basse_moyenne': None,
    }
    
    if moyennes_values:
        # Trier pour obtenir le rang
        moyennes_classe_sorted = sorted(moyennes_classe, key=lambda x: x['moyenne'], reverse=True)
        for idx, m in enumerate(moyennes_classe_sorted, start=1):
            if m['eleve_id'] == eleve.id:
                statistiques['rang'] = idx
                break
        
        # Statistiques descriptives
        statistiques['moyenne_classe'] = round(statistics.mean(moyennes_values), 2)
        if len(moyennes_values) > 1:
            statistiques['ecart_type'] = round(statistics.stdev(moyennes_values), 2)
        statistiques['meilleure_moyenne'] = round(max(moyennes_values), 2)
        statistiques['plus_basse_moyenne'] = round(min(moyennes_values), 2)
        
        # Percentile
        if moyenne_generale and statistiques['rang']:
            statistiques['percentile'] = round((1 - (statistiques['rang'] - 1) / len(moyennes_values)) * 100, 1)
    
    # 3. Calculer les moyennes de classe par matière
    moyennes_classe_par_matiere = {}
    for mat in matieres:
        moyennes_mat = []
        for e in eleves_classe:
            moy_sem = semester_avg(e, mat, annee_scolaire, semestre, mode='weighted')
            if moy_sem is not None:
                moyennes_mat.append(float(moy_sem))
        
        if moyennes_mat:
            moyennes_classe_par_matiere[mat.id] = round(statistics.mean(moyennes_mat), 2)
    
    # 4. Identifier les points forts et faibles
    points_forts = []
    points_faibles = []
    
    for ligne in lignes:
        if ligne['moy_sem'] is None:
            continue
        
        # Trouver la matière correspondante
        mat = next((m for m in matieres if m.nom == ligne['matiere']), None)
        if not mat:
            continue
        
        moyenne_mat_eleve = float(ligne['moy_sem'])
        moyenne_mat_classe = moyennes_classe_par_matiere.get(mat.id)
        
        if moyenne_mat_classe is None:
            continue
        
        ecart = round(moyenne_mat_eleve - moyenne_mat_classe, 2)
        
        # Point fort : au-dessus de la moyenne de classe ET >= 12
        if ecart > 0 and moyenne_mat_eleve >= 12:
            points_forts.append({
                'matiere': ligne['matiere'],
                'moyenne': moyenne_mat_eleve,
                'moyenne_classe': moyenne_mat_classe,
                'ecart': ecart
            })
        
        # Point faible : en-dessous de la moyenne de classe OU < 10
        if ecart < -1 or moyenne_mat_eleve < 10:
            points_faibles.append({
                'matiere': ligne['matiere'],
                'moyenne': moyenne_mat_eleve,
                'moyenne_classe': moyenne_mat_classe,
                'ecart': ecart
            })
    
    # Trier par écart (meilleurs points forts en premier, pires points faibles en premier)
    points_forts.sort(key=lambda x: x['ecart'], reverse=True)
    points_faibles.sort(key=lambda x: x['ecart'])
    
    # 5. Générer des recommandations
    recommandations = []
    
    if moyenne_generale:
        mg = float(moyenne_generale)
        
        # Recommandations basées sur la moyenne générale
        if mg >= 16:
            recommandations.append("Excellent travail ! Continuez sur cette lancée et visez l'excellence dans toutes les matières.")
        elif mg >= 14:
            recommandations.append("Très bon niveau général. Concentrez-vous sur les matières à améliorer pour viser l'excellence.")
        elif mg >= 12:
            recommandations.append("Bon niveau. Travaillez davantage les matières faibles pour progresser.")
        elif mg >= 10:
            recommandations.append("Résultats passables. Un effort supplémentaire est nécessaire dans plusieurs matières.")
        else:
            recommandations.append("Résultats insuffisants. Un travail régulier et sérieux est indispensable pour progresser.")
        
        # Recommandations basées sur le rang
        if statistiques['rang'] and statistiques['total_eleves']:
            if statistiques['rang'] <= 3:
                recommandations.append(f"Félicitations pour votre {statistiques['rang']}{'er' if statistiques['rang'] == 1 else 'ème'} rang ! Maintenez vos efforts.")
            elif statistiques['rang'] <= statistiques['total_eleves'] * 0.25:
                recommandations.append("Vous faites partie du premier quart de la classe. Continuez vos efforts pour progresser encore.")
            elif statistiques['rang'] >= statistiques['total_eleves'] * 0.75:
                recommandations.append("Vous êtes dans le dernier quart de la classe. Un travail régulier et sérieux est nécessaire.")
    
    # Recommandations basées sur les points faibles
    if points_faibles:
        matieres_faibles = [pf['matiere'] for pf in points_faibles[:3]]
        if len(matieres_faibles) == 1:
            recommandations.append(f"Concentrez vos efforts sur {matieres_faibles[0]}.")
        elif len(matieres_faibles) == 2:
            recommandations.append(f"Travaillez davantage {matieres_faibles[0]} et {matieres_faibles[1]}.")
        else:
            recommandations.append(f"Renforcez vos bases en {', '.join(matieres_faibles[:-1])} et {matieres_faibles[-1]}.")
    
    # Recommandations basées sur les points forts
    if points_forts:
        matieres_fortes = [pf['matiere'] for pf in points_forts[:2]]
        if matieres_fortes:
            recommandations.append(f"Excellents résultats en {' et '.join(matieres_fortes)}. Continuez ainsi !")
    
    # Recommandation sur la régularité
    if lignes:
        moyennes_non_nulles = [l['moy_sem'] for l in lignes if l['moy_sem'] is not None]
        if moyennes_non_nulles and len(moyennes_non_nulles) > 1:
            ecart_type_eleve = statistics.stdev([float(m) for m in moyennes_non_nulles])
            if ecart_type_eleve > 3:
                recommandations.append("Vos résultats sont irréguliers. Travaillez toutes les matières de manière équilibrée.")
    
    return {
        'statistiques': statistiques,
        'points_forts': points_forts[:5],  # Top 5
        'points_faibles': points_faibles[:5],  # Top 5
        'recommandations': recommandations,
        'moyennes_classe_par_matiere': moyennes_classe_par_matiere
    }


@login_required
@require_school_object(model=Eleve, pk_kwarg='eleve_id', field_path='classe__ecole')
def bulletin_semestre_ameliore_pdf(request, classe_id: int, eleve_id: int, semestre: int = 1):
    """
    Génère un bulletin semestriel amélioré (S1 ou S2) pour Collège/Lycée.
    Inclut : notes mensuelles, composition, statistiques, analyse et recommandations.
    """
    # Sécuriser classe/élève
    classe = get_object_or_404(filter_by_user_school(Classe.objects.select_related('ecole'), request.user, 'ecole'), pk=classe_id)
    eleve = get_object_or_404(filter_by_user_school(Eleve.objects.select_related('classe', 'classe__ecole'), request.user, 'classe__ecole'), pk=eleve_id, classe=classe)

    # Matières actives
    matieres = MatiereClasse.objects.filter(classe=classe, ecole=classe.ecole, actif=True).order_by('nom')
    annee_scolaire = getattr(classe, 'annee_scolaire', None)

    # Déterminer les mois du semestre
    if semestre == 1:
        mois_semestre = [10, 11, 12]  # Octobre, Novembre, Décembre
        mois_labels = ['Oct', 'Nov', 'Déc']
    else:
        mois_semestre = [3, 4, 5]  # Mars, Avril, Mai
        mois_labels = ['Mars', 'Avr', 'Mai']

    lignes = []
    somme_moyennes_coef = Decimal('0')
    somme_coef_matieres = Decimal('0')
    
    for mat in matieres:
        # Moyennes mensuelles
        moyennes_mensuelles = []
        for mois in mois_semestre:
            moy_mois = monthly_avg(eleve, mat, annee_scolaire, mois, mode='weighted')
            moyennes_mensuelles.append(moy_mois)
        
        # Moyenne des cours (semestre)
        moy_cours = semester_course_avg(eleve, mat, annee_scolaire, semestre)
        
        # Moyenne composition (semestre)
        moy_compo = semester_compo_avg(eleve, mat, annee_scolaire, semestre)
        
        # Moyenne semestrielle
        moy_sem = semester_avg(eleve, mat, annee_scolaire, semestre, mode='weighted')
        
        if moy_sem is not None:
            somme_moyennes_coef += moy_sem * Decimal(mat.coefficient or 1)
            somme_coef_matieres += Decimal(mat.coefficient or 1)
        
        lignes.append({
            'matiere': mat.nom,
            'coef_matiere': mat.coefficient,
            'moyennes_mensuelles': moyennes_mensuelles,
            'moy_cours': moy_cours,
            'moy_compo': moy_compo,
            'moy_sem': moy_sem,
        })

    moyenne_generale = (somme_moyennes_coef / somme_coef_matieres).quantize(Decimal('0.01')) if somme_coef_matieres > 0 else None

    # Analyse des performances
    analyse = analyser_performance_eleve(eleve, matieres, lignes, moyenne_generale, classe, semestre, annee_scolaire)

    # PDF
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.lib.units import cm
    except Exception:
        return HttpResponse("ReportLab requis (pip install reportlab)", status=500)

    response = HttpResponse(content_type='application/pdf')
    filename = f"bulletin_semestre{semestre}_ameliore_{eleve.matricule}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    c = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Filigrane
    try:
        from ecole_moderne.pdf_utils import draw_logo_watermark
        draw_logo_watermark(c, width, height, opacity=0.04, rotate=30, scale=1.5, ecole=getattr(classe, 'ecole', None))
    except Exception:
        pass

    margin = 1.5 * cm
    y = height - margin

    # En-tête
    if getattr(classe, 'ecole', None):
        y = _draw_school_header(c, classe.ecole, y_start=y, margin=margin, page_width=width)
    
    y -= 15
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(width/2, y, f"Bulletin Semestriel — Semestre {semestre}")
    y -= 30
    
    c.setFont('Helvetica', 11)
    c.drawString(margin, y, f"Élève: {eleve.nom} {eleve.prenom}  (Matricule: {eleve.matricule or '-'})")
    y -= 14
    c.drawString(margin, y, f"Classe: {classe.nom} — Année: {annee_scolaire or ''}")
    y -= 10
    c.setFillColor(colors.grey)
    c.rect(margin, y-2, width-2*margin, 1, fill=1, stroke=0)
    c.setFillColor(colors.black)
    y -= 20

    # Tableau des notes
    c.setFont('Helvetica-Bold', 10)
    headers = ["Matière", "Coef."] + mois_labels + ["Cours", "Compo", f"Moy. S{semestre}"]
    colw = [5*cm, 1.2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.8*cm]
    
    x = margin
    for i, htxt in enumerate(headers):
        c.drawString(x, y, htxt)
        x += colw[i]
    y -= 12
    c.setFillColor(colors.lightgrey)
    c.rect(margin, y-2, width-2*margin, 1, fill=1, stroke=0)
    c.setFillColor(colors.black)
    y -= 10

    c.setFont('Helvetica', 9)
    for row in lignes:
        if y < margin + 180:  # Espace pour statistiques et recommandations
            c.showPage()
            try:
                from ecole_moderne.pdf_utils import draw_logo_watermark
                draw_logo_watermark(c, width, height, opacity=0.04, rotate=30, scale=1.5, ecole=getattr(classe, 'ecole', None))
            except Exception:
                pass
            y = height - margin
        
        x = margin
        c.drawString(x, y, str(row['matiere'])[:30])
        x += colw[0]
        c.drawString(x, y, str(row['coef_matiere']))
        x += colw[1]
        
        # Moyennes mensuelles
        for moy_mois in row['moyennes_mensuelles']:
            c.drawString(x, y, '-' if moy_mois is None else f"{moy_mois}")
            x += colw[2]
        
        c.drawString(x, y, '-' if row['moy_cours'] is None else f"{row['moy_cours']}")
        x += colw[5]
        c.drawString(x, y, '-' if row['moy_compo'] is None else f"{row['moy_compo']}")
        x += colw[6]
        
        # Moyenne semestrielle en gras si >= 12
        if row['moy_sem'] is not None and row['moy_sem'] >= 12:
            c.setFont('Helvetica-Bold', 9)
        c.drawString(x, y, '-' if row['moy_sem'] is None else f"{row['moy_sem']}")
        c.setFont('Helvetica', 9)
        
        y -= 12

    # Séparateur
    y -= 8
    c.setFillColor(colors.grey)
    c.rect(margin, y-2, width-2*margin, 1, fill=1, stroke=0)
    c.setFillColor(colors.black)
    y -= 15

    # Moyenne générale et statistiques
    c.setFont('Helvetica-Bold', 12)
    c.drawString(margin, y, f"Moyenne générale: {moyenne_generale if moyenne_generale is not None else '-'} / 20")
    
    stats = analyse['statistiques']
    if stats['rang']:
        c.setFont('Helvetica', 11)
        y -= 14
        c.drawString(margin, y, f"Rang: {stats['rang']} / {stats['total_eleves']}")
        
        if stats['percentile']:
            c.drawString(margin + 6*cm, y, f"Percentile: {stats['percentile']}%")
        
        y -= 12
        if stats['moyenne_classe']:
            c.drawString(margin, y, f"Moyenne de classe: {stats['moyenne_classe']} / 20")
        
        if stats['ecart_type']:
            c.drawString(margin + 6*cm, y, f"Écart-type: {stats['ecart_type']}")

    y -= 20

    # Points forts et faibles
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(colors.HexColor('#059669'))
    c.drawString(margin, y, "✓ Points forts:")
    c.setFillColor(colors.black)
    y -= 12
    
    c.setFont('Helvetica', 9)
    if analyse['points_forts']:
        for pf in analyse['points_forts'][:3]:
            c.drawString(margin + 0.5*cm, y, f"• {pf['matiere']}: {pf['moyenne']}/20 (+{pf['ecart']} vs classe)")
            y -= 10
    else:
        c.setFillColor(colors.grey)
        c.drawString(margin + 0.5*cm, y, "Aucun point fort identifié")
        c.setFillColor(colors.black)
        y -= 10
    
    y -= 8
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(colors.HexColor('#DC2626'))
    c.drawString(margin, y, "⚠ Points faibles:")
    c.setFillColor(colors.black)
    y -= 12
    
    c.setFont('Helvetica', 9)
    if analyse['points_faibles']:
        for pf in analyse['points_faibles'][:3]:
            c.drawString(margin + 0.5*cm, y, f"• {pf['matiere']}: {pf['moyenne']}/20 ({pf['ecart']:+.2f} vs classe)")
            y -= 10
    else:
        c.setFillColor(colors.grey)
        c.drawString(margin + 0.5*cm, y, "Aucun point faible identifié")
        c.setFillColor(colors.black)
        y -= 10

    y -= 12

    # Recommandations
    c.setFont('Helvetica-Bold', 11)
    c.setFillColor(colors.HexColor('#2563EB'))
    c.drawString(margin, y, "📋 Recommandations:")
    c.setFillColor(colors.black)
    y -= 12
    
    c.setFont('Helvetica', 9)
    for reco in analyse['recommandations']:
        # Wrapper le texte si trop long
        max_width = width - 2*margin - 1*cm
        from reportlab.pdfbase import pdfmetrics
        if pdfmetrics.stringWidth(reco, 'Helvetica', 9) > max_width:
            words = reco.split()
            line = ""
            for word in words:
                test = (line + " " + word).strip()
                if pdfmetrics.stringWidth(test, 'Helvetica', 9) <= max_width:
                    line = test
                else:
                    if line:
                        c.drawString(margin + 0.5*cm, y, f"• {line}")
                        y -= 10
                    line = word
            if line:
                c.drawString(margin + 0.5*cm, y, f"• {line}")
                y -= 10
        else:
            c.drawString(margin + 0.5*cm, y, f"• {reco}")
            y -= 10

    # Signatures
    y -= 15
    c.setFont('Helvetica', 10)
    sig_y = margin + 50
    c.drawString(margin, sig_y, "Prof. principal:")
    c.line(margin + 100, sig_y-2, margin + 220, sig_y-2)
    c.drawString(margin + 250, sig_y, "Chef d'établ.:")
    c.line(margin + 340, sig_y-2, margin + 460, sig_y-2)
    c.drawString(margin, sig_y - 25, "Parent/Tuteur:")
    c.line(margin + 120, sig_y-27, margin + 280, sig_y-27)

    # Pied de page
    c.setFont('Helvetica-Oblique', 8)
    c.setFillColor(colors.darkgrey)
    c.drawString(margin, margin/2, f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.showPage()
    c.save()
    return response
