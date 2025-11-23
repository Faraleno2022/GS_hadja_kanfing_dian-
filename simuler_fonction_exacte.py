#!/usr/bin/env python
"""
Simuler exactement la fonction bulletins_dynamiques_classe_pdf
pour identifier où se produit la 404
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.test import RequestFactory
from notes.models import ClasseNote, MatiereNote
from eleves.models import Classe as ClasseEleve

def simuler_fonction_bulletins_classe_pdf():
    """Simuler exactement la fonction bulletins_dynamiques_classe_pdf"""
    print("🔍 SIMULATION FONCTION BULLETINS_DYNAMIQUES_CLASSE_PDF")
    print("=" * 60)
    
    # Créer une requête factice
    factory = RequestFactory()
    request = factory.get('/notes/bulletins/classe/pdf/', {
        'classe_id': '59',
        'periode': 'TRIMESTRE_1',
        'system_type': 'trimestre'
    })
    
    # Ajouter un utilisateur
    try:
        user = User.objects.filter(is_superuser=True).first()
        request.user = user
        print(f"✅ Utilisateur: {user.username}")
    except Exception as e:
        print(f"❌ Erreur utilisateur: {e}")
        return False
    
    # Simuler exactement le code de la fonction
    print(f"\n📋 Étape 1: Récupération des paramètres")
    classe_id = request.GET.get('classe_id')
    periode = request.GET.get('periode', '')
    system_type = request.GET.get('system_type', 'trimestre')
    
    print(f"   - classe_id: {classe_id}")
    print(f"   - periode: {periode}")
    print(f"   - system_type: {system_type}")
    
    # Validation des paramètres
    print(f"\n📋 Étape 2: Validation des paramètres")
    if not classe_id or not periode:
        print(f"❌ Paramètres manquants")
        return False
    print(f"✅ Paramètres présents")
    
    # Convertir classe_id en entier
    print(f"\n📋 Étape 3: Conversion classe_id")
    try:
        classe_id = int(classe_id)
        print(f"✅ classe_id converti: {classe_id}")
    except (ValueError, TypeError):
        print(f"❌ Conversion échouée: {classe_id}")
        return False
    
    # Récupérer les informations de l'école et de la classe
    print(f"\n📋 Étape 4: Récupération profil utilisateur")
    user_profil = getattr(request.user, 'profil', None)
    ecole = user_profil.ecole if user_profil else None
    print(f"   - Profil: {user_profil}")
    print(f"   - École: {ecole}")
    
    # POINT CRITIQUE: get_object_or_404
    print(f"\n📋 Étape 5: get_object_or_404 (POINT CRITIQUE)")
    try:
        classe_selectionnee = get_object_or_404(ClasseNote, pk=classe_id)
        print(f"✅ ClasseNote trouvée: {classe_selectionnee.nom}")
    except Exception as e:
        print(f"❌ ERREUR 404 ICI: {e}")
        print(f"   Type d'erreur: {type(e)}")
        return False
    
    # Récupérer les matières
    print(f"\n📋 Étape 6: Récupération matières")
    try:
        matieres = MatiereNote.objects.filter(classe=classe_selectionnee, actif=True).order_by('nom')
        print(f"✅ Matières trouvées: {matieres.count()}")
    except Exception as e:
        print(f"❌ Erreur matières: {e}")
    
    # Mapping ClasseEleve
    print(f"\n📋 Étape 7: Mapping ClasseEleve")
    mapping_classes = {
        61: 56,  # ClasseNote '12ème Année' -> ClasseEleve '12ÈME ANNÉE'
        59: 8,   # ClasseNote '11ème Série littéraire' -> ClasseEleve '11ème série littéraire'
    }
    
    if classe_selectionnee.id in mapping_classes:
        classe_eleve_id = mapping_classes[classe_selectionnee.id]
        print(f"✅ Mapping trouvé: {classe_selectionnee.id} → {classe_eleve_id}")
        
        try:
            classe_eleve = ClasseEleve.objects.filter(id=classe_eleve_id).first()
            if classe_eleve:
                print(f"✅ ClasseEleve trouvée: {classe_eleve.nom}")
            else:
                print(f"❌ ClasseEleve non trouvée")
                return False
        except Exception as e:
            print(f"❌ Erreur ClasseEleve: {e}")
            return False
    else:
        print(f"⚠️  Pas de mapping, recherche par nom")
        try:
            classe_eleve = ClasseEleve.objects.filter(
                nom=classe_selectionnee.nom,
                annee_scolaire=classe_selectionnee.annee_scolaire,
                ecole=classe_selectionnee.ecole
            ).first()
            
            if classe_eleve:
                print(f"✅ ClasseEleve trouvée par nom: {classe_eleve.nom}")
            else:
                print(f"❌ ClasseEleve non trouvée par nom")
                return False
        except Exception as e:
            print(f"❌ Erreur recherche ClasseEleve: {e}")
            return False
    
    print(f"\n✅ SIMULATION RÉUSSIE - Aucune erreur 404 détectée")
    return True

def tester_avec_filtrage_ecole():
    """Tester avec un filtrage par école comme les autres fonctions"""
    print(f"\n🔍 TEST AVEC FILTRAGE ÉCOLE")
    print("=" * 35)
    
    # Créer une requête factice
    factory = RequestFactory()
    request = factory.get('/notes/bulletins/classe/pdf/', {
        'classe_id': '59',
        'periode': 'TRIMESTRE_1',
        'system_type': 'trimestre'
    })
    
    # Ajouter un utilisateur
    user = User.objects.filter(is_superuser=True).first()
    request.user = user
    
    classe_id = 59
    
    # Test avec filtrage école (comme les autres fonctions)
    print(f"📋 Test avec filter_by_user_school:")
    try:
        from utilisateurs.utils import filter_by_user_school
        
        # Filtrer comme les autres fonctions
        classe_selectionnee = get_object_or_404(
            filter_by_user_school(ClasseNote.objects.all(), request.user, 'ecole'), 
            pk=classe_id
        )
        print(f"✅ Avec filtrage école: {classe_selectionnee.nom}")
        return True
        
    except Exception as e:
        print(f"❌ ERREUR avec filtrage école: {e}")
        print(f"   Cela explique la 404 !")
        return False

if __name__ == "__main__":
    try:
        # Test simulation exacte
        success1 = simuler_fonction_bulletins_classe_pdf()
        
        # Test avec filtrage école
        success2 = tester_avec_filtrage_ecole()
        
        print(f"\n🎯 RÉSUMÉ")
        print("=" * 15)
        
        if success1:
            print("✅ Simulation exacte: AUCUNE erreur 404")
            print("❓ Le problème vient d'ailleurs")
        else:
            print("❌ Simulation exacte: Erreur 404 reproduite")
        
        if success2:
            print("✅ Avec filtrage école: Fonctionne")
        else:
            print("❌ Avec filtrage école: Erreur 404")
            print("🔧 SOLUTION: Ajouter filter_by_user_school à la fonction")
        
        print(f"\n💡 CONCLUSION:")
        if success1 and not success2:
            print("La fonction devrait utiliser filter_by_user_school")
            print("comme toutes les autres fonctions du fichier")
        elif not success1:
            print("Il y a un problème plus profond dans la fonction")
        else:
            print("Le problème vient d'un autre endroit")
        
    except Exception as e:
        print(f"❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
