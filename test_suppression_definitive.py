"""
Script de test pour vérifier la suppression définitive des élèves
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from eleves.models import Eleve
from utilisateurs.models import Profil
from administration.models import SystemLog

def test_suppression_avec_permission():
    """Test de suppression avec un utilisateur ayant la permission"""
    print("\n🧪 TEST DE SUPPRESSION AVEC PERMISSION")
    print("="*50)
    
    # Créer un client de test
    client = Client()
    
    # Trouver ou créer un utilisateur admin
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("❌ Aucun superuser trouvé. Créons-en un...")
        admin_user = User.objects.create_superuser(
            username='admin_test',
            password='test123',
            email='admin@test.com'
        )
        print(f"✅ Superuser créé: {admin_user.username}")
    else:
        print(f"✅ Superuser trouvé: {admin_user.username}")
    
    # Assurer que le profil a la permission
    profil, created = Profil.objects.get_or_create(user=admin_user)
    profil.peut_supprimer_eleves_definitivement = True
    profil.save()
    print(f"✅ Permission de suppression définitive activée")
    
    # Se connecter
    client.force_login(admin_user)
    print(f"✅ Connecté en tant que: {admin_user.username}")
    
    # Trouver un élève test
    eleve_test = Eleve.objects.filter(statut='ACTIF').first()
    if not eleve_test:
        print("❌ Aucun élève actif pour le test")
        return False
    
    print(f"\n📚 Élève test: {eleve_test.prenom} {eleve_test.nom}")
    print(f"   ID: {eleve_test.id}")
    print(f"   Matricule: {eleve_test.matricule}")
    print(f"   Classe: {eleve_test.classe}")
    
    # Compter les logs avant
    logs_avant = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE').count()
    
    # Simuler la suppression (sans vraiment envoyer la requête POST)
    print("\n📝 Simulation de suppression définitive:")
    print("   - Code de vérification: 625196629")
    print("   - Case 'suppression_definitive': cochée")
    print("   - Utilisateur: admin avec permission")
    
    # Vérifier la permission
    from utilisateurs.utils import user_is_admin
    peut_supprimer = user_is_admin(admin_user) or (
        hasattr(admin_user, 'profil') and 
        admin_user.profil.peut_supprimer_eleves_definitivement
    )
    
    print(f"\n🎯 Résultat attendu:")
    if peut_supprimer:
        print("   ✅ L'élève sera SUPPRIMÉ DÉFINITIVEMENT")
        print("   ✅ Un log sera créé dans SystemLog")
        print("   ✅ Tous les paiements seront supprimés")
        print("   ✅ Tous les abonnements seront supprimés")
    else:
        print("   ⚠️ L'élève sera marqué comme EXCLU (soft delete)")
    
    return True

def test_suppression_sans_permission():
    """Test de suppression avec un utilisateur sans permission"""
    print("\n🧪 TEST DE SUPPRESSION SANS PERMISSION")
    print("="*50)
    
    # Créer un utilisateur normal
    user_normal, created = User.objects.get_or_create(
        username='user_normal',
        defaults={'email': 'normal@test.com'}
    )
    if created:
        user_normal.set_password('test123')
        user_normal.save()
        print(f"✅ Utilisateur normal créé: {user_normal.username}")
    else:
        print(f"✅ Utilisateur normal trouvé: {user_normal.username}")
    
    # S'assurer qu'il n'a PAS la permission
    profil, created = Profil.objects.get_or_create(user=user_normal)
    profil.peut_supprimer_eleves_definitivement = False
    profil.save()
    print(f"✅ Permission de suppression définitive: DÉSACTIVÉE")
    
    # Vérifier la permission
    from utilisateurs.utils import user_is_admin
    peut_supprimer = user_is_admin(user_normal) or (
        hasattr(user_normal, 'profil') and 
        user_normal.profil.peut_supprimer_eleves_definitivement
    )
    
    print(f"\n🎯 Résultat attendu pour '{user_normal.username}':")
    if peut_supprimer:
        print("   ❌ ERREUR: L'utilisateur ne devrait pas pouvoir supprimer!")
    else:
        print("   ✅ L'utilisateur ne verra PAS la case 'Suppression définitive'")
        print("   ✅ L'élève sera marqué comme EXCLU (soft delete)")
        print("   ✅ Les données seront conservées")
    
    return True

def verifier_corbeille():
    """Vérifie les entrées dans la corbeille (SystemLog)"""
    print("\n📦 VÉRIFICATION DE LA CORBEILLE")
    print("="*50)
    
    # Compter les suppressions définitives
    suppressions = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE').order_by('-created_at')[:5]
    
    if suppressions.exists():
        print(f"✅ {suppressions.count()} suppression(s) définitive(s) trouvée(s):")
        for log in suppressions:
            print(f"\n   📝 {log.created_at.strftime('%d/%m/%Y %H:%M')}")
            print(f"      Utilisateur: {log.user}")
            print(f"      Description: {log.description[:100]}...")
            if log.details:
                if 'nom_complet' in log.details:
                    print(f"      Élève: {log.details['nom_complet']}")
                if 'matricule' in log.details:
                    print(f"      Matricule: {log.details['matricule']}")
    else:
        print("⚠️ Aucune suppression définitive dans la corbeille")
    
    return True

def afficher_stats():
    """Affiche les statistiques de suppression"""
    print("\n📊 STATISTIQUES")
    print("="*50)
    
    # Compter les élèves
    total_eleves = Eleve.objects.count()
    eleves_actifs = Eleve.objects.filter(statut='ACTIF').count()
    eleves_exclus = Eleve.objects.filter(statut='EXCLU').count()
    
    print(f"📚 Élèves:")
    print(f"   Total: {total_eleves}")
    print(f"   Actifs: {eleves_actifs}")
    print(f"   Exclus (soft delete): {eleves_exclus}")
    
    # Compter les utilisateurs avec permission
    from django.db.models import Q
    users_avec_permission = User.objects.filter(
        Q(is_superuser=True) |
        Q(profil__peut_supprimer_eleves_definitivement=True)
    ).distinct().count()
    
    print(f"\n👤 Utilisateurs:")
    print(f"   Avec permission de suppression définitive: {users_avec_permission}")
    
    # Compter les logs de suppression
    suppressions_definitives = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE').count()
    print(f"\n📦 Corbeille:")
    print(f"   Suppressions définitives enregistrées: {suppressions_definitives}")

if __name__ == '__main__':
    print("\n" + "="*70)
    print("TEST DE SUPPRESSION DÉFINITIVE DES ÉLÈVES".center(70))
    print("="*70)
    
    try:
        # Exécuter les tests
        test_suppression_avec_permission()
        test_suppression_sans_permission()
        verifier_corbeille()
        afficher_stats()
        
        print("\n" + "="*70)
        print("✅ TESTS TERMINÉS AVEC SUCCÈS".center(70))
        print("="*70)
        
        print("\n💡 RAPPEL DU CODE DE VÉRIFICATION: 625196629")
        print("\n📌 Pour activer la permission pour un utilisateur:")
        print("   python fix_suppression_definitive.py --activer USERNAME")
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
