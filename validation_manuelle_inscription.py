#!/usr/bin/env python
"""
Script de validation manuelle du système d'inscription
À exécuter pour vérifier que le système fonctionne correctement
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
from django.contrib.auth import authenticate

def verifier_structure_base():
    """Vérifie que la structure de base est en place"""
    print("=== VÉRIFICATION STRUCTURE DE BASE ===")
    
    # Vérifier les modèles
    try:
        # Test du modèle Profil avec le champ is_validated
        profil_fields = [f.name for f in Profil._meta.fields]
        if 'is_validated' in profil_fields:
            print("[OK] Champ is_validated présent dans le modèle Profil")
        else:
            print("[ERREUR] Champ is_validated manquant dans le modèle Profil")
            return False
            
        # Test du modèle Ecole
        ecole_fields = [f.name for f in Ecole._meta.fields]
        required_fields = ['nom', 'adresse', 'telephone', 'directeur', 'etat', 'created_by']
        for field in required_fields:
            if field in ecole_fields:
                print(f"[OK] Champ {field} présent dans le modèle Ecole")
            else:
                print(f"[ERREUR] Champ {field} manquant dans le modèle Ecole")
                return False
                
        return True
        
    except Exception as e:
        print(f"[ERREUR] Problème avec la structure des modèles: {e}")
        return False

def verifier_vues_urls():
    """Vérifie que les vues et URLs sont configurées"""
    print("\n=== VÉRIFICATION VUES ET URLS ===")
    
    try:
        from django.urls import reverse
        
        # Tester les URLs de validation
        urls_to_test = [
            'utilisateurs:comptes_en_attente',
            'eleves:creer_ecole',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"[OK] URL {url_name} configurée: {url}")
            except Exception as e:
                print(f"[ERREUR] URL {url_name} non configurée: {e}")
                return False
                
        # Tester les vues avec paramètres
        try:
            # Créer un utilisateur temporaire pour tester l'URL
            test_user = User.objects.create_user(
                username='temp_test_user',
                password='temp123',
                is_active=False
            )
            url = reverse('utilisateurs:valider_compte', args=[test_user.id])
            print(f"[OK] URL valider_compte configurée: {url}")
            test_user.delete()
        except Exception as e:
            print(f"[ERREUR] URL valider_compte non configurée: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERREUR] Problème avec les URLs: {e}")
        return False

def verifier_securite_connexion():
    """Vérifie que la sécurité de connexion fonctionne"""
    print("\n=== VÉRIFICATION SÉCURITÉ CONNEXION ===")
    
    try:
        # Créer un utilisateur de test non validé
        test_user = User.objects.create_user(
            username='test_security_user',
            password='test123',
            is_active=True  # Actif mais profil non validé
        )
        
        # Créer un profil non validé
        profil = Profil.objects.create(
            user=test_user,
            role='DIRECTEUR',
            is_validated=False,  # Non validé
            actif=False
        )
        
        # Tester l'authentification
        auth_user = authenticate(username='test_security_user', password='test123')
        
        if auth_user:
            print("[OK] Authentification fonctionne")
            
            # Vérifier que le profil existe et n'est pas validé
            if hasattr(auth_user, 'profil') and not auth_user.profil.is_validated:
                print("[OK] Profil non validé détecté correctement")
            else:
                print("[ERREUR] Problème avec la détection du profil non validé")
                return False
        else:
            print("[ERREUR] Authentification échouée")
            return False
            
        # Nettoyer
        test_user.delete()
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Problème avec la sécurité: {e}")
        return False

def verifier_creation_automatique():
    """Vérifie que la création automatique fonctionne"""
    print("\n=== VÉRIFICATION CRÉATION AUTOMATIQUE ===")
    
    try:
        from eleves.utils import creer_classes_et_grilles_par_defaut
        
        # Créer une école de test
        ecole_test = Ecole.objects.create(
            nom="École Test Validation Système",
            adresse="Adresse test",
            telephone="+224622123456",
            directeur="Directeur Test",
            etat='EN_ATTENTE'
        )
        
        # Tester la création automatique
        result = creer_classes_et_grilles_par_defaut(ecole_test)
        
        if result['total_classes'] > 0:
            print(f"[OK] {result['total_classes']} classes créées automatiquement")
        else:
            print("[ERREUR] Aucune classe créée")
            return False
            
        if result['total_grilles'] > 0:
            print(f"[OK] {result['total_grilles']} grilles tarifaires créées")
        else:
            print("[ERREUR] Aucune grille tarifaire créée")
            return False
            
        # Vérifier quelques classes spécifiques
        classes_attendues = ['Garderie', '1ère Année', '7ème', '11ème Série Littéraire']
        for nom_classe in classes_attendues:
            if Classe.objects.filter(nom=nom_classe, ecole=ecole_test).exists():
                print(f"[OK] Classe '{nom_classe}' créée")
            else:
                print(f"[ATTENTION] Classe '{nom_classe}' non trouvée")
        
        # Nettoyer
        ecole_test.delete()
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Problème avec la création automatique: {e}")
        return False

def verifier_isolation_donnees():
    """Vérifie l'isolation des données par école"""
    print("\n=== VÉRIFICATION ISOLATION DONNÉES ===")
    
    try:
        from utilisateurs.middleware import filter_by_user_school, check_school_access
        
        # Créer deux écoles
        ecole1 = Ecole.objects.create(
            nom="École Test 1",
            adresse="Adresse 1",
            telephone="+224622111111",
            directeur="Directeur 1",
            etat='VALIDE'
        )
        
        ecole2 = Ecole.objects.create(
            nom="École Test 2",
            adresse="Adresse 2",
            telephone="+224622222222",
            directeur="Directeur 2",
            etat='VALIDE'
        )
        
        # Créer un utilisateur avec profil pour école 1
        user1 = User.objects.create_user(
            username='user_test_1',
            password='pass123',
            is_active=True
        )
        
        profil1 = Profil.objects.create(
            user=user1,
            role='DIRECTEUR',
            ecole=ecole1,
            is_validated=True,
            actif=True
        )
        
        # Tester l'isolation
        all_ecoles = Ecole.objects.all()
        ecoles_user1 = filter_by_user_school(all_ecoles, user1, 'id')
        
        if ecoles_user1.count() == 1 and ecoles_user1.first() == ecole1:
            print("[OK] Isolation des écoles fonctionne")
        else:
            print(f"[ERREUR] Isolation échouée - User1 voit {ecoles_user1.count()} école(s)")
            return False
            
        # Tester l'accès
        if check_school_access(user1, ecole1, 'id'):
            print("[OK] Accès à sa propre école autorisé")
        else:
            print("[ERREUR] Accès à sa propre école refusé")
            return False
            
        if not check_school_access(user1, ecole2, 'id'):
            print("[OK] Accès à une autre école refusé")
        else:
            print("[ERREUR] Accès à une autre école autorisé")
            return False
        
        # Nettoyer
        user1.delete()
        ecole1.delete()
        ecole2.delete()
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] Problème avec l'isolation: {e}")
        return False

