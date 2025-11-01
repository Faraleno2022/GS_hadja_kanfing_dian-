"""
Script de test pour vérifier la configuration des cartes scolaires
"""

import os
import sys

def verifier_configuration():
    print("\n" + "="*80)
    print(" "*20 + "🎴 TEST CONFIGURATION CARTES SCOLAIRES")
    print("="*80)
    
    resultats = []
    
    # Test 1: Vérifier les fonctions dans views.py
    print("\n1️⃣  Vérification des fonctions Python...")
    try:
        with open('eleves/views.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'def generer_carte_scolaire_pdf' in content:
            print("   ✅ Fonction generer_carte_scolaire_pdf trouvée")
            resultats.append(True)
        else:
            print("   ❌ Fonction generer_carte_scolaire_pdf manquante")
            resultats.append(False)
            
        if 'def generer_cartes_classe_pdf' in content:
            print("   ✅ Fonction generer_cartes_classe_pdf trouvée")
            resultats.append(True)
        else:
            print("   ❌ Fonction generer_cartes_classe_pdf manquante")
            resultats.append(False)
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        resultats.extend([False, False])
    
    # Test 2: Vérifier les URLs
    print("\n2️⃣  Vérification des routes URL...")
    try:
        with open('eleves/urls.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'carte-scolaire-pdf' in content:
            print("   ✅ Route carte-scolaire-pdf trouvée")
            resultats.append(True)
        else:
            print("   ❌ Route carte-scolaire-pdf manquante")
            resultats.append(False)
            
        if 'cartes-scolaires-pdf' in content:
            print("   ✅ Route cartes-scolaires-pdf trouvée")
            resultats.append(True)
        else:
            print("   ❌ Route cartes-scolaires-pdf manquante")
            resultats.append(False)
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        resultats.extend([False, False])
    
    # Test 3: Vérifier les templates
    print("\n3️⃣  Vérification des templates...")
    try:
        with open('templates/eleves/liste_eleves.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'cartes-scolaires-pdf' in content and 'en cours de développement' not in content:
            print("   ✅ Template liste_eleves.html mis à jour")
            resultats.append(True)
        else:
            print("   ⚠️  Template liste_eleves.html pourrait nécessiter une mise à jour")
            resultats.append(False)
            
        with open('templates/eleves/partials/_liste_eleves_results.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'carte-scolaire-pdf' in content and content.count('en cours de développement') <= 1:
            print("   ✅ Template _liste_eleves_results.html mis à jour")
            resultats.append(True)
        else:
            print("   ⚠️  Template _liste_eleves_results.html pourrait nécessiter une mise à jour")
            resultats.append(False)
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        resultats.extend([False, False])
    
    # Résumé
    print("\n" + "="*80)
    print(" "*25 + "📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    total = len(resultats)
    reussis = sum(resultats)
    
    print(f"\n   Tests réussis: {reussis}/{total}")
    
    if reussis == total:
        print("\n   ✅ CONFIGURATION COMPLÈTE ET OPÉRATIONNELLE!")
        print("\n   🚀 Prochaines étapes:")
        print("      1. Redémarrer le serveur Django")
        print("      2. Aller sur http://127.0.0.1:8000/eleves/liste/")
        print("      3. Tester la génération de cartes")
    elif reussis >= total * 0.7:
        print("\n   ⚠️  CONFIGURATION PARTIELLE")
        print("      Certains éléments nécessitent une attention")
    else:
        print("\n   ❌ CONFIGURATION INCOMPLÈTE")
        print("      Veuillez vérifier les erreurs ci-dessus")
    
    # URLs de test
    print("\n" + "="*80)
    print(" "*25 + "🔗 URLs DE TEST")
    print("="*80)
    
    print("\n   Carte individuelle (élève ID 8):")
    print("   http://127.0.0.1:8000/eleves/8/carte-scolaire-pdf/")
    
    print("\n   Cartes en masse (classe ID 1):")
    print("   http://127.0.0.1:8000/eleves/classe/1/cartes-scolaires-pdf/")
    
    print("\n   Interface utilisateur:")
    print("   http://127.0.0.1:8000/eleves/liste/")
    
    print("\n" + "="*80)
    print(" "*25 + "📚 DOCUMENTATION")
    print("="*80)
    
    print("\n   Guide complet:")
    print("   CARTES_SCOLAIRES_CONFIGURATION_COMPLETE.md")
    
    print("\n   Guide d'implémentation original:")
    print("   IMPLEMENTATION_CARTES_SCOLAIRES.md")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    verifier_configuration()
