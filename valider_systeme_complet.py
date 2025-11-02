#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Validation Complète du Système de Calcul de Notes Guinéen
Vérifie que toutes les spécifications sont implémentées correctement
"""

import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notes.calculateur_notes_guineen import (
    CalculateurNotes, NiveauScolaire, SystemeEvaluation,
    EleveSecondaire, ElevePrimaire
)

def afficher_titre(titre):
    """Affiche un titre formaté"""
    print("\n" + "=" * 80)
    print(f"   {titre}")
    print("=" * 80)

def test_formules_primaire():
    """Teste les formules pour le primaire"""
    afficher_titre("🔵 TEST PRIMAIRE - Formule de Calcul")
    
    print("\n📝 Spécification:")
    print("   Moyenne Annuelle = (Comp T1 + Comp T2 + Comp T3) / 3")
    
    print("\n🧪 Test avec données réelles:")
    print("   Compositions: 8.0, 7.5, 9.0")
    print("   Résultat attendu: 8.17/10")
    
    eleve = ElevePrimaire("DIALLO", "Fatou", "4ème Année")
    eleve.ajouter_matiere("Mathématiques")
    eleve.ajouter_composition("Mathématiques", 8.0)
    eleve.ajouter_composition("Mathématiques", 7.5)
    eleve.ajouter_composition("Mathématiques", 9.0)
    
    moyenne = eleve.calculer_moyenne_matiere("Mathématiques")
    print(f"\n   Résultat obtenu: {moyenne}/10")
    
    if abs(moyenne - 8.17) < 0.01:
        print("   ✅ CONFORME - Calcul exact")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: 8.17, Obtenu: {moyenne}")
        return False

def test_formules_secondaire_semestre():
    """Teste les formules pour le secondaire en système semestriel"""
    afficher_titre("🔴 TEST SECONDAIRE - Système Semestriel")
    
    print("\n📝 Spécifications:")
    print("   1. Moy Cours = Σ moyennes mensuelles / Nombre de mois")
    print("   2. Note Période = (Moy Cours × 40%) + (Composition × 60%)")
    print("   3. Moy Annuelle = (S1 + S2) / 2")
    
    print("\n🧪 Test Semestre 1:")
    print("   Notes mensuelles: Oct(14), Nov(13), Dec(15.5), Jan(12.67)")
    print("   Composition: 12")
    print("   Moy Cours attendue: 13.79")
    print("   Note S1 attendue: 12.72")
    
    eleve = EleveSecondaire("CAMARA", "Mariama", "9ème", SystemeEvaluation.SEMESTRE)
    eleve.ajouter_matiere("Mathématiques", 4)
    
    # Semestre 1
    notes_s1 = {
        'octobre': [14],
        'novembre': [13],
        'decembre': [15.5],
        'janvier': [12.67]
    }
    eleve.ajouter_notes_periode("Mathématiques", notes_s1, 12)
    
    print("\n🧪 Test Semestre 2:")
    print("   Notes mensuelles: Mars(14.5), Avr(15.5), Mai(16.5), Juin(14.5)")
    print("   Composition: 14")
    print("   Moy Cours attendue: 15.25")
    print("   Note S2 attendue: 14.50")
    
    # Semestre 2
    notes_s2 = {
        'mars': [14.5],
        'avril': [15.5],
        'mai': [16.5],
        'juin': [14.5]
    }
    eleve.ajouter_notes_periode("Mathématiques", notes_s2, 14)
    
    print("\n🧪 Test Moyenne Annuelle:")
    print("   Moy Annuelle attendue: 13.61")
    
    moyenne = eleve.calculer_moyenne_matiere("Mathématiques")
    print(f"   Résultat obtenu: {moyenne}/20")
    
    if abs(moyenne - 13.61) < 0.01:
        print("   ✅ CONFORME - Calcul exact (formule 40/60 respectée)")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: 13.61, Obtenu: {moyenne}")
        return False

def test_ponderation_40_60():
    """Teste spécifiquement la pondération 40/60"""
    afficher_titre("⚖️  TEST PONDÉRATION 40/60")
    
    print("\n📝 Spécification:")
    print("   Note Période = (Moy Cours × 40%) + (Composition × 60%)")
    
    print("\n🧪 Test simple:")
    print("   Moy Cours: 15.0")
    print("   Composition: 10.0")
    print("   Calcul: (15.0 × 0.4) + (10.0 × 0.6)")
    print("   Attendu: 6.0 + 6.0 = 12.0")
    
    calculateur = CalculateurNotes(NiveauScolaire.COLLEGE, SystemeEvaluation.TRIMESTRE)
    notes_mensuelles = {'octobre': [15.0]}
    resultat = calculateur.calculer_note_periode_secondaire(notes_mensuelles, 10.0)
    
    print(f"   Résultat obtenu: {resultat}")
    
    if abs(resultat - 12.0) < 0.01:
        print("   ✅ CONFORME - Pondération 40/60 respectée")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: 12.0, Obtenu: {resultat}")
        return False

def test_moyenne_ponderee():
    """Teste le calcul de moyenne pondérée avec coefficients"""
    afficher_titre("🎯 TEST MOYENNE PONDÉRÉE (Coefficients)")
    
    print("\n📝 Spécification:")
    print("   Moy Générale = Σ(Moy Matière × Coefficient) / Σ(Coefficients)")
    
    print("\n🧪 Test avec 3 matières:")
    print("   Maths (coef 4): 13.61")
    print("   Français (coef 4): 12.00")
    print("   Anglais (coef 2): 14.00")
    print("   Calcul: (13.61×4 + 12.00×4 + 14.00×2) / (4+4+2)")
    print("   Attendu: (54.44 + 48.00 + 28.00) / 10 = 130.44 / 10 = 13.04")
    
    eleve = EleveSecondaire("TEST", "Eleve", "9ème", SystemeEvaluation.SEMESTRE)
    
    # Maths
    eleve.ajouter_matiere("Mathématiques", 4)
    notes_s1_math = {'octobre': [13.61]}
    notes_s2_math = {'mars': [13.61]}
    eleve.ajouter_notes_periode("Mathématiques", notes_s1_math, 13.61)
    eleve.ajouter_notes_periode("Mathématiques", notes_s2_math, 13.61)
    
    # Français
    eleve.ajouter_matiere("Français", 4)
    notes_s1_fr = {'octobre': [12.00]}
    notes_s2_fr = {'mars': [12.00]}
    eleve.ajouter_notes_periode("Français", notes_s1_fr, 12.00)
    eleve.ajouter_notes_periode("Français", notes_s2_fr, 12.00)
    
    # Anglais
    eleve.ajouter_matiere("Anglais", 2)
    notes_s1_ang = {'octobre': [14.00]}
    notes_s2_ang = {'mars': [14.00]}
    eleve.ajouter_notes_periode("Anglais", notes_s1_ang, 14.00)
    eleve.ajouter_notes_periode("Anglais", notes_s2_ang, 14.00)
    
    bulletin = eleve.calculer_moyenne_generale()
    moyenne_generale = bulletin['moyenne_generale']
    
    print(f"   Résultat obtenu: {moyenne_generale}/20")
    
    if abs(moyenne_generale - 13.04) < 0.02:
        print("   ✅ CONFORME - Moyenne pondérée correcte")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: ~13.04, Obtenu: {moyenne_generale}")
        return False

def test_validation_donnees():
    """Teste les validations de données"""
    afficher_titre("🛡️  TEST VALIDATIONS")
    
    tests_reussis = 0
    tests_total = 0
    
    # Test 1: Primaire - 3 compositions obligatoires
    print("\n🧪 Test 1: Primaire - validation 3 compositions")
    tests_total += 1
    try:
        calculateur = CalculateurNotes(NiveauScolaire.PRIMAIRE, SystemeEvaluation.TRIMESTRE)
        calculateur.calculer_moyenne_annuelle_matiere_primaire([8.0, 7.5])  # Seulement 2
        print("   ❌ ÉCHEC - Devrait rejeter 2 compositions")
    except ValueError as e:
        if "3 compositions" in str(e):
            print("   ✅ CONFORME - Validation 3 compositions OK")
            tests_reussis += 1
        else:
            print(f"   ❌ Message incorrect: {e}")
    
    # Test 2: Primaire - notes entre 0 et 10
    print("\n🧪 Test 2: Primaire - validation notes 0-10")
    tests_total += 1
    try:
        eleve = ElevePrimaire("TEST", "Test", "CP1")
        eleve.ajouter_matiere("Maths")
        eleve.ajouter_composition("Maths", 15.0)  # Note > 10
        print("   ❌ ÉCHEC - Devrait rejeter note > 10")
    except ValueError as e:
        if "entre 0 et 10" in str(e):
            print("   ✅ CONFORME - Validation plage notes OK")
            tests_reussis += 1
        else:
            print(f"   ❌ Message incorrect: {e}")
    
    # Test 3: Secondaire - nombre de périodes
    print("\n🧪 Test 3: Secondaire - validation nombre périodes")
    tests_total += 1
    try:
        calculateur = CalculateurNotes(NiveauScolaire.COLLEGE, SystemeEvaluation.SEMESTRE)
        calculateur.calculer_moyenne_annuelle_matiere_secondaire([12.0, 13.0, 14.0])  # 3 au lieu de 2
        print("   ❌ ÉCHEC - Devrait rejeter 3 périodes pour semestre")
    except ValueError as e:
        if "Attendu: 2" in str(e):
            print("   ✅ CONFORME - Validation nombre périodes OK")
            tests_reussis += 1
        else:
            print(f"   ❌ Message incorrect: {e}")
    
    print(f"\n   📊 Validations: {tests_reussis}/{tests_total} réussies")
    return tests_reussis == tests_total

def test_systemes_evaluation():
    """Teste le support des deux systèmes d'évaluation"""
    afficher_titre("🔄 TEST SYSTÈMES D'ÉVALUATION")
    
    tests_reussis = 0
    
    # Test système semestriel (2 périodes)
    print("\n🧪 Test 1: Système Semestriel (2 périodes)")
    try:
        eleve = EleveSecondaire("TEST", "Semestre", "9ème", SystemeEvaluation.SEMESTRE)
        eleve.ajouter_matiere("Maths", 4)
        
        eleve.ajouter_notes_periode("Maths", {'octobre': [12]}, 12)
        eleve.ajouter_notes_periode("Maths", {'mars': [14]}, 14)
        
        moyenne = eleve.calculer_moyenne_matiere("Maths")
        print(f"   Moyenne calculée: {moyenne}")
        print("   ✅ CONFORME - Système semestriel OK")
        tests_reussis += 1
    except Exception as e:
        print(f"   ❌ ERREUR: {e}")
    
    # Test système trimestriel (3 périodes)
    print("\n🧪 Test 2: Système Trimestriel (3 périodes)")
    try:
        eleve = EleveSecondaire("TEST", "Trimestre", "9ème", SystemeEvaluation.TRIMESTRE)
        eleve.ajouter_matiere("Maths", 4)
        
        eleve.ajouter_notes_periode("Maths", {'octobre': [12]}, 12)
        eleve.ajouter_notes_periode("Maths", {'janvier': [13]}, 13)
        eleve.ajouter_notes_periode("Maths", {'avril': [14]}, 14)
        
        moyenne = eleve.calculer_moyenne_matiere("Maths")
        print(f"   Moyenne calculée: {moyenne}")
        print("   ✅ CONFORME - Système trimestriel OK")
        tests_reussis += 1
    except Exception as e:
        print(f"   ❌ ERREUR: {e}")
    
    return tests_reussis == 2

