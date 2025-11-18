#!/usr/bin/env python
"""
Script de test pour vérifier la permission d'importation d'élèves pour les comptables
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from utilisateurs.models import Profil
from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from eleves.views_import import importer_eleves

def test_permission_comptable():
    """
    Test 1 : Vérifier qu'un comptable SANS permission ne peut pas importer
    """
    print("\n" + "="*70)
    print("TEST 1 : Comptable SANS permission")
    print("="*70)
    
    # Créer un utilisateur comptable sans permission
    user_comptable = User.objects.filter(profil__role='COMPTABLE').first()
    
    if not user_comptable:
        print("❌ Aucun comptable trouvé dans le système.")
        return False
    
    profil = user_comptable.profil
    profil.peut_importer_eleves = False
    profil.save()
    
    # Créer une requête
    factory = RequestFactory()
    request = factory.get('/eleves/importer/')
    request.user = user_comptable
    
    # Tester l'accès
    response = importer_eleves(request)
    
    if response.status_code == 302:  # Redirection
        print(f"✅ Comptable {user_comptable.username} BLOQUÉ (redirection vers liste_eleves)")
        return True
    else:
        print(f"❌ Comptable {user_comptable.username} a pu accéder (status: {response.status_code})")
        return False

def test_permission_comptable_avec_acces():
    """
    Test 2 : Vérifier qu'un comptable AVEC permission peut importer
    """
    print("\n" + "="*70)
    print("TEST 2 : Comptable AVEC permission")
    print("="*70)
    
    # Créer un utilisateur comptable avec permission
    user_comptable = User.objects.filter(profil__role='COMPTABLE').first()
    
    if not user_comptable:
        print("❌ Aucun comptable trouvé dans le système.")
        return False
    
    profil = user_comptable.profil
    profil.peut_importer_eleves = True
    profil.save()
    
    # Créer une requête
    factory = RequestFactory()
    request = factory.get('/eleves/importer/')
    request.user = user_comptable
    
    # Tester l'accès
    response = importer_eleves(request)
    
    if response.status_code == 200:
        print(f"✅ Comptable {user_comptable.username} AUTORISÉ (status: 200)")
        return True
    else:
        print(f"❌ Comptable {user_comptable.username} BLOQUÉ (status: {response.status_code})")
        return False

def test_permission_administrateur():
    """
    Test 3 : Vérifier qu'un administrateur peut toujours importer
    """
    print("\n" + "="*70)
    print("TEST 3 : Administrateur (toujours autorisé)")
    print("="*70)
    
    # Créer un utilisateur admin
    admin = User.objects.filter(is_superuser=True).first()
    
    if not admin:
        print("❌ Aucun administrateur trouvé dans le système.")
        return False
    
    # Créer une requête
    factory = RequestFactory()
    request = factory.get('/eleves/importer/')
    request.user = admin
    
    # Tester l'accès
    response = importer_eleves(request)
    
    if response.status_code == 200:
        print(f"✅ Administrateur {admin.username} AUTORISÉ (status: 200)")
        return True
    else:
        print(f"❌ Administrateur {admin.username} BLOQUÉ (status: {response.status_code})")
        return False

def afficher_etat_permissions():
    """
    Affiche l'état des permissions pour tous les comptables
    """
    print("\n" + "="*70)
    print("ÉTAT DES PERMISSIONS - COMPTABLES")
    print("="*70)
    
    comptables = Profil.objects.filter(role='COMPTABLE')
    
    if not comptables.exists():
        print("❌ Aucun comptable trouvé.")
        return
    
    print(f"\n📊 Total comptables : {comptables.count()}\n")
    
    for profil in comptables:
        status = "✅ AUTORISÉ" if profil.peut_importer_eleves else "❌ BLOQUÉ"
        print(f"{status} | {profil.user.get_full_name():<30} ({profil.user.username})")
    
    autorisés = comptables.filter(peut_importer_eleves=True).count()
    bloqués = comptables.count() - autorisés
    
    print(f"\n{'='*70}")
    print(f"Résumé : {autorisés} autorisé(s) | {bloqués} bloqué(s)")

def main():
    """
    Exécute tous les tests
    """
    print("\n" + "🧪 TESTS DE PERMISSION D'IMPORTATION D'ÉLÈVES".center(70))
    
    # Afficher l'état actuel
    afficher_etat_permissions()
    
    # Exécuter les tests
    tests = [
        ("Comptable sans permission", test_permission_comptable),
        ("Comptable avec permission", test_permission_comptable_avec_acces),
        ("Administrateur", test_permission_administrateur),
    ]
    
    resultats = []
    for nom_test, test_func in tests:
        try:
            resultat = test_func()
            resultats.append((nom_test, resultat))
        except Exception as e:
            print(f"❌ Erreur lors du test : {e}")
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
    else:
        print(f"❌ {total_tests - total_reussis} test(s) échoué(s)")

if __name__ == '__main__':
    main()
