"""
Système de Bulletin Intelligent avec Calculs Automatiques
Exports PDF (avec filigrane) et Excel
Conforme au système guinéen (40% cours + 60% composition)
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.db.models import Avg, Count
from decimal import Decimal
import io
from datetime import datetime

# ReportLab pour PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader
from PIL import Image

# OpenPyXL pour Excel
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from eleves.models import Eleve, Classe
from .models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from .calculs import (
    calculer_moyenne_devoirs,
    calculer_moyenne_periode,
    calculer_moyenne_annuelle,
    calculer_moyenne_generale,
    calculer_moyenne_cours_mensuels,
    obtenir_mention,
    obtenir_appreciation,
    calculer_rang,
    formater_rang_intelligent
)
from .classifier import classify
from utilisateurs.utils import filter_by_user_school, user_school
from ecole_moderne.security_decorators import require_school_object


class CalculateurBulletinIntelligent:
    """Calculateur intelligent de bulletin conforme au système guinéen"""
    
    def __init__(self, eleve, classe_note, periode, systeme='TRIMESTRE'):
        self.eleve = eleve
        self.classe_note = classe_note
        self.periode = periode
        self.systeme = systeme
        self.niveau, self.serie, self.section = self._detecter_niveau_intelligent()
        
    def _detecter_niveau_intelligent(self):
        """Détecte intelligemment le niveau, la série et la section à partir du nom de classe"""
        # Essayer d'abord le champ niveau_enseignement si disponible et cohérent
        niveau_db = getattr(self.classe_note, 'niveau_enseignement', None)
        
        # Classification intelligente à partir du nom
        niveau_auto, serie, section = classify(self.classe_note.nom)
        
        # Si le niveau DB existe et est cohérent, on le garde
        if niveau_db in ['PRIMAIRE', 'MATERNELLE']:
            niveau_final = 'PRIMAIRE'
        elif niveau_db in ['COLLEGE', 'LYCEE']:
            niveau_final = 'SECONDAIRE'
        else:
            # Sinon on utilise la détection automatique
            niveau_final = niveau_auto
        
        return niveau_final, serie, section
    
    def _obtenir_mois_periode(self):
        """Retourne les mois d'une période"""
        mapping = {
            'TRIMESTRE_1': ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE'],
            'TRIMESTRE_2': ['JANVIER', 'FEVRIER', 'MARS'],
            'TRIMESTRE_3': ['AVRIL', 'MAI', 'JUIN'],
            'SEMESTRE_1': ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER'],
            'SEMESTRE_2': ['MARS', 'AVRIL', 'MAI', 'JUIN'],
        }
        return mapping.get(self.periode, [])
    
    def calculer_notes_matiere(self, matiere):
        """Calcule les notes d'une matière pour la période"""
        mois_periode = self._obtenir_mois_periode()
        
        # Récupérer les notes mensuelles
        notes_mensuelles = {}
        for mois in mois_periode:
            notes_mois = NoteEleve.objects.filter(
                eleve=self.eleve,
                evaluation__matiere=matiere,
                evaluation__periode=mois,
                evaluation__type_eval='DEVOIR'
            ).values_list('note', flat=True)
            
            if notes_mois:
                notes_mensuelles[mois.lower()] = [Decimal(str(n)) for n in notes_mois if n]
        
        # Récupérer la composition
        composition = None
        compo_obj = NoteEleve.objects.filter(
            eleve=self.eleve,
            evaluation__matiere=matiere,
            evaluation__periode=self.periode,
            evaluation__type_eval='COMPOSITION'
        ).first()
        
        if compo_obj and compo_obj.note:
            composition = Decimal(str(compo_obj.note))
        
        # Calculer selon le niveau
        if self.niveau == 'PRIMAIRE':
            # Primaire : composition uniquement
            moyenne_periode = composition
        else:
            # Secondaire : 40% cours + 60% composition
            moyenne_cours = None
            if notes_mensuelles:
                moyenne_cours = calculer_moyenne_cours_mensuels(notes_mensuelles)
            
            moyenne_periode = calculer_moyenne_periode(
                moyenne_cours,
                composition,
                niveau=self.niveau
            )
        
        return {
            'matiere': matiere.nom,
            'coefficient': matiere.coefficient,
            'notes_mensuelles': notes_mensuelles,
            'composition': composition,
            'moyenne': moyenne_periode
        }
    
    def generer_bulletin(self):
        """Génère le bulletin complet pour la période"""
        # Récupérer toutes les matières
        matieres = MatiereNote.objects.filter(classe=self.classe_note)
        
        # Calculer les notes par matière
        resultats_matieres = []
        notes_pour_generale = {}
        
        for matiere in matieres:
            resultat = self.calculer_notes_matiere(matiere)
            resultats_matieres.append(resultat)
            
            if resultat['moyenne'] is not None:
                notes_pour_generale[matiere.nom] = {
                    'moyenne': resultat['moyenne'],
                    'coefficient': resultat['coefficient']
                }
        
        # Calculer la moyenne générale
        moyenne_generale = calculer_moyenne_generale(
            notes_pour_generale,
            niveau=self.niveau
        )
        
        # Calculer le rang (optionnel - nécessite tous les élèves)
        rang = self._calculer_rang_eleve(moyenne_generale)
        
        return {
            'eleve': f"{self.eleve.prenom} {self.eleve.nom}",
            'classe': self.classe_note.nom,
            'periode': self.periode,
            'niveau': self.niveau,
            'serie': self.serie,
            'section': self.section,
            'matieres': resultats_matieres,
            'moyenne_generale': moyenne_generale,
            'mention': obtenir_mention(moyenne_generale) if moyenne_generale else None,
            'appreciation': obtenir_appreciation(moyenne_generale, self.eleve.prenom) if moyenne_generale else None,
            'rang': rang,
            'total_eleves': Eleve.objects.filter(classe=self.eleve.classe).count()
        }
    
    def _calculer_rang_eleve(self, moyenne_eleve):
        """Calcule le rang de l'élève dans la classe"""
        if not moyenne_eleve:
            return None
        
        # Récupérer tous les élèves de la classe
        eleves = Eleve.objects.filter(classe=self.eleve.classe)
        
        moyennes_eleves = []
        for eleve in eleves:
            calc = CalculateurBulletinIntelligent(
                eleve, 
                self.classe_note, 
                self.periode, 
                self.systeme
            )
            bulletin = calc.generer_bulletin()
            if bulletin['moyenne_generale']:
                moyennes_eleves.append({
                    'eleve_id': eleve.id,
                    'prenom': eleve.prenom,
                    'sexe': eleve.sexe,
                    'moyenne': bulletin['moyenne_generale']
                })
        
        # Calculer les rangs avec accord grammatical
        eleves_classes = calculer_rang(moyennes_eleves)
        
        # Trouver le rang de notre élève
        for e in eleves_classes:
            if e['eleve_id'] == self.eleve.id:
                return e['rang']
        
        return None


