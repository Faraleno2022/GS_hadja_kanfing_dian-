"""
Système de calcul des notes selon le système guinéen
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional


def calculer_moyenne_devoirs(notes: List[Decimal]) -> Optional[Decimal]:
    """
    Calcule la moyenne des devoirs (exclut les absents/None)
    
    Args:
        notes: Liste des notes des devoirs
        
    Returns:
        Moyenne arrondie à 2 décimales ou None si aucune note
    """
    notes_valides = [n for n in notes if n is not None]
    
    if not notes_valides:
        return None
    
    moyenne = sum(notes_valides) / len(notes_valides)
    return moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculer_moyenne_periode(moyenne_devoirs: Optional[Decimal], 
                             composition: Optional[Decimal]) -> Optional[Decimal]:
    """
    Calcule la moyenne d'une période (trimestre/semestre)
    Formule: (Moyenne Devoirs + Composition) / 2
    
    Args:
        moyenne_devoirs: Moyenne des devoirs
        composition: Note de composition
        
    Returns:
        Moyenne de la période ou None
    """
    # Si les deux sont None, pas de moyenne
    if moyenne_devoirs is None and composition is None:
        return None
    
    # Si un seul est disponible, on le prend
    if moyenne_devoirs is None:
        return composition
    if composition is None:
        return moyenne_devoirs
    
    # Les deux disponibles: moyenne
    moyenne = (moyenne_devoirs + composition) / 2
    return moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculer_moyenne_annuelle(moyennes_periodes: List[Decimal]) -> Optional[Decimal]:
    """
    Calcule la moyenne annuelle d'une matière
    
    Args:
        moyennes_periodes: Liste des moyennes de chaque période
        
    Returns:
        Moyenne annuelle ou None
    """
    moyennes_valides = [m for m in moyennes_periodes if m is not None]
    
    if not moyennes_valides:
        return None
    
    moyenne = sum(moyennes_valides) / len(moyennes_valides)
    return moyenne.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculer_moyenne_generale(notes_matieres: Dict[str, Dict]) -> Optional[Decimal]:
    """
    Calcule la moyenne générale avec coefficients
    Formule: Somme(Moyenne × Coefficient) / Somme(Coefficients)
    
    Args:
        notes_matieres: {
            'matiere_id': {
                'moyenne': Decimal,
                'coefficient': Decimal
            }
        }
        
    Returns:
        Moyenne générale ou None
    """
    total_points = Decimal('0')
    total_coefficients = Decimal('0')
    
    for matiere_data in notes_matieres.values():
        moyenne = matiere_data.get('moyenne')
        coefficient = matiere_data.get('coefficient', Decimal('1'))
        
        if moyenne is not None:
            total_points += moyenne * coefficient
            total_coefficients += coefficient
    
    if total_coefficients == 0:
        return None
    
    moyenne_generale = total_points / total_coefficients
    return moyenne_generale.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def obtenir_mention(moyenne: Decimal) -> str:
    """
    Détermine la mention selon la moyenne
    
    Args:
        moyenne: Moyenne de l'élève
        
    Returns:
        Mention (Excellent, Très Bien, etc.)
    """
    if moyenne >= 18:
        return "Excellent"
    elif moyenne >= 16:
        return "Très Bien"
    elif moyenne >= 14:
        return "Bien"
    elif moyenne >= 12:
        return "Assez Bien"
    elif moyenne >= 10:
        return "Passable"
    else:
        return "Insuffisant"


def obtenir_appreciation(moyenne: Decimal) -> str:
    """
    Génère une appréciation selon la moyenne
    
    Args:
        moyenne: Moyenne de l'élève
        
    Returns:
        Appréciation textuelle
    """
    if moyenne >= 18:
        return "Excellent travail ! Continue ainsi."
    elif moyenne >= 16:
        return "Très bon travail. Félicitations !"
    elif moyenne >= 14:
        return "Bon travail. Continue tes efforts."
    elif moyenne >= 12:
        return "Travail satisfaisant. Peut mieux faire."
    elif moyenne >= 10:
        return "Travail passable. Doit fournir plus d'efforts."
    else:
        return "Travail insuffisant. Doit redoubler d'efforts."


def calculer_rang(moyennes_eleves: List[Dict]) -> List[Dict]:
    """
    Calcule le rang de chaque élève
    
    Args:
        moyennes_eleves: [
            {'eleve_id': 1, 'moyenne': Decimal('15.5')},
            {'eleve_id': 2, 'moyenne': Decimal('14.2')},
            ...
        ]
        
    Returns:
        Liste avec rangs ajoutés, triée par moyenne décroissante
    """
    # Filtrer les élèves avec moyenne
    eleves_avec_moyenne = [e for e in moyennes_eleves if e.get('moyenne') is not None]
    
    # Trier par moyenne décroissante
    eleves_tries = sorted(
        eleves_avec_moyenne,
        key=lambda x: x['moyenne'],
        reverse=True
    )
    
    # Attribuer les rangs
    for rang, eleve in enumerate(eleves_tries, start=1):
        eleve['rang'] = rang
        eleve['mention'] = obtenir_mention(eleve['moyenne'])
        eleve['appreciation'] = obtenir_appreciation(eleve['moyenne'])
    
    return eleves_tries


def valider_note(note: any, note_sur: Decimal = Decimal('20')) -> tuple:
    """
    Valide une note
    
    Args:
        note: Note à valider
        note_sur: Note maximale (défaut 20)
        
    Returns:
        (est_valide: bool, message_erreur: str)
    """
    if note is None:
        return True, ""
    
    try:
        note_decimal = Decimal(str(note))
    except:
        return False, "Format de note invalide"
    
    if note_decimal < 0:
        return False, "La note ne peut pas être négative"
    
    if note_decimal > note_sur:
        return False, f"La note ne peut pas dépasser {note_sur}"
    
    return True, ""


# Exemple d'utilisation
if __name__ == "__main__":
    # Test calcul moyenne devoirs
    devoirs = [Decimal('15'), Decimal('14'), Decimal('16')]
    moy_devoirs = calculer_moyenne_devoirs(devoirs)
    print(f"Moyenne devoirs: {moy_devoirs}")
    
    # Test calcul moyenne période
    composition = Decimal('17')
    moy_periode = calculer_moyenne_periode(moy_devoirs, composition)
    print(f"Moyenne période: {moy_periode}")
    
    # Test moyenne générale
    notes_matieres = {
        'francais': {'moyenne': Decimal('16'), 'coefficient': Decimal('4')},
        'math': {'moyenne': Decimal('14'), 'coefficient': Decimal('4')},
        'histoire': {'moyenne': Decimal('16'), 'coefficient': Decimal('2')},
    }
    moy_generale = calculer_moyenne_generale(notes_matieres)
    print(f"Moyenne générale: {moy_generale}")
    
    # Test mention
    mention = obtenir_mention(moy_generale)
    print(f"Mention: {mention}")
    
    # Test rang
    eleves = [
        {'eleve_id': 1, 'moyenne': Decimal('15.5')},
        {'eleve_id': 2, 'moyenne': Decimal('14.2')},
        {'eleve_id': 3, 'moyenne': Decimal('16.8')},
    ]
    eleves_classes = calculer_rang(eleves)
    for e in eleves_classes:
        print(f"Élève {e['eleve_id']}: Rang {e['rang']}, Moyenne {e['moyenne']}, {e['mention']}")
