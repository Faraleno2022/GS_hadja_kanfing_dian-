from __future__ import annotations
from datetime import date
from calendar import monthrange
from decimal import Decimal
from typing import Iterable, Optional, Tuple, Dict

from django.db.models import Q

from .models import Evaluation, Note, MatiereClasse
from eleves.models import Eleve, Classe

# --- Périodes académiques ---
# Collège/Lycée semestres
SEMESTRE_1_MONTHS = (10, 11, 12, 1)   # Oct, Nov, Dec, Jan
SEMESTRE_2_MONTHS = (2, 3, 4, 5)      # Feb, Mar, Apr, May

# Primaire trimestres (T1, T2, T3)
TRIMESTRE_MONTHS = {
    'T1': (10, 11, 12),
    'T2': (1, 2, 3),
    'T3': (4, 5, 6),
}


def _daterange_for_month(annee: int, month: int) -> Tuple[date, date]:
    if month == 1:
        year = annee + 1  # année scolaire traverse l'année civile
    else:
        year = annee
    start = date(year if month != 1 else year - 0, month, 1)
    end = date(year if month != 1 else year - 0, month, monthrange(year, month)[1])
    return start, end


def _school_year_start(annee_scolaire: str) -> int:
    """Retourne l'année de début de l'année scolaire, ex: '2024-2025' -> 2024."""
    try:
        return int((annee_scolaire or '').split('-')[0])
    except Exception:
        # Fallback basique: année courante - 1
        return date.today().year - 1


def _avg_decimal(values: Iterable[Decimal]) -> Optional[Decimal]:
    values = [v for v in values if v is not None]
    if not values:
        return None
    s = sum(values)
    return (s / Decimal(len(values))).quantize(Decimal('0.01'))


def course_month_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, month: int) -> Optional[Decimal]:
    """Moyenne pondérée des évaluations de catégorie COURS pour un mois donné (par matière/élève)."""
    y0 = _school_year_start(annee_scolaire)
    d1, d2 = _daterange_for_month(y0, month)
    # Filtrer évaluations COURS du mois
    evals = Evaluation.objects.filter(
        ecole=matiere.ecole,
        classe=matiere.classe,
        matiere=matiere,
        categorie='COURS',
        date__range=(d1, d2),
        annee_scolaire=annee_scolaire,
    )
    if not evals.exists():
        return None
    notes = Note.objects.filter(evaluation__in=evals, eleve=eleve).select_related('evaluation')
    num = Decimal('0'); den = Decimal('0')
    for n in notes:
        if n.note is None:
            continue
        c = Decimal(getattr(n.evaluation, 'coefficient', 1) or 1)
        num += Decimal(n.note) * c
        den += c
    return (num / den).quantize(Decimal('0.01')) if den > 0 else None


def compo_month_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, month: int) -> Optional[Decimal]:
    """Moyenne pondérée des COMPOSITION du mois (s'il y en a)."""
    y0 = _school_year_start(annee_scolaire)
    d1, d2 = _daterange_for_month(y0, month)
    evals = Evaluation.objects.filter(
        ecole=matiere.ecole,
        classe=matiere.classe,
        matiere=matiere,
        categorie='COMPOSITION',
        date__range=(d1, d2),
        annee_scolaire=annee_scolaire,
    )
    if not evals.exists():
        return None
    notes = Note.objects.filter(evaluation__in=evals, eleve=eleve).select_related('evaluation')
    num = Decimal('0'); den = Decimal('0')
    for n in notes:
        if n.note is None:
            continue
        c = Decimal(getattr(n.evaluation, 'coefficient', 1) or 1)
        num += Decimal(n.note) * c
        den += c
    return (num / den).quantize(Decimal('0.01')) if den > 0 else None


def monthly_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, month: int, mode: str = 'weighted') -> Optional[Decimal]:
    """Combine cours et composition du mois.
    - S'il y a des compositions ce mois, on applique la règle pondérée 2:1 si mode='weighted'.
    - Sinon, retourne la moyenne de cours du mois.
    """
    cours = course_month_avg(eleve, matiere, annee_scolaire, month)
    compo = compo_month_avg(eleve, matiere, annee_scolaire, month)
    if cours is None and compo is None:
        return None
    if cours is None:
        return compo
    if compo is None:
        return cours
    if mode == 'weighted':
        return (((compo * Decimal('2')) + cours) / Decimal('3')).quantize(Decimal('0.01'))
    return ((compo + cours) / Decimal('2')).quantize(Decimal('0.01'))


