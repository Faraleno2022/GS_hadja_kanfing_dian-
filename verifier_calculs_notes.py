#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Vérification des Calculs de Notes
S'assure que toutes les fonctionnalités du système guinéen sont appliquées
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from decimal import Decimal
from notes.calculs import (
    calculer_moyenne_devoirs,
    calculer_moyenne_periode,
    calculer_moyenne_annuelle,
    calculer_moyenne_generale,
    calculer_moyenne_cours_mensuels,
    obtenir_mention,
    obtenir_appreciation,
    calculer_rang
)

def test_formule_40_60():
    """Test de la formule 40/60 pour le secondaire"""
    print("\n" + "="*80)
    print(" "*20 + "🧪 TEST FORMULE 40/60 (SECONDAIRE)")
    print("="*80)
    
    # Données de test
    moyenne_cours = Decimal('13.79')
    composition = Decimal('12.00')
    
    print(f"\n📊 Données:")
    print(f"   Moyenne de cours: {moyenne_cours}")
    print(f"   Composition: {composition}")
    
    # Calcul attendu
    attendu = (moyenne_cours * Decimal('0.4')) + (composition * Decimal('0.6'))
    print(f"\n📐 Calcul attendu:")
    print(f"   ({moyenne_cours} × 0.4) + ({composition} × 0.6)")
    print(f"   = {moyenne_cours * Decimal('0.4')} + {composition * Decimal('0.6')}")
    print(f"   = {attendu}")
    
    # Calcul avec la fonction
    resultat = calculer_moyenne_periode(moyenne_cours, composition, niveau='SECONDAIRE')
    print(f"\n📊 Résultat de la fonction:")
    print(f"   {resultat}")
    
    if abs(resultat - attendu) < Decimal('0.01'):
        print("\n   ✅ CONFORME - Formule 40/60 correcte")
        return True
    else:
        print(f"\n   ❌ ERREUR - Attendu: {attendu}, Obtenu: {resultat}")
        return False


def test_moyenne_cours_mensuels():
    """Test du calcul de moyenne des cours mensuels"""
    print("\n" + "="*80)
    print(" "*20 + "🧪 TEST MOYENNE COURS MENSUELS")
    print("="*80)
    
    # Notes mensuelles (exemple réel)
    notes_mensuelles = {
        'octobre': [Decimal('14'), Decimal('15')],
        'novembre': [Decimal('12'), Decimal('14')],
        'decembre': [Decimal('16'), Decimal('15')],
        'janvier': [Decimal('11'), Decimal('13'), Decimal('14')]
    }
    
    print(f"\n📊 Notes mensuelles:")
    for mois, notes in notes_mensuelles.items():
        moy_mois = sum(notes) / len(notes)
        print(f"   {mois.capitalize()}: {notes} → Moyenne: {moy_mois:.2f}")
    
    # Calcul manuel
    moy_oct = Decimal('14.5')
    moy_nov = Decimal('13')
    moy_dec = Decimal('15.5')
    moy_jan = Decimal('12.67')
    moyenne_attendue = (moy_oct + moy_nov + moy_dec + moy_jan) / 4
    
    print(f"\n📐 Calcul attendu:")
    print(f"   ({moy_oct} + {moy_nov} + {moy_dec} + {moy_jan}) / 4")
    print(f"   = {moyenne_attendue:.2f}")
    
    # Calcul avec la fonction
    resultat = calculer_moyenne_cours_mensuels(notes_mensuelles)
    print(f"\n📊 Résultat de la fonction:")
    print(f"   {resultat}")
    
    if abs(resultat - moyenne_attendue) < Decimal('0.01'):
        print("\n   ✅ CONFORME - Moyenne cours mensuels correcte")
        return True
    else:
        print(f"\n   ❌ ERREUR - Attendu: {moyenne_attendue:.2f}, Obtenu: {resultat}")
        return False


