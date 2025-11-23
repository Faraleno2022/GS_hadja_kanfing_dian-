"""
Module centralisé pour le calcul des moyennes et classements
Garantit la cohérence entre bulletins et classements
"""
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from .models import Evaluation, NoteEleve, MatiereNote, NoteMensuelle, CompositionNote


def detecter_niveau_scolaire(classe_nom):
    """
    Détecte le niveau scolaire à partir du nom de la classe
    
    Returns:
        str: 'MATERNELLE', 'PRIMAIRE', 'COLLEGE', 'LYCEE'
    """
    nom_upper = str(classe_nom).upper()
    
    # Maternelle et garderie
    if any(x in nom_upper for x in ['MATERNELLE', 'GARDERIE', 'PETITE SECTION', 'MOYENNE SECTION', 'GRANDE SECTION', 'CRÈCHE']):
        return 'MATERNELLE'
    
    # Primaire (1ère à 6ème année ou CP, CE1, CE2, CM1, CM2)
    if any(x in nom_upper for x in ['1ÈRE ANNÉE', '2ÈME ANNÉE', '3ÈME ANNÉE', '4ÈME ANNÉE', '5ÈME ANNÉE', '6ÈME ANNÉE',
                                     'CP1', 'CP2', 'CE1', 'CE2', 'CM1', 'CM2']):
        return 'PRIMAIRE'
    
    # Collège (7ème à 10ème année)
    if any(x in nom_upper for x in ['7ÈME', '8ÈME', '9ÈME', '10ÈME']):
        return 'COLLEGE'
    
    # Lycée (11ème à Terminale)
    if any(x in nom_upper for x in ['11ÈME', '12ÈME', 'TERMINALE']):
        return 'LYCEE'
    
    # Par défaut, considérer comme collège
    return 'COLLEGE'


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
            # Note n'existe pas, continuer sans erreur
            continue
    
    if count_devoirs > 0:
        moyenne_continue = round(float(total_devoirs / count_devoirs), 2)
    
    if count_compo > 0:
        note_composition = round(float(total_compo / count_compo), 2)
    
    # Calculer la moyenne de la matière selon le système
    moyenne_matiere = None
    if system_type == 'mensuel':
        moyenne_matiere = moyenne_continue
    elif moyenne_continue is not None and note_composition is not None:
        # Formule corrigée : (Moyenne Continue + Composition) / 2 (poids égal)
        moyenne_matiere = round((moyenne_continue + note_composition) / 2, 2)
    elif note_composition is not None:
        moyenne_matiere = note_composition
    elif moyenne_continue is not None:
        moyenne_matiere = moyenne_continue
    
    # Calculer les points (avec validation du coefficient)
    points = None
    if moyenne_matiere is not None:
        # Validation et conversion sécurisée du coefficient
        try:
            coefficient = float(matiere.coefficient) if matiere.coefficient and matiere.coefficient > 0 else 1.0
        except (TypeError, ValueError):
            coefficient = 1.0
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
            - niveau: niveau scolaire détecté
            - appreciations_only: bool (True pour maternelle/garderie)
    """
    # Détecter le niveau scolaire
    niveau = 'COLLEGE'  # Par défaut
    if matieres.exists():
        classe = matieres.first().classe
        niveau = detecter_niveau_scolaire(classe.nom if hasattr(classe, 'nom') else '')
    
    # MATERNELLE/GARDERIE: Pas de notes, seulement des appréciations
    if niveau == 'MATERNELLE':
        return {
            'moyenne_generale': None,
            'total_points': 0,
            'total_coefficients': 0,
            'details_matieres': [],
            'niveau': niveau,
            'appreciations_only': True,
            'appreciation': 'Suivi pédagogique qualitatif - Pas de notes numériques',
            'mention': 'Suivi continu'
        }
    
    total_points = Decimal('0')
    total_coefficients = Decimal('0')
    details_matieres = []
    
    for matiere in matieres:
        result = calculer_moyenne_matiere(eleve, matiere, periode, system_type)
        
        # RÈGLE PÉDAGOGIQUE: Toutes les matières comptent
        # Si pas de notes = 0 (comme une absence)
        moyenne_matiere = result['moyenne_matiere']
        if moyenne_matiere is None:
            moyenne_matiere = 0.0
        
        # PRIMAIRE: Pas de coefficients (tous égaux à 1)
        if niveau == 'PRIMAIRE':
            coefficient = Decimal('1')
        else:
            coefficient = matiere.coefficient if matiere.coefficient and matiere.coefficient > 0 else Decimal('1')
        
        # Calculer les points
        points = round(moyenne_matiere * float(coefficient), 2)
        
        # Ajouter au total (toutes les matières comptent)
        total_points += Decimal(str(moyenne_matiere)) * coefficient
        total_coefficients += coefficient
        
        details_matieres.append({
            'matiere': matiere,
            'moyenne_continue': result['moyenne_continue'],
            'note_composition': result['note_composition'],
            'moyenne': moyenne_matiere if result['moyenne_matiere'] is not None else None,  # Garder None pour affichage
            'moyenne_calculee': moyenne_matiere,  # Valeur utilisée dans le calcul (0 si None)
            'coefficient': coefficient if niveau != 'PRIMAIRE' else 1,
            'points': points,
        })
    
    # Calculer la moyenne générale (avec protection contre division par zéro)
    moyenne_generale = None
    if total_coefficients and total_coefficients > 0:
        try:
            moyenne_generale = round(float(total_points / total_coefficients), 2)
        except (ZeroDivisionError, ValueError, TypeError) as e:
            # En cas d'erreur de calcul, retourner None
            moyenne_generale = None
    
    return {
        'moyenne_generale': moyenne_generale,
        'total_points': round(float(total_points), 2) if total_points > 0 else 0,
        'total_coefficients': float(total_coefficients),
        'details_matieres': details_matieres,
        'niveau': niveau,
        'appreciations_only': False
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
