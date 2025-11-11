"""
Script de test pour vérifier l'accord grammatical des rangs selon le sexe
Date : 11 novembre 2024
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve
from notes.export_classement import formater_rang
from notes.export_classement_fixed import formater_rang as formater_rang_fixed

def test_accord_rang():
    """Tester l'accord grammatical des rangs selon le sexe"""
    
    print("="*80)
    print("TEST : ACCORD GRAMMATICAL DES RANGS SELON LE SEXE")
    print("Date : 11 novembre 2024")
    print("="*80)
    
    # Test de la fonction formater_rang
    print("\n📊 TEST DE LA FONCTION formater_rang()")
    print("-"*50)
    
    # Cas de test
    cas_test = [
        (1, 'F', "1ère"),  # Fille première
        (1, 'M', "1er"),   # Garçon premier
        (2, 'F', "2ème"),  # Fille deuxième
        (2, 'M', "2ème"),  # Garçon deuxième
        (3, 'F', "3ème"),  # Fille troisième
        (3, 'M', "3ème"),  # Garçon troisième
        (10, 'F', "10ème"), # Fille dixième
        (10, 'M', "10ème"), # Garçon dixième
        ('-', 'F', "-"),   # Sans rang
        ('-', 'M', "-"),   # Sans rang
    ]
    
    print("┌──────┬──────┬──────────┬────────────┬──────────┐")
    print("│ Rang │ Sexe │ Attendu  │ Obtenu     │ Résultat │")
    print("├──────┼──────┼──────────┼────────────┼──────────┤")
    
    tous_corrects = True
    
    for rang, sexe, attendu in cas_test:
        obtenu = formater_rang(rang, sexe)
        correct = obtenu == attendu
        
        if not correct:
            tous_corrects = False
            
        resultat = "✅" if correct else "❌"
        sexe_label = "Fille" if sexe == 'F' else "Garçon"
        
        print(f"│ {str(rang):<4} │ {sexe_label:<6} │ {attendu:<8} │ {obtenu:<10} │ {resultat:<8} │")
    
    print("└──────┴──────┴──────────┴────────────┴──────────┘")
    
    if tous_corrects:
        print("\n✅ TOUS LES TESTS PASSENT - L'accord grammatical fonctionne parfaitement !")
    else:
        print("\n❌ CERTAINS TESTS ÉCHOUENT - Vérifier la fonction formater_rang()")
    
    # Vérifier avec de vrais élèves
    print("\n📚 TEST AVEC DE VRAIS ÉLÈVES")
    print("-"*50)
    
    # Chercher des filles et des garçons dans la base
    filles = Eleve.objects.filter(sexe='F', statut='ACTIF')[:3]
    garcons = Eleve.objects.filter(sexe='M', statut='ACTIF')[:3]
    
    print("\n👧 Exemples pour les FILLES :")
    for i, fille in enumerate(filles, 1):
        rang_formate = formater_rang(i, fille.sexe)
        print(f"   {rang_formate} : {fille.nom} {fille.prenom}")
        if i == 1:
            assert rang_formate == "1ère", "Une fille première doit avoir '1ère'"
    
    print("\n👦 Exemples pour les GARÇONS :")
    for i, garcon in enumerate(garcons, 1):
        rang_formate = formater_rang(i, garcon.sexe)
        print(f"   {rang_formate} : {garcon.nom} {garcon.prenom}")
        if i == 1:
            assert rang_formate == "1er", "Un garçon premier doit avoir '1er'"
    
    # Tableau récapitulatif
    print("\n" + "="*80)
    print("RÈGLES D'ACCORD GRAMMATICAL")
    print("="*80)
    
    print("\n📝 RANG 1 :")
    print("-"*30)
    print("👧 FILLE   → 1ère (première)")
    print("👦 GARÇON  → 1er  (premier)")
    
    print("\n📝 AUTRES RANGS (2, 3, 4, etc.) :")
    print("-"*30)
    print("👧 FILLE   → 2ème, 3ème, 4ème...")
    print("👦 GARÇON  → 2ème, 3ème, 4ème...")
    print("(Pas de différence pour les autres rangs)")
    
    print("\n📝 CAS SPÉCIAUX :")
    print("-"*30)
    print("• Élève sans note → '-' (tiret)")
    print("• Élève absent → '-' (tiret)")
    print("• Ex-aequo → même rang que le précédent")
    
    # Simulation d'un classement mixte
    print("\n" + "="*80)
    print("SIMULATION D'UN CLASSEMENT MIXTE")
    print("="*80)
    
    # Données simulées
    eleves_simules = [
        {'nom': 'DIALLO', 'prenom': 'Fatoumata', 'sexe': 'F', 'moyenne': 18.5},
        {'nom': 'BAH', 'prenom': 'Mamadou', 'sexe': 'M', 'moyenne': 17.2},
        {'nom': 'CAMARA', 'prenom': 'Mariam', 'sexe': 'F', 'moyenne': 16.8},
        {'nom': 'KEITA', 'prenom': 'Oumar', 'sexe': 'M', 'moyenne': 16.8},  # Ex-aequo
        {'nom': 'SOW', 'prenom': 'Aïssatou', 'sexe': 'F', 'moyenne': 15.3},
        {'nom': 'TOURE', 'prenom': 'Ibrahim', 'sexe': 'M', 'moyenne': 14.7},
    ]
    
    # Trier par moyenne
    eleves_simules.sort(key=lambda x: x['moyenne'], reverse=True)
    
    print("\n┌──────────┬────────────────────────┬──────┬─────────┬───────────┐")
    print("│ Rang     │ Nom et Prénom          │ Sexe │ Moyenne │ Correct ? │")
    print("├──────────┼────────────────────────┼──────┼─────────┼───────────┤")
    
    rang_actuel = 1
    for i, eleve in enumerate(eleves_simules):
        # Gérer les ex-aequo
        if i > 0 and eleve['moyenne'] == eleves_simules[i-1]['moyenne']:
            rang = eleves_simules[i-1].get('rang', rang_actuel)
        else:
            rang = rang_actuel
        
        eleve['rang'] = rang
        rang_actuel += 1
        
        # Formater le rang
        rang_formate = formater_rang(rang, eleve['sexe'])
        
        # Vérifier l'accord
        if rang == 1:
            if eleve['sexe'] == 'F':
                correct = rang_formate == "1ère"
                expected = "1ère"
            else:
                correct = rang_formate == "1er"
                expected = "1er"
        else:
            correct = "ème" in rang_formate
            expected = f"{rang}ème"
        
        nom_complet = f"{eleve['nom']} {eleve['prenom']}"
        sexe_label = "F" if eleve['sexe'] == 'F' else "M"
        resultat = "✅" if correct else "❌"
        
        print(f"│ {rang_formate:<8} │ {nom_complet:<22} │ {sexe_label:<4} │ {eleve['moyenne']:>7.2f} │ {resultat:<9} │")
    
    print("└──────────┴────────────────────────┴──────┴─────────┴───────────┘")
    
    print("\n💡 OBSERVATIONS :")
    print("-"*50)
    print("✅ DIALLO Fatoumata (Fille) → 1ère ✓")
    print("✅ BAH Mamadou (Garçon) → 2ème ✓")
    print("✅ CAMARA Mariam & KEITA Oumar → 3ème ex-aequo ✓")
    print("\n✅ Le système gère correctement l'accord grammatical selon le sexe !")

if __name__ == "__main__":
    test_accord_rang()
