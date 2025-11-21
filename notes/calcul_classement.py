"""
Module pour calculer et sauvegarder les classements
"""
from decimal import Decimal
from django.db import transaction
from .models import ClasseNote, MatiereNote, Evaluation, NoteEleve, Classement
from eleves.models import Eleve, Classe as ClasseEleve
from .calculs_intelligent import formater_rang_intelligent, obtenir_mention_intelligente, obtenir_appreciation_intelligente


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
    
    # Calculer les moyennes pour chaque élève
    moyennes_eleves = []  # [(eleve, moyenne, total_points, total_coef)]
    
    for eleve in eleves:
        total_points = Decimal('0')
        total_coefficients = Decimal('0')
        
        for matiere in matieres:
            # Récupérer les évaluations de cette matière pour la période
            evaluations = Evaluation.objects.filter(
                matiere=matiere,
                periode=periode
            )
            
            # Séparer devoirs/contrôles et compositions
            total_devoirs = Decimal('0')
            count_devoirs = 0
            total_compo = Decimal('0')
            count_compo = 0
            
            for evaluation in evaluations:
                try:
                    note_obj = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                    # Traiter les absences comme 0
                    note_value = Decimal(str(note_obj.note)) if note_obj.note is not None and not note_obj.absent else Decimal('0')
                    
                    if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                        total_compo += note_value
                        count_compo += 1
                    else:
                        total_devoirs += note_value
                        count_devoirs += 1
                except NoteEleve.DoesNotExist:
                    # Pas de note = 0
                    if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                        count_compo += 1
                    else:
                        count_devoirs += 1
            
            # Calculer la moyenne de la matière
            moy_continue = total_devoirs / count_devoirs if count_devoirs > 0 else None
            moy_compo = total_compo / count_compo if count_compo > 0 else None
            moy_matiere = None
            
            if system_type == 'mensuel':
                moy_matiere = moy_continue
            elif moy_continue is not None and moy_compo is not None:
                # Pondération 1:2 (continue:composition)
                moy_matiere = (moy_continue + moy_compo * 2) / 3
            elif moy_compo is not None:
                moy_matiere = moy_compo
            elif moy_continue is not None:
                moy_matiere = moy_continue
            
            # Ajouter aux totaux
            if moy_matiere is not None:
                total_points += moy_matiere * matiere.coefficient
                total_coefficients += matiere.coefficient
        
        # Calculer la moyenne générale
        if total_coefficients > 0:
            moyenne_generale = total_points / total_coefficients
            moyennes_eleves.append((eleve, moyenne_generale, total_points, total_coefficients))
    
    # Trier par moyenne décroissante
    moyennes_eleves.sort(key=lambda x: x[1], reverse=True)
    
    # Attribuer les rangs avec gestion des ex-aequo
    rang_map = {}  # {eleve_id: (rang, rang_formate)}
    prev_moy = None
    prev_rank = None
    effectif = len(moyennes_eleves)
    
    for idx, (eleve, moyenne, _, _) in enumerate(moyennes_eleves, start=1):
        if prev_moy is not None and abs(moyenne - prev_moy) < Decimal('0.01'):
            # ex-aequo: même rang que le précédent
            rang_num = prev_rank
        else:
            rang_num = idx
            prev_rank = idx
            prev_moy = moyenne
        
        # Formater le rang avec accord grammatical
        sexe = getattr(eleve, 'sexe', 'M') or 'M'
        rang_formate = formater_rang_intelligent(rang_num, sexe, effectif)
        rang_map[eleve.id] = (rang_num, rang_formate)
    
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
