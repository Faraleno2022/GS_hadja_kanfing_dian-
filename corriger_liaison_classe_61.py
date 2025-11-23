#!/usr/bin/env python
"""
Script pour corriger la liaison manquante entre ClasseNote et ClasseEleve pour la classe 61
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve, Ecole

def corriger_liaison_classe_61():
    """Corriger la liaison pour la classe 61"""
    print("🔧 CORRECTION LIAISON CLASSE 61")
    print("=" * 40)
    
    # 1. Récupérer la classe note 61
    try:
        classe_note = ClasseNote.objects.get(pk=61)
        print(f"✅ ClasseNote 61: {classe_note.nom}")
        print(f"   - École: {classe_note.ecole}")
        print(f"   - Année: {classe_note.annee_scolaire}")
    except ClasseNote.DoesNotExist:
        print("❌ ClasseNote 61 n'existe pas")
        return
    
    # 2. Vérifier si une ClasseEleve correspondante existe déjà
    classe_eleve_existante = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if classe_eleve_existante:
        print(f"✅ ClasseEleve correspondante existe déjà: {classe_eleve_existante}")
        return classe_eleve_existante
    
    # 3. Chercher une classe élève similaire à associer
    print("\n🔍 RECHERCHE CLASSE ÉLÈVE SIMILAIRE")
    print("-" * 35)
    
    # Chercher par nom similaire
    classes_similaires = ClasseEleve.objects.filter(
        nom__icontains="12",
        annee_scolaire=classe_note.annee_scolaire
    )
    
    print("Classes élèves 12ème disponibles:")
    for i, c in enumerate(classes_similaires, 1):
        print(f"   {i}. {c.nom} ({c.annee_scolaire}) - {c.ecole}")
    
    if not classes_similaires.exists():
        print("❌ Aucune classe élève 12ème trouvée")
        
        # 4. Créer une nouvelle ClasseEleve
        print("\n🆕 CRÉATION NOUVELLE CLASSE ÉLÈVE")
        print("-" * 35)
        
        try:
            nouvelle_classe = ClasseEleve.objects.create(
                nom=classe_note.nom,
                niveau=classe_note.niveau,
                annee_scolaire=classe_note.annee_scolaire,
                ecole=classe_note.ecole,
                effectif_max=50,  # Valeur par défaut
                description=f"Classe créée automatiquement pour liaison avec ClasseNote {classe_note.id}"
            )
            print(f"✅ Nouvelle ClasseEleve créée: {nouvelle_classe}")
            return nouvelle_classe
            
        except Exception as e:
            print(f"❌ Erreur lors de la création: {e}")
            return None
    
    else:
        # 5. Proposer d'utiliser une classe existante ou créer une nouvelle
        print(f"\n💡 SOLUTIONS POSSIBLES:")
        print("1. Utiliser une classe existante (recommandé si c'est la même classe)")
        print("2. Créer une nouvelle classe élève")
        print("3. Modifier le nom de la ClasseNote pour correspondre")
        
        # Pour l'automatisation, on va créer une nouvelle classe
        print(f"\n🆕 Création d'une nouvelle ClasseEleve pour '{classe_note.nom}'")
        
        try:
            nouvelle_classe = ClasseEleve.objects.create(
                nom=classe_note.nom,
                niveau=classe_note.niveau,
                annee_scolaire=classe_note.annee_scolaire,
                ecole=classe_note.ecole,
                effectif_max=50,
                description=f"Classe créée pour liaison avec ClasseNote {classe_note.id}"
            )
            print(f"✅ Nouvelle ClasseEleve créée: {nouvelle_classe}")
            return nouvelle_classe
            
        except Exception as e:
            print(f"❌ Erreur lors de la création: {e}")
            return None

def tester_consultation_apres_correction():
    """Tester la consultation après correction"""
    print("\n🧪 TEST CONSULTATION APRÈS CORRECTION")
    print("=" * 40)
    
    from notes.models import MatiereNote, Evaluation
    from eleves.models import Eleve
    
    # Récupérer la classe note 61
    classe_note = ClasseNote.objects.get(pk=61)
    
    # Vérifier la liaison
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if classe_eleve:
        print(f"✅ Liaison OK: ClasseNote 61 ↔ ClasseEleve {classe_eleve.id}")
        
        # Vérifier les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"📊 Élèves actifs: {eleves.count()}")
        
        # Vérifier les matières
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        print(f"📊 Matières actives: {matieres.count()}")
        
        # Vérifier les évaluations OCTOBRE
        evaluations_octobre = Evaluation.objects.filter(
            matiere__classe=classe_note,
            periode='OCTOBRE'
        )
        print(f"📊 Évaluations OCTOBRE: {evaluations_octobre.count()}")
        
        if eleves.count() == 0:
            print("⚠️  Pas d'élèves - Il faut inscrire des élèves dans cette classe")
        
        if matieres.count() == 0:
            print("⚠️  Pas de matières - Il faut créer des matières pour cette classe")
        
        if evaluations_octobre.count() == 0:
            print("⚠️  Pas d'évaluations OCTOBRE - Il faut créer des évaluations")
    
    else:
        print("❌ Liaison toujours manquante")

def creer_donnees_test():
    """Créer des données de test si nécessaire"""
    print("\n🎯 CRÉATION DONNÉES DE TEST")
    print("=" * 30)
    
    classe_note = ClasseNote.objects.get(pk=61)
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe_note.nom,
        annee_scolaire=classe_note.annee_scolaire,
        ecole=classe_note.ecole
    ).first()
    
    if not classe_eleve:
        print("❌ Pas de ClasseEleve - Exécutez d'abord la correction")
        return
    
    # Créer quelques matières si elles n'existent pas
    matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
    if matieres.count() == 0:
        print("🆕 Création de matières de test...")
        
        matieres_test = [
            ('Mathématiques', 4),
            ('Physique-Chimie', 3),
            ('SVT', 2),
            ('Français', 3),
            ('Anglais', 2),
        ]
        
        for nom, coef in matieres_test:
            matiere, created = MatiereNote.objects.get_or_create(
                classe=classe_note,
                nom=nom,
                defaults={
                    'code': nom[:3].upper(),
                    'coefficient': coef,
                    'actif': True,
                    'description': f'Matière créée automatiquement pour test'
                }
            )
            if created:
                print(f"   ✅ {nom} (coef: {coef})")
    
    # Créer une évaluation OCTOBRE si elle n'existe pas
    from notes.models import Evaluation
    evaluations_octobre = Evaluation.objects.filter(
        matiere__classe=classe_note,
        periode='OCTOBRE'
    )
    
    if evaluations_octobre.count() == 0:
        print("🆕 Création d'évaluations OCTOBRE de test...")
        
        matieres = MatiereNote.objects.filter(classe=classe_note, actif=True)
        for matiere in matieres[:3]:  # Créer pour les 3 premières matières
            evaluation, created = Evaluation.objects.get_or_create(
                matiere=matiere,
                titre=f"Devoir OCTOBRE - {matiere.nom}",
                periode='OCTOBRE',
                defaults={
                    'type_evaluation': 'DEVOIR',
                    'date_evaluation': '2024-10-15',
                    'note_sur': 20.0,
                    'coefficient': 1.0,
                    'description': 'Évaluation créée automatiquement pour test'
                }
            )
            if created:
                print(f"   ✅ {evaluation.titre}")

if __name__ == "__main__":
    try:
        # 1. Corriger la liaison
        classe_eleve = corriger_liaison_classe_61()
        
        # 2. Tester la consultation
        tester_consultation_apres_correction()
        
        # 3. Créer des données de test si nécessaire
        creer_donnees_test()
        
        print("\n🎉 CORRECTION TERMINÉE")
        print("=" * 25)
        print("✅ Vous pouvez maintenant tester l'URL:")
        print("   http://127.0.0.1:8000/notes/consulter/?classe_id=61&periode=OCTOBRE")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
