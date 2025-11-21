"""
Module centralisé pour le calcul des moyennes et classements
Garantit la cohérence entre bulletins et classements
"""
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from .models import Evaluation, NoteEleve, MatiereNote, NoteMensuelle, CompositionNote


def calculer_moyenne_matiere(eleve, matiere, periode, system_type='mensuel'):
    """
    Calcule la moyenne d'un élève pour une matière donnée
    
    Args:
        eleve: Instance Eleve
        matiere: Instance MatiereNote
        periode: Période (ex: 'OCTOBRE', '1er Trimestre')
        system_type: Type de système ('mensuel', 'trimestre', 'semestre')
    
    Returns:
        dict avec:
            - moyenne_continue: float ou None
            - note_composition: float ou None
            - moyenne_matiere: float ou None (moyenne finale calculée)
            - points: float ou None (moyenne × coefficient)
    """
    moyenne_continue = None
    note_composition = None
    
    # Récupérer les évaluations
    evaluations = Evaluation.objects.filter(
        matiere=matiere,
        periode=periode
    ).order_by('date_evaluation')
    
    # Calculer moyennes continue et composition
    total_devoirs = Decimal('0')
    count_devoirs = 0
    total_compo = Decimal('0')
    count_compo = 0
    
    for evaluation in evaluations:
        try:
            note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
            if note_obj.note is not None and not note_obj.absent:
                if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                    total_compo += Decimal(str(note_obj.note))
                    count_compo += 1
                else:
                    total_devoirs += Decimal(str(note_obj.note))
                    count_devoirs += 1
        except NoteEleve.DoesNotExist:
            pass
    
    if count_devoirs > 0:
        moyenne_continue = round(float(total_devoirs / count_devoirs), 2)
    
    if count_compo > 0:
        note_composition = round(float(total_compo / count_compo), 2)
    
    # Calculer la moyenne de la matière selon le système
    moyenne_matiere = None
    if system_type == 'mensuel':
        moyenne_matiere = moyenne_continue
    elif moyenne_continue is not None and note_composition is not None:
        moyenne_matiere = round((moyenne_continue + note_composition * 2) / 3, 2)
    elif note_composition is not None:
        moyenne_matiere = note_composition
    elif moyenne_continue is not None:
        moyenne_matiere = moyenne_continue
    
    # Calculer les points
    points = None
    if moyenne_matiere is not None:
        coefficient = float(matiere.coefficient) if matiere.coefficient else 1.0
        points = round(moyenne_matiere * coefficient, 2)
    
    return {
        'moyenne_continue': moyenne_continue,
        'note_composition': note_composition,
        'moyenne_matiere': moyenne_matiere,
        'points': points,
    }


def calculer_moyenne_generale_eleve(eleve, matieres, periode, system_type='mensuel'):
    """
    Calcule la moyenne générale d'un élève pour toutes les matières
    
    Args:
        eleve: Instance Eleve
        matieres: QuerySet de MatiereNote
        periode: Période
        system_type: Type de système
    
    Returns:
        dict avec:
            - moyenne_generale: float ou None
            - total_points: float
            - total_coefficients: float
            - details_matieres: list de dict (une par matière)
    """
    total_points = Decimal('0')
    total_coefficients = Decimal('0')
    details_matieres = []
    
    for matiere in matieres:
        result = calculer_moyenne_matiere(eleve, matiere, periode, system_type)
        
        if result['moyenne_matiere'] is not None:
            total_points += Decimal(str(result['moyenne_matiere'])) * matiere.coefficient
            total_coefficients += matiere.coefficient
        
        details_matieres.append({
            'matiere': matiere,
            'moyenne_continue': result['moyenne_continue'],
            'note_composition': result['note_composition'],
            'moyenne': result['moyenne_matiere'],
            'coefficient': matiere.coefficient,
            'points': result['points'],
        })
    
    # Calculer la moyenne générale
    moyenne_generale = None
    if total_coefficients > 0:
        moyenne_generale = round(float(total_points / total_coefficients), 2)
    
    return {
        'moyenne_generale': moyenne_generale,
        'total_points': round(float(total_points), 2) if total_points > 0 else 0,
        'total_coefficients': float(total_coefficients),
        'details_matieres': details_matieres,
    }


