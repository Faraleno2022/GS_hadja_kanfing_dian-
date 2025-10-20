"""
Vues modernes pour le module de gestion des notes
Interface simplifiée et intuitive avec logiques de calcul préservées
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Avg, Count, Q, Max, Min
from django.db import models
from django.core.paginator import Paginator
from decimal import Decimal
import json

from .models import MatiereClasse, Evaluation, Note, BaremeAppreciation
from .utils import (
    semester_avg, trimestre_avg, annual_avg_from_semesters, 
    primaire_annual_avg
)
from eleves.models import Classe, Eleve
from utilisateurs.utils import filter_by_user_school, user_school
from ecole_moderne.security_decorators import require_school_object


@login_required
def dashboard_moderne(request):
    """
    Tableau de bord moderne pour la gestion des notes
    """
    user_school_obj = user_school(request.user)
    
    # Si pas d'école associée, afficher un message
    if not user_school_obj:
        messages.warning(request, "Aucune école n'est associée à votre compte. Contactez l'administrateur.")
        context = {
            'classes_primaire': [],
            'classes_college': [],
            'classes_lycee': [],
            'stats': {
                'total_evaluations': 0,
                'total_notes': 0,
                'classes_actives': 0,
                'moyenne_generale': None
            },
            'evaluations_recentes': [],
        }
        return render(request, 'notes/dashboard.html', context)
    
    # Récupération des classes par niveau
    classes_qs = filter_by_user_school(Classe.objects.all(), request.user, 'ecole')
    
    classes_primaire = classes_qs.filter(niveau__startswith='PRIMAIRE').order_by('niveau')
    classes_college = classes_qs.filter(niveau__startswith='COLLEGE').order_by('niveau')  
    classes_lycee = classes_qs.filter(niveau__startswith='LYCEE').order_by('niveau')
    
    # Statistiques générales
    total_evaluations = Evaluation.objects.filter(ecole=user_school_obj).count() if user_school_obj else 0
    total_notes = Note.objects.filter(ecole=user_school_obj).count() if user_school_obj else 0
    classes_actives = classes_qs.count()
    
    # Calcul de la moyenne générale avec gestion des cas null
    moyenne_result = Note.objects.filter(ecole=user_school_obj).aggregate(avg=Avg('note')) if user_school_obj else {'avg': None}
    moyenne_generale = moyenne_result['avg']
    
    stats = {
        'total_evaluations': total_evaluations,
        'total_notes': total_notes,
        'classes_actives': classes_actives,
        'moyenne_generale': moyenne_generale
    }
    
    # Évaluations récentes
    evaluations_recentes = []
    if user_school_obj:
        evaluations_recentes = Evaluation.objects.filter(
            ecole=user_school_obj
        ).select_related('classe', 'matiere').order_by('-date_creation')[:5]
    
    context = {
        'classes_primaire': classes_primaire,
        'classes_college': classes_college,
        'classes_lycee': classes_lycee,
        'stats': stats,
        'evaluations_recentes': evaluations_recentes,
    }
    
    return render(request, 'notes/dashboard.html', context)


@login_required
@require_school_object
def saisie_notes_moderne(request, evaluation_id):
    """
    Interface moderne pour la saisie des notes
    """
    evaluation = get_object_or_404(
        filter_by_user_school(Evaluation.objects.all(), request.user, 'ecole'),
        pk=evaluation_id
    )
    
    # Récupération des élèves de la classe
    eleves = Eleve.objects.filter(
        classe=evaluation.classe,
        statut='ACTIF'
    ).order_by('nom', 'prenom')
    
    # Notes déjà existantes
    notes_existantes = Note.objects.filter(
        evaluation=evaluation
    ).select_related('eleve').order_by('eleve__nom', 'eleve__prenom')
    
    if request.method == 'POST':
        donnees = request.POST.get('donnees', '').strip()
        
        if not donnees:
            messages.error(request, "Aucune donnée saisie.")
            return redirect('notes:saisie_notes_moderne', evaluation_id=evaluation_id)
        
        # Traitement des données
        lignes = [ligne.strip() for ligne in donnees.split('\n') if ligne.strip()]
        notes_traitees = 0
        erreurs = []
        
        for ligne in lignes:
            try:
                if ';' not in ligne:
                    continue
                    
                matricule, note_str = ligne.split(';', 1)
                matricule = matricule.strip()
                note_str = note_str.strip()
                
                # Validation de la note
                try:
                    note_value = float(note_str.replace(',', '.'))
                    if not (0 <= note_value <= 20):
                        erreurs.append(f"{matricule}: Note invalide ({note_value})")
                        continue
                except ValueError:
                    erreurs.append(f"{matricule}: Format de note invalide")
                    continue
                
                # Recherche de l'élève
                try:
                    eleve = Eleve.objects.get(
                        matricule=matricule,
                        classe=evaluation.classe,
                        statut='ACTIF'
                    )
                except Eleve.DoesNotExist:
                    erreurs.append(f"{matricule}: Élève non trouvé dans la classe")
                    continue
                
                # Création ou mise à jour de la note
                note_obj, created = Note.objects.update_or_create(
                    evaluation=evaluation,
                    eleve=eleve,
                    defaults={
                        'ecole': evaluation.ecole,
                        'classe': evaluation.classe,
                        'matiere': evaluation.matiere,
                        'matricule': matricule,
                        'note': Decimal(str(note_value)),
                        'saisie_par': request.user,
                    }
                )
                
                notes_traitees += 1
                
            except Exception as e:
                erreurs.append(f"Ligne '{ligne}': Erreur de traitement")
        
        # Messages de retour
        if notes_traitees > 0:
            messages.success(request, f"{notes_traitees} note(s) enregistrée(s) avec succès.")
        
        if erreurs:
            messages.warning(request, f"{len(erreurs)} erreur(s) détectée(s): " + " | ".join(erreurs[:5]))
        
        return redirect('notes:saisie_notes_moderne', evaluation_id=evaluation_id)
    
    # Formulaire simple pour la saisie
    from .forms import SaisieNotesForm
    form = SaisieNotesForm()
    
    context = {
        'evaluation': evaluation,
        'eleves': eleves,
        'notes_existantes': notes_existantes,
        'form': form,
    }
    
    return render(request, 'notes/saisie_notes.html', context)


@login_required
@require_school_object
def classement_moderne(request, classe_id, trimestre='T1'):
    """
    Classement moderne avec interface améliorée
    """
    classe = get_object_or_404(
        filter_by_user_school(Classe.objects.all(), request.user, 'ecole'),
        pk=classe_id
    )
    
    # Récupération des élèves actifs
    eleves = Eleve.objects.filter(
        classe=classe,
        statut='ACTIF'
    ).order_by('nom', 'prenom')
    
    # Calcul des moyennes selon le niveau
    classement_data = []
    annee_scolaire = classe.annee_scolaire or "2024-2025"
    
    for eleve in eleves:
        # Récupération des matières de la classe
        matieres = MatiereClasse.objects.filter(
            classe=classe,
            actif=True
        )
        
        moyennes_matieres = []
        total_coefficients = 0
        
        for matiere in matieres:
            # Calcul de la moyenne selon le cycle
            if classe.niveau.startswith('PRIMAIRE'):
                moyenne = trimestre_avg(eleve, matiere, annee_scolaire, trimestre)
            else:
                # Collège/Lycée - système semestriel
                if trimestre in ['T1', 'S1']:
                    moyenne = semester_avg(eleve, matiere, annee_scolaire, 1)
                elif trimestre in ['T2', 'S2']:
                    moyenne = semester_avg(eleve, matiere, annee_scolaire, 2)
                else:  # Moyenne annuelle
                    moyenne = annual_avg_from_semesters(eleve, matiere, annee_scolaire)
            
            if moyenne is not None:
                moyennes_matieres.append(moyenne * matiere.coefficient)
                total_coefficients += matiere.coefficient
        
        # Calcul de la moyenne générale
        if total_coefficients > 0 and moyennes_matieres:
            moyenne_generale = sum(moyennes_matieres) / total_coefficients
        else:
            moyenne_generale = None
        
        if moyenne_generale is not None:
            classement_data.append({
                'eleve': eleve,
                'nom_complet': f"{eleve.nom} {eleve.prenom}",
                'matricule': eleve.matricule,
                'moyenne': moyenne_generale,
            })
    
    # Tri par moyenne décroissante
    classement_data.sort(key=lambda x: x['moyenne'], reverse=True)
    
    # Calcul des statistiques
    if classement_data:
        moyennes = [item['moyenne'] for item in classement_data]
        moyenne_classe = sum(moyennes) / len(moyennes)
        eleves_admis = len([m for m in moyennes if m >= 10])
        eleves_rattrapage = len([m for m in moyennes if 8 <= m < 10])
        eleves_redouble = len([m for m in moyennes if m < 8])
    else:
        moyenne_classe = 0
        eleves_admis = eleves_rattrapage = eleves_redouble = 0
    
    context = {
        'classe': classe,
        'trimestre': trimestre,
        'classement': classement_data,
        'total_eleves': len(classement_data),
        'moyenne_classe': moyenne_classe,
        'eleves_admis': eleves_admis,
        'eleves_rattrapage': eleves_rattrapage,
        'eleves_redouble': eleves_redouble,
    }
    
    return render(request, 'notes/classement_moderne.html', context)


@login_required
@require_school_object
def ajax_stats_notes(request):
    """
    API AJAX pour les statistiques en temps réel
    """
    user_school_obj = user_school(request.user)
    
    # Statistiques par période
    periode = request.GET.get('periode', 'mois')
    
    stats = {
        'evaluations_total': Evaluation.objects.filter(ecole=user_school_obj).count(),
        'notes_total': Note.objects.filter(ecole=user_school_obj).count(),
        'moyenne_ecole': Note.objects.filter(ecole=user_school_obj).aggregate(
            avg=Avg('note')
        )['avg'] or 0,
        'classes_actives': Classe.objects.filter(ecole=user_school_obj).count(),
    }
    
    # Répartition des notes par tranche
    notes_repartition = {
        'excellent': Note.objects.filter(ecole=user_school_obj, note__gte=16).count(),
        'bien': Note.objects.filter(ecole=user_school_obj, note__gte=14, note__lt=16).count(),
        'assez_bien': Note.objects.filter(ecole=user_school_obj, note__gte=12, note__lt=14).count(),
        'passable': Note.objects.filter(ecole=user_school_obj, note__gte=10, note__lt=12).count(),
        'insuffisant': Note.objects.filter(ecole=user_school_obj, note__lt=10).count(),
    }
    
    return JsonResponse({
        'stats': stats,
        'repartition': notes_repartition,
        'status': 'success'
    })


@login_required
@require_school_object
def gestion_matieres_moderne(request, classe_id=None):
    """
    Gestion moderne des matières par classe
    """
    user_school_obj = user_school(request.user)
    
    if classe_id:
        classe = get_object_or_404(
            filter_by_user_school(Classe.objects.all(), request.user, 'ecole'),
            pk=classe_id
        )
        
        # Matières de la classe
        matieres = MatiereClasse.objects.filter(
            classe=classe,
            actif=True
        ).order_by('nom')
        
        # Évaluations par matière
        evaluations_par_matiere = {}
        for matiere in matieres:
            evaluations_par_matiere[matiere.id] = Evaluation.objects.filter(
                matiere=matiere
            ).order_by('-date')[:3]
        
        context = {
            'classe': classe,
            'matieres': matieres,
            'evaluations_par_matiere': evaluations_par_matiere,
        }
        
        return render(request, 'notes/matieres_classe_moderne.html', context)
    
    else:
        # Vue d'ensemble des classes
        classes = filter_by_user_school(Classe.objects.all(), request.user, 'ecole').order_by('niveau', 'nom')
        
        context = {
            'classes': classes,
        }
        
        return render(request, 'notes/gestion_classes.html', context)


@login_required
@require_school_object
def details_notes_eleve(request, eleve_id):
    """
    Affichage détaillé des notes d'un élève avec moyennes et appréciations
    """
    user_school_obj = user_school(request.user)
    
    # Récupération de l'élève
    eleve = get_object_or_404(
        filter_by_user_school(Eleve.objects.all(), request.user, 'ecole'),
        pk=eleve_id
    )
    
    # Récupération de toutes les notes de l'élève
    notes_qs = Note.objects.filter(
        eleve=eleve,
        ecole=user_school_obj
    ).select_related('evaluation', 'matiere').order_by('-evaluation__date')
    
    # Organisation des notes par matière et trimestre
    notes_par_matiere = {}
    matieres = MatiereClasse.objects.filter(
        classe=eleve.classe,
        actif=True
    ).order_by('nom')
    
    for matiere in matieres:
        notes_matiere = notes_qs.filter(matiere=matiere)
        
        # Organisation par trimestre
        notes_par_trimestre = {
            'T1': notes_matiere.filter(evaluation__trimestre='T1'),
            'T2': notes_matiere.filter(evaluation__trimestre='T2'),
            'T3': notes_matiere.filter(evaluation__trimestre='T3'),
        }
        
        # Calcul des moyennes par trimestre
        moyennes_trimestre = {}
        for trimestre, notes_trim in notes_par_trimestre.items():
            if notes_trim.exists():
                # Moyenne pondérée par coefficient
                total_points = sum(
                    float(note.note) * note.evaluation.coefficient 
                    for note in notes_trim
                )
                total_coeffs = sum(note.evaluation.coefficient for note in notes_trim)
                
                if total_coeffs > 0:
                    moyennes_trimestre[trimestre] = round(total_points / total_coeffs, 2)
                else:
                    moyennes_trimestre[trimestre] = None
            else:
                moyennes_trimestre[trimestre] = None
        
        # Moyenne annuelle de la matière
        if notes_matiere.exists():
            total_points = sum(
                float(note.note) * note.evaluation.coefficient 
                for note in notes_matiere
            )
            total_coeffs = sum(note.evaluation.coefficient for note in notes_matiere)
            moyenne_annuelle = round(total_points / total_coeffs, 2) if total_coeffs > 0 else None
        else:
            moyenne_annuelle = None
        
        notes_par_matiere[matiere] = {
            'matiere': matiere,
            'notes_par_trimestre': notes_par_trimestre,
            'moyennes_trimestre': moyennes_trimestre,
            'moyenne_annuelle': moyenne_annuelle,
            'total_notes': notes_matiere.count()
        }
    
    # Calcul de la moyenne générale de l'élève
    toutes_notes = notes_qs.all()
    if toutes_notes.exists():
        # Moyenne générale pondérée par coefficient de matière ET d'évaluation
        total_points_general = 0
        total_coeffs_general = 0
        
        for note in toutes_notes:
            coeff_total = note.evaluation.coefficient * note.matiere.coefficient
            total_points_general += float(note.note) * coeff_total
            total_coeffs_general += coeff_total
        
        moyenne_generale = round(total_points_general / total_coeffs_general, 2) if total_coeffs_general > 0 else None
    else:
        moyenne_generale = None
    
    # Statistiques générales
    stats_eleve = {
        'total_notes': toutes_notes.count(),
        'moyenne_generale': moyenne_generale,
        'note_max': toutes_notes.aggregate(max_note=Max('note'))['max_note'],
        'note_min': toutes_notes.aggregate(min_note=Min('note'))['min_note'],
        'nb_matieres': matieres.count(),
    }
    
    # Répartition des notes par tranche
    if toutes_notes.exists():
        repartition = {
            'excellent': toutes_notes.filter(note__gte=16).count(),
            'bien': toutes_notes.filter(note__gte=14, note__lt=16).count(),
            'assez_bien': toutes_notes.filter(note__gte=12, note__lt=14).count(),
            'passable': toutes_notes.filter(note__gte=10, note__lt=12).count(),
            'insuffisant': toutes_notes.filter(note__lt=10).count(),
        }
    else:
        repartition = {
            'excellent': 0, 'bien': 0, 'assez_bien': 0, 
            'passable': 0, 'insuffisant': 0
        }
    
    # Évolution des moyennes par trimestre (toutes matières confondues)
    evolution_trimestre = {}
    for trimestre in ['T1', 'T2', 'T3']:
        notes_trim = toutes_notes.filter(evaluation__trimestre=trimestre)
        if notes_trim.exists():
            total_points = sum(
                float(note.note) * note.evaluation.coefficient * note.matiere.coefficient
                for note in notes_trim
            )
            total_coeffs = sum(
                note.evaluation.coefficient * note.matiere.coefficient 
                for note in notes_trim
            )
            evolution_trimestre[trimestre] = round(total_points / total_coeffs, 2) if total_coeffs > 0 else None
        else:
            evolution_trimestre[trimestre] = None
    
    context = {
        'eleve': eleve,
        'notes_par_matiere': notes_par_matiere,
        'stats_eleve': stats_eleve,
        'repartition': repartition,
        'evolution_trimestre': evolution_trimestre,
        'trimestres': ['T1', 'T2', 'T3'],
    }
    
    return render(request, 'notes/details_notes_eleve.html', context)


@login_required
@require_school_object
def liste_eleves_notes_modal(request):
    """
    Vue AJAX pour récupérer la liste des élèves avec leurs notes par période
    Pour affichage dans une fenêtre modale
    """
    user_school_obj = user_school(request.user)
    
    # Paramètres de filtrage
    classe_id = request.GET.get('classe_id')
    periode_type = request.GET.get('periode_type', 'trimestre')  # trimestre, semestre, mois
    periode_value = request.GET.get('periode_value', 'T1')
    
    # Récupération de la classe
    if classe_id:
        try:
            classe = get_object_or_404(
                filter_by_user_school(Classe.objects.all(), request.user, 'ecole'),
                pk=classe_id
            )
        except:
            return JsonResponse({'error': 'Classe non trouvée'}, status=404)
    else:
        # Si aucune classe spécifiée, prendre la première disponible
        classe = filter_by_user_school(Classe.objects.all(), request.user, 'ecole').first()
        if not classe:
            return JsonResponse({'error': 'Aucune classe disponible'}, status=404)
    
    # Récupération des élèves de la classe
    eleves = Eleve.objects.filter(classe=classe, statut='ACTIF').order_by('nom', 'prenom')
    
    # Calcul des moyennes selon la période
    eleves_data = []
    
    for eleve in eleves:
        # Récupération des notes selon la période
        notes_qs = Note.objects.filter(
            eleve=eleve,
            ecole=user_school_obj
        ).select_related('evaluation', 'matiere')
        
        # Filtrage par période
        if periode_type == 'trimestre':
            notes_qs = notes_qs.filter(evaluation__trimestre=periode_value)
        elif periode_type == 'semestre':
            if periode_value == 'S1':
                notes_qs = notes_qs.filter(evaluation__trimestre__in=['T1', 'T2'])
            else:  # S2
                notes_qs = notes_qs.filter(evaluation__trimestre='T3')
        elif periode_type == 'mois':
            # Filtrage par mois (format: 2024-09)
            try:
                year, month = periode_value.split('-')
                notes_qs = notes_qs.filter(
                    evaluation__date__year=int(year),
                    evaluation__date__month=int(month)
                )
            except:
                notes_qs = notes_qs.none()
        
        # Calcul de la moyenne pondérée
        if notes_qs.exists():
            total_points = 0
            total_coeffs = 0
            
            notes_par_matiere = {}
            
            for note in notes_qs:
                matiere_nom = note.matiere.nom
                if matiere_nom not in notes_par_matiere:
                    notes_par_matiere[matiere_nom] = {
                        'notes': [],
                        'coefficient_matiere': note.matiere.coefficient
                    }
                
                notes_par_matiere[matiere_nom]['notes'].append({
                    'note': float(note.note),
                    'coefficient': note.evaluation.coefficient,
                    'evaluation': note.evaluation.titre,
                    'date': note.evaluation.date.strftime('%d/%m/%Y') if note.evaluation.date else ''
                })
            
            # Calcul de la moyenne générale
            for matiere_nom, data in notes_par_matiere.items():
                # Moyenne de la matière
                total_points_matiere = sum(
                    n['note'] * n['coefficient'] for n in data['notes']
                )
                total_coeffs_matiere = sum(n['coefficient'] for n in data['notes'])
                
                if total_coeffs_matiere > 0:
                    moyenne_matiere = total_points_matiere / total_coeffs_matiere
                    # Pondération par coefficient de matière
                    total_points += moyenne_matiere * data['coefficient_matiere']
                    total_coeffs += data['coefficient_matiere']
            
            moyenne_generale = round(total_points / total_coeffs, 2) if total_coeffs > 0 else 0
        else:
            moyenne_generale = 0
            notes_par_matiere = {}
        
        eleves_data.append({
            'id': eleve.id,
            'nom_complet': f"{eleve.nom} {eleve.prenom}",
            'matricule': eleve.matricule,
            'moyenne_generale': moyenne_generale,
            'nb_notes': notes_qs.count(),
            'notes_par_matiere': notes_par_matiere
        })
    
    # Tri par moyenne décroissante
    eleves_data.sort(key=lambda x: x['moyenne_generale'], reverse=True)
    
    # Ajout du rang
    for i, eleve in enumerate(eleves_data, 1):
        eleve['rang'] = i
    
    # Statistiques de la classe
    moyennes = [e['moyenne_generale'] for e in eleves_data if e['moyenne_generale'] > 0]
    stats_classe = {
        'nb_eleves': len(eleves_data),
        'nb_eleves_notes': len(moyennes),
        'moyenne_classe': round(sum(moyennes) / len(moyennes), 2) if moyennes else 0,
        'admis': len([m for m in moyennes if m >= 10]),
        'rattrapage': len([m for m in moyennes if 8 <= m < 10]),
        'redoublants': len([m for m in moyennes if m < 8])
    }
    
    return JsonResponse({
        'success': True,
        'classe': {
            'id': classe.id,
            'nom': classe.nom,
            'niveau': classe.get_niveau_display() if hasattr(classe, 'get_niveau_display') else classe.niveau
        },
        'periode': {
            'type': periode_type,
            'value': periode_value,
            'label': get_periode_label(periode_type, periode_value)
        },
        'eleves': eleves_data,
        'stats': stats_classe
    })


def get_periode_label(periode_type, periode_value):
    """Génère un label lisible pour la période"""
    if periode_type == 'trimestre':
        labels = {
            'T1': '1er Trimestre',
            'T2': '2ème Trimestre', 
            'T3': '3ème Trimestre'
        }
        return labels.get(periode_value, periode_value)
    elif periode_type == 'semestre':
        labels = {
            'S1': '1er Semestre',
            'S2': '2ème Semestre'
        }
        return labels.get(periode_value, periode_value)
    elif periode_type == 'mois':
        try:
            year, month = periode_value.split('-')
            mois_noms = [
                'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
            ]
            return f"{mois_noms[int(month)-1]} {year}"
        except:
            return periode_value
    return periode_value
