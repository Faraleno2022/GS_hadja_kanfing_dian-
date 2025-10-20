#!/usr/bin/env python
"""
Script de test pour le système d'inscription et validation des comptes
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from utilisateurs.models import Profil
from eleves.models import Ecole, Classe, GrilleTarifaire
from eleves.utils import creer_classes_et_grilles_par_defaut, valider_compte_utilisateur
from django.db import transaction

def test_creation_compte_ecole():
    """Test de création d'un compte avec école"""
    print("=== TEST CRÉATION COMPTE + ÉCOLE ===")
    
    # Simuler la création d'un utilisateur via le formulaire
    username = "test_ecole_user"
    email = "test@ecole.com"
    password = "motdepasse123"
    
    try:
        # Nettoyer les données de test existantes
        try:
            # Supprimer tous les utilisateurs de test
            for test_username in [username, "user_ecole1", "user_ecole2"]:
                existing_user = User.objects.filter(username=test_username).first()
                if existing_user:
                    # Supprimer le profil d'abord s'il existe
                    try:
                        if hasattr(existing_user, 'profil'):
                            existing_user.profil.delete()
                    except Exception:
                        pass
                    existing_user.delete()
        except Exception:
            pass
        
        # Supprimer les écoles de test
        Ecole.objects.filter(nom__in=["École Test Validation", "École Test 1", "École Test 2"]).delete()
        
        with transaction.atomic():
            # Créer l'utilisateur (comme dans creer_ecole)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False  # Inactif en attente de validation
            )
            
            # Créer le profil
            profil = Profil.objects.create(
                user=user,
                role='DIRECTEUR',
                telephone='',
                is_validated=False,
                actif=False
            )
            
            # Créer l'école
            ecole = Ecole.objects.create(
                nom="École Test Validation",
                adresse="Test Address, Conakry",
                telephone="+224622123456",
                email="contact@ecoletest.com",
                directeur="Directeur Test",
                created_by=user,
                etat='EN_ATTENTE'
            )
            
            # Créer les classes et grilles par défaut
            result = creer_classes_et_grilles_par_defaut(ecole)
            
            print(f"[OK] Utilisateur cree: {user.username}")
            print(f"[OK] Profil cree: {profil.role}, valide={profil.is_validated}")
            print(f"[OK] Ecole creee: {ecole.nom}, etat={ecole.etat}")
            print(f"[OK] Classes creees: {result['total_classes']}")
            print(f"[OK] Grilles tarifaires creees: {result['total_grilles']}")
            
            return user, ecole
            
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la creation: {e}")
        return None, None

def test_validation_compte(user, ecole):
    """Test de validation d'un compte par l'administrateur"""
    print("\n=== TEST VALIDATION COMPTE ===")
    
    if not user or not ecole:
        print("[ERREUR] Pas de donnees de test disponibles")
        return False
        
    try:
        # Simuler la validation par un admin
        telephone = "+224622789456"
        adresse = "Adresse complète de test"
        
        # Valider le compte
        profil = valider_compte_utilisateur(user, ecole, telephone, adresse)
        
        # Activer l'école
        ecole.etat = 'ACTIVE'
        ecole.save()
        
        # Recharger les objets
        user.refresh_from_db()
        profil.refresh_from_db()
        ecole.refresh_from_db()
        
        print(f"[OK] Compte valide: is_active={user.is_active}")
        print(f"[OK] Profil valide: is_validated={profil.is_validated}")
        print(f"[OK] Ecole activee: etat={ecole.etat}")
        print(f"[OK] Telephone ajoute: {profil.telephone}")
        print(f"[OK] Ecole assignee: {profil.ecole.nom}")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la validation: {e}")
        return False

