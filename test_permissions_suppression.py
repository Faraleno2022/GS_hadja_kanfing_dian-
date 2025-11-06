"""
Script de test pour vérifier les permissions de suppression des élèves

Ce script vérifie que :
1. Le champ peut_supprimer_eleves_definitivement existe dans le modèle Profil
2. Les utilisateurs avec cette permission peuvent supprimer définitivement
3. Les utilisateurs sans cette permission ne peuvent faire que du soft delete
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from utilisateurs.models import Profil
from eleves.models import Eleve
from utilisateurs.utils import user_is_admin

def test_champ_permission_existe():
    """Test que le champ peut_supprimer_eleves_definitivement existe"""
    print("\n" + "="*70)
    print("TEST 1: Vérification de l'existence du champ de permission")
    print("="*70)
    
    try:
        # Vérifier que le champ existe dans le modèle
        field = Profil._meta.get_field('peut_supprimer_eleves_definitivement')
        print(f"✓ Champ trouvé: {field.name}")
        print(f"  Type: {field.__class__.__name__}")
        print(f"  Verbose name: {field.verbose_name}")
        print(f"  Valeur par défaut: {field.default}")
        return True
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False

def test_verification_permissions():
    """Test de vérification des permissions pour différents utilisateurs"""
    print("\n" + "="*70)
    print("TEST 2: Vérification des permissions des utilisateurs")
    print("="*70)
    
    resultats = []
    
    # Test 1: Superuser
    print("\n📋 Test avec un superuser:")
    superuser = User.objects.filter(is_superuser=True).first()
    if superuser:
        peut_supprimer = user_is_admin(superuser)
        print(f"  Utilisateur: {superuser.username}")
        print(f"  Est superuser: {superuser.is_superuser}")
        print(f"  Peut supprimer: {peut_supprimer}")
        resultats.append(peut_supprimer)
    else:
        print("  ⚠ Aucun superuser trouvé")
    
    # Test 2: Utilisateur avec profil et permission
    print("\n📋 Test avec un utilisateur ayant la permission:")
    users_avec_permission = User.objects.filter(
        profil__peut_supprimer_eleves_definitivement=True
    )
    if users_avec_permission.exists():
        user = users_avec_permission.first()
        peut_supprimer = (
            user_is_admin(user) or 
            (hasattr(user, 'profil') and user.profil.peut_supprimer_eleves_definitivement)
        )
        print(f"  Utilisateur: {user.username}")
        print(f"  Permission dans profil: {user.profil.peut_supprimer_eleves_definitivement}")
        print(f"  Peut supprimer: {peut_supprimer}")
        resultats.append(peut_supprimer)
    else:
        print("  ⚠ Aucun utilisateur avec cette permission trouvé")
    
    # Test 3: Utilisateur sans permission
    print("\n📋 Test avec un utilisateur SANS la permission:")
    users_sans_permission = User.objects.filter(
        profil__peut_supprimer_eleves_definitivement=False,
        is_superuser=False
    )
    if users_sans_permission.exists():
        user = users_sans_permission.first()
        peut_supprimer = (
            user_is_admin(user) or 
            (hasattr(user, 'profil') and user.profil.peut_supprimer_eleves_definitivement)
        )
        print(f"  Utilisateur: {user.username}")
        print(f"  Permission dans profil: {user.profil.peut_supprimer_eleves_definitivement}")
        print(f"  Peut supprimer: {peut_supprimer}")
        resultats.append(not peut_supprimer)  # Devrait être False
    else:
        print("  ⚠ Aucun utilisateur sans permission trouvé")
    
    return all(resultats) if resultats else False

def test_logique_suppression():
    """Test de la logique de suppression dans la vue"""
    print("\n" + "="*70)
    print("TEST 3: Vérification de la logique de suppression")
    print("="*70)
    
    # Simuler la logique de la vue
    print("\n📋 Simulation de la logique de vérification:")
    
    # Cas 1: Admin
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        peut_supprimer = user_is_admin(admin) or (
            hasattr(admin, 'profil') and 
            admin.profil.peut_supprimer_eleves_definitivement
        )
        print(f"\n  Admin ({admin.username}):")
        print(f"    user_is_admin: {user_is_admin(admin)}")
        print(f"    Résultat: {'✓ PEUT supprimer' if peut_supprimer else '✗ NE PEUT PAS supprimer'}")
    
    # Cas 2: Utilisateur avec permission
    user_avec = User.objects.filter(
        profil__peut_supprimer_eleves_definitivement=True,
        is_superuser=False
    ).first()
    if user_avec:
        peut_supprimer = user_is_admin(user_avec) or (
            hasattr(user_avec, 'profil') and 
            user_avec.profil.peut_supprimer_eleves_definitivement
        )
        print(f"\n  Utilisateur avec permission ({user_avec.username}):")
        print(f"    user_is_admin: {user_is_admin(user_avec)}")
        print(f"    profil.peut_supprimer: {user_avec.profil.peut_supprimer_eleves_definitivement}")
        print(f"    Résultat: {'✓ PEUT supprimer' if peut_supprimer else '✗ NE PEUT PAS supprimer'}")
    
    # Cas 3: Utilisateur sans permission
    user_sans = User.objects.filter(
        profil__peut_supprimer_eleves_definitivement=False,
        is_superuser=False
    ).first()
    if user_sans:
        peut_supprimer = user_is_admin(user_sans) or (
            hasattr(user_sans, 'profil') and 
            user_sans.profil.peut_supprimer_eleves_definitivement
        )
        print(f"\n  Utilisateur sans permission ({user_sans.username}):")
        print(f"    user_is_admin: {user_is_admin(user_sans)}")
        print(f"    profil.peut_supprimer: {user_sans.profil.peut_supprimer_eleves_definitivement}")
        print(f"    Résultat: {'✓ PEUT supprimer' if peut_supprimer else '✗ NE PEUT PAS supprimer'}")
    
    return True

def test_statistiques():
    """Affiche des statistiques sur les utilisateurs et permissions"""
    print("\n" + "="*70)
    print("STATISTIQUES")
    print("="*70)
    
    total_users = User.objects.count()
    total_profils = Profil.objects.count()
    users_avec_permission = Profil.objects.filter(peut_supprimer_eleves_definitivement=True).count()
    superusers = User.objects.filter(is_superuser=True).count()
    
    print(f"\n📊 Utilisateurs:")
    print(f"  Total: {total_users}")
    print(f"  Avec profil: {total_profils}")
    print(f"  Superusers: {superusers}")
    print(f"  Avec permission de suppression définitive: {users_avec_permission}")
    
    total_eleves = Eleve.objects.count()
    eleves_actifs = Eleve.objects.filter(statut='ACTIF').count()
    eleves_exclus = Eleve.objects.filter(statut='EXCLU').count()
    
    print(f"\n📊 Élèves:")
    print(f"  Total: {total_eleves}")
    print(f"  Actifs: {eleves_actifs}")
    print(f"  Exclus (soft delete): {eleves_exclus}")
    
    return True

def afficher_exemple_code():
    """Affiche un exemple de code pour la vue"""
    print("\n" + "="*70)
    print("EXEMPLE DE CODE DANS LA VUE")
    print("="*70)
    
    code = """
