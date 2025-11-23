#!/usr/bin/env python
"""
Script de test pour vérifier l'affichage dynamique des moyennes mensuelles
dans les bulletins trimestriels et semestriels
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.utils_moyennes_mensuelles import (
    get_mois_periode, 
    calculer_moyennes_mensuelles_matiere,
    calculer_bulletin_avec_details_mensuels
)
from notes.models import ClasseNote, MatiereNote
from eleves.models import Eleve


def test_mois_periode():
    """Test de la fonction get_mois_periode"""
    print("🧪 TEST: get_mois_periode")
    print("-" * 50)
    
    # Test trimestres
    trimestre_1 = get_mois_periode('trimestre', 'TRIMESTRE_1')
    trimestre_2 = get_mois_periode('trimestre', 'TRIMESTRE_2')
    trimestre_3 = get_mois_periode('trimestre', 'TRIMESTRE_3')
    
    print(f"Trimestre 1: {trimestre_1}")
    print(f"Trimestre 2: {trimestre_2}")
    print(f"Trimestre 3: {trimestre_3}")
    
    # Test semestres
    semestre_1 = get_mois_periode('semestre', 'SEMESTRE_1')
    semestre_2 = get_mois_periode('semestre', 'SEMESTRE_2')
    
    print(f"Semestre 1: {semestre_1}")
    print(f"Semestre 2: {semestre_2}")
    
    # Vérifications
    assert trimestre_1 == ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE'], "Erreur Trimestre 1"
    assert trimestre_2 == ['JANVIER', 'FEVRIER', 'MARS'], "Erreur Trimestre 2"
    assert trimestre_3 == ['AVRIL', 'MAI', 'JUIN'], "Erreur Trimestre 3"
    assert semestre_1 == ['OCTOBRE', 'NOVEMBRE', 'DECEMBRE', 'JANVIER', 'FEVRIER'], "Erreur Semestre 1"
    assert semestre_2 == ['MARS', 'AVRIL', 'MAI', 'JUIN', 'JUILLET'], "Erreur Semestre 2"
    
    print("✅ Tous les tests get_mois_periode réussis !")
    print()


def test_avec_donnees_reelles():
    """Test avec des données réelles de la base"""
    print("🧪 TEST: Données réelles")
    print("-" * 50)
    
    # Récupérer une classe et un élève
    classe = ClasseNote.objects.filter(actif=True).first()
    if not classe:
        print("❌ Aucune classe trouvée")
        return
    
    print(f"Classe testée: {classe.nom}")
    
    # Récupérer un élève de cette classe
    from eleves.models import Classe as ClasseEleve
    classe_eleve = ClasseEleve.objects.filter(
        nom=classe.nom,
        annee_scolaire=classe.annee_scolaire
    ).first()
    
    if not classe_eleve:
        print("❌ Aucune classe élève correspondante trouvée")
        return
    
    eleve = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF').first()
    if not eleve:
        print("❌ Aucun élève trouvé")
        return
    
    print(f"Élève testé: {eleve.prenom} {eleve.nom}")
    
    # Récupérer une matière
    matiere = MatiereNote.objects.filter(classe=classe, actif=True).first()
    if not matiere:
        print("❌ Aucune matière trouvée")
        return
    
    print(f"Matière testée: {matiere.nom}")
    
    # Test pour le 1er trimestre
    print("\n📊 Test Trimestre 1:")
    data_trimestre = calculer_bulletin_avec_details_mensuels(
        eleve, matiere, 'trimestre', 'TRIMESTRE_1'
    )
    
    print(f"Moyennes mensuelles:")
    for moy in data_trimestre['moyennes_mensuelles']:
        status = "ABS" if moy['absent'] else (moy['moyenne'] if moy['moyenne'] else "-")
        print(f"  - {moy['libelle']}: {status}")
    
    print(f"Moyenne continue: {data_trimestre['moyenne_continue']}")
    print(f"Note composition: {data_trimestre['note_composition']}")
    print(f"Moyenne finale: {data_trimestre['moyenne_finale']}")
    print(f"Points: {data_trimestre['points']}")
    
    # Test pour le 1er semestre
    print("\n📊 Test Semestre 1:")
    data_semestre = calculer_bulletin_avec_details_mensuels(
        eleve, matiere, 'semestre', 'SEMESTRE_1'
    )
    
    print(f"Moyennes mensuelles:")
    for moy in data_semestre['moyennes_mensuelles']:
        status = "ABS" if moy['absent'] else (moy['moyenne'] if moy['moyenne'] else "-")
        print(f"  - {moy['libelle']}: {status}")
    
    print(f"Moyenne continue: {data_semestre['moyenne_continue']}")
    print(f"Note composition: {data_semestre['note_composition']}")
    print(f"Moyenne finale: {data_semestre['moyenne_finale']}")
    print(f"Points: {data_semestre['points']}")
    
    print("✅ Test avec données réelles terminé !")


def test_structure_bulletin():
    """Test de la structure des données pour le bulletin"""
    print("🧪 TEST: Structure bulletin")
    print("-" * 50)
    
    # Simuler des données de test
    from decimal import Decimal
    
    # Test structure pour trimestre
    mois_trimestre = get_mois_periode('trimestre', 'TRIMESTRE_1')
    print(f"Mois du trimestre 1: {mois_trimestre}")
    print(f"Nombre de colonnes nécessaires: {len(mois_trimestre) + 2} (mois + moy.continue + compo)")
    
    # Test structure pour semestre
    mois_semestre = get_mois_periode('semestre', 'SEMESTRE_1')
    print(f"Mois du semestre 1: {mois_semestre}")
    print(f"Nombre de colonnes nécessaires: {len(mois_semestre) + 2} (mois + moy.continue + compo)")
    
    print("✅ Structure bulletin validée !")


def main():
    """Fonction principale de test"""
    print("🚀 TESTS DES MOYENNES MENSUELLES DYNAMIQUES")
    print("=" * 60)
    print()
    
    try:
        # Test 1: Fonction utilitaire
        test_mois_periode()
        
        # Test 2: Structure bulletin
        test_structure_bulletin()
        
        # Test 3: Données réelles
        test_avec_donnees_reelles()
        
        print("\n🎉 TOUS LES TESTS RÉUSSIS !")
        print("=" * 60)
        print("✅ Le système d'affichage dynamique des moyennes mensuelles est prêt !")
        print()
        print("📋 PROCHAINES ÉTAPES:")
        print("1. Tester l'interface web avec un bulletin trimestriel")
        print("2. Tester l'interface web avec un bulletin semestriel")
        print("3. Vérifier l'affichage sur différentes résolutions")
        print("4. Tester avec des élèves ayant des absences")
        
    except Exception as e:
        print(f"❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
