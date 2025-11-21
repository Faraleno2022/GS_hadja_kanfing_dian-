"""
Module pour calculer et sauvegarder les classements
Utilise le module centralisé calculs_moyennes pour garantir la cohérence
"""
from decimal import Decimal
from django.db import transaction
from .models import ClasseNote, MatiereNote, Evaluation, NoteEleve, Classement
from eleves.models import Eleve, Classe as ClasseEleve
from .calculs_moyennes import (
    calculer_moyenne_generale_eleve,
    calculer_classement_classe as calculer_classement_centralise,
    formater_rang_intelligent,
    obtenir_mention_intelligente,
    obtenir_appreciation_intelligente
)


def calculer_classement_classe(classe_note, periode, system_type='trimestre', user=None):
    """
    Calcule et sauvegarde le classement d'une classe pour une période donnée
    
    Args:
        classe_note: Instance de ClasseNote
        periode: Code de la période (TRIMESTRE_1, NOVEMBRE, etc.)
        system_type: Type de système (mensuel, trimestre, semestre, annuel)
        user: Utilisateur qui effectue le calcul
    
    Returns:
        dict: Statistiques du calcul
    """
    # Récupérer les élèves de la classe
    classe_eleve = ClasseEleve.objects.filter(
        nom__iexact=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if not classe_eleve:
        # Essayer une recherche plus flexible
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains=classe_note.nom.split()[0],
            annee_scolaire=classe_note.annee_scolaire
        ).first()
    
    if not classe_eleve:
        return {'erreur': 'Classe d\'élèves introuvable'}
    
    eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').order_by('nom', 'prenom')
    
    if not eleves.exists():
        return {'erreur': 'Aucun élève actif dans la classe'}
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    
    if not matieres.exists():
        return {'erreur': 'Aucune matière active dans la classe'}
    
    # UTILISER LE MODULE CENTRALISÉ pour calculer toutes les moyennes et rangs (SOURCE UNIQUE)
    classement_complet = calculer_classement_centralise(eleves, matieres, periode, system_type)
    
    # Extraire les données du classement centralisé
    moyennes_par_eleve = classement_complet['moyennes_par_eleve']
    classement = classement_complet['classement']
    rang_map = classement_complet['rang_map']
    details_par_eleve = classement_complet['details_par_eleve']
    effectif = classement_complet['total_eleves']
    
    # Préparer les données pour la sauvegarde
    moyennes_eleves = []
    for eleve_id, moyenne in moyennes_par_eleve.items():
        eleve = next((e for e in eleves if e.id == eleve_id), None)
        if eleve and moyenne is not None:
            details = details_par_eleve.get(eleve_id, {})
            total_pts = details.get('total_points', Decimal('0'))
            total_coef = details.get('total_coefficients', Decimal('0'))
            moyennes_eleves.append((eleve, Decimal(str(moyenne)), Decimal(str(total_pts)), Decimal(str(total_coef))))
    
    # Les données sont déjà triées et rangées par le module centralisé
    
    # Sauvegarder les classements dans la base de données
    stats = {
        'crees': 0,
        'mis_a_jour': 0,
        'erreurs': 0
    }
    
    with transaction.atomic():
        for eleve, moyenne, total_pts, total_coef in moyennes_eleves:
            rang_num, rang_formate = rang_map[eleve.id]
            
            # Déterminer la mention et l'appréciation
            mention = obtenir_mention_intelligente(moyenne)
            appreciation = obtenir_appreciation_intelligente(moyenne, eleve.prenom)
            
            try:
                # Créer ou mettre à jour le classement
                classement, created = Classement.objects.update_or_create(
                    eleve=eleve,
                    classe=classe_note,
                    periode=periode,
                    annee_scolaire=classe_note.annee_scolaire,
                    defaults={
                        'moyenne_generale': moyenne,
                        'total_points': total_pts,
                        'total_coefficients': total_coef,
                        'rang': rang_num,
                        'rang_formate': rang_formate,
                        'effectif': effectif,
                        'mention': mention,
                        'appreciation': appreciation,
                        'calcule_par': user
                    }
                )
                
                if created:
                    stats['crees'] += 1
                else:
                    stats['mis_a_jour'] += 1
            except Exception as e:
                stats['erreurs'] += 1
                print(f"Erreur pour {eleve}: {e}")
    
    return stats


def recalculer_tous_classements(classe_note, user=None):
    """
    Recalcule tous les classements pour toutes les périodes d'une classe
    
    Args:
        classe_note: Instance de ClasseNote
        user: Utilisateur qui effectue le calcul
    
    Returns:
        dict: Statistiques globales
    """
    periodes = [
        ('TRIMESTRE_1', 'trimestre'),
        ('TRIMESTRE_2', 'trimestre'),
        ('TRIMESTRE_3', 'trimestre'),
        ('SEMESTRE_1', 'semestre'),
        ('SEMESTRE_2', 'semestre'),
        ('OCTOBRE', 'mensuel'),
        ('NOVEMBRE', 'mensuel'),
        ('DECEMBRE', 'mensuel'),
        ('JANVIER', 'mensuel'),
        ('FEVRIER', 'mensuel'),
        ('MARS', 'mensuel'),
        ('AVRIL', 'mensuel'),
        ('MAI', 'mensuel'),
    ]
    
    stats_globales = {
        'total_crees': 0,
        'total_mis_a_jour': 0,
        'total_erreurs': 0,
        'periodes_traitees': 0
    }
    
    for periode, system_type in periodes:
        # Vérifier si des évaluations existent pour cette période
        if Evaluation.objects.filter(
            matiere__classe=classe_note,
            periode=periode
        ).exists():
            stats = calculer_classement_classe(classe_note, periode, system_type, user)
            
            if 'erreur' not in stats:
                stats_globales['total_crees'] += stats.get('crees', 0)
                stats_globales['total_mis_a_jour'] += stats.get('mis_a_jour', 0)
                stats_globales['total_erreurs'] += stats.get('erreurs', 0)
                stats_globales['periodes_traitees'] += 1
    
    return stats_globales
