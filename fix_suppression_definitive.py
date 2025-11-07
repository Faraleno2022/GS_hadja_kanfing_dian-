"""
Script pour diagnostiquer et corriger le problème de suppression définitive des élèves
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

def afficher_separateur():
    print("\n" + "="*70 + "\n")

def diagnostiquer_utilisateur(username=None):
    """Diagnostique les permissions d'un utilisateur"""
    print("🔍 DIAGNOSTIC DES PERMISSIONS DE SUPPRESSION")
    afficher_separateur()
    
    # Si aucun username fourni, chercher l'admin ou le premier utilisateur
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            print(f"❌ Utilisateur '{username}' introuvable")
            return None
    else:
        # Chercher d'abord les superusers
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
    
    if not user:
        print("❌ Aucun utilisateur trouvé")
        return None
    
    print(f"👤 Utilisateur: {user.username}")
    print(f"   Email: {user.email or 'Non défini'}")
    print(f"   Superuser: {'✅ Oui' if user.is_superuser else '❌ Non'}")
    print(f"   Staff: {'✅ Oui' if user.is_staff else '❌ Non'}")
    print(f"   Actif: {'✅ Oui' if user.is_active else '❌ Non'}")
    
    # Vérifier le profil
    try:
        profil = user.profil
        print(f"\n📋 Profil trouvé:")
        print(f"   École: {profil.ecole.nom if profil.ecole else 'Non définie'}")
        print(f"   Rôle: {profil.role}")
        print(f"   Peut supprimer définitivement: {'✅ Oui' if profil.peut_supprimer_eleves_definitivement else '❌ Non'}")
        print(f"   Peut supprimer paiements: {'✅ Oui' if profil.peut_supprimer_paiements else '❌ Non'}")
        print(f"   Peut supprimer dépenses: {'✅ Oui' if profil.peut_supprimer_depenses else '❌ Non'}")
        print(f"   Peut supprimer abonnements: {'✅ Oui' if profil.peut_supprimer_abonnements else '❌ Non'}")
    except:
        print(f"\n⚠️ Pas de profil associé")
        profil = None
    
    # Calculer la permission finale
    peut_supprimer = user_is_admin(user) or (
        hasattr(user, 'profil') and 
        user.profil.peut_supprimer_eleves_definitivement
    )
    
    print(f"\n🎯 Permission finale de suppression définitive: {'✅ OUI' if peut_supprimer else '❌ NON'}")
    
    if not peut_supprimer:
        print("\n⚠️ Raisons possibles:")
        if not user.is_superuser:
            print("   - L'utilisateur n'est pas superuser")
        if profil and not profil.peut_supprimer_eleves_definitivement:
            print("   - Le profil n'a pas la permission 'peut_supprimer_eleves_definitivement'")
        if not profil:
            print("   - L'utilisateur n'a pas de profil associé")
    
    return user, profil, peut_supprimer

def activer_permission_suppression(username):
    """Active la permission de suppression définitive pour un utilisateur"""
    print(f"\n🔧 ACTIVATION DE LA PERMISSION POUR '{username}'")
    afficher_separateur()
    
    try:
        user = User.objects.get(username=username)
        print(f"✅ Utilisateur trouvé: {user.username}")
        
        # Créer ou récupérer le profil
        profil, created = Profil.objects.get_or_create(user=user)
        if created:
            print("✅ Profil créé")
        else:
            print("✅ Profil existant")
        
        # Activer la permission
        profil.peut_supprimer_eleves_definitivement = True
        profil.save()
        print("✅ Permission 'peut_supprimer_eleves_definitivement' activée")
        
        # Vérifier
        peut_supprimer = user_is_admin(user) or profil.peut_supprimer_eleves_definitivement
        print(f"\n🎯 Résultat: L'utilisateur {'PEUT' if peut_supprimer else 'NE PEUT PAS'} maintenant supprimer définitivement")
        
        return True
        
    except User.DoesNotExist:
        print(f"❌ Utilisateur '{username}' introuvable")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def lister_utilisateurs_avec_permission():
    """Liste tous les utilisateurs ayant la permission de suppression définitive"""
    print("\n📊 UTILISATEURS AVEC PERMISSION DE SUPPRESSION DÉFINITIVE")
    afficher_separateur()
    
    # Superusers
    superusers = User.objects.filter(is_superuser=True, is_active=True)
    if superusers.exists():
        print("👑 Superusers (permission automatique):")
        for user in superusers:
            print(f"   - {user.username} ({user.email or 'pas d\'email'})")
    else:
        print("👑 Aucun superuser actif")
    
    # Utilisateurs avec permission via profil
    users_avec_permission = User.objects.filter(
        profil__peut_supprimer_eleves_definitivement=True,
        is_superuser=False,
        is_active=True
    )
    if users_avec_permission.exists():
        print("\n👤 Utilisateurs avec permission via profil:")
        for user in users_avec_permission:
            print(f"   - {user.username} ({user.email or 'pas d\'email'})")
    else:
        print("\n👤 Aucun utilisateur normal avec cette permission")
    
    # Total
    total = superusers.count() + users_avec_permission.count()
    print(f"\n📈 Total: {total} utilisateur(s) peuvent supprimer définitivement")

