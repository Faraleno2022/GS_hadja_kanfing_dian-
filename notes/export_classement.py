"""
Module pour exporter les classements par classe
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from decimal import Decimal
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .models import ClasseNote, MatiereNote, NoteMensuelle, CompositionNote
from eleves.models import Eleve, Classe as ClasseEleve


def formater_rang(rang, sexe):
    """
    Formate le rang avec l'accord grammatical selon le sexe
    
    Args:
        rang: Le numéro de rang (int ou str)
        sexe: 'M' pour masculin, 'F' pour féminin
    
    Returns:
        str: Le rang formaté (ex: "1er", "1ère", "2ème", "3ème", etc.)
    """
    if rang == '-' or rang is None:
        return '-'
    
    rang_num = int(rang)
    
    # Cas spécial pour le rang 1
    if rang_num == 1:
        if sexe == 'F':
            return "1ère"
        else:
            return "1er"
    
    # Pour tous les autres rangs, on utilise "ème"
    return f"{rang_num}ème"


@login_required
def exporter_classement_classe(request):
    """
    Exporter le classement d'une classe avec rang, nom complet, matricule et moyenne
    Format: Excel (.xlsx)
    """
    # Récupérer les paramètres
    classe_id = request.GET.get('classe_id')
    matiere_id = request.GET.get('matiere_id')
    type_note = request.GET.get('type_note', 'mensuelle')
    periode = request.GET.get('periode', '')
    
    if not classe_id:
        return HttpResponse("Classe non spécifiée", status=400)
    
    # Récupérer la classe
    classe_note = get_object_or_404(ClasseNote, pk=classe_id)
    
    # Récupérer la classe élève correspondante
    try:
        classe_eleve = ClasseEleve.objects.filter(
            nom=classe_note.nom,
            annee_scolaire=classe_note.annee_scolaire,
            ecole=classe_note.ecole
        ).first()
        
        if not classe_eleve:
            return HttpResponse("Classe élève non trouvée", status=404)
        
        # Récupérer les élèves actifs
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('nom', 'prenom')
    except Exception as e:
        return HttpResponse(f"Erreur lors de la récupération des élèves: {str(e)}", status=500)
    
    # Préparer les données de classement
    if matiere_id:
        classement_data, titre_export = _generer_classement_matiere(
            eleves, classe_note, matiere_id, type_note, periode
        )
    else:
        classement_data, titre_export = _generer_classement_general(
            eleves, classe_note, type_note, periode
        )
    
    # Créer le fichier Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Classement"
    
    # Styles
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=12)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Titre
    ws.merge_cells('A1:D1')
    title_cell = ws['A1']
    title_cell.value = titre_export
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30
    
    # Date d'export
    ws.merge_cells('A2:D2')
    date_cell = ws['A2']
    date_cell.value = f"Exporté le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    date_cell.alignment = Alignment(horizontal='center')
    date_cell.font = Font(italic=True, size=10)
    ws.row_dimensions[2].height = 20
    
    # En-têtes
    headers = ['Rang', 'Matricule', 'Nom Complet', 'Moyenne /20']
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    ws.row_dimensions[4].height = 25
    
    # Données
    for row_num, eleve_data in enumerate(classement_data, 5):
        # Rang
        rang_cell = ws.cell(row=row_num, column=1)
        rang_value = eleve_data['rang']
        sexe = eleve_data.get('sexe', 'M')  # Par défaut masculin si non spécifié
        
        # Formater le rang avec l'accord grammatical
        rang_formate = formater_rang(rang_value, sexe)
        
        if rang_value == 1:
            rang_cell.value = f"🥇 {rang_formate}"
            rang_cell.fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
        elif rang_value == 2:
            rang_cell.value = f"🥈 {rang_formate}"
            rang_cell.fill = PatternFill(start_color="E7F3FF", end_color="E7F3FF", fill_type="solid")
        elif rang_value == 3:
            rang_cell.value = f"🥉 {rang_formate}"
            rang_cell.fill = PatternFill(start_color="FFE7D9", end_color="FFE7D9", fill_type="solid")
        else:
            rang_cell.value = rang_formate
        
        rang_cell.alignment = Alignment(horizontal='center', vertical='center')
        rang_cell.border = border
        rang_cell.font = Font(bold=True, size=11)
        
        # Matricule
        matricule_cell = ws.cell(row=row_num, column=2)
        matricule_cell.value = eleve_data['matricule']
        matricule_cell.alignment = Alignment(horizontal='center', vertical='center')
        matricule_cell.border = border
        
        # Nom complet
        nom_cell = ws.cell(row=row_num, column=3)
        nom_cell.value = eleve_data['nom_complet']
        nom_cell.alignment = Alignment(horizontal='left', vertical='center')
        nom_cell.border = border
        nom_cell.font = Font(size=11)
        
        # Moyenne
        moyenne_cell = ws.cell(row=row_num, column=4)
        if eleve_data['moyenne'] is not None:
            moyenne_cell.value = eleve_data['moyenne']
            moyenne_cell.number_format = '0.00'
            
            # Coloration selon la moyenne
            moyenne_val = eleve_data['moyenne']
            if moyenne_val >= 16:
                moyenne_cell.fill = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
            elif moyenne_val >= 14:
                moyenne_cell.fill = PatternFill(start_color="D1ECF1", end_color="D1ECF1", fill_type="solid")
            elif moyenne_val >= 10:
                moyenne_cell.fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
            else:
                moyenne_cell.fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
        else:
            moyenne_cell.value = "Non saisi" if not eleve_data.get('absent') else "Absent"
            moyenne_cell.font = Font(italic=True, color="999999")
        
        moyenne_cell.alignment = Alignment(horizontal='center', vertical='center')
        moyenne_cell.border = border
        moyenne_cell.font = Font(bold=True, size=11)
        
        ws.row_dimensions[row_num].height = 20
    
    # Ajuster les largeurs de colonnes
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 15
    
    # Statistiques
    eleves_avec_moyenne = [e for e in classement_data if e['moyenne'] is not None]
    if eleves_avec_moyenne:
        stats_row = len(classement_data) + 6
        
        ws.merge_cells(f'A{stats_row}:D{stats_row}')
        stats_title = ws[f'A{stats_row}']
        stats_title.value = "STATISTIQUES"
        stats_title.font = Font(bold=True, size=12)
        stats_title.alignment = Alignment(horizontal='center')
        
        moyennes = [e['moyenne'] for e in eleves_avec_moyenne]
        moyenne_classe = sum(moyennes) / len(moyennes)
        note_max = max(moyennes)
        note_min = min(moyennes)
        
        stats_data = [
            ('Nombre d\'élèves:', len(classement_data)),
            ('Élèves avec notes:', len(eleves_avec_moyenne)),
            ('Moyenne de classe:', f"{moyenne_classe:.2f}"),
            ('Note maximale:', f"{note_max:.2f}"),
            ('Note minimale:', f"{note_min:.2f}"),
        ]
        
        for i, (label, value) in enumerate(stats_data, stats_row + 1):
            label_cell = ws.cell(row=i, column=2)
            label_cell.value = label
            label_cell.font = Font(bold=True)
            label_cell.alignment = Alignment(horizontal='right')
            
            value_cell = ws.cell(row=i, column=3)
            value_cell.value = value
            value_cell.alignment = Alignment(horizontal='left')
    
    # Préparer la réponse HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    filename = f"Classement_{classe_note.nom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response


def _generer_classement_matiere(eleves, classe_note, matiere_id, type_note, periode):
    """Générer le classement pour une matière spécifique"""
    matiere = get_object_or_404(MatiereNote, pk=matiere_id)
    classement_data = []
    
    for eleve in eleves:
        note_value = None
        absent = False
        
        # Récupérer la note selon le type
        if type_note == 'mensuelle' and periode:
            try:
                note_obj = NoteMensuelle.objects.get(
                    eleve=eleve,
                    matiere=matiere,
                    mois=periode,
                    annee_scolaire=classe_note.annee_scolaire
                )
                note_value = float(note_obj.note) if note_obj.note else None
                absent = note_obj.absent
            except NoteMensuelle.DoesNotExist:
                pass
        
        elif type_note == 'composition' and periode:
            try:
                note_obj = CompositionNote.objects.get(
                    eleve=eleve,
                    matiere=matiere,
                    periode=periode,
                    annee_scolaire=classe_note.annee_scolaire
                )
                note_value = float(note_obj.note) if note_obj.note else None
                absent = note_obj.absent
            except CompositionNote.DoesNotExist:
                pass
        
        classement_data.append({
            'matricule': eleve.matricule or 'N/A',
            'nom_complet': f"{eleve.nom} {eleve.prenom}",
            'moyenne': note_value,
            'absent': absent,
            'sexe': eleve.sexe  # Ajouter le sexe pour l'accord grammatical
        })
    
    # Trier et attribuer les rangs
    classement_data = _calculer_rangs(classement_data)
    
    titre_export = f"Classement - {classe_note.nom} - {matiere.nom}"
    if periode:
        titre_export += f" - {periode}"
    
    return classement_data, titre_export


def _generer_classement_general(eleves, classe_note, type_note, periode):
    """Générer le classement général (moyenne de toutes les matières)"""
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    classement_data = []
    
    for eleve in eleves:
        total_notes = Decimal('0')
        total_coefficients = Decimal('0')
        
        for matiere in matieres:
            note_value = None
            coefficient = matiere.coefficient or Decimal('1')
            
            # Récupérer la note selon le type
            if type_note == 'mensuelle' and periode:
                try:
                    note_obj = NoteMensuelle.objects.get(
                        eleve=eleve,
                        matiere=matiere,
                        mois=periode,
                        annee_scolaire=classe_note.annee_scolaire
                    )
                    if not note_obj.absent and note_obj.note:
                        note_value = note_obj.note
                except NoteMensuelle.DoesNotExist:
                    pass
            
            elif type_note == 'composition' and periode:
                try:
                    note_obj = CompositionNote.objects.get(
                        eleve=eleve,
                        matiere=matiere,
                        periode=periode,
                        annee_scolaire=classe_note.annee_scolaire
                    )
                    if not note_obj.absent and note_obj.note:
                        note_value = note_obj.note
                except CompositionNote.DoesNotExist:
                    pass
            
            if note_value is not None:
                total_notes += note_value * coefficient
                total_coefficients += coefficient
        
        # Calculer la moyenne générale
        if total_coefficients > 0:
            moyenne_generale = float(total_notes / total_coefficients)
            classement_data.append({
                'matricule': eleve.matricule or 'N/A',
                'nom_complet': f"{eleve.nom} {eleve.prenom}",
                'moyenne': round(moyenne_generale, 2),
                'absent': False,
                'sexe': eleve.sexe  # Ajouter le sexe pour l'accord grammatical
            })
        else:
            classement_data.append({
                'matricule': eleve.matricule or 'N/A',
                'nom_complet': f"{eleve.nom} {eleve.prenom}",
                'moyenne': None,
                'absent': False,
                'sexe': eleve.sexe  # Ajouter le sexe pour l'accord grammatical
            })
    
    # Trier et attribuer les rangs
    classement_data = _calculer_rangs(classement_data)
    
    titre_export = f"Classement Général - {classe_note.nom}"
    if periode:
        titre_export += f" - {periode}"
    
    return classement_data, titre_export


def _calculer_rangs(classement_data):
    """Calculer les rangs avec gestion des ex-aequo"""
    # Séparer élèves avec et sans notes
    eleves_avec_notes = [e for e in classement_data if e['moyenne'] is not None]
    eleves_sans_notes = [e for e in classement_data if e['moyenne'] is None]
    
    # Trier par moyenne décroissante
    eleves_avec_notes.sort(key=lambda x: x['moyenne'], reverse=True)
    
    # Attribuer les rangs avec gestion des ex-aequo
    rang = 1
    for i, eleve_note in enumerate(eleves_avec_notes):
        if i > 0 and eleve_note['moyenne'] == eleves_avec_notes[i-1]['moyenne']:
            eleve_note['rang'] = eleves_avec_notes[i-1]['rang']
        else:
            eleve_note['rang'] = rang
        rang += 1
    
    # Marquer les élèves sans notes
    for eleve_note in eleves_sans_notes:
        eleve_note['rang'] = '-'
    
    # Reconstruire la liste triée
    return eleves_avec_notes + eleves_sans_notes