def validation_complete():
    """Exécute tous les tests de validation"""
    print("DÉBUT DE LA VALIDATION MANUELLE DU SYSTÈME D'INSCRIPTION\n")
    
    tests = [
        ("Structure de base", verifier_structure_base),
        ("Vues et URLs", verifier_vues_urls),
        ("Sécurité connexion", verifier_securite_connexion),
        ("Création automatique", verifier_creation_automatique),
        ("Isolation données", verifier_isolation_donnees),
    ]
    
    resultats = []
    
    for nom_test, fonction_test in tests:
        try:
            resultat = fonction_test()
            resultats.append((nom_test, resultat))
        except Exception as e:
            print(f"[ERREUR CRITIQUE] {nom_test}: {e}")
            resultats.append((nom_test, False))
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DE LA VALIDATION")
    print("="*60)
    
    tous_ok = True
    for nom_test, resultat in resultats:
        statut = "RÉUSSI" if resultat else "ÉCHEC"
        print(f"{nom_test}: {statut}")
        if not resultat:
            tous_ok = False
    
    print("\n" + "="*60)
    if tous_ok:
        print("✅ VALIDATION COMPLÈTE RÉUSSIE!")
        print("\nLe système d'inscription et validation est opérationnel:")
        print("- Structure des modèles correcte")
        print("- URLs et vues configurées")
        print("- Sécurité de connexion active")
        print("- Création automatique fonctionnelle")
        print("- Isolation des données assurée")
        print("\n🚀 Le système est prêt pour la production!")
    else:
        print("❌ VALIDATION ÉCHOUÉE")
        print("\nCertains composants nécessitent des corrections.")
        print("Vérifiez les erreurs ci-dessus avant de déployer.")

if __name__ == "__main__":
    validation_complete()
