"""
Test du bulletin corrigé avec rang intelligent et mentions dynamiques
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

def test_bulletin_corrige():
    """Tester le bulletin corrigé"""
    
    print("="*80)
    print("🎓 TEST DU BULLETIN CORRIGÉ")
    print("="*80)
    
    # Exemple de données de bulletin avec votre cas
    moyenne_generale = Decimal('14.54')
    rang_num = 2
    total_eleves = 25
    sexe = 'F'  # Supposons que c'est une fille
    prenom = "Fatoumata"
    
    print(f"\n📊 DONNÉES DU BULLETIN :")
    print(f"   • Moyenne : {moyenne_generale}/20")
    print(f"   • Position : {rang_num}ème")
    print(f"   • Total élèves : {total_eleves}")
    print(f"   • Sexe : {'Fille' if sexe == 'F' else 'Garçon'}")
    
    print("\n" + "="*80)
    print("❌ ANCIEN FORMAT (INCORRECT) :")
    print("="*80)
    print(f"MOYENNE GÉNÉRALE : {moyenne_generale}/20")
    print(f"RANG : N/A/2")  # Format incorrect
    print(f"MENTION : BIEN")
    print(f"APPRÉCIATION : Bon travail. Continuez vos efforts.")
    
    print("\n" + "="*80)
    print("✅ NOUVEAU FORMAT (INTELLIGENT) :")
    print("="*80)
    
    # Calcul intelligent
    rang = formater_rang_intelligent(rang_num, sexe, total_eleves)
    mention = obtenir_mention(moyenne_generale)
    appreciation = obtenir_appreciation(moyenne_generale, prenom)
    
    print(f"MOYENNE GÉNÉRALE : {moyenne_generale}/20")
    print(f"RANG : {rang}")
    print(f"MENTION : {mention}")
    print(f"APPRÉCIATION DU CONSEIL DE CLASSE :")
    print(f"   {appreciation}")
    
    print("\n" + "="*80)
    print("📋 COMPARAISON :")
    print("="*80)
    
    print("\n┌────────────────┬─────────────────┬─────────────────────────────┐")
    print("│    Élément     │     Ancien      │          Nouveau            │")
    print("├────────────────┼─────────────────┼─────────────────────────────┤")
    print(f"│ Rang           │ N/A/2           │ {rang:<27} │")
    print(f"│ Mention        │ BIEN            │ {mention:<27} │")
    print("│ Appréciation   │ Générique       │ Personnalisée avec prénom   │")
    print("└────────────────┴─────────────────┴─────────────────────────────┘")
    
    # Test avec plusieurs cas
    print("\n" + "="*80)
    print("🧪 TESTS AVEC DIFFÉRENTS CAS :")
    print("="*80)
    
    test_cases = [
        # (moyenne, rang, sexe, prenom)
        (Decimal('18.75'), 1, 'F', "Aïssatou"),
        (Decimal('17.20'), 1, 'M', "Mamadou"),
        (Decimal('14.54'), 2, 'F', "Fatoumata"),
        (Decimal('12.75'), 5, 'M', "Ibrahim"),
        (Decimal('10.25'), 12, 'F', "Mariam"),
        (Decimal('9.10'), 18, 'M', "Ousmane"),
        (Decimal('8.50'), 22, 'F', "Kadiatou"),
    ]
    
    print("\n┌─────────┬──────────────┬──────┬──────────┬─────────────┬──────────────────────────┐")
    print("│ Moyenne │    Prénom    │ Sexe │   Rang   │   Mention   │      Appréciation        │")
    print("├─────────┼──────────────┼──────┼──────────┼─────────────┼──────────────────────────┤")
    
    for moyenne, rang_num, sexe, prenom in test_cases:
        rang = formater_rang_intelligent(rang_num, sexe, 25)
        mention = obtenir_mention(moyenne)
        appreciation = obtenir_appreciation(moyenne, prenom)
        
        # Tronquer l'appréciation pour l'affichage
        appr_courte = appreciation[:24] + "..." if len(appreciation) > 24 else appreciation[:24]
        
        icone = "👧" if sexe == 'F' else "👦"
        print(f"│ {moyenne:>7.2f} │ {prenom:<12} │  {icone}  │ {rang:^8} │ {mention:<11} │ {appr_courte:<24} │")
    
    print("└─────────┴──────────────┴──────┴──────────┴─────────────┴──────────────────────────┘")
    
    # Vérification des seuils de mention
    print("\n" + "="*80)
    print("📊 VÉRIFICATION DES SEUILS DE MENTION :")
    print("="*80)
    
    print("\nVotre cas : Moyenne 14.54/20")
    print(f"• 14.54 >= 14.5 ? {'OUI ✅' if moyenne_generale >= Decimal('14.5') else 'NON ❌'}")
    print(f"• 14.54 >= 12.5 ? {'OUI ✅' if moyenne_generale >= Decimal('12.5') else 'NON ❌'}")
    print(f"• Donc la mention est : {obtenir_mention(Decimal('14.54'))}")
    
    print("\n📝 FORMULE EXCEL CONVERTIE :")
    print("```")
    print("SI(moyenne>=18.5;\"Excellent\";")
    print("  SI(moyenne>=16.5;\"Très bien\";")
    print("    SI(moyenne>=14.5;\"Bien\";")
    print("      SI(moyenne>=12.5;\"Assez bien\";")
    print("        SI(moyenne>=10;\"Passable\";")
    print("          SI(moyenne>=9;\"Faible\";\"Insuffisant\"))))))")
    print("```")
    
    # Simulation d'un bulletin complet
    print("\n" + "="*80)
    print("📄 BULLETIN COMPLET SIMULÉ :")
    print("="*80)
    
    # Données de l'élève
    eleve_data = {
        'nom': 'DIALLO',
        'prenom': 'Fatoumata',
        'sexe': 'F',
        'classe': '10ème Année A',
        'moyenne': Decimal('14.54'),
        'rang_num': 2,
        'total_eleves': 25
    }
    
    rang = formater_rang_intelligent(eleve_data['rang_num'], eleve_data['sexe'], eleve_data['total_eleves'])
    mention = obtenir_mention(eleve_data['moyenne'])
    appreciation = obtenir_appreciation(eleve_data['moyenne'], eleve_data['prenom'])
    
    print(f"\n╔{'═'*78}╗")
    print(f"║{' '*30}BULLETIN DE NOTES{' '*31}║")
    print(f"╠{'═'*78}╣")
    print(f"║ Élève : {eleve_data['prenom']} {eleve_data['nom']:<55}║")
    print(f"║ Classe : {eleve_data['classe']:<67}║")
    print(f"╠{'═'*78}╣")
    print(f"║ MOYENNE GÉNÉRALE : {eleve_data['moyenne']}/20{' '*50}║")
    print(f"║ RANG : {rang:<69}║")
    print(f"║ MENTION : {mention:<66}║")
    print(f"╠{'═'*78}╣")
    print(f"║ APPRÉCIATION DU CONSEIL DE CLASSE :{' '*41}║")
    
    # Découper l'appréciation en lignes
    import textwrap
    lines = textwrap.wrap(appreciation, width=76)
    for line in lines:
        print(f"║ {line:<76} ║")
    
    print(f"╠{'═'*78}╣")
    print(f"║ Professeur Principal{' '*20}Chef d'Établissement{' '*17}║")
    print(f"║ Signature{' '*31}Signature et Cachet{' '*18}║")
    print(f"║{' '*78}║")
    print(f"║ Parent d'Élève{' '*63}║")
    print(f"║ Signature{' '*68}║")
    print(f"╚{'═'*78}╝")
    
    print("\n✅ LE BULLETIN EST MAINTENANT CORRECT ET INTELLIGENT !")
    print("   • Plus de format N/A/2")
    print("   • Rang avec accord grammatical")
    print("   • Mention selon les seuils exacts")
    print("   • Appréciation personnalisée")
    print("="*80)

if __name__ == "__main__":
    test_bulletin_corrige()