def semester_course_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, semestre: int) -> Optional[Decimal]:
    months = SEMESTRE_1_MONTHS if semestre == 1 else SEMESTRE_2_MONTHS
    avgs = []
    for m in months:
        avgs.append(course_month_avg(eleve, matiere, annee_scolaire, m))
    return _avg_decimal([a for a in avgs if a is not None])


def semester_compo_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, semestre: int) -> Optional[Decimal]:
    y0 = _school_year_start(annee_scolaire)
    months = SEMESTRE_1_MONTHS if semestre == 1 else SEMESTRE_2_MONTHS
    # Bornes de dates du semestre
    d1_list = [_daterange_for_month(y0, m)[0] for m in months]
    d2_list = [_daterange_for_month(y0, m)[1] for m in months]
    d1, d2 = min(d1_list), max(d2_list)
    evals = Evaluation.objects.filter(
        ecole=matiere.ecole,
        classe=matiere.classe,
        matiere=matiere,
        categorie='COMPOSITION',
        date__range=(d1, d2),
        annee_scolaire=annee_scolaire,
    ).order_by('date', 'id')
    if not evals.exists():
        return None
    notes = Note.objects.filter(evaluation__in=evals, eleve=eleve).select_related('evaluation')
    num = Decimal('0'); den = Decimal('0')
    for n in notes:
        if n.note is None:
            continue
        c = Decimal(getattr(n.evaluation, 'coefficient', 1) or 1)
        num += Decimal(n.note) * c
        den += c
    return (num / den).quantize(Decimal('0.01')) if den > 0 else None


SEMESTER_MODE_WEIGHTED = 'weighted'
SEMESTER_MODE_EQUAL = 'equal'


def semester_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, semestre: int, mode: str = 'weighted') -> Optional[Decimal]:
    """Calcule la moyenne semestrielle selon la règle choisie.
    - mode='weighted' -> ((composition*2) + cours)/3
    - mode='equal' -> (composition + cours)/2
    """
    cours = semester_course_avg(eleve, matiere, annee_scolaire, semestre)
    compo = semester_compo_avg(eleve, matiere, annee_scolaire, semestre)
    if cours is None and compo is None:
        return None
    if cours is None:
        return compo
    if compo is None:
        return cours
    if mode == 'weighted':
        return ((compo * Decimal('2')) + cours) / Decimal('3')
    return (compo + cours) / Decimal('2')


def annual_avg_from_semesters(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, mode: str = 'weighted') -> Optional[Decimal]:
    s1 = semester_avg(eleve, matiere, annee_scolaire, 1, mode)
    s2 = semester_avg(eleve, matiere, annee_scolaire, 2, mode)
    if s1 is None and s2 is None:
        return None
    if s1 is None:
        return s2
    if s2 is None:
        return s1
    return ((s1 + s2) / Decimal('2')).quantize(Decimal('0.01'))


def trimestre_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str, trimestre: str) -> Optional[Decimal]:
    """Moyenne pondérée des évaluations (toutes catégories) d'un trimestre Primaire."""
    months = TRIMESTRE_MONTHS.get(trimestre.upper())
    if not months:
        return None
    y0 = _school_year_start(annee_scolaire)
    d1_list = [_daterange_for_month(y0, m)[0] for m in months]
    d2_list = [_daterange_for_month(y0, m)[1] for m in months]
    d1, d2 = min(d1_list), max(d2_list)
    evals = Evaluation.objects.filter(
        ecole=matiere.ecole,
        classe=matiere.classe,
        matiere=matiere,
        date__range=(d1, d2),
        annee_scolaire=annee_scolaire,
    ).order_by('date', 'id')
    if not evals.exists():
        return None
    notes = Note.objects.filter(evaluation__in=evals, eleve=eleve).select_related('evaluation')
    num = Decimal('0'); den = Decimal('0')
    for n in notes:
        if n.note is None:
            continue
        c = Decimal(getattr(n.evaluation, 'coefficient', 1) or 1)
        num += Decimal(n.note) * c
        den += c
    return (num / den).quantize(Decimal('0.01')) if den > 0 else None


def primaire_annual_avg(eleve: Eleve, matiere: MatiereClasse, annee_scolaire: str) -> Optional[Decimal]:
    t1 = trimestre_avg(eleve, matiere, annee_scolaire, 'T1')
    t2 = trimestre_avg(eleve, matiere, annee_scolaire, 'T2')
    t3 = trimestre_avg(eleve, matiere, annee_scolaire, 'T3')
    vals = [v for v in (t1, t2, t3) if v is not None]
    if not vals:
        return None
    return (sum(vals) / Decimal(len(vals))).quantize(Decimal('0.01'))