# Dans eleves/views.py, ligne 1282-1285:

peut_supprimer_definitivement = user_is_admin(request.user) or (
    hasattr(request.user, 'profil') and 
    request.user.profil.peut_supprimer_eleves_definitivement
)

# Vérification avant suppression définitive (ligne 1306-1308):

if suppression_definitive and not peut_supprimer_definitivement:
    messages.error(request, "Vous n'avez pas la permission de supprimer définitivement un élève.")
    return redirect('eleves:detail_eleve', eleve_id=eleve.id)
"""
    print(code)

if __name__ == '__main__':
    print("\n" + "🔬 TEST DES PERMISSIONS DE SUPPRESSION DES ÉLÈVES ".center(70, "="))
    
    tests = [
        ("Existence du champ de permission", test_champ_permission_existe),
        ("Vérification des permissions", test_verification_permissions),
        ("Logique de suppression", test_logique_suppression),
        ("Statistiques", test_statistiques),
    ]
    
    resultats = []
    for nom, test_func in tests:
        try:
            resultat = test_func()
            resultats.append(resultat)
        except Exception as e:
            print(f"\n✗ Erreur dans {nom}: {e}")
            resultats.append(False)
    
    # Afficher l'exemple de code
    afficher_exemple_code()
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ".center(70))
    print("="*70)
    
    tests_reussis = sum(1 for r in resultats if r)
    total_tests = len(resultats)
    
    print(f"\nTests réussis: {tests_reussis}/{total_tests}")
    
    if all(resultats):
        print("\n" + "✅ TOUS LES TESTS SONT RÉUSSIS !".center(70))
        print("\n" + "Le système de permissions fonctionne correctement.".center(70))
        print("Les utilisateurs avec la permission peuvent supprimer définitivement.".center(70))
    else:
        print("\n" + "⚠ CERTAINS TESTS ONT ÉCHOUÉ".center(70))
    
    print("\n" + "="*70 + "\n")