def calculer_classement_classe(eleves, matieres, periode, system_type='mensuel'):
    """
    Calcule le classement complet d'une classe
    
    Args:
        eleves: QuerySet d'Eleve
        matieres: QuerySet de MatiereNote
        periode: Période
        system_type: Type de système
    
    Returns:
        dict avec:
            - moyennes_par_eleve: dict {eleve_id: moyenne_generale}
            - classement: list de tuples (eleve_id, moyenne_generale) triée
            - rang_map: dict {eleve_id: rang}
            - details_par_eleve: dict {eleve_id: dict complet des calculs}
    """
    moyennes_par_eleve = {}
    details_par_eleve = {}
    
    # Calculer la moyenne de chaque élève
    for eleve in eleves:
        result = calculer_moyenne_generale_eleve(eleve, matieres, periode, system_type)
        
        if result['moyenne_generale'] is not None:
            moyennes_par_eleve[eleve.id] = result['moyenne_generale']
            details_par_eleve[eleve.id] = result
    
    # Créer le classement trié
    classement = sorted(moyennes_par_eleve.items(), key=lambda x: x[1], reverse=True)
    
    # Créer le mapping des rangs (gestion des ex-aequo)
    rang_map = {}
    prev_moyenne = None
    prev_rang = 0
    
    for idx, (eleve_id, moyenne) in enumerate(classement, start=1):
        if moyenne == prev_moyenne:
            # Ex-aequo: même rang que le précédent
            rang_map[eleve_id] = prev_rang
        else:
            rang_map[eleve_id] = idx
            prev_rang = idx
        prev_moyenne = moyenne
    
    return {
        'moyennes_par_eleve': moyennes_par_eleve,
        'classement': classement,
        'rang_map': rang_map,
        'details_par_eleve': details_par_eleve,
        'total_eleves': len(classement),
    }


def obtenir_mention_intelligente(moyenne):
    """
    Détermine la mention selon la moyenne
    
    Args:
        moyenne: float ou Decimal
    
    Returns:
        str: Mention correspondante
    """
    if moyenne is None:
        return None
    
    moyenne = float(moyenne)
    
    if moyenne >= 18.5:
        return "Excellent"
    elif moyenne >= 16.5:
        return "Très bien"
    elif moyenne >= 14.5:
        return "Bien"
    elif moyenne >= 12.5:
        return "Assez bien"
    elif moyenne >= 10.0:
        return "Passable"
    elif moyenne >= 9.0:
        return "Faible"
    else:
        return "Insuffisant"


def obtenir_appreciation_intelligente(moyenne, prenom):
    """
    Génère une appréciation personnalisée selon la moyenne
    
    Args:
        moyenne: float ou Decimal
        prenom: str
    
    Returns:
        str: Appréciation personnalisée
    """
    if moyenne is None:
        return f"{prenom}, aucune note disponible pour cette période."
    
    moyenne = float(moyenne)
    
    if moyenne >= 18.5:
        return f"Excellent travail {prenom}! Continue sur cette lancée exceptionnelle."
    elif moyenne >= 16.5:
        return f"Très bon travail {prenom}! Tes efforts sont remarquables."
    elif moyenne >= 14.5:
        return f"Bon travail {prenom}! Continue ainsi."
    elif moyenne >= 12.5:
        return f"Travail assez satisfaisant {prenom}. Tu peux faire mieux."
    elif moyenne >= 10.0:
        return f"{prenom}, travail passable. Plus d'efforts sont nécessaires."
    elif moyenne >= 9.0:
        return f"{prenom}, résultats faibles. Il faut redoubler d'efforts."
    else:
        return f"{prenom}, résultats insuffisants. Un travail sérieux s'impose."


def formater_rang_intelligent(rang, sexe, total=None):
    """
    Formate le rang avec accord grammatical selon le sexe
    
    Args:
        rang: int
        sexe: str ('M' ou 'F')
        total: int optionnel (nombre total d'élèves)
    
    Returns:
        str: Rang formaté (ex: "1er", "1ère", "2ème")
    """
    if rang is None:
        return "N/A"
    
    # Accord grammatical pour le rang 1
    if rang == 1:
        if sexe == 'F':
            rang_str = "1ère"
        else:
            rang_str = "1er"
    else:
        rang_str = f"{rang}ème"
    
    # Ajouter le total si fourni
    if total:
        return f"{rang_str}/{total}"
    
    return rang_str