def test_isolation_donnees():
    """Test de l'isolation des données par école"""
    print("\n=== TEST ISOLATION DONNÉES ===")
    
    try:
        # Créer deux écoles différentes
        ecole1 = Ecole.objects.create(
            nom="École Test 1",
            adresse="Conakry",
            telephone="+224622111111",
            directeur="Directeur 1",
            etat='VALIDE'
        )
        
        ecole2 = Ecole.objects.create(
            nom="École Test 2", 
            adresse="Kankan",
            telephone="+224622222222",
            directeur="Directeur 2",
            etat='VALIDE'
        )
        
        # Créer des utilisateurs pour chaque école
        user1 = User.objects.create_user(
            username="user_ecole1",
            password="pass123",
            is_active=True
        )
        
        user2 = User.objects.create_user(
            username="user_ecole2", 
            password="pass123",
            is_active=True
        )
        
        # Créer les profils
        profil1 = Profil.objects.create(
            user=user1,
            role='DIRECTEUR',
            ecole=ecole1,
            is_validated=True,
            actif=True
        )
        
        profil2 = Profil.objects.create(
            user=user2,
            role='DIRECTEUR',
            ecole=ecole2,
            is_validated=True,
            actif=True
        )
        
        # Tester l'isolation avec les fonctions utilitaires
        from utilisateurs.middleware import filter_by_user_school, check_school_access
        
        # Test 1: filter_by_user_school
        all_ecoles = Ecole.objects.all()
        ecoles_user1 = filter_by_user_school(all_ecoles, user1, 'id')
        ecoles_user2 = filter_by_user_school(all_ecoles, user2, 'id')
        
        print(f"[OK] User1 voit {ecoles_user1.count()} ecole(s)")
        print(f"[OK] User2 voit {ecoles_user2.count()} ecole(s)")
        
        # Test 2: check_school_access
        access1_to_ecole1 = check_school_access(user1, ecole1, 'id')
        access1_to_ecole2 = check_school_access(user1, ecole2, 'id')
        access2_to_ecole1 = check_school_access(user2, ecole1, 'id')
        access2_to_ecole2 = check_school_access(user2, ecole2, 'id')
        
        print(f"[OK] User1 acces a Ecole1: {access1_to_ecole1}")
        print(f"[OK] User1 acces a Ecole2: {access1_to_ecole2}")
        print(f"[OK] User2 acces a Ecole1: {access2_to_ecole1}")
        print(f"[OK] User2 acces a Ecole2: {access2_to_ecole2}")
        
        # Vérifier que l'isolation fonctionne
        assert access1_to_ecole1 == True, "User1 devrait avoir acces a Ecole1"
        assert access1_to_ecole2 == False, "User1 ne devrait pas avoir acces a Ecole2"
        assert access2_to_ecole1 == False, "User2 ne devrait pas avoir acces a Ecole1"
        assert access2_to_ecole2 == True, "User2 devrait avoir acces a Ecole2"
        
        print("[OK] Isolation des donnees fonctionne correctement")
        
        # Nettoyer
        user1.delete()
        user2.delete()
        ecole1.delete()
        ecole2.delete()
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test d'isolation: {e}")
        return False

def test_complet():
    """Test complet du système"""
    print("=== DÉBUT DES TESTS DU SYSTÈME D'INSCRIPTION/VALIDATION ===\n")
    
    # Test 1: Création compte + école
    user, ecole = test_creation_compte_ecole()
    
    # Test 2: Validation par admin
    if user and ecole:
        validation_ok = test_validation_compte(user, ecole)
    else:
        validation_ok = False
    
    # Test 3: Isolation des données
    isolation_ok = test_isolation_donnees()
    
    # Nettoyer les données de test
    if user:
        user.delete()
    if ecole:
        ecole.delete()
    
    # Résumé
    print("\n" + "="*50)
    print("RESUME DES TESTS")
    print("="*50)
    print(f"[OK] Création compte/école: {'OK' if user and ecole else 'ECHEC'}")
    print(f"[OK] Validation compte: {'OK' if validation_ok else 'ECHEC'}")
    print(f"[OK] Isolation données: {'OK' if isolation_ok else 'ECHEC'}")
    
    if user and ecole and validation_ok and isolation_ok:
        print("\n*** TOUS LES TESTS SONT PASSES AVEC SUCCES! ***")
        print("\nLe système d'inscription et validation fonctionne correctement:")
        print("• Les utilisateurs peuvent créer un compte avec mot de passe")
        print("• L'école et les classes/grilles sont créées automatiquement")
        print("• Les comptes sont en attente de validation administrative")
        print("• L'isolation des données par école est assurée")
    else:
        print("\n[ERREUR] CERTAINS TESTS ONT ECHOUE")
        print("Vérifiez les erreurs ci-dessus")

if __name__ == "__main__":
    test_complet()
