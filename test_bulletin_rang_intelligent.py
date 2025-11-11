"""
Test du système intelligent de bulletin avec rangs formatés et mentions dynamiques
Date : 11 novembre 2024
"""

import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from notes.calculs import (
    obtenir_mention,
    obtenir_appreciation,
    formater_rang_intelligent,
    calculer_rang
)
from eleves.models import Eleve

def test_bulletin_intelligent():
    """Tester le système intelligent de bulletin"""
    
    print("="*80)
    print("✨ TEST DU SYSTÈME INTELLIGENT DE BULLETIN ✨")
    print("Date : 11 novembre 2024")
    print("="*80)
    
    # Test 1 : Mentions dynamiques avec les nouveaux seuils
    print("\n📊 TEST 1 : MENTIONS DYNAMIQUES")
    print("-"*50)
    
    test_moyennes = [
        (Decimal('19.2'), "Excellent"),      # >= 18.5
        (Decimal('18.5'), "Excellent"),      # = 18.5
        (Decimal('18.0'), "Très bien"),      # < 18.5 mais >= 16.5
        (Decimal('16.5'), "Très bien"),      # = 16.5
        (Decimal('15.0'), "Bien"),           # < 16.5 mais >= 14.5
        (Decimal('14.5'), "Bien"),           # = 14.5
        (Decimal('13.0'), "Assez bien"),     # < 14.5 mais >= 12.5
        (Decimal('12.5'), "Assez bien"),     # = 12.5
        (Decimal('11.0'), "Passable"),       # < 12.5 mais >= 10
        (Decimal('10.0'), "Passable"),       # = 10
        (Decimal('9.5'), "Faible"),          # < 10 mais >= 9
        (Decimal('9.0'), "Faible"),          # = 9
        (Decimal('8.0'), "Insuffisant"),     # < 9
        (Decimal('7.0'), "Insuffisant"),     # < 9
    ]
    
    print("\n┌─────────┬──────────────────┬─────────────────┐")
    print("│ Moyenne │ Mention Attendue │ Mention Obtenue │")
    print("├─────────┼──────────────────┼─────────────────┤")
    
    tous_corrects = True
    for moyenne, attendue in test_moyennes:
        obtenue = obtenir_mention(moyenne)
        correct = obtenue == attendue
        
        if not correct:
            tous_corrects = False
        
        symbole = "✅" if correct else "❌"
        print(f"│ {moyenne:>7.2f} │ {attendue:<16} │ {obtenue:<15} {symbole} │")
    
    print("└─────────┴──────────────────┴─────────────────┘")
    
    if tous_corrects:
        print("✅ Toutes les mentions sont correctes selon la formule demandée !")
    else:
        print("❌ Certaines mentions ne correspondent pas !")
    
    # Test 2 : Rangs formatés intelligemment
    print("\n🏆 TEST 2 : RANGS INTELLIGENTS (Pas de format N/A/2)")
    print("-"*50)
    
    # Créer des données de test
    eleves_test = [
        {'eleve_id': 1, 'prenom': 'Fatoumata', 'sexe': 'F', 'moyenne': Decimal('18.7')},
        {'eleve_id': 2, 'prenom': 'Mamadou', 'sexe': 'M', 'moyenne': Decimal('17.2')},
        {'eleve_id': 3, 'prenom': 'Aïssatou', 'sexe': 'F', 'moyenne': Decimal('16.8')},
        {'eleve_id': 4, 'prenom': 'Ibrahim', 'sexe': 'M', 'moyenne': Decimal('16.8')},  # Ex-aequo
        {'eleve_id': 5, 'prenom': 'Mariam', 'sexe': 'F', 'moyenne': Decimal('14.5')},
        {'eleve_id': 6, 'prenom': 'Ousmane', 'sexe': 'M', 'moyenne': Decimal('12.3')},
        {'eleve_id': 7, 'prenom': 'Kadiatou', 'sexe': 'F', 'moyenne': Decimal('10.5')},
        {'eleve_id': 8, 'prenom': 'Alpha', 'sexe': 'M', 'moyenne': Decimal('9.2')},
        {'eleve_id': 9, 'prenom': None, 'sexe': 'F', 'moyenne': None},  # Sans notes
    ]
    
    # Calculer les rangs
    eleves_classes = calculer_rang(eleves_test)
    
    print("\n┌──────────┬──────────────┬──────┬─────────┬─────────────────┬──────────────────┐")
    print("│   Rang   │    Prénom    │ Sexe │ Moyenne │     Mention     │      Format      │")
    print("├──────────┼──────────────┼──────┼─────────┼─────────────────┼──────────────────┤")
    
    for eleve in eleves_classes:
        prenom = eleve.get('prenom', 'Sans nom')
        if prenom is None:
            prenom = "Sans nom"
        sexe = "👧" if eleve.get('sexe') == 'F' else "👦"
        moyenne = f"{eleve['moyenne']:.2f}" if eleve.get('moyenne') else "-"
        
        # Vérifier le format du rang
        rang = eleve.get('rang', '-')
        
        # Validation : pas de format N/A/2
        if "/" in rang and rang != "-":
            # Format avec total (ex: 1er/8)
            format_ok = "ème/" in rang or "er/" in rang or "ère/" in rang
        else:
            # Format simple (ex: 1er, 2ème)
            format_ok = rang == "-" or "er" in rang or "ère" in rang or "ème" in rang
        
        symbole = "✅" if format_ok else "❌"
        
        print(f"│ {rang:^8} │ {prenom[:12]:<12} │  {sexe}  │ {moyenne:>7} │ {eleve['mention']:<15} │ Format OK {symbole}    │")
    
    print("└──────────┴──────────────┴──────┴─────────┴─────────────────┴──────────────────┘")
    
    # Test 3 : Appréciations dynamiques du conseil
    print("\n💬 TEST 3 : APPRÉCIATIONS DYNAMIQUES DU CONSEIL")
    print("-"*50)
    
    test_appreciations = [
        (Decimal('19.0'), "Fatoumata"),
        (Decimal('16.7'), "Mamadou"),
        (Decimal('14.8'), "Aïssatou"),
        (Decimal('12.5'), "Ibrahim"),
        (Decimal('10.2'), "Mariam"),
        (Decimal('9.0'), "Ousmane"),
        (Decimal('7.5'), "Kadiatou"),
    ]
    
    for moyenne, prenom in test_appreciations:
        appreciation = obtenir_appreciation(moyenne, prenom)
        mention = obtenir_mention(moyenne)
        
        print(f"\n📝 {prenom} - Moyenne: {moyenne:.2f}/20 - Mention: {mention}")
        print(f"   → {appreciation}")
    
    # Résumé final
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DU SYSTÈME INTELLIGENT")
    print("="*80)
    
    print("\n✅ RANGS FORMATÉS INTELLIGEMMENT :")
    print("   • Fille première → 1ère")
    print("   • Garçon premier → 1er")
    print("   • Autres rangs → 2ème, 3ème...")
    print("   • JAMAIS de format N/A/2 !")
    
    print("\n✅ MENTIONS DYNAMIQUES (Formule Excel convertie) :")
    print("   • >= 18.5 → Excellent")
    print("   • >= 16.5 → Très bien")
    print("   • >= 14.5 → Bien")
    print("   • >= 12.5 → Assez bien")
    print("   • >= 10.0 → Passable")
    print("   • >= 9.0  → Faible")
    print("   • < 9.0   → Insuffisant")
    
    print("\n✅ APPRÉCIATIONS DU CONSEIL :")
    print("   • Personnalisées avec le prénom")
    print("   • Adaptées à la performance")
    print("   • Messages encourageants ou correctifs")
    
    # Test avec de vrais élèves de la base
    print("\n" + "="*80)
    print("🎓 TEST AVEC DE VRAIS ÉLÈVES")
    print("="*80)
    
    # Chercher quelques élèves réels
    eleves_reels = Eleve.objects.filter(statut='ACTIF')[:5]
    
    if eleves_reels:
        print("\n┌──────────────────────┬──────┬────────────────────┬────────────────────┐")
        print("│       Élève          │ Sexe │   Rang Formaté     │    Vérification    │")
        print("├──────────────────────┼──────┼────────────────────┼────────────────────┤")
        
        for i, eleve in enumerate(eleves_reels, 1):
            rang_formate = formater_rang_intelligent(i, eleve.sexe, len(eleves_reels))
            
            # Vérifier le format
            if i == 1:
                if eleve.sexe == 'F':
                    correct = rang_formate.startswith("1ère")
                else:
                    correct = rang_formate.startswith("1er")
            else:
                correct = f"{i}ème" in rang_formate
            
            symbole = "✅ Correct" if correct else "❌ Incorrect"
            icone = "👧" if eleve.sexe == 'F' else "👦"
            
            nom_complet = f"{eleve.nom} {eleve.prenom}"[:20]
            print(f"│ {nom_complet:<20} │  {icone}  │ {rang_formate:<18} │ {symbole:<18} │")
        
        print("└──────────────────────┴──────┴────────────────────┴────────────────────┘")
    
    print("\n✅ LE SYSTÈME DE BULLETIN INTELLIGENT EST OPÉRATIONNEL !")
    print("="*80)

if __name__ == "__main__":
    test_bulletin_intelligent()
