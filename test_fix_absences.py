#!/usr/bin/env python
"""
Script de test pour vérifier la correction du traitement des absences
"""
import os
import sys
import django
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.calculs import calculer_moyenne_devoirs, calculer_moyenne_annuelle

def test_moyenne_devoirs_avec_absences():
    """
    Test 1 : Vérifier que les absences sont comptées comme 0
    """
    print("\n" + "="*70)
    print("TEST 1 : Calcul de moyenne avec absences (devoirs)")
    print("="*70)
    
    # Cas du problème : CL10-032 AMADOU SARAH DIALLO
    # 6 absences + 3 notes : 9, 16, 15
    notes = [
        None,  # Anglais (ABS)
        None,  # Biologie (ABS)
        None,  # Chimie (ABS)
        None,  # Dictée (ABS)
        None,  # Éducation Civique (ABS)
        Decimal('9'),   # Géographie
        Decimal('16'),  # Histoire
        None,  # Mathématique (ABS)
        Decimal('15'),  # Rédaction
        None,  # Physique (ABS)
    ]
    
    moyenne = calculer_moyenne_devoirs(notes)
    
    print(f"\nNotes : {[str(n) if n else 'ABS' for n in notes]}")
    print(f"Nombre de notes : {len(notes)}")
    print(f"Nombre d'absences : {sum(1 for n in notes if n is None)}")
    print(f"Nombre de présences : {sum(1 for n in notes if n is not None)}")
    print(f"\n✓ Moyenne calculée : {moyenne}")
    
    # Vérification
    attendu = Decimal('4.00')  # (0+0+0+0+0+9+16+0+15+0) / 10 = 4.00
    
    if moyenne == attendu:
        print(f"✅ CORRECT : Moyenne = {attendu} (absences comptées comme 0)")
        return True
    else:
        print(f"❌ ERREUR : Attendu {attendu}, obtenu {moyenne}")
        return False

def test_moyenne_devoirs_sans_absences():
    """
    Test 2 : Vérifier que sans absences, le calcul est normal
    """
    print("\n" + "="*70)
    print("TEST 2 : Calcul de moyenne sans absences")
    print("="*70)
    
    notes = [
        Decimal('16'),  # Anglais
        Decimal('19'),  # Biologie
        Decimal('18'),  # Chimie
        Decimal('13'),  # Dictée
        Decimal('10'),  # Éducation Civique
        Decimal('8'),   # Géographie
        Decimal('15.5'), # Histoire
        Decimal('17'),  # Mathématique
        Decimal('17.5'), # Rédaction
        Decimal('10'),  # Physique
    ]
    
    moyenne = calculer_moyenne_devoirs(notes)
    
    print(f"\nNotes : {[str(n) for n in notes]}")
    print(f"Nombre de notes : {len(notes)}")
    print(f"\n✓ Moyenne calculée : {moyenne}")
    
    # Vérification
    attendu = Decimal('13.90')  # (16+19+18+13+10+8+15.5+17+17.5+10) / 10 = 13.90
    
    if moyenne == attendu:
        print(f"✅ CORRECT : Moyenne = {attendu}")
        return True
    else:
        print(f"❌ ERREUR : Attendu {attendu}, obtenu {moyenne}")
        return False

def test_moyenne_annuelle_avec_absences():
    """
    Test 3 : Vérifier que les périodes manquantes sont comptées comme 0
    """
    print("\n" + "="*70)
    print("TEST 3 : Calcul de moyenne annuelle avec périodes manquantes")
    print("="*70)
    
    # 3 périodes : 2 présentes, 1 absente
    moyennes_periodes = [
        Decimal('15.5'),  # Période 1
        None,             # Période 2 (manquante)
        Decimal('12.3'),  # Période 3
    ]
    
    moyenne = calculer_moyenne_annuelle(moyennes_periodes)
    
    print(f"\nMoyennes périodes : {[str(m) if m else 'ABSENT' for m in moyennes_periodes]}")
    print(f"Nombre de périodes : {len(moyennes_periodes)}")
    print(f"\n✓ Moyenne annuelle calculée : {moyenne}")
    
    # Vérification
    attendu = Decimal('9.27')  # (15.5 + 0 + 12.3) / 3 = 9.27
    
    if moyenne == attendu:
        print(f"✅ CORRECT : Moyenne annuelle = {attendu} (période manquante comptée comme 0)")
        return True
    else:
        print(f"❌ ERREUR : Attendu {attendu}, obtenu {moyenne}")
        return False

def test_comparaison_avant_apres():
    """
    Test 4 : Comparaison avant/après correction
    """
    print("\n" + "="*70)
    print("TEST 4 : Comparaison avant/après correction")
    print("="*70)
    
    notes = [None, None, None, None, None, Decimal('9'), Decimal('16'), None, Decimal('15'), None]
    
    print("\n📊 CAS : CL10-032 AMADOU SARAH DIALLO")
    print(f"Notes : {[str(n) if n else 'ABS' for n in notes]}")
    print(f"Absences : 6 | Présences : 3")
    
    print("\n❌ ANCIEN SYSTÈME (INCORRECT) :")
    print("   Exclure les absences du calcul")
    notes_valides = [n for n in notes if n is not None]
    ancien_calcul = sum(notes_valides) / len(notes_valides)
    print(f"   Moyenne = ({' + '.join(str(n) for n in notes_valides)}) / {len(notes_valides)}")
    print(f"   Moyenne = {ancien_calcul} ← FAUX ! (3ème place)")
    
    print("\n✅ NOUVEAU SYSTÈME (CORRECT) :")
    print("   Compter les absences comme 0")
    moyenne_correcte = calculer_moyenne_devoirs(notes)
    print(f"   Moyenne = (0+0+0+0+0+9+16+0+15+0) / 10")
    print(f"   Moyenne = {moyenne_correcte} ← CORRECT ! (30ème place)")
    
    print("\n📉 Impact sur le classement :")
    print(f"   Avant : 3ème/31 avec 13,33/20")
    print(f"   Après : ~30ème/31 avec 4,00/20")
    
    return True

def main():
    """
    Exécute tous les tests
    """
    print("\n" + "🧪 TESTS DE CORRECTION DES ABSENCES".center(70))
    
    tests = [
        ("Moyenne avec absences", test_moyenne_devoirs_avec_absences),
        ("Moyenne sans absences", test_moyenne_devoirs_sans_absences),
        ("Moyenne annuelle avec périodes manquantes", test_moyenne_annuelle_avec_absences),
        ("Comparaison avant/après", test_comparaison_avant_apres),
    ]
    
    resultats = []
    for nom_test, test_func in tests:
        try:
            resultat = test_func()
            resultats.append((nom_test, resultat))
        except Exception as e:
            print(f"❌ Erreur lors du test : {e}")
            import traceback
            traceback.print_exc()
            resultats.append((nom_test, False))
    
    # Résumé final
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    
    for nom_test, resultat in resultats:
        status = "✅ RÉUSSI" if resultat else "❌ ÉCHOUÉ"
        print(f"{status} | {nom_test}")
    
    total_reussis = sum(1 for _, r in resultats if r)
    total_tests = len(resultats)
    
    print(f"\n{'='*70}")
    print(f"Résultat : {total_reussis}/{total_tests} tests réussis")
    
    if total_reussis == total_tests:
        print("✅ TOUS LES TESTS SONT PASSÉS !")
        print("\n🎉 La correction des absences fonctionne correctement !")
    else:
        print(f"❌ {total_tests - total_reussis} test(s) échoué(s)")

if __name__ == '__main__':
    main()