def test_scenario_complet_secondaire():
    """Test d'un scénario complet pour un élève du secondaire"""
    print("\n" + "="*80)
    print(" "*15 + "🧪 SCÉNARIO COMPLET - ÉLÈVE SECONDAIRE")
    print("="*80)
    
    print("\n📚 Élève: Mariama CAMARA - 9ème Année - Mathématiques (Coef 4)")
    print("─"*80)
    
    # SEMESTRE 1
    print("\n📅 SEMESTRE 1")
    print("─"*80)
    
    notes_s1 = {
        'octobre': [Decimal('13'), Decimal('15')],
        'novembre': [Decimal('12'), Decimal('14')],
        'decembre': [Decimal('16'), Decimal('15')],
        'janvier': [Decimal('11'), Decimal('13'), Decimal('14')]
    }
    
    for mois, notes in notes_s1.items():
        moy = sum(notes) / len(notes)
        print(f"   {mois.capitalize()}: {notes} → Moy: {moy:.2f}")
    
    moy_cours_s1 = calculer_moyenne_cours_mensuels(notes_s1)
    print(f"\n   Moyenne de cours S1: {moy_cours_s1}")
    
    compo_s1 = Decimal('12')
    print(f"   Composition S1: {compo_s1}")
    
    note_s1 = calculer_moyenne_periode(moy_cours_s1, compo_s1, niveau='SECONDAIRE')
    print(f"   Note S1 (40% + 60%): {note_s1}")
    
    # SEMESTRE 2
    print("\n📅 SEMESTRE 2")
    print("─"*80)
    
    notes_s2 = {
        'mars': [Decimal('15'), Decimal('14')],
        'avril': [Decimal('16'), Decimal('15')],
        'mai': [Decimal('17'), Decimal('16')],
        'juin': [Decimal('14'), Decimal('15')]
    }
    
    for mois, notes in notes_s2.items():
        moy = sum(notes) / len(notes)
        print(f"   {mois.capitalize()}: {notes} → Moy: {moy:.2f}")
    
    moy_cours_s2 = calculer_moyenne_cours_mensuels(notes_s2)
    print(f"\n   Moyenne de cours S2: {moy_cours_s2}")
    
    compo_s2 = Decimal('14')
    print(f"   Composition S2: {compo_s2}")
    
    note_s2 = calculer_moyenne_periode(moy_cours_s2, compo_s2, niveau='SECONDAIRE')
    print(f"   Note S2 (40% + 60%): {note_s2}")
    
    # MOYENNE ANNUELLE
    print("\n📊 MOYENNE ANNUELLE")
    print("─"*80)
    
    moy_annuelle = calculer_moyenne_annuelle([note_s1, note_s2])
    print(f"   Moyenne annuelle Maths: {moy_annuelle}/20")
    
    # Vérification
    attendu = Decimal('13.61')
    if abs(moy_annuelle - attendu) < Decimal('0.01'):
        print(f"   ✅ CONFORME - Attendu: {attendu}, Obtenu: {moy_annuelle}")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: {attendu}, Obtenu: {moy_annuelle}")
        return False


def test_scenario_complet_primaire():
    """Test d'un scénario complet pour un élève du primaire"""
    print("\n" + "="*80)
    print(" "*15 + "🧪 SCÉNARIO COMPLET - ÉLÈVE PRIMAIRE")
    print("="*80)
    
    print("\n📚 Élève: Fatou DIALLO - CM2 - Mathématiques")
    print("─"*80)
    
    # Compositions trimestrielles
    comp_t1 = Decimal('8.0')
    comp_t2 = Decimal('7.5')
    comp_t3 = Decimal('9.0')
    
    print(f"\n   Composition Trimestre 1: {comp_t1}/10")
    print(f"   Composition Trimestre 2: {comp_t2}/10")
    print(f"   Composition Trimestre 3: {comp_t3}/10")
    
    # Moyenne annuelle
    moy_annuelle = calculer_moyenne_annuelle([comp_t1, comp_t2, comp_t3])
    print(f"\n📊 Moyenne annuelle: {moy_annuelle}/10")
    
    # Vérification
    attendu = Decimal('8.17')
    if abs(moy_annuelle - attendu) < Decimal('0.01'):
        print(f"   ✅ CONFORME - Attendu: {attendu}, Obtenu: {moy_annuelle}")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: {attendu}, Obtenu: {moy_annuelle}")
        return False


def test_moyenne_generale_ponderee():
    """Test de la moyenne générale pondérée"""
    print("\n" + "="*80)
    print(" "*15 + "🧪 TEST MOYENNE GÉNÉRALE PONDÉRÉE")
    print("="*80)
    
    notes_matieres = {
        'maths': {'moyenne': Decimal('13.61'), 'coefficient': Decimal('4')},
        'francais': {'moyenne': Decimal('12.00'), 'coefficient': Decimal('4')},
        'anglais': {'moyenne': Decimal('14.00'), 'coefficient': Decimal('2')}
    }
    
    print("\n📊 Matières:")
    total_points = Decimal('0')
    total_coef = Decimal('0')
    for nom, data in notes_matieres.items():
        moy = data['moyenne']
        coef = data['coefficient']
        points = moy * coef
        print(f"   {nom.capitalize()}: {moy} × {coef} = {points:.2f} points")
        total_points += points
        total_coef += coef
    
    print(f"\n   Total points: {total_points:.2f}")
    print(f"   Total coefficients: {total_coef}")
    
    attendu = total_points / total_coef
    print(f"   Moyenne attendue: {attendu:.2f}")
    
    # Calcul avec la fonction
    resultat = calculer_moyenne_generale(notes_matieres, niveau='SECONDAIRE')
    print(f"\n📊 Résultat de la fonction: {resultat}")
    
    if abs(resultat - attendu) < Decimal('0.01'):
        print(f"   ✅ CONFORME - Moyenne pondérée correcte")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: {attendu:.2f}, Obtenu: {resultat}")
        return False


