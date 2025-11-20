"""
Utilitaires pour le calcul centralisé des rangs
Garantit la cohérence entre classement et bulletins
"""
from decimal import Decimal
from typing import Dict, List, Optional
from .calculs_intelligent import calculer_rang_intelligent


def calculer_rangs_classe_periode(classe_note, periode: str) -> Dict[int, dict]:
    """
    Calcule les rangs pour tous les élèves d'une classe pour une période donnée.
    
    Cette fonction centralise le calcul des rangs pour garantir la cohérence
    entre le classement web et les bulletins PDF.
    
    Args:
        classe_note: Instance de ClasseNote
        periode: Période (ex: "OCTOBRE", "NOVEMBRE", etc.)
        
    Returns:
        Dictionnaire {eleve_id: {'rang': '10ème', 'rang_num': 10, 'moyenne': Decimal('15.5')}}
    """
    from eleves.models import Eleve, Classe as ClasseEleve
    from .models import MatiereNote, Evaluation, NoteEleve
    
    # Récupérer la classe élève correspondante
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if not classe_eleve:
        return {}
    
    # Récupérer les élèves actifs
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    
    # Calculer les moyennes pour chaque élève
    moyennes_pour_rang = []
    
    for eleve in eleves:
        total_points = Decimal('0')
        total_coefficients = Decimal('0')
        
        for matiere in matieres:
            # Récupérer les évaluations de la période
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode=periode
            )
            
            if not evaluations.exists():
                continue
            
            # Calculer la moyenne de la matière
            total_devoirs = Decimal('0')
            count_devoirs = 0
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    # Traiter les absences comme 0
                    if note_obj.note is not None and not note_obj.absent:
                        note_value = Decimal(str(note_obj.note))
                    else:
                        note_value = Decimal('0')
                    
                    total_devoirs += note_value
                    count_devoirs += 1
                except NoteEleve.DoesNotExist:
                    # Pas de note = 0
                    count_devoirs += 1
            
            if count_devoirs > 0:
                moyenne_matiere = total_devoirs / count_devoirs
                total_points += moyenne_matiere * matiere.coefficient
                total_coefficients += matiere.coefficient
        
        if total_coefficients > 0:
            moyenne_generale = (total_points / total_coefficients).quantize(Decimal('0.01'))
            moyennes_pour_rang.append({
                'eleve_id': eleve.id,
                'prenom': eleve.prenom,
                'nom': eleve.nom,
                'sexe': getattr(eleve, 'sexe', 'M'),
                'moyenne': moyenne_generale
            })
    
    # Calculer les rangs avec la fonction centralisée
    resultats_rangs = calculer_rang_intelligent(moyennes_pour_rang)
    
    # Créer le dictionnaire de résultats
    rangs_dict = {}
    for r in resultats_rangs:
        rangs_dict[r['eleve_id']] = {
            'rang': r['rang'],
            'rang_num': r['rang_num'],
            'moyenne': r['moyenne'],
            'total_eleves': r.get('total_eleves', len(resultats_rangs))
        }
    
    return rangs_dict


def get_rang_eleve(classe_note, periode: str, eleve_id: int) -> Optional[dict]:
    """
    Récupère le rang d'un élève spécifique.
    
    Args:
        classe_note: Instance de ClasseNote
        periode: Période (ex: "OCTOBRE", "NOVEMBRE", etc.)
        eleve_id: ID de l'élève
        
    Returns:
        Dictionnaire {'rang': '10ème', 'rang_num': 10, 'moyenne': Decimal('15.5')}
        ou None si l'élève n'a pas de rang
    """
    rangs_dict = calculer_rangs_classe_periode(classe_note, periode)
    return rangs_dict.get(eleve_id)


def get_rangs_avec_total(rangs_dict: Dict[int, dict]) -> Dict[int, str]:
    """
    Ajoute le total au format du rang (ex: "10ème" → "10ème/18").
    
    Args:
        rangs_dict: Dictionnaire retourné par calculer_rangs_classe_periode
        
    Returns:
        Dictionnaire {eleve_id: "10ème/18"}
    """
    if not rangs_dict:
        return {}
    
    # Récupérer le total d'élèves (même pour tous)
    total_eleves = next(iter(rangs_dict.values()))['total_eleves']
    
    rangs_avec_total = {}
    for eleve_id, info in rangs_dict.items():
        rang = info['rang']
        rangs_avec_total[eleve_id] = f"{rang}/{total_eleves}"
    
    return rangs_avec_total
