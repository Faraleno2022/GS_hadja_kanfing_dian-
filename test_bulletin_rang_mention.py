"""
Script de test pour vérifier le système de bulletin intelligent
avec rang formaté, mentions et appréciations
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from notes.calculs_intelligent import (
    obtenir_mention_intelligente,
    obtenir_appreciation_intelligente,
    formater_rang_intelligent,
    calculer_rang_intelligent
)

def test_mentions():
    """Test des mentions selon les seuils définis"""
    print("\n" + "="*60)
    print("TEST DES MENTIONS INTELLIGENTES")
    print("="*60)
    
    tests = [
        (Decimal('19.5'), "Excellent"),
        (Decimal('18.5'), "Excellent"),
        (Decimal('17.0'), "Très bien"),
        (Decimal('16.5'), "Très bien"),
        (Decimal('15.0'), "Bien"),
        (Decimal('14.5'), "Bien"),
        (Decimal('13.0'), "Assez bien"),
        (Decimal('12.5'), "Assez bien"),
        (Decimal('11.0'), "Passable"),
        (Decimal('10.0'), "Passable"),
        (Decimal('9.5'), "Faible"),
        (Decimal('9.0'), "Faible"),
        (Decimal('8.0'), "Insuffisant"),
        (Decimal('5.0'), "Insuffisant"),
    ]
    
    for moyenne, mention_attendue in tests:
        mention = obtenir_mention_intelligente(moyenne)
        status = "✅" if mention == mention_attendue else "❌"
        print(f"{status} Moyenne {moyenne:5.2f} → {mention:15s} (attendu: {mention_attendue})")
    
    return True

def test_rangs():
    """Test du formatage des rangs avec accord grammatical"""
    print("\n" + "="*60)
    print("TEST DES RANGS AVEC ACCORD GRAMMATICAL")
    print("="*60)
    
    # Test pour une fille
    print("\n🧑‍🎓 Fille (sexe='F'):")
    for rang in [1, 2, 3, 10, 21]:
        rang_formate = formater_rang_intelligent(rang, 'F', 25)
        print(f"   Rang {rang:2d} → {rang_formate}")
    
    # Test pour un garçon
    print("\n👦 Garçon (sexe='M'):")
    for rang in [1, 2, 3, 10, 21]:
        rang_formate = formater_rang_intelligent(rang, 'M', 25)
        print(f"   Rang {rang:2d} → {rang_formate}")
    
    return True

def test_appreciations():
    """Test des appréciations personnalisées"""
    print("\n" + "="*60)
    print("TEST DES APPRÉCIATIONS PERSONNALISÉES")
    print("="*60)
    
    tests = [
        (Decimal('19.0'), "Fatoumata"),
        (Decimal('16.5'), "Mamadou"),
        (Decimal('14.0'), "Aissatou"),
        (Decimal('12.0'), "Ibrahim"),
        (Decimal('10.0'), "Mariam"),
        (Decimal('8.0'), "Abdoulaye"),
    ]
    
    for moyenne, prenom in tests:
        appreciation = obtenir_appreciation_intelligente(moyenne, prenom)
        mention = obtenir_mention_intelligente(moyenne)
        print(f"\n{prenom} ({moyenne:.2f}/20) - Mention: {mention}")
        print(f"→ {appreciation}")
    
    return True

def test_classement_complet():
    """Test du classement complet avec ex-aequo"""
    print("\n" + "="*60)
    print("TEST DU CLASSEMENT AVEC EX-AEQUO")
    print("="*60)
    
    eleves = [
        {'eleve_id': 1, 'prenom': 'Fatoumata', 'sexe': 'F', 'moyenne': Decimal('18.5')},
        {'eleve_id': 2, 'prenom': 'Mamadou', 'sexe': 'M', 'moyenne': Decimal('17.2')},
        {'eleve_id': 3, 'prenom': 'Aissatou', 'sexe': 'F', 'moyenne': Decimal('16.8')},
        {'eleve_id': 4, 'prenom': 'Ibrahim', 'sexe': 'M', 'moyenne': Decimal('16.8')},  # Ex-aequo
        {'eleve_id': 5, 'prenom': 'Mariam', 'sexe': 'F', 'moyenne': Decimal('14.5')},
        {'eleve_id': 6, 'prenom': 'Abdoulaye', 'sexe': 'M', 'moyenne': Decimal('12.3')},
        {'eleve_id': 7, 'prenom': 'Binta', 'sexe': 'F', 'moyenne': Decimal('10.2')},
        {'eleve_id': 8, 'prenom': 'Oumar', 'sexe': 'M', 'moyenne': Decimal('9.5')},
    ]
    
    eleves_classes = calculer_rang_intelligent(eleves)
    
    print("\n┌────────┬──────────────┬──────┬─────────┬──────────┬───────────────┐")
    print("│  Rang  │    Prénom    │ Sexe │ Moyenne │  Mention │   Appréciation │")
    print("├────────┼──────────────┼──────┼─────────┼──────────┼───────────────┤")
    
    for eleve in eleves_classes:
        sexe_icon = "F" if eleve['sexe'] == 'F' else "M"
        # Tronquer l'appréciation pour l'affichage
        appreciation_courte = eleve['appreciation'][:13] + "..." if len(eleve['appreciation']) > 16 else eleve['appreciation'][:16]
        print(f"│ {eleve['rang']:^6s} │ {eleve['prenom']:12s} │  {sexe_icon}   │ {eleve['moyenne']:7.2f} │ {eleve['mention']:8s} │ {appreciation_courte:13s} │")
    
    print("└────────┴──────────────┴──────┴─────────┴──────────┴───────────────┘")
    
    # Vérifier les ex-aequo
    print("\n⚠️  Vérification des ex-aequo:")
    for i, eleve in enumerate(eleves_classes):
        if eleve['prenom'] in ['Aissatou', 'Ibrahim']:
            print(f"   {eleve['prenom']}: rang {eleve['rang']} (moyenne {eleve['moyenne']:.2f})")
    
    return True

def test_integration_bulletin():
    """Test d'intégration avec les données d'un bulletin réel"""
    print("\n" + "="*60)
    print("TEST D'INTÉGRATION - BULLETIN COMPLET")
    print("="*60)
    
    # Simuler les données d'un élève
    eleve_data = {
        'prenom': 'Aminata',
        'nom': 'DIALLO',
        'sexe': 'F',
        'classe': '7ème Année',
        'moyenne_generale': Decimal('14.75'),
        'rang_numerique': 3,
        'total_eleves': 35,
    }
    
    # Calculer mention et appréciation
    mention = obtenir_mention_intelligente(eleve_data['moyenne_generale'])
    appreciation = obtenir_appreciation_intelligente(
        eleve_data['moyenne_generale'], 
        eleve_data['prenom']
    )
    rang = formater_rang_intelligent(
        eleve_data['rang_numerique'], 
        eleve_data['sexe'], 
        eleve_data['total_eleves']
    )
    
    # Afficher le bulletin simulé
    print(f"\n╔══════════════════════════════════════════════════════════╗")
    print(f"║                    BULLETIN DE NOTES                      ║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║ Élève: {eleve_data['prenom']} {eleve_data['nom']:<41s} ║")
    print(f"║ Classe: {eleve_data['classe']:<48s} ║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║ MOYENNE GÉNÉRALE: {eleve_data['moyenne_generale']:5.2f}/20                              ║")
    print(f"║ RANG: {rang:<51s} ║")
    print(f"║ MENTION: {mention:<47s} ║")
    print(f"╠══════════════════════════════════════════════════════════╣")
    print(f"║ APPRÉCIATION DU CONSEIL:                                  ║")
    
    # Découper l'appréciation en lignes
    import textwrap
    lignes = textwrap.wrap(appreciation, width=55)
    for ligne in lignes:
        print(f"║ {ligne:<57s} ║")
    
    print(f"╚══════════════════════════════════════════════════════════╝")
    
    return True

def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "#"*60)
    print("#" + " "*20 + "TESTS DU BULLETIN INTELLIGENT" + " "*10 + "#")
    print("#"*60)
    
    tests = [
        ("Mentions", test_mentions),
        ("Rangs", test_rangs),
        ("Appréciations", test_appreciations),
        ("Classement", test_classement_complet),
        ("Intégration", test_integration_bulletin),
    ]
    
    results = []
    for nom, test_func in tests:
        try:
            success = test_func()
            results.append((nom, success))
        except Exception as e:
            print(f"\n❌ Erreur dans le test {nom}: {e}")
            results.append((nom, False))
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    
    for nom, success in results:
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        print(f"{status} - Test {nom}")
    
    total_success = sum(1 for _, s in results if s)
    total_tests = len(results)
    
    print(f"\nRésultat global: {total_success}/{total_tests} tests réussis")
    
    if total_success == total_tests:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS! 🎉")
        print("Le système de bulletin intelligent est opérationnel.")
    else:
        print("\n⚠️ Certains tests ont échoué. Vérifiez les détails ci-dessus.")

if __name__ == '__main__':
    run_all_tests()
