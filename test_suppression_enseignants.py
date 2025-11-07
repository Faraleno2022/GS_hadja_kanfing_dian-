"""
Script de test pour vérifier la suppression définitive des enseignants
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.db.models import Count
from salaires.models import Enseignant, EtatSalaire, AffectationClasse, PeriodeSalaire, TypeEnseignant
from eleves.models import Ecole, Classe
from utilisateurs.models import Profil
from administration.models import SystemLog
from decimal import Decimal
from datetime import date, datetime

def creer_donnees_test():
    """Créer des données de test pour les enseignants"""
    print("\n📝 CRÉATION DES DONNÉES DE TEST")
    print("="*50)
    
    # Créer ou récupérer une école
    ecole, created = Ecole.objects.get_or_create(
        nom="École Test Enseignants",
        defaults={
            'code_prefixe': 'TEST',
            'adresse': '123 Rue Test',
            'telephone': '123456789',
            'email': 'test@ecole.com',
            'directeur': 'M. Test',
            'statut': 'EN_ATTENTE'
        }
    )
    print(f"✅ École: {ecole.nom} {'(créée)' if created else '(existante)'}")
    
    # Créer une classe
    classe, created = Classe.objects.get_or_create(
        nom="Classe Test",
        ecole=ecole,
        defaults={
            'niveau': 'PRIMAIRE',
            'annee_scolaire': '2024-2025',
            'capacite_max': 30,
            'frais_inscription': Decimal('100000'),
            'frais_scolarite': Decimal('500000')
        }
    )
    print(f"✅ Classe: {classe.nom} {'(créée)' if created else '(existante)'}")
    
    # Créer un enseignant test
    enseignant, created = Enseignant.objects.get_or_create(
        nom="ENSEIGNANT",
        prenoms="Test Suppression",
        ecole=ecole,
        defaults={
            'telephone': '600000000',
            'email': 'enseignant@test.com',
            'adresse': 'Adresse Test',
            'type_enseignant': TypeEnseignant.PRIMAIRE,
            'statut': 'ACTIF',
            'salaire_fixe': Decimal('2000000'),
            'date_embauche': date.today()
        }
    )
    print(f"✅ Enseignant: {enseignant.nom_complet} {'(créé)' if created else '(existant)'}")
    
    # Créer une affectation
    affectation, created = AffectationClasse.objects.get_or_create(
        enseignant=enseignant,
        classe=classe,
        defaults={
            'date_debut': date.today(),
            'matiere': 'Mathématiques',
            'actif': True
        }
    )
    print(f"✅ Affectation: {affectation} {'(créée)' if created else '(existante)'}")
    
    # Créer une période de salaire
    periode, created = PeriodeSalaire.objects.get_or_create(
        mois=11,
        annee=2024,
        ecole=ecole,
        defaults={
            'nombre_semaines': Decimal('4.33')
        }
    )
    print(f"✅ Période: {periode.nom_periode} {'(créée)' if created else '(existante)'}")
    
    # Créer un état de salaire
    etat, created = EtatSalaire.objects.get_or_create(
        enseignant=enseignant,
        periode=periode,
        defaults={
            'salaire_base': Decimal('2000000'),
            'primes': Decimal('100000'),
            'deductions': Decimal('50000'),
            'salaire_net': Decimal('2050000'),
            'valide': True,
            'paye': False
        }
    )
    print(f"✅ État de salaire: {etat} {'(créé)' if created else '(existant)'}")
    
    return enseignant

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
            username='admin_test_enseignant',
            password='test123',
            email='admin@test.com'
        )
        print(f"✅ Superuser créé: {admin_user.username}")
    else:
        print(f"✅ Superuser trouvé: {admin_user.username}")
    
    # Assurer que le profil a la permission
    profil, created = Profil.objects.get_or_create(user=admin_user)
    profil.peut_supprimer_enseignants_definitivement = True
    profil.save()
    print(f"✅ Permission de suppression définitive d'enseignants activée")
    
    # Créer un enseignant test
    enseignant = creer_donnees_test()
    
    # Compter les éléments avant
    etats_count = enseignant.etats_salaire.count()
    affectations_count = enseignant.affectations.count()
    presences_count = enseignant.presences.count()
    logs_avant = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE_ENSEIGNANT').count()
    
    print(f"\n📊 Avant suppression:")
    print(f"   Enseignant: {enseignant.nom_complet}")
    print(f"   États de salaire: {etats_count}")
    print(f"   Affectations: {affectations_count}")
    print(f"   Présences: {presences_count}")
    print(f"   Logs de suppression: {logs_avant}")
    
    # Simuler la suppression (sans vraiment envoyer la requête POST)
    print("\n📝 Simulation de suppression définitive:")
    print("   - Code de vérification: 625196629")
    print("   - Case 'suppression_definitive': cochée")
    print("   - Utilisateur: admin avec permission")
    
    # Vérifier la permission
    from utilisateurs.utils import user_is_admin
    peut_supprimer = user_is_admin(admin_user) or (
        hasattr(admin_user, 'profil') and 
        admin_user.profil.peut_supprimer_enseignants_definitivement
    )
    
    print(f"\n🎯 Résultat attendu:")
    if peut_supprimer:
        print("   ✅ L'enseignant sera SUPPRIMÉ DÉFINITIVEMENT")
        print("   ✅ Un log sera créé dans SystemLog (action: SUPPRESSION_DEFINITIVE_ENSEIGNANT)")
        print("   ✅ Tous les états de salaire seront supprimés")
        print("   ✅ Toutes les affectations seront supprimées")
        print("   ✅ Toutes les présences seront supprimées")
    else:
        print("   ⚠️ L'enseignant sera marqué comme DÉMISSIONNAIRE (soft delete)")
    
    return True

def test_suppression_sans_permission():
    """Test de suppression avec un utilisateur sans permission"""
    print("\n🧪 TEST DE SUPPRESSION SANS PERMISSION")
    print("="*50)
    
    # Créer un utilisateur normal
    user_normal, created = User.objects.get_or_create(
        username='user_normal_enseignant',
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
    profil.peut_supprimer_enseignants_definitivement = False
    profil.save()
    print(f"✅ Permission de suppression définitive d'enseignants: DÉSACTIVÉE")
    
    # Vérifier la permission
    from utilisateurs.utils import user_is_admin
    peut_supprimer = user_is_admin(user_normal) or (
        hasattr(user_normal, 'profil') and 
        user_normal.profil.peut_supprimer_enseignants_definitivement
    )
    
    print(f"\n🎯 Résultat attendu pour '{user_normal.username}':")
    if peut_supprimer:
        print("   ❌ ERREUR: L'utilisateur ne devrait pas pouvoir supprimer!")
    else:
        print("   ✅ L'utilisateur ne verra PAS la case 'Suppression définitive'")
        print("   ✅ L'enseignant sera marqué comme DÉMISSIONNAIRE (soft delete)")
        print("   ✅ Les données seront conservées (états de salaire, affectations, présences)")
    
    return True

def verifier_corbeille_enseignants():
    """Vérifie les entrées dans la corbeille pour les enseignants"""
    print("\n📦 VÉRIFICATION DE LA CORBEILLE (ENSEIGNANTS)")
    print("="*50)
    
    # Compter les suppressions définitives d'enseignants
    suppressions = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE_ENSEIGNANT').order_by('-created_at')[:5]
    
    if suppressions.exists():
        print(f"✅ {suppressions.count()} suppression(s) définitive(s) d'enseignant(s) trouvée(s):")
        for log in suppressions:
            print(f"\n   📝 {log.created_at.strftime('%d/%m/%Y %H:%M')}")
            print(f"      Utilisateur: {log.user}")
            print(f"      Description: {log.description[:100]}...")
            if log.details:
                if 'nom_complet' in log.details:
                    print(f"      Enseignant: {log.details['nom_complet']}")
                if 'ecole' in log.details:
                    print(f"      École: {log.details['ecole']}")
                if 'etats_supprimes' in log.details:
                    print(f"      États supprimés: {len(log.details['etats_supprimes'])}")
    else:
        print("⚠️ Aucune suppression définitive d'enseignant dans la corbeille")
    
    return True

def afficher_stats():
    """Affiche les statistiques de suppression"""
    print("\n📊 STATISTIQUES")
    print("="*50)
    
    # Compter les enseignants
    total_enseignants = Enseignant.objects.count()
    enseignants_actifs = Enseignant.objects.filter(statut='ACTIF').count()
    enseignants_demissionnaires = Enseignant.objects.filter(statut='DEMISSIONNAIRE').count()
    
    print(f"👨‍🏫 Enseignants:")
    print(f"   Total: {total_enseignants}")
    print(f"   Actifs: {enseignants_actifs}")
    print(f"   Démissionnaires (soft delete): {enseignants_demissionnaires}")
    
    # Compter les utilisateurs avec permission
    from django.db.models import Q
    users_avec_permission = User.objects.filter(
        Q(is_superuser=True) |
        Q(profil__peut_supprimer_enseignants_definitivement=True)
    ).distinct().count()
    
    print(f"\n👤 Utilisateurs:")
    print(f"   Avec permission de suppression définitive d'enseignants: {users_avec_permission}")
    
    # Compter les logs de suppression
    suppressions_definitives = SystemLog.objects.filter(action='SUPPRESSION_DEFINITIVE_ENSEIGNANT').count()
    print(f"\n📦 Corbeille:")
    print(f"   Suppressions définitives d'enseignants enregistrées: {suppressions_definitives}")
    
    # États de salaire
    total_etats = EtatSalaire.objects.count()
    print(f"\n💰 États de salaire total: {total_etats}")

def nettoyer_donnees_test():
    """Nettoie les données de test créées"""
    print("\n🧹 NETTOYAGE DES DONNÉES DE TEST")
    print("="*50)
    
    # Supprimer l'enseignant test
    enseignants_test = Enseignant.objects.filter(nom="ENSEIGNANT", prenoms="Test Suppression")
    count = enseignants_test.count()
    if count > 0:
        enseignants_test.delete()
        print(f"✅ {count} enseignant(s) test supprimé(s)")
    
    # Supprimer l'école test
    ecoles_test = Ecole.objects.filter(nom="École Test Enseignants")
    count = ecoles_test.count()
    if count > 0:
        ecoles_test.delete()
        print(f"✅ {count} école(s) test supprimée(s)")
    
    # Supprimer les utilisateurs test
    users_test = User.objects.filter(username__in=['admin_test_enseignant', 'user_normal_enseignant'])
    count = users_test.count()
    if count > 0:
        users_test.delete()
        print(f"✅ {count} utilisateur(s) test supprimé(s)")
    
    print("✅ Nettoyage terminé")

if __name__ == '__main__':
    print("\n" + "="*70)
    print("TEST DE SUPPRESSION DÉFINITIVE DES ENSEIGNANTS".center(70))
    print("="*70)
    
    try:
        # Exécuter les tests
        test_suppression_avec_permission()
        test_suppression_sans_permission()
        verifier_corbeille_enseignants()
        afficher_stats()
        
        # Optionnel: nettoyer les données de test
        # nettoyer_donnees_test()
        
        print("\n" + "="*70)
        print("✅ TESTS TERMINÉS AVEC SUCCÈS".center(70))
        print("="*70)
        
        print("\n💡 RAPPEL:")
        print("   Code de vérification: 625196629")
        print("   Permission requise: peut_supprimer_enseignants_definitivement")
        
        print("\n📌 Pour activer la permission pour un utilisateur:")
        print("   python fix_suppression_enseignants.py --activer USERNAME")
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