def test_suppression_simulee():
    """Simule une suppression pour tester la logique"""
    print("\n🧪 TEST DE SIMULATION DE SUPPRESSION")
    afficher_separateur()
    
    # Prendre le premier élève comme test (sans vraiment supprimer)
    eleve = Eleve.objects.filter(statut='ACTIF').first()
    if not eleve:
        print("❌ Aucun élève actif trouvé pour le test")
        return
    
    print(f"📚 Élève test: {eleve.prenom} {eleve.nom} ({eleve.matricule})")
    print(f"   Classe: {eleve.classe}")
    print(f"   Statut: {eleve.statut}")
    
    # Simuler différents scénarios
    print("\n📝 Scénarios de suppression:")
    
    # Scénario 1: Utilisateur avec permission
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        peut_supprimer = user_is_admin(admin) or (
            hasattr(admin, 'profil') and 
            admin.profil.peut_supprimer_eleves_definitivement
        )
        print(f"\n1. Admin '{admin.username}':")
        print(f"   Peut supprimer définitivement: {'✅ OUI' if peut_supprimer else '❌ NON'}")
        if peut_supprimer:
            print("   → Résultat attendu: SUPPRESSION DÉFINITIVE + CORBEILLE")
        else:
            print("   → Résultat attendu: STATUT → EXCLU (soft delete)")
    
    # Scénario 2: Utilisateur sans permission
    user_normal = User.objects.filter(is_superuser=False).first()
    if user_normal:
        peut_supprimer = user_is_admin(user_normal) or (
            hasattr(user_normal, 'profil') and 
            user_normal.profil.peut_supprimer_eleves_definitivement
        )
        print(f"\n2. Utilisateur normal '{user_normal.username}':")
        print(f"   Peut supprimer définitivement: {'✅ OUI' if peut_supprimer else '❌ NON'}")
        if peut_supprimer:
            print("   → Résultat attendu: SUPPRESSION DÉFINITIVE + CORBEILLE")
        else:
            print("   → Résultat attendu: STATUT → EXCLU (soft delete)")
    
    print("\n💡 Note: Aucune suppression réelle effectuée (simulation seulement)")

def afficher_solution():
    """Affiche la solution pour corriger le problème"""
    print("\n💊 SOLUTION POUR ACTIVER LA SUPPRESSION DÉFINITIVE")
    afficher_separateur()
    
    print("Pour qu'un utilisateur puisse supprimer définitivement, il faut:")
    print("\nOPTION 1: Rendre l'utilisateur superuser")
    print("   python manage.py shell")
    print("   >>> from django.contrib.auth.models import User")
    print("   >>> user = User.objects.get(username='votre_username')")
    print("   >>> user.is_superuser = True")
    print("   >>> user.save()")
    
    print("\nOPTION 2: Activer la permission dans le profil")
    print("   python manage.py shell")
    print("   >>> from django.contrib.auth.models import User")
    print("   >>> from utilisateurs.models import Profil")
    print("   >>> user = User.objects.get(username='votre_username')")
    print("   >>> profil, created = Profil.objects.get_or_create(user=user)")
    print("   >>> profil.peut_supprimer_eleves_definitivement = True")
    print("   >>> profil.save()")
    
    print("\nOPTION 3: Utiliser ce script")
    print("   python fix_suppression_definitive.py --activer USERNAME")
    
    print("\n📌 Après activation, l'utilisateur verra:")
    print("   ✅ La case 'Suppression définitive' dans le formulaire")
    print("   ✅ Possibilité de supprimer définitivement avec le code 625196629")
    print("   ✅ L'élève sera supprimé et placé dans la corbeille (SystemLog)")

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*70)
    print("🔧 FIX SUPPRESSION DÉFINITIVE DES ÉLÈVES".center(70))
    print("="*70)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--activer' and len(sys.argv) > 2:
            # Activer la permission pour un utilisateur
            username = sys.argv[2]
            activer_permission_suppression(username)
        elif sys.argv[1] == '--diagnostic' and len(sys.argv) > 2:
            # Diagnostiquer un utilisateur spécifique
            username = sys.argv[2]
            diagnostiquer_utilisateur(username)
        elif sys.argv[1] == '--liste':
            # Lister les utilisateurs avec permission
            lister_utilisateurs_avec_permission()
        elif sys.argv[1] == '--test':
            # Test de simulation
            test_suppression_simulee()
        else:
            print("Usage:")
            print("  python fix_suppression_definitive.py                    # Diagnostic général")
            print("  python fix_suppression_definitive.py --diagnostic USER  # Diagnostic d'un utilisateur")
            print("  python fix_suppression_definitive.py --activer USER     # Activer la permission")
            print("  python fix_suppression_definitive.py --liste           # Lister les utilisateurs avec permission")
            print("  python fix_suppression_definitive.py --test            # Test de simulation")
    else:
        # Mode par défaut: diagnostic général
        diagnostiquer_utilisateur()
        lister_utilisateurs_avec_permission()
        afficher_solution()
    
    print("\n" + "="*70 + "\n")