def executer_validation_complete():
    """Exécute tous les tests de validation"""
    afficher_titre("🚀 VALIDATION COMPLÈTE DU SYSTÈME")
    
    print("\nCe script vérifie que TOUTES les spécifications sont implémentées")
    print("conformément au système éducatif guinéen.\n")
    
    tests = [
        ("Formules Primaire", test_formules_primaire),
        ("Formules Secondaire Semestriel", test_formules_secondaire_semestre),
        ("Pondération 40/60", test_ponderation_40_60),
        ("Moyenne Pondérée", test_moyenne_ponderee),
        ("Validations Données", test_validation_donnees),
        ("Systèmes Évaluation", test_systemes_evaluation),
    ]
    
    resultats = []
    
    for nom, test_func in tests:
        try:
            succes = test_func()
            resultats.append((nom, succes))
        except Exception as e:
            print(f"\n❌ ERREUR dans {nom}: {e}")
            import traceback
            traceback.print_exc()
            resultats.append((nom, False))
    
    # Afficher le résumé
    afficher_titre("📊 RÉSUMÉ DE LA VALIDATION")
    
    print("\n" + "─" * 80)
    print(f"{'Test':<40} {'Statut':<40}")
    print("─" * 80)
    
    tests_reussis = 0
    for nom, succes in resultats:
        statut = "✅ CONFORME" if succes else "❌ ÉCHEC"
        print(f"{nom:<40} {statut:<40}")
        if succes:
            tests_reussis += 1
    
    print("─" * 80)
    print(f"\nRésultat global: {tests_reussis}/{len(resultats)} tests réussis")
    
    if tests_reussis == len(resultats):
        afficher_titre("✅ VALIDATION TOTALE RÉUSSIE")
        print("\n🎉 Le système est 100% conforme aux spécifications guinéennes !")
        print("\n✅ Toutes les fonctionnalités sont correctement implémentées:")
        print("   • Notes mensuelles → Moyenne de cours")
        print("   • Moyenne de cours + Composition → Note de période (40/60)")
        print("   • Notes de périodes → Moyenne annuelle")
        print("   • Moyennes matières → Moyenne générale (pondérée)")
        print("   • Support Primaire (/10) et Secondaire (/20)")
        print("   • Support Trimestre (3) et Semestre (2)")
        print("   • Validations robustes")
        print("\n🚀 SYSTÈME PRÊT POUR LA PRODUCTION\n")
        return True
    else:
        afficher_titre("⚠️  VALIDATION PARTIELLE")
        print(f"\n❌ {len(resultats) - tests_reussis} test(s) échoué(s)")
        print("   Veuillez vérifier les erreurs ci-dessus.\n")
        return False

if __name__ == "__main__":
    try:
        succes = executer_validation_complete()
        sys.exit(0 if succes else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrompue\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
