#!/usr/bin/env python
"""
Tester la requête exacte qui cause l'erreur 404
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from notes.models import ClasseNote

def tester_get_object_or_404():
    """Tester exactement get_object_or_404(ClasseNote, pk=classe_id)"""
    print("🧪 TEST GET_OBJECT_OR_404 EXACT")
    print("=" * 35)
    
    # Paramètres exacts de la requête
    classe_id_str = '59'
    
    # Test 1: Conversion
    print(f"📋 Test 1: Conversion")
    try:
        classe_id = int(classe_id_str)
        print(f"✅ Conversion: '{classe_id_str}' -> {classe_id}")
    except (ValueError, TypeError) as e:
        print(f"❌ Erreur conversion: {e}")
        return
    
    # Test 2: get_object_or_404 exact
    print(f"\n📋 Test 2: get_object_or_404(ClasseNote, pk={classe_id})")
    try:
        classe_selectionnee = get_object_or_404(ClasseNote, pk=classe_id)
        print(f"✅ ClasseNote trouvée: {classe_selectionnee.nom}")
        print(f"   - ID: {classe_selectionnee.id}")
        print(f"   - Type ID: {type(classe_selectionnee.id)}")
        print(f"   - École: {classe_selectionnee.ecole}")
        print(f"   - Actif: {classe_selectionnee.actif}")
    except Exception as e:
        print(f"❌ Erreur get_object_or_404: {e}")
        print(f"   - Type erreur: {type(e)}")
        
        # Test alternatif avec .get()
        print(f"\n📋 Test alternatif avec .get()")
        try:
            classe_alt = ClasseNote.objects.get(pk=classe_id)
            print(f"✅ .get() fonctionne: {classe_alt.nom}")
        except ClasseNote.DoesNotExist:
            print(f"❌ .get() échoue aussi: ClasseNote.DoesNotExist")
        except Exception as e2:
            print(f"❌ .get() erreur: {e2}")
        
        return
    
    # Test 3: Vérifier les matières
    print(f"\n📋 Test 3: Matières")
    from notes.models import MatiereNote
    matieres = MatiereNote.objects.filter(classe=classe_selectionnee, actif=True).order_by('nom')
    print(f"✅ Matières trouvées: {matieres.count()}")
    
    # Test 4: Simuler la requête HTTP
    print(f"\n📋 Test 4: Simulation requête HTTP")
    factory = RequestFactory()
    request = factory.get('/notes/bulletins/classe/pdf/', {
        'classe_id': '59',
        'periode': 'OCTOBRE',
        'system_type': 'mensuel'
    })
    
    # Ajouter un utilisateur
    try:
        user = User.objects.filter(is_superuser=True).first()
        if user:
            request.user = user
            print(f"✅ Utilisateur: {user.username}")
        else:
            print(f"⚠️  Aucun superuser trouvé")
    except Exception as e:
        print(f"⚠️  Erreur utilisateur: {e}")
    
    # Test des paramètres de la requête
    classe_id_from_request = request.GET.get('classe_id')
    periode_from_request = request.GET.get('periode', '')
    system_type_from_request = request.GET.get('system_type', 'trimestre')
    
    print(f"✅ Paramètres requête:")
    print(f"   - classe_id: '{classe_id_from_request}' (type: {type(classe_id_from_request)})")
    print(f"   - periode: '{periode_from_request}'")
    print(f"   - system_type: '{system_type_from_request}'")
    
    # Test conversion depuis la requête
    try:
        classe_id_converted = int(classe_id_from_request)
        print(f"✅ Conversion depuis requête: {classe_id_converted}")
        
        # Test get_object_or_404 avec la valeur convertie
        classe_from_request = get_object_or_404(ClasseNote, pk=classe_id_converted)
        print(f"✅ get_object_or_404 depuis requête: {classe_from_request.nom}")
        
    except Exception as e:
        print(f"❌ Erreur depuis requête: {e}")

def verifier_base_donnees():
    """Vérifier l'état de la base de données"""
    print(f"\n🗄️  VÉRIFICATION BASE DE DONNÉES")
    print("=" * 35)
    
    # Compter les classes
    total_classes = ClasseNote.objects.count()
    classes_actives = ClasseNote.objects.filter(actif=True).count()
    
    print(f"📊 Statistiques:")
    print(f"   - Total classes: {total_classes}")
    print(f"   - Classes actives: {classes_actives}")
    
    # Lister les classes autour de l'ID 59
    classes_autour = ClasseNote.objects.filter(id__in=[57, 58, 59, 60, 61]).order_by('id')
    print(f"\n📋 Classes autour de l'ID 59:")
    for classe in classes_autour:
        print(f"   - ID {classe.id}: {classe.nom} ({'Actif' if classe.actif else 'Inactif'})")
    
    # Vérifier spécifiquement l'ID 59
    print(f"\n🔍 Vérification spécifique ID 59:")
    try:
        classe_59 = ClasseNote.objects.get(id=59)
        print(f"✅ Existe: {classe_59.nom}")
        print(f"   - pk: {classe_59.pk}")
        print(f"   - id: {classe_59.id}")
        print(f"   - Égalité pk==id: {classe_59.pk == classe_59.id}")
    except ClasseNote.DoesNotExist:
        print(f"❌ N'existe pas")

if __name__ == "__main__":
    try:
        tester_get_object_or_404()
        verifier_base_donnees()
        
        print(f"\n🎯 CONCLUSION")
        print("=" * 15)
        print("Si tous les tests passent ici mais l'erreur 404 persiste dans le navigateur:")
        print("1. Problème de cache Django")
        print("2. Problème de session utilisateur")
        print("3. Problème de permissions")
        print("4. Différence entre environnement script et serveur web")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