def test_moyenne_generale_simple():
    """Test de la moyenne générale simple (primaire)"""
    print("\n" + "="*80)
    print(" "*15 + "🧪 TEST MOYENNE GÉNÉRALE SIMPLE (PRIMAIRE)")
    print("="*80)
    
    notes_matieres = {
        'francais': {'moyenne': Decimal('8.0')},
        'maths': {'moyenne': Decimal('7.5')},
        'sciences': {'moyenne': Decimal('9.0')},
        'histoire': {'moyenne': Decimal('7.0')}
    }
    
    print("\n📊 Matières:")
    somme = Decimal('0')
    for nom, data in notes_matieres.items():
        moy = data['moyenne']
        print(f"   {nom.capitalize()}: {moy}")
        somme += moy
    
    attendu = somme / len(notes_matieres)
    print(f"\n   Moyenne attendue: {attendu:.2f}/10")
    
    # Calcul avec la fonction
    resultat = calculer_moyenne_generale(notes_matieres, niveau='PRIMAIRE')
    print(f"\n📊 Résultat de la fonction: {resultat}")
    
    if abs(resultat - attendu) < Decimal('0.01'):
        print(f"   ✅ CONFORME - Moyenne simple correcte")
        return True
    else:
        print(f"   ❌ ERREUR - Attendu: {attendu:.2f}, Obtenu: {resultat}")
        return False


def executer_verification():
    """Exécute tous les tests de vérification"""
    print("\n" + "="*80)
    print(" "*10 + "🔍 VÉRIFICATION COMPLÈTE DES CALCULS DE NOTES")
    print("="*80)
    
    tests = [
        ("Formule 40/60 (Secondaire)", test_formule_40_60),
        ("Moyenne cours mensuels", test_moyenne_cours_mensuels),
        ("Scénario complet Secondaire", test_scenario_complet_secondaire),
        ("Scénario complet Primaire", test_scenario_complet_primaire),
        ("Moyenne générale pondérée", test_moyenne_generale_ponderee),
        ("Moyenne générale simple", test_moyenne_generale_simple),
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
    print("\n" + "="*80)
    print(" "*25 + "📊 RÉSUMÉ")
    print("="*80)
    
    print("\n" + "─"*80)
    print(f"{'Test':<50} {'Statut':<30}")
    print("─"*80)
    
    tests_reussis = 0
    for nom, succes in resultats:
        statut = "✅ CONFORME" if succes else "❌ ÉCHEC"
        print(f"{nom:<50} {statut:<30}")
        if succes:
            tests_reussis += 1
    
    print("─"*80)
    print(f"\nRésultat global: {tests_reussis}/{len(resultats)} tests réussis")
    
    if tests_reussis == len(resultats):
        print("\n" + "="*80)
        print(" "*15 + "✅ TOUS LES CALCULS SONT CONFORMES")
        print("="*80)
        print("\n🎉 Le système de calcul de notes est 100% conforme !")
        print("\n✅ Fonctionnalités validées:")
        print("   • Formule 40/60 pour le secondaire")
        print("   • Moyenne des cours mensuels")
        print("   • Moyenne de période (trimestre/semestre)")
        print("   • Moyenne annuelle par matière")
        print("   • Moyenne générale pondérée (secondaire)")
        print("   • Moyenne générale simple (primaire)")
        print("\n🚀 SYSTÈME PRÊT POUR UTILISATION\n")
        return True
    else:
        print("\n" + "="*80)
        print(" "*20 + "⚠️  ATTENTION")
        print("="*80)
        print(f"\n❌ {len(resultats) - tests_reussis} test(s) échoué(s)")
        print("   Veuillez vérifier les erreurs ci-dessus.\n")
        return False


if __name__ == "__main__":
    try:
        succes = executer_verification()
        sys.exit(0 if succes else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Vérification interrompue\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
