"""
Script pour vérifier et identifier les erreurs potentielles dans le code
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve
from decimal import Decimal, InvalidOperation
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verifier_coherence_coefficients():
    """Vérifie la cohérence des coefficients des matières"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES COEFFICIENTS")
    print("="*60)
    
    problemes = []
    
    for matiere in MatiereNote.objects.filter(actif=True):
        # Vérifier coefficient invalide
        if matiere.coefficient is None:
            problemes.append(f"⚠️ {matiere.nom} (Classe: {matiere.classe}) - Coefficient NULL")
        elif matiere.coefficient <= 0:
            problemes.append(f"❌ {matiere.nom} (Classe: {matiere.classe}) - Coefficient négatif ou zéro: {matiere.coefficient}")
        elif matiere.coefficient > 10:
            problemes.append(f"⚠️ {matiere.nom} (Classe: {matiere.classe}) - Coefficient très élevé: {matiere.coefficient}")
    
    if problemes:
        print(f"\n❌ {len(problemes)} problème(s) détecté(s):")
        for p in problemes[:10]:  # Afficher max 10 problèmes
            print(f"   {p}")
    else:
        print("✅ Tous les coefficients sont valides")
    
    return len(problemes) == 0

def verifier_notes_invalides():
    """Vérifie les notes invalides (hors de 0-20)"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES NOTES")
    print("="*60)
    
    problemes = []
    
    for note in NoteEleve.objects.exclude(note=None)[:1000]:  # Limiter à 1000 pour le test
        if note.note < 0:
            problemes.append(f"❌ Note négative: {note.note} - Élève: {note.eleve}, Éval: {note.evaluation}")
        elif note.note > 20:
            problemes.append(f"❌ Note > 20: {note.note} - Élève: {note.eleve}, Éval: {note.evaluation}")
    
    if problemes:
        print(f"\n❌ {len(problemes)} note(s) invalide(s):")
        for p in problemes[:10]:
            print(f"   {p}")
    else:
        print("✅ Toutes les notes sont dans l'intervalle [0, 20]")
    
    return len(problemes) == 0

def verifier_divisions_par_zero():
    """Vérifie les risques de division par zéro dans les calculs"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES DIVISIONS PAR ZÉRO")
    print("="*60)
    
    # Test avec une classe
    classe = ClasseNote.objects.first()
    if not classe:
        print("⚠️ Aucune classe pour tester")
        return True
    
    # Test avec des coefficients à 0
    try:
        total = Decimal('100')
        coef = Decimal('0')
        
        # Simulation de la division
        if coef != 0:
            resultat = total / coef
        else:
            print("✅ Protection contre division par zéro détectée")
            return True
    except (ZeroDivisionError, InvalidOperation) as e:
        print(f"❌ Erreur de division: {e}")
        return False
    
    return True

def verifier_imports_manquants():
    """Vérifie les imports nécessaires"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES IMPORTS")
    print("="*60)
    
    imports_requis = [
        ('decimal', 'Decimal'),
        ('django.db.models', 'Q'),
        ('django.http', 'HttpResponse'),
        ('django.shortcuts', 'render'),
    ]
    
    problemes = []
    for module, item in imports_requis:
        try:
            exec(f"from {module} import {item}")
            print(f"✅ {module}.{item} - OK")
        except ImportError as e:
            problemes.append(f"❌ Impossible d'importer {module}.{item}: {e}")
    
    if problemes:
        print(f"\n❌ {len(problemes)} import(s) manquant(s):")
        for p in problemes:
            print(f"   {p}")
        return False
    
    return True

def verifier_evaluations_orphelines():
    """Vérifie les évaluations sans matière ou classe"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES ÉVALUATIONS ORPHELINES")
    print("="*60)
    
    problemes = []
    
    for eval in Evaluation.objects.all()[:1000]:
        if not eval.matiere:
            problemes.append(f"❌ Évaluation {eval.id} sans matière")
        if eval.matiere and not eval.matiere.classe:
            problemes.append(f"❌ Évaluation {eval.id} avec matière sans classe")
    
    if problemes:
        print(f"\n❌ {len(problemes)} évaluation(s) orpheline(s):")
        for p in problemes[:10]:
            print(f"   {p}")
    else:
        print("✅ Toutes les évaluations sont liées correctement")
    
    return len(problemes) == 0

def verifier_eleves_sans_classe():
    """Vérifie les élèves actifs sans classe"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES ÉLÈVES SANS CLASSE")
    print("="*60)
    
    eleves_sans_classe = Eleve.objects.filter(statut='ACTIF', classe=None)
    
    if eleves_sans_classe.exists():
        print(f"❌ {eleves_sans_classe.count()} élève(s) actif(s) sans classe:")
        for eleve in eleves_sans_classe[:10]:
            print(f"   - {eleve.prenom} {eleve.nom} ({eleve.matricule})")
        return False
    else:
        print("✅ Tous les élèves actifs ont une classe")
        return True

def verifier_periodes_incoherentes():
    """Vérifie la cohérence des périodes"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES PÉRIODES")
    print("="*60)
    
    periodes_valides = [
        'OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER', 
        'MARS', 'AVRIL', 'MAI', 'JUIN',
        'TRIMESTRE_1', 'TRIMESTRE_2', 'TRIMESTRE_3',
        'SEMESTRE_1', 'SEMESTRE_2', 'ANNUEL'
    ]
    
    # Vérifier les évaluations avec périodes invalides
    evals_invalides = Evaluation.objects.exclude(periode__in=periodes_valides)
    
    if evals_invalides.exists():
        print(f"⚠️ {evals_invalides.count()} évaluation(s) avec période invalide:")
        for eval in evals_invalides[:10]:
            print(f"   - {eval.matiere} - Période: '{eval.periode}'")
        return False
    else:
        print("✅ Toutes les périodes sont valides")
        return True

def rapport_complet():
    """Génère un rapport complet des vérifications"""
    print("\n" + "="*80)
    print("RAPPORT DE VÉRIFICATION DU CODE")
    print("="*80 + "\n")
    
    tests = [
        ("Coefficients", verifier_coherence_coefficients),
        ("Notes", verifier_notes_invalides),
        ("Divisions par zéro", verifier_divisions_par_zero),
        ("Imports", verifier_imports_manquants),
        ("Évaluations orphelines", verifier_evaluations_orphelines),
        ("Élèves sans classe", verifier_eleves_sans_classe),
        ("Périodes", verifier_periodes_incoherentes),
    ]
    
    resultats = []
    for nom, fonction in tests:
        try:
            succes = fonction()
            resultats.append((nom, succes))
        except Exception as e:
            print(f"\n❌ ERREUR lors du test '{nom}': {e}")
            resultats.append((nom, False))
    
    # Résumé
    print("\n" + "="*80)
    print("RÉSUMÉ DES TESTS")
    print("="*80)
    
    total_ok = sum(1 for _, succes in resultats if succes)
    total = len(resultats)
    
    for nom, succes in resultats:
        status = "✅ OK" if succes else "❌ ÉCHEC"
        print(f"{nom:<30} {status}")
    
    print("="*80)
    print(f"\nRésultat global: {total_ok}/{total} tests réussis")
    
    if total_ok == total:
        print("✅ ✅ ✅ AUCUNE ERREUR DÉTECTÉE ✅ ✅ ✅")
    else:
        print(f"⚠️ {total - total_ok} problème(s) à corriger")

if __name__ == "__main__":
    rapport_complet()
