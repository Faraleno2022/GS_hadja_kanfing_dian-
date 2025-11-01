"""
Script pour gérer les notes mensuelles (système guinéen)
Permet de créer des évaluations mensuelles et saisir des notes
"""

import os
import django
from datetime import date, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe
from django.contrib.auth.models import User
from decimal import Decimal
import random

# Mapping des mois avec leurs dates
MOIS_DATES = {
    'OCTOBRE': (10, 2024),
    'NOVEMBRE': (11, 2024),
    'DECEMBRE': (12, 2024),
    'JANVIER': (1, 2025),
    'FEVRIER': (2, 2025),
    'MARS': (3, 2025),
    'AVRIL': (4, 2025),
    'MAI': (5, 2025),
    'JUIN': (6, 2025),
}

def creer_evaluations_mensuelles(classe_id, mois):
    """Créer des évaluations mensuelles pour une classe"""
    print(f"\n{'='*80}")
    print(f"   📅 CRÉATION D'ÉVALUATIONS MENSUELLES - {mois.upper()}")
    print(f"{'='*80}")
    
    # Récupérer la classe
    try:
        classe = ClasseNote.objects.get(pk=classe_id)
        print(f"\n✅ Classe: {classe.nom}")
    except ClasseNote.DoesNotExist:
        print(f"\n❌ Classe {classe_id} introuvable!")
        return
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe, actif=True)
    print(f"✅ Matières: {matieres.count()}")
    
    # Récupérer un utilisateur
    user = User.objects.first()
    
    # Date pour les évaluations
    mois_num, annee = MOIS_DATES.get(mois, (10, 2024))
    
    evaluations_creees = 0
    
    for matiere in matieres:
        # Vérifier si des évaluations existent déjà
        existing = Evaluation.objects.filter(
            matiere=matiere,
            periode=mois
        )
        
        if existing.exists():
            print(f"   ⚠️  {matiere.nom}: {existing.count()} évaluation(s) déjà existante(s)")
            continue
        
        # Créer 2 devoirs et 1 composition pour chaque matière
        # Devoir 1
        Evaluation.objects.create(
            matiere=matiere,
            titre=f"Devoir {mois.capitalize()} N°1",
            type_evaluation='DEVOIR',
            periode=mois,
            date_evaluation=date(annee, mois_num, 10),
            note_sur=20,
            coefficient=1,
            cree_par=user
        )
        
        # Devoir 2
        Evaluation.objects.create(
            matiere=matiere,
            titre=f"Devoir {mois.capitalize()} N°2",
            type_evaluation='DEVOIR',
            periode=mois,
            date_evaluation=date(annee, mois_num, 20),
            note_sur=20,
            coefficient=1,
            cree_par=user
        )
        
        # Composition
        Evaluation.objects.create(
            matiere=matiere,
            titre=f"Composition {mois.capitalize()}",
            type_evaluation='COMPOSITION',
            periode=mois,
            date_evaluation=date(annee, mois_num, 28) if mois_num != 2 else date(annee, 2, 25),
            note_sur=20,
            coefficient=2,
            cree_par=user
        )
        
        evaluations_creees += 3
        print(f"   ✅ {matiere.nom}: 3 évaluations créées")
    
    print(f"\n✅ Total: {evaluations_creees} évaluations créées pour {mois}")
    return evaluations_creees

