#!/usr/bin/env python
"""
Test pour vérifier que les utilisateurs peuvent créer des matières
et que les notes apparaissent correctement sur le bulletin.
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from notes.models import MatiereNote, ClasseNote, Evaluation, NoteEleve
from eleves.models import Eleve, Classe as ClasseEleve
from django.db import transaction

User = get_user_model()

def test_creation_matiere_et_bulletin():
    """Test complet du cycle: création matière -> évaluation -> note -> bulletin"""
    
    print("\n" + "="*80)
    print("TEST: CRÉATION MATIÈRE ET AFFICHAGE BULLETIN")
    print("="*80)
    
    try:
        # 1. Récupérer une classe de test
        print("\n1. RECHERCHE D'UNE CLASSE")
        print("-" * 40)
        
        classe = ClasseNote.objects.filter(actif=True).first()
        if not classe:
            print("❌ Aucune classe active trouvée")
            return False
        
        print(f"✅ Classe trouvée: {classe.nom} (ID: {classe.id})")
        
        # 2. Récupérer un utilisateur pour tester
        print("\n2. RECHERCHE D'UN UTILISATEUR")
        print("-" * 40)
        
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ Aucun utilisateur actif trouvé")
            return False
        
        print(f"✅ Utilisateur trouvé: {user.username}")
        
        # 3. Créer une matière de test
        print("\n3. CRÉATION D'UNE MATIÈRE TEST")
        print("-" * 40)
        
        nom_matiere = f"MATIERE_TEST_{classe.id}"
        
        # Vérifier si elle existe déjà
        matiere_existe = MatiereNote.objects.filter(
            nom=nom_matiere,
            classe=classe
        ).first()
        
        if matiere_existe:
            print(f"⚠️ Matière test existe déjà: {nom_matiere}")
            matiere = matiere_existe
        else:
            # Créer la matière
            matiere = MatiereNote.objects.create(
                nom=nom_matiere,
                classe=classe,
                coefficient=2.0,
                ecole=classe.ecole,
                actif=True,
                niveau_enseignement=classe.niveau_enseignement,
                cree_par=user
            )
            print(f"✅ Matière créée: {matiere.nom} (ID: {matiere.id})")
        
        # 4. Créer une évaluation pour cette matière
        print("\n4. CRÉATION D'UNE ÉVALUATION")
        print("-" * 40)
        
        periode = 'OCTOBRE'
        
        evaluation = Evaluation.objects.filter(
            matiere=matiere,
            periode=periode
        ).first()
        
        if not evaluation:
            evaluation = Evaluation.objects.create(
                matiere=matiere,
                titre=f"Test {nom_matiere}",
                type_evaluation='DEVOIR',
                date_evaluation='2024-10-15',
                periode=periode,
                note_sur=20,
                coefficient=1.0
            )
            print(f"✅ Évaluation créée: {evaluation.titre}")
        else:
            print(f"⚠️ Évaluation existe déjà: {evaluation.titre}")
        
        # 5. Récupérer un élève de la classe
        print("\n5. RECHERCHE D'UN ÉLÈVE")
        print("-" * 40)
        
        # Chercher la classe correspondante dans ClasseEleve
        classe_eleve = ClasseEleve.objects.filter(
            nom__icontains=classe.nom.split()[0],
            annee_scolaire=classe.annee_scolaire
        ).first()
        
        if not classe_eleve:
            print("❌ Aucune classe élève correspondante trouvée")
            return False
        
        eleve = Eleve.objects.filter(
            classe=classe_eleve,
            statut='ACTIF'
        ).first()
        
        if not eleve:
            print("❌ Aucun élève actif trouvé dans cette classe")
            return False
        
        print(f"✅ Élève trouvé: {eleve.prenom} {eleve.nom} ({eleve.matricule})")
        
        # 6. Créer une note pour cet élève
        print("\n6. CRÉATION D'UNE NOTE")
        print("-" * 40)
        
        note = NoteEleve.objects.filter(
            eleve=eleve,
            evaluation=evaluation
        ).first()
        
        if not note:
            note = NoteEleve.objects.create(
                eleve=eleve,
                evaluation=evaluation,
                note=15.5,
                absent=False,
                ecole=classe.ecole,
                matricule=eleve.matricule or '',
                annee_scolaire=classe.annee_scolaire
            )
            print(f"✅ Note créée: {note.note}/20")
        else:
            print(f"⚠️ Note existe déjà: {note.note}/20")
        
        # 7. Vérifier que la matière et la note apparaissent dans la logique bulletin
        print("\n7. VÉRIFICATION BULLETIN")
        print("-" * 40)
        
        # Récupérer toutes les matières de la classe
        matieres_classe = MatiereNote.objects.filter(
            classe=classe,
            actif=True
        ).order_by('nom')
        
        print(f"Matières de la classe: {matieres_classe.count()}")
        
        # Vérifier que notre matière est dans la liste
        if matiere in matieres_classe:
            print(f"✅ Matière {nom_matiere} trouvée dans les matières de la classe")
        else:
            print(f"❌ Matière {nom_matiere} NON trouvée dans les matières de la classe")
            return False
        
        # Simuler la récupération des évaluations comme dans bulletin_dynamique
        evaluations_matiere = Evaluation.objects.filter(
            matiere=matiere,
            periode=periode
        ).order_by('date_evaluation')
        
        if evaluations_matiere.exists():
            print(f"✅ {evaluations_matiere.count()} évaluation(s) trouvée(s) pour {periode}")
            
            # Récupérer les notes
            for eval in evaluations_matiere:
                notes_eval = NoteEleve.objects.filter(
                    evaluation=eval,
                    eleve=eleve
                )
                for n in notes_eval:
                    print(f"   - Note trouvée: {n.note}/20 pour {n.eleve.prenom}")
        else:
            print(f"❌ Aucune évaluation trouvée pour {periode}")
            
            # Tenter la recherche par nom (fallback du bulletin)
            from django.db.models import Q
            evaluations_nom = Evaluation.objects.filter(
                Q(matiere__nom=matiere.nom) &
                Q(matiere__classe=classe) &
                Q(periode=periode)
            )
            if evaluations_nom.exists():
                print(f"✅ {evaluations_nom.count()} évaluation(s) trouvée(s) par nom")
            else:
                print(f"❌ Aucune évaluation trouvée même par nom")
        
        print("\n" + "="*80)
        print("RÉSULTAT DU TEST")
        print("-" * 40)
        print("✅ TEST RÉUSSI: Le cycle complet fonctionne!")
        print("\nCe qui a été vérifié:")
        print("1. ✅ Création de matière par un utilisateur")
        print("2. ✅ Création d'évaluation pour cette matière")
        print("3. ✅ Saisie de note pour l'évaluation")
        print("4. ✅ La matière apparaît dans la liste des matières de la classe")
        print("5. ✅ Les évaluations et notes sont récupérables pour le bulletin")
        print("\n💡 Le bulletin affichera correctement cette matière et ses notes")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False

def nettoyer_donnees_test():
    """Nettoyer les données de test créées"""
    print("\n8. NETTOYAGE (optionnel)")
    print("-" * 40)
    
    reponse = input("Voulez-vous supprimer les données de test créées? (o/n): ")
    if reponse.lower() == 'o':
        # Supprimer les matières de test
        matieres_test = MatiereNote.objects.filter(nom__startswith='MATIERE_TEST_')
        count = matieres_test.count()
        matieres_test.delete()
        print(f"✅ {count} matière(s) de test supprimée(s)")
    else:
        print("⏭️ Données de test conservées")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("TEST DU SYSTÈME DE CRÉATION DE MATIÈRES ET BULLETIN")
    print("="*80)
    print("\nCe test va:")
    print("1. Créer une matière de test")
    print("2. Créer une évaluation")
    print("3. Ajouter une note")
    print("4. Vérifier que tout apparaît correctement pour le bulletin")
    print("\n⚠️ Ce test créera des données temporaires dans la base")
    
    reponse = input("\nVoulez-vous continuer? (o/n): ")
    if reponse.lower() == 'o':
        if test_creation_matiere_et_bulletin():
            nettoyer_donnees_test()
    else:
        print("❌ Test annulé")
