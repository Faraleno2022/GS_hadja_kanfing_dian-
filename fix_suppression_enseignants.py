"""
Script pour diagnostiquer et activer la permission de suppression définitive des enseignants
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from utilisateurs.models import Profil
from salaires.models import Enseignant, EtatSalaire, AffectationClasse, PresenceEnseignant
from utilisateurs.utils import user_is_admin

def afficher_separateur():
    print("\n" + "="*70 + "\n")

def diagnostiquer_utilisateur(username=None):
    """Diagnostique les permissions d'un utilisateur pour les enseignants"""
    print("🔍 DIAGNOSTIC DES PERMISSIONS DE SUPPRESSION D'ENSEIGNANTS")
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
        print(f"   Peut supprimer enseignants définitivement: {'✅ Oui' if profil.peut_supprimer_enseignants_definitivement else '❌ Non'}")
        print(f"   Peut supprimer élèves définitivement: {'✅ Oui' if profil.peut_supprimer_eleves_definitivement else '❌ Non'}")
    except:
        print(f"\n⚠️ Pas de profil associé")
        profil = None
    
    # Calculer la permission finale
    peut_supprimer = user_is_admin(user) or (
        hasattr(user, 'profil') and 
        user.profil.peut_supprimer_enseignants_definitivement
    )
    
    print(f"\n🎯 Permission finale de suppression définitive d'enseignants: {'✅ OUI' if peut_supprimer else '❌ NON'}")
    
    if not peut_supprimer:
        print("\n⚠️ Raisons possibles:")
        if not user.is_superuser:
            print("   - L'utilisateur n'est pas superuser")
        if profil and not profil.peut_supprimer_enseignants_definitivement:
            print("   - Le profil n'a pas la permission 'peut_supprimer_enseignants_definitivement'")
        if not profil:
            print("   - L'utilisateur n'a pas de profil associé")
    
    return user, profil, peut_supprimer

def activer_permission_suppression(username):
    """Active la permission de suppression définitive des enseignants pour un utilisateur"""
    print(f"\n🔧 ACTIVATION DE LA PERMISSION ENSEIGNANTS POUR '{username}'")
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
        profil.peut_supprimer_enseignants_definitivement = True
        profil.save()
        print("✅ Permission 'peut_supprimer_enseignants_definitivement' activée")
        
        # Vérifier
        peut_supprimer = user_is_admin(user) or profil.peut_supprimer_enseignants_definitivement
        print(f"\n🎯 Résultat: L'utilisateur {'PEUT' if peut_supprimer else 'NE PEUT PAS'} maintenant supprimer définitivement des enseignants")
        
        return True
        
    except User.DoesNotExist:
        print(f"❌ Utilisateur '{username}' introuvable")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def lister_utilisateurs_avec_permission():
    """Liste tous les utilisateurs ayant la permission de suppression définitive des enseignants"""
    print("\n📊 UTILISATEURS AVEC PERMISSION DE SUPPRESSION D'ENSEIGNANTS")
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
        profil__peut_supprimer_enseignants_definitivement=True,
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
    print(f"\n📈 Total: {total} utilisateur(s) peuvent supprimer définitivement des enseignants")

def afficher_statistiques():
    """Affiche les statistiques sur les enseignants"""
    print("\n📊 STATISTIQUES DES ENSEIGNANTS")
    afficher_separateur()
    
    total_enseignants = Enseignant.objects.count()
    enseignants_actifs = Enseignant.objects.filter(statut='ACTIF').count()
    enseignants_demissionnaires = Enseignant.objects.filter(statut='DEMISSIONNAIRE').count()
    enseignants_suspendus = Enseignant.objects.filter(statut='SUSPENDU').count()
    enseignants_conge = Enseignant.objects.filter(statut='CONGE').count()
    
    print(f"👨‍🏫 Enseignants:")
    print(f"   Total: {total_enseignants}")
    print(f"   Actifs: {enseignants_actifs}")
    print(f"   En congé: {enseignants_conge}")
    print(f"   Suspendus: {enseignants_suspendus}")
    print(f"   Démissionnaires (soft delete): {enseignants_demissionnaires}")
    
    # États de salaire
    total_etats_salaire = EtatSalaire.objects.count()
    etats_payes = EtatSalaire.objects.filter(paye=True).count()
    etats_non_payes = EtatSalaire.objects.filter(paye=False).count()
    
    print(f"\n💰 États de salaire:")
    print(f"   Total: {total_etats_salaire}")
    print(f"   Payés: {etats_payes}")
    print(f"   Non payés: {etats_non_payes}")
    
    # Affectations
    total_affectations = AffectationClasse.objects.count()
    affectations_actives = AffectationClasse.objects.filter(actif=True).count()
    
    print(f"\n🏫 Affectations de classe:")
    print(f"   Total: {total_affectations}")
    print(f"   Actives: {affectations_actives}")
    
    # Présences
    total_presences = PresenceEnseignant.objects.count() if hasattr(PresenceEnseignant, 'objects') else 0
    print(f"\n📅 Présences enregistrées: {total_presences}")