def saisir_notes_mensuelles(classe_id, mois, nombre_eleves=None):
    """Saisir des notes aléatoires pour les évaluations mensuelles"""
    print(f"\n{'='*80}")
    print(f"   ✏️  SAISIE DE NOTES MENSUELLES - {mois.upper()}")
    print(f"{'='*80}")
    
    # Récupérer la classe
    try:
        classe = ClasseNote.objects.get(pk=classe_id)
        print(f"\n✅ Classe: {classe.nom}")
    except ClasseNote.DoesNotExist:
        print(f"\n❌ Classe {classe_id} introuvable!")
        return
    
    # Récupérer les élèves
    try:
        classe_eleve = Classe.objects.get(
            nom=classe.nom,
            annee_scolaire=classe.annee_scolaire
        )
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        
        if nombre_eleves:
            eleves = eleves[:nombre_eleves]
        
        print(f"✅ Élèves: {eleves.count()}")
    except Classe.DoesNotExist:
        print(f"❌ Classe élève non trouvée")
        return
    
    # Récupérer les évaluations du mois
    evaluations = Evaluation.objects.filter(
        matiere__classe=classe,
        periode=mois
    )
    
    if not evaluations.exists():
        print(f"\n❌ Aucune évaluation pour {mois}!")
        print(f"   Exécutez d'abord: creer_evaluations_mensuelles({classe_id}, '{mois}')")
        return
    
    print(f"✅ Évaluations: {evaluations.count()}")
    
    # Récupérer un utilisateur
    user = User.objects.first()
    
    notes_creees = 0
    notes_existantes = 0
    
    for eleve in eleves:
        for evaluation in evaluations:
            # Vérifier si la note existe déjà
            if NoteEleve.objects.filter(eleve=eleve, evaluation=evaluation).exists():
                notes_existantes += 1
                continue
            
            # Générer une note aléatoire
            if evaluation.type_evaluation in ['COMPOSITION', 'EXAMEN']:
                # Compositions: notes généralement plus élevées
                note = Decimal(str(round(random.uniform(11, 19), 2)))
            else:
                # Devoirs: plus de variation
                note = Decimal(str(round(random.uniform(8, 18), 2)))
            
            # Créer la note
            NoteEleve.objects.create(
                evaluation=evaluation,
                eleve=eleve,
                note=note,
                absent=False,
                cree_par=user
            )
            notes_creees += 1
    
    print(f"\n✅ {notes_creees} notes créées")
    if notes_existantes > 0:
        print(f"⚠️  {notes_existantes} notes déjà existantes (ignorées)")

def afficher_bulletin_mensuel(classe_id, mois, eleve_id):
    """Afficher un aperçu du bulletin mensuel pour un élève"""
    print(f"\n{'='*80}")
    print(f"   📊 BULLETIN MENSUEL - {mois.upper()}")
    print(f"{'='*80}")
    
    # Récupérer les données
    try:
        classe = ClasseNote.objects.get(pk=classe_id)
        eleve = Eleve.objects.get(pk=eleve_id)
        
        print(f"\n📚 Classe: {classe.nom}")
        print(f"👤 Élève: {eleve.nom} {eleve.prenom}")
        print(f"📅 Mois: {mois.capitalize()}")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return
    
    # Récupérer les matières
    matieres = MatiereNote.objects.filter(classe=classe, actif=True)
    
    print(f"\n{'─'*80}")
    print(f"{'MATIÈRE':<25} | {'NOTE':>6} | {'COEF':>4} | {'POINTS':>7}")
    print(f"{'─'*80}")
    
    total_points = Decimal('0')
    total_coef = Decimal('0')
    
    for matiere in matieres:
        # Récupérer les évaluations du mois
        evaluations = Evaluation.objects.filter(
            matiere=matiere,
            periode=mois
        )
        
        if not evaluations.exists():
            continue
        
        # Calculer la moyenne des notes
        total_notes = Decimal('0')
        count_notes = 0
        
        for evaluation in evaluations:
            try:
                note = NoteEleve.objects.get(eleve=eleve, evaluation=evaluation)
                if note.note is not None and not note.absent:
                    total_notes += note.note
                    count_notes += 1
            except NoteEleve.DoesNotExist:
                pass
        
        if count_notes > 0:
            moyenne = total_notes / count_notes
            points = moyenne * matiere.coefficient
            total_points += points
            total_coef += matiere.coefficient
            
            print(f"{matiere.nom[:24]:<25} | {float(moyenne):6.2f} | {float(matiere.coefficient):4} | {float(points):7.2f}")
        else:
            print(f"{matiere.nom[:24]:<25} | {'':>6} | {float(matiere.coefficient):4} | {'':>7}")
    
    print(f"{'─'*80}")
    
    if total_coef > 0:
        moyenne_generale = total_points / total_coef
        print(f"{'TOTAL':<25} | {'':>6} | {float(total_coef):4} | {float(total_points):7.2f}")
        print(f"{'─'*80}")
        print(f"\n{'MOYENNE GÉNÉRALE:':<25} {float(moyenne_generale):>6.2f}/20")
        
        # Mention
        moy = float(moyenne_generale)
        if moy >= 16:
            mention = "Très Bien"
        elif moy >= 14:
            mention = "Bien"
        elif moy >= 12:
            mention = "Assez Bien"
        elif moy >= 10:
            mention = "Passable"
        else:
            mention = "Insuffisant"
        
        print(f"{'MENTION:':<25} {mention}")
    else:
        print(f"\n⚠️  Aucune note disponible")
    
    # URL pour voir le bulletin complet
    url = f"http://127.0.0.1:8001/notes/bulletins/?classe_id={classe_id}&system_type=mensuel&periode={mois}&eleve_id={eleve_id}"
    print(f"\n🔗 URL DU BULLETIN COMPLET:")
    print(f"   {url}")

