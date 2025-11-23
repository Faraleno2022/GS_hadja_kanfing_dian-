#!/usr/bin/env python
"""
Tester spécifiquement le get_object_or_404 qui cause la 404
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from notes.models import ClasseNote
from utilisateurs.models import Profil

def tester_get_object_or_404():
    """Tester le get_object_or_404 qui cause l'erreur"""
    print("🔍 TEST GET_OBJECT_OR_404")
    print("=" * 30)
    
    classe_id = 59
    
    # 1. Test direct sans filtrage
    print(f"📋 Test 1: get_object_or_404 direct")
    try:
        classe = get_object_or_404(ClasseNote, pk=classe_id)
        print(f"✅ ClasseNote trouvée: {classe.nom}")
        print(f"   - ID: {classe.id}")
        print(f"   - École: {classe.ecole}")
    except Exception as e:
        print(f"❌ Erreur get_object_or_404: {e}")
        return False
    
    # 2. Vérifier l'utilisateur admin et son profil
    print(f"\n📋 Test 2: Vérification utilisateur admin")
    try:
        user = User.objects.filter(is_superuser=True).first()
        print(f"✅ Utilisateur admin: {user.username}")
        
        # Vérifier le profil
        user_profil = getattr(user, 'profil', None)
        if user_profil:
            print(f"✅ Profil trouvé: {user_profil}")
            print(f"   - École: {user_profil.ecole}")
        else:
            print(f"⚠️  Pas de profil pour l'utilisateur admin")
            
    except Exception as e:
        print(f"❌ Erreur utilisateur: {e}")
    
    # 3. Vérifier si la classe appartient à l'école de l'utilisateur
    print(f"\n📋 Test 3: Vérification école")
    try:
        user = User.objects.filter(is_superuser=True).first()
        user_profil = getattr(user, 'profil', None)
        ecole = user_profil.ecole if user_profil else None
        
        classe = ClasseNote.objects.get(pk=classe_id)
        
        print(f"École utilisateur: {ecole}")
        print(f"École classe: {classe.ecole}")
        
        if ecole and classe.ecole != ecole:
            print(f"❌ PROBLÈME: La classe n'appartient pas à l'école de l'utilisateur !")
            print(f"   Solution: Filtrer par école ou utiliser un admin sans école")
            return False
        else:
            print(f"✅ École compatible")
            
    except Exception as e:
        print(f"❌ Erreur vérification école: {e}")
    
    # 4. Test avec filtrage par école (comme dans la vraie fonction)
    print(f"\n📋 Test 4: Test avec filtrage école")
    try:
        user = User.objects.filter(is_superuser=True).first()
        user_profil = getattr(user, 'profil', None)
        ecole = user_profil.ecole if user_profil else None
        
        if ecole:
            # Filtrer par école comme dans la vraie fonction
            classe = get_object_or_404(ClasseNote, pk=classe_id, ecole=ecole)
            print(f"✅ Classe trouvée avec filtrage école: {classe.nom}")
        else:
            # Pas d'école, pas de filtrage
            classe = get_object_or_404(ClasseNote, pk=classe_id)
            print(f"✅ Classe trouvée sans filtrage école: {classe.nom}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur avec filtrage école: {e}")
        print(f"   Cela explique la 404 !")
        return False

def proposer_correction():
    """Proposer une correction"""
    print(f"\n💡 CORRECTION PROPOSÉE")
    print("=" * 25)
    
    print("🔧 Le problème vient probablement du filtrage par école.")
    print("   La fonction bulletins_dynamiques_classe_pdf filtre")
    print("   implicitement par l'école de l'utilisateur.")
    
    print(f"\n📋 Solutions possibles:")
    print("1. Modifier l'utilisateur admin pour qu'il n'ait pas d'école")
    print("2. Assigner la classe à l'école de l'utilisateur")
    print("3. Modifier la fonction pour ne pas filtrer par école")
    
    print(f"\n🔧 Correction immédiate:")
    print("Modifier la ligne get_object_or_404 pour ne pas filtrer par école")
    print("si l'utilisateur est admin")

def appliquer_correction():
    """Appliquer la correction"""
    print(f"\n🔧 APPLICATION DE LA CORRECTION")
    print("=" * 35)
    
    print("La correction consiste à modifier la fonction")
    print("bulletins_dynamiques_classe_pdf pour ne pas filtrer")
    print("par école si l'utilisateur est superuser")
    
    return True

if __name__ == "__main__":
    try:
        success = tester_get_object_or_404()
        
        proposer_correction()
        
        if not success:
            appliquer_correction()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        
        if success:
            print("✅ get_object_or_404 fonctionne")
            print("❓ Le problème vient d'ailleurs")
        else:
            print("❌ get_object_or_404 échoue à cause du filtrage école")
            print("🔧 Correction nécessaire dans la fonction")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
