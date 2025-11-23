#!/usr/bin/env python
"""
Tester le comportement du décorateur @require_school_object
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from notes.models import ClasseNote
from eleves.models import Ecole

def tester_decorateur_school():
    """Tester le décorateur @require_school_object"""
    print("🔍 TEST DÉCORATEUR @require_school_object")
    print("=" * 45)
    
    # Vérifier l'utilisateur admin et son école
    print(f"📋 Vérification utilisateur admin:")
    try:
        user = User.objects.filter(is_superuser=True).first()
        print(f"✅ Utilisateur: {user.username}")
        
        user_profil = getattr(user, 'profil', None)
        if user_profil:
            print(f"✅ Profil: {user_profil}")
            print(f"   - École: {user_profil.ecole}")
            print(f"   - Rôle: {user_profil.role}")
        else:
            print(f"❌ Pas de profil")
            
    except Exception as e:
        print(f"❌ Erreur utilisateur: {e}")
        return False
    
    # Vérifier la ClasseNote et son école
    print(f"\n📋 Vérification ClasseNote 59:")
    try:
        classe = ClasseNote.objects.get(pk=59)
        print(f"✅ ClasseNote: {classe.nom}")
        print(f"   - École: {classe.ecole}")
        print(f"   - ID École: {classe.ecole.id if classe.ecole else None}")
        
    except Exception as e:
        print(f"❌ Erreur ClasseNote: {e}")
        return False
    
    # Vérifier la compatibilité école
    print(f"\n📋 Vérification compatibilité école:")
    user_ecole = user_profil.ecole if user_profil else None
    classe_ecole = classe.ecole
    
    print(f"   - École utilisateur: {user_ecole}")
    print(f"   - École classe: {classe_ecole}")
    
    if user_ecole is None:
        print(f"⚠️  Utilisateur admin sans école assignée")
        print(f"   Le décorateur @require_school_object pourrait bloquer")
    elif user_ecole == classe_ecole:
        print(f"✅ Écoles compatibles")
    else:
        print(f"❌ Écoles incompatibles - Cela explique la 404 !")
        return False
    
    # Test avec une URL qui fonctionne (avec décorateur)
    print(f"\n📋 Test URL avec décorateur qui fonctionne:")
    client = Client()
    client.force_login(user)
    
    try:
        # Tester classement_classe qui a le même décorateur
        response = client.get('/notes/classement/8/T1/')  # ClasseEleve 8
        print(f"   URL classement: Status {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Le décorateur fonctionne pour ClasseEleve")
        elif response.status_code == 404:
            print(f"❌ Même problème avec ClasseEleve")
        else:
            print(f"⚠️  Status inattendu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur test classement: {e}")

def proposer_solutions():
    """Proposer des solutions"""
    print(f"\n💡 SOLUTIONS POSSIBLES")
    print("=" * 25)
    
    print("🔧 Solution 1: Assigner une école à l'admin")
    print("   - Modifier le profil admin pour lui assigner l'école")
    print("   - Avantage: Simple")
    print("   - Inconvénient: Admin limité à une école")
    
    print(f"\n🔧 Solution 2: Modifier le décorateur")
    print("   - Permettre aux superusers d'accéder sans filtrage")
    print("   - Avantage: Admin peut tout voir")
    print("   - Inconvénient: Modification du système de sécurité")
    
    print(f"\n🔧 Solution 3: Supprimer le décorateur")
    print("   - Enlever @require_school_object de la fonction")
    print("   - Ajouter un filtrage manuel dans la fonction")
    print("   - Avantage: Contrôle total")
    print("   - Inconvénient: Code spécifique")

def appliquer_solution_1():
    """Appliquer la solution 1: Assigner l'école à l'admin"""
    print(f"\n🔧 APPLICATION SOLUTION 1")
    print("=" * 30)
    
    try:
        user = User.objects.filter(is_superuser=True).first()
        user_profil = getattr(user, 'profil', None)
        
        if user_profil and not user_profil.ecole:
            # Trouver l'école de la classe
            classe = ClasseNote.objects.get(pk=59)
            ecole = classe.ecole
            
            print(f"📋 Assignation école à l'admin:")
            print(f"   - Utilisateur: {user.username}")
            print(f"   - École à assigner: {ecole.nom}")
            
            # Assigner l'école
            user_profil.ecole = ecole
            user_profil.save()
            
            print(f"✅ École assignée avec succès")
            return True
        else:
            print(f"⚠️  Utilisateur a déjà une école ou pas de profil")
            return False
            
    except Exception as e:
        print(f"❌ Erreur assignation: {e}")
        return False

if __name__ == "__main__":
    try:
        tester_decorateur_school()
        proposer_solutions()
        
        # Demander si on applique la solution
        print(f"\n🎯 RECOMMANDATION")
        print("=" * 20)
        print("Appliquer la Solution 1: Assigner l'école à l'admin")
        
        success = appliquer_solution_1()
        
        if success:
            print(f"\n✅ Solution appliquée - Retester l'URL")
            print("URL: http://127.0.0.1:8000/notes/bulletins/classe/pdf/?classe_id=59&periode=TRIMESTRE_1&system_type=trimestre")
        else:
            print(f"\n⚠️  Solution non appliquée - Utiliser les alternatives")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