def menu_interactif():
    """Menu interactif pour gérer les notes mensuelles"""
    print("\n" + "="*80)
    print(" "*20 + "📅 GESTION DES NOTES MENSUELLES")
    print("="*80)
    
    print("\n1️⃣  Créer des évaluations mensuelles")
    print("2️⃣  Saisir des notes mensuelles")
    print("3️⃣  Afficher un bulletin mensuel")
    print("4️⃣  Tout faire automatiquement (création + saisie)")
    print("0️⃣  Quitter")
    
    choix = input("\n👉 Votre choix: ").strip()
    
    if choix == '1':
        classe_id = input("ID de la classe: ").strip()
        print("\nMois disponibles:")
        for i, mois in enumerate(MOIS_DATES.keys(), 1):
            print(f"   {i}. {mois.capitalize()}")
        mois_choix = input("Mois (ex: OCTOBRE): ").strip().upper()
        
        if mois_choix in MOIS_DATES:
            creer_evaluations_mensuelles(int(classe_id), mois_choix)
        else:
            print("❌ Mois invalide!")
    
    elif choix == '2':
        classe_id = input("ID de la classe: ").strip()
        mois_choix = input("Mois (ex: OCTOBRE): ").strip().upper()
        nb_eleves = input("Nombre d'élèves (laisser vide pour tous): ").strip()
        nb = int(nb_eleves) if nb_eleves else None
        
        if mois_choix in MOIS_DATES:
            saisir_notes_mensuelles(int(classe_id), mois_choix, nb)
        else:
            print("❌ Mois invalide!")
    
    elif choix == '3':
        classe_id = input("ID de la classe: ").strip()
        eleve_id = input("ID de l'élève: ").strip()
        mois_choix = input("Mois (ex: OCTOBRE): ").strip().upper()
        
        if mois_choix in MOIS_DATES:
            afficher_bulletin_mensuel(int(classe_id), mois_choix, int(eleve_id))
        else:
            print("❌ Mois invalide!")
    
    elif choix == '4':
        classe_id = input("ID de la classe (ex: 6): ").strip()
        mois_choix = input("Mois (ex: OCTOBRE): ").strip().upper()
        nb_eleves = input("Nombre d'élèves (ex: 5, laisser vide pour tous): ").strip()
        nb = int(nb_eleves) if nb_eleves else None
        
        if mois_choix in MOIS_DATES:
            creer_evaluations_mensuelles(int(classe_id), mois_choix)
            saisir_notes_mensuelles(int(classe_id), mois_choix, nb)
            print(f"\n✅ Évaluations et notes créées pour {mois_choix}")
        else:
            print("❌ Mois invalide!")

def mode_automatique():
    """Mode automatique pour tests rapides"""
    print("\n" + "="*80)
    print(" "*15 + "🚀 MODE AUTOMATIQUE - NOTES MENSUELLES")
    print("="*80)
    
    classe_id = 6
    mois = 'OCTOBRE'
    
    print(f"\n📋 Configuration:")
    print(f"   - Classe ID: {classe_id}")
    print(f"   - Mois: {mois}")
    print(f"   - Élèves: 5 premiers")
    
    # Créer les évaluations
    creer_evaluations_mensuelles(classe_id, mois)
    
    # Saisir les notes
    saisir_notes_mensuelles(classe_id, mois, 5)
    
    # Afficher un bulletin exemple
    afficher_bulletin_mensuel(classe_id, mois, 805)
    
    print(f"\n" + "="*80)
    print(" "*20 + "✅ NOTES MENSUELLES CRÉÉES")
    print("="*80)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        mode_automatique()
    else:
        menu_interactif()