def test_suppression_simulee():
    """Simule une suppression pour tester la logique"""
    print("\n🧪 TEST DE SIMULATION DE SUPPRESSION D'ENSEIGNANT")
    afficher_separateur()
    
    # Prendre le premier enseignant actif comme test (sans vraiment supprimer)
    enseignant = Enseignant.objects.filter(statut='ACTIF').first()
    if not enseignant:
        print("❌ Aucun enseignant actif trouvé pour le test")
        return
    
    print(f"👨‍🏫 Enseignant test: {enseignant.nom_complet}")
    print(f"   École: {enseignant.ecole.nom}")
    print(f"   Type: {enseignant.get_type_enseignant_display()}")
    print(f"   Statut: {enseignant.statut}")
    
    # Compter les éléments associés
    etats_count = enseignant.etats_salaire.count()
    affectations_count = enseignant.affectations.count()
    presences_count = enseignant.presences.count()
    
    print(f"\n📋 Éléments associés:")
    print(f"   États de salaire: {etats_count}")
    print(f"   Affectations de classe: {affectations_count}")
    print(f"   Présences: {presences_count}")
    
    # Simuler différents scénarios
    print("\n📝 Scénarios de suppression:")
    
    # Scénario 1: Utilisateur avec permission
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        peut_supprimer = user_is_admin(admin) or (
            hasattr(admin, 'profil') and 
            admin.profil.peut_supprimer_enseignants_definitivement
        )
        print(f"\n1. Admin '{admin.username}':")
        print(f"   Peut supprimer définitivement: {'✅ OUI' if peut_supprimer else '❌ NON'}")
        if peut_supprimer:
            print("   → Résultat attendu: SUPPRESSION DÉFINITIVE + CORBEILLE")
            print("   → États de salaire, affectations et présences supprimés")
        else:
            print("   → Résultat attendu: STATUT → DÉMISSIONNAIRE (soft delete)")
    
    # Scénario 2: Utilisateur sans permission
    user_normal = User.objects.filter(is_superuser=False).first()
    if user_normal:
        peut_supprimer = user_is_admin(user_normal) or (
            hasattr(user_normal, 'profil') and 
            user_normal.profil.peut_supprimer_enseignants_definitivement
        )
        print(f"\n2. Utilisateur normal '{user_normal.username}':")
        print(f"   Peut supprimer définitivement: {'✅ OUI' if peut_supprimer else '❌ NON'}")
        if peut_supprimer:
            print("   → Résultat attendu: SUPPRESSION DÉFINITIVE + CORBEILLE")
        else:
            print("   → Résultat attendu: STATUT → DÉMISSIONNAIRE (soft delete)")
            print("   → Données conservées")
    
    print("\n💡 Note: Aucune suppression réelle effectuée (simulation seulement)")

def afficher_solution():
    """Affiche la solution pour activer la suppression définitive"""
    print("\n💊 SOLUTION POUR ACTIVER LA SUPPRESSION DÉFINITIVE D'ENSEIGNANTS")
    afficher_separateur()
    
    print("Pour qu'un utilisateur puisse supprimer définitivement des enseignants:")
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
    print("   >>> profil.peut_supprimer_enseignants_definitivement = True")
    print("   >>> profil.save()")
    
    print("\nOPTION 3: Utiliser ce script")
    print("   python fix_suppression_enseignants.py --activer USERNAME")
    
    print("\n📌 Après activation, l'utilisateur verra:")
    print("   ✅ La case 'Suppression définitive' dans le formulaire")
    print("   ✅ Possibilité de supprimer définitivement avec le code 625196629")
    print("   ✅ L'enseignant et ses états de salaire seront supprimés")
    print("   ✅ Une entrée sera créée dans la corbeille (SystemLog)")
    
    print("\n🔒 Code de vérification: 625196629")

if __name__ == '__main__':
    import sys
    
    print("\n" + "="*70)
    print("🔧 FIX SUPPRESSION DÉFINITIVE DES ENSEIGNANTS".center(70))
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
        elif sys.argv[1] == '--stats':
            # Afficher les statistiques
            afficher_statistiques()
        elif sys.argv[1] == '--test':
            # Test de simulation
            test_suppression_simulee()
        else:
            print("Usage:")
            print("  python fix_suppression_enseignants.py                    # Diagnostic général")
            print("  python fix_suppression_enseignants.py --diagnostic USER  # Diagnostic d'un utilisateur")
            print("  python fix_suppression_enseignants.py --activer USER     # Activer la permission")
            print("  python fix_suppression_enseignants.py --liste           # Lister les utilisateurs avec permission")
            print("  python fix_suppression_enseignants.py --stats           # Statistiques des enseignants")
            print("  python fix_suppression_enseignants.py --test            # Test de simulation")
    else:
        # Mode par défaut: diagnostic général
        diagnostiquer_utilisateur()
        lister_utilisateurs_avec_permission()
        afficher_statistiques()
        afficher_solution()
    
    print("\n" + "="*70 + "\n")