def generer_pdf_avec_filigrane(bulletin_data, logo_path=None):
    """Génère un PDF avec le logo en filigrane"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Dessiner le filigrane (logo en transparence)
    if logo_path:
        try:
            # Charger l'image
            img = Image.open(logo_path)
            
            # Créer un ImageReader
            img_reader = ImageReader(logo_path)
            
            # Dessiner en filigrane (centré, grande taille, opacité réduite)
            c.saveState()
            c.setFillAlpha(0.1)  # Transparence 10%
            
            # Taille du filigrane
            filigrane_width = 15 * cm
            filigrane_height = 15 * cm
            
            # Position centrée
            x = (width - filigrane_width) / 2
            y = (height - filigrane_height) / 2
            
            c.drawImage(img_reader, x, y, width=filigrane_width, height=filigrane_height, 
                       preserveAspectRatio=True, mask='auto')
            c.restoreState()
        except Exception as e:
            print(f"Erreur filigrane: {e}")
    
    # En-tête
    y = height - 2*cm
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, y, "RÉPUBLIQUE DE GUINÉE")
    
    y -= 0.5*cm
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width/2, y, "Travail - Justice - Solidarité")
    
    y -= 1*cm
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, y, "BULLETIN DE NOTES")
    
    # Informations élève
    y -= 1.5*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, f"Élève: {bulletin_data['eleve']}")
    
    y -= 0.7*cm
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, y, f"Classe: {bulletin_data['classe']}")
    c.drawString(12*cm, y, f"Période: {bulletin_data['periode']}")
    
    # Tableau des notes
    y -= 1.5*cm
    
    # Préparer les données du tableau
    data = [['Matière', 'Coef.', 'Moy. Cours', 'Composition', 'Moyenne', 'Points']]
    
    for matiere in bulletin_data['matieres']:
        moy_cours = '-'
        if matiere['notes_mensuelles']:
            notes_list = []
            for notes in matiere['notes_mensuelles'].values():
                notes_list.extend(notes)
            if notes_list:
                moy_cours = f"{sum(notes_list) / len(notes_list):.2f}"
        
        composition = f"{matiere['composition']:.2f}" if matiere['composition'] else '-'
        moyenne = f"{matiere['moyenne']:.2f}" if matiere['moyenne'] else '-'
        points = f"{matiere['moyenne'] * matiere['coefficient']:.2f}" if matiere['moyenne'] else '-'
        
        data.append([
            matiere['matiere'],
            str(matiere['coefficient']),
            moy_cours,
            composition,
            moyenne,
            points
        ])
    
    # Créer le tableau
    table = Table(data, colWidths=[6*cm, 1.5*cm, 2*cm, 2*cm, 2*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ]))
    
    # Dessiner le tableau
    table.wrapOn(c, width, height)
    table.drawOn(c, 2*cm, y - len(data) * 0.6*cm)
    
    # Résultats
    y = y - len(data) * 0.6*cm - 1.5*cm
    
    c.setFont("Helvetica-Bold", 12)
    if bulletin_data['moyenne_generale']:
        c.drawString(2*cm, y, f"Moyenne Générale: {bulletin_data['moyenne_generale']:.2f}/20")
        
        # Afficher le rang correctement formaté
        rang_affiche = bulletin_data['rang'] if bulletin_data['rang'] else "-"
        c.drawString(10*cm, y, f"Rang: {rang_affiche}")
        
        y -= 0.7*cm
        c.drawString(2*cm, y, f"Mention: {bulletin_data['mention']}")
        
        y -= 0.7*cm
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(2*cm, y, f"Appréciation: {bulletin_data['appreciation']}")
    
    # Signatures
    y -= 2*cm
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, y, "Directeur")
    c.drawString(10*cm, y, "Enseignant")
    c.drawString(15*cm, y, "Parent")
    
    # Pied de page
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width/2, 1*cm, 
                       f"Bulletin généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    c.drawCentredString(width/2, 0.5*cm, 
                       "Système de calcul: 40% cours + 60% composition")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer


def generer_excel(bulletin_data):
    """Génère un fichier Excel du bulletin"""
    if not EXCEL_AVAILABLE:
        return None
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Bulletin"
    
    # Styles
    header_font = Font(bold=True, size=14, color="FFFFFF")
    header_fill = PatternFill(start_color="1e40af", end_color="1e40af", fill_type="solid")
    
    title_font = Font(bold=True, size=16)
    subtitle_font = Font(bold=True, size=12)
    
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # En-tête
    ws.merge_cells('A1:F1')
    ws['A1'] = "BULLETIN DE NOTES"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center')
    
    # Informations
    ws['A3'] = f"Élève: {bulletin_data['eleve']}"
    ws['A3'].font = subtitle_font
    
    ws['A4'] = f"Classe: {bulletin_data['classe']}"
    ws['D4'] = f"Période: {bulletin_data['periode']}"
    
    # En-têtes du tableau
    row = 6
    headers = ['Matière', 'Coefficient', 'Moy. Cours', 'Composition', 'Moyenne', 'Points']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border
    
    # Données
    row += 1
    for matiere in bulletin_data['matieres']:
        # Moyenne cours
        moy_cours = ''
        if matiere['notes_mensuelles']:
            notes_list = []
            for notes in matiere['notes_mensuelles'].values():
                notes_list.extend(notes)
            if notes_list:
                moy_cours = float(sum(notes_list) / len(notes_list))
        
        composition = float(matiere['composition']) if matiere['composition'] else ''
        moyenne = float(matiere['moyenne']) if matiere['moyenne'] else ''
        points = float(matiere['moyenne'] * matiere['coefficient']) if matiere['moyenne'] else ''
        
        ws.cell(row=row, column=1, value=matiere['matiere']).border = border
        ws.cell(row=row, column=2, value=matiere['coefficient']).border = border
        ws.cell(row=row, column=3, value=moy_cours).border = border
        ws.cell(row=row, column=4, value=composition).border = border
        ws.cell(row=row, column=5, value=moyenne).border = border
        ws.cell(row=row, column=6, value=points).border = border
        
        row += 1
    
    # Résultats
    row += 2
    if bulletin_data['moyenne_generale']:
        ws.cell(row=row, column=1, value="Moyenne Générale:").font = subtitle_font
        ws.cell(row=row, column=2, value=float(bulletin_data['moyenne_generale']))
        
        row += 1
        ws.cell(row=row, column=1, value="Rang:").font = subtitle_font
        rang_affiche = bulletin_data['rang'] if bulletin_data['rang'] else "-"
        ws.cell(row=row, column=2, value=rang_affiche)
        
        row += 1
        ws.cell(row=row, column=1, value="Mention:").font = subtitle_font
        ws.cell(row=row, column=2, value=bulletin_data['mention'])
        
        row += 1
        ws.cell(row=row, column=1, value="Appréciation:").font = subtitle_font
        ws.merge_cells(f'B{row}:F{row}')
        ws.cell(row=row, column=2, value=bulletin_data['appreciation'])
    
    # Ajuster les largeurs
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    
    # Sauvegarder dans un buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer


@login_required
@require_school_object(model=Eleve, pk_kwarg='eleve_id', field_path='classe__ecole')
def bulletin_intelligent_view(request, eleve_id, classe_note_id, periode):
    """Vue pour afficher le bulletin intelligent"""
    eleve = get_object_or_404(Eleve, pk=eleve_id)
    classe_note = get_object_or_404(ClasseNote, pk=classe_note_id)
    
    # Déterminer le système
    systeme = 'SEMESTRE' if 'SEMESTRE' in periode else 'TRIMESTRE'
    
    # Calculer le bulletin
    calculateur = CalculateurBulletinIntelligent(eleve, classe_note, periode, systeme)
    bulletin_data = calculateur.generer_bulletin()
    
    return render(request, 'notes/bulletin_intelligent.html', {
        'bulletin': bulletin_data,
        'eleve': eleve,
        'classe_note': classe_note,
        'periode': periode
    })


@login_required
@require_school_object(model=Eleve, pk_kwarg='eleve_id', field_path='classe__ecole')
def bulletin_intelligent_pdf(request, eleve_id, classe_note_id, periode):
    """Génère le bulletin en PDF avec filigrane"""
    eleve = get_object_or_404(Eleve, pk=eleve_id)
    classe_note = get_object_or_404(ClasseNote, pk=classe_note_id)
    
    # Déterminer le système
    systeme = 'SEMESTRE' if 'SEMESTRE' in periode else 'TRIMESTRE'
    
    # Calculer le bulletin
    calculateur = CalculateurBulletinIntelligent(eleve, classe_note, periode, systeme)
    bulletin_data = calculateur.generer_bulletin()
    
    # Chemin du logo
    ecole = eleve.classe.ecole
    logo_path = None
    if hasattr(ecole, 'logo') and ecole.logo:
        logo_path = ecole.logo.path
    
    # Générer le PDF
    pdf_buffer = generer_pdf_avec_filigrane(bulletin_data, logo_path)
    
    # Réponse HTTP
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"bulletin_{eleve.nom}_{eleve.prenom}_{periode}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
@require_school_object(model=Eleve, pk_kwarg='eleve_id', field_path='classe__ecole')
def bulletin_intelligent_excel(request, eleve_id, classe_note_id, periode):
    """Génère le bulletin en Excel"""
    if not EXCEL_AVAILABLE:
        return HttpResponse("Excel export n'est pas disponible", status=500)
    
    eleve = get_object_or_404(Eleve, pk=eleve_id)
    classe_note = get_object_or_404(ClasseNote, pk=classe_note_id)
    
    # Déterminer le système
    systeme = 'SEMESTRE' if 'SEMESTRE' in periode else 'TRIMESTRE'
    
    # Calculer le bulletin
    calculateur = CalculateurBulletinIntelligent(eleve, classe_note, periode, systeme)
    bulletin_data = calculateur.generer_bulletin()
    
    # Générer l'Excel
    excel_buffer = generer_excel(bulletin_data)
    
    if not excel_buffer:
        return HttpResponse("Erreur lors de la génération Excel", status=500)
    
    # Réponse HTTP
    response = HttpResponse(
        excel_buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"bulletin_{eleve.nom}_{eleve.prenom}_{periode}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
