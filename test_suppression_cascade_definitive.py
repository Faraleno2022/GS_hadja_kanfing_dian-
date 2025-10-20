#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de la suppression définitive avec cascade
Teste le flux complet de suppression d'un élève avec ses paiements
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model
import json
import uuid

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Responsable, Classe
from paiements.models import Paiement, TypePaiement
from utilisateurs.models import Profil, Ecole

User = get_user_model()

def create_test_data():
    """Créer des données de test pour la suppression cascade"""
    print("📋 Création des données de test...")
    
    # Créer une école de test
    ecole = Ecole.objects.create(
        nom="École Test Cascade",
        adresse="Test Address",
        telephone="+224123456789",
        directeur="Directeur Test"
    )
    
    # Créer un utilisateur admin
    admin_username = f"admin_cascade_{uuid.uuid4().hex[:8]}"
    admin_user = User.objects.create_user(
        username=admin_username,
        password='testpass123',
        is_superuser=True,
        is_staff=True
    )
    
    profil_admin = Profil.objects.create(
        user=admin_user,
        ecole=ecole,
        role='ADMIN'
    )
    
    # Créer une classe
    classe = Classe.objects.create(
        nom="Test Classe Cascade",
        niveau="PRIMAIRE_1",
        ecole=ecole,
        annee_scolaire="2024-2025"
    )
    
    # Créer un responsable
    responsable = Responsable.objects.create(
        nom="Test Responsable",
        prenom="Cascade",
        relation="PERE",
        telephone="+224987654321",
        adresse="Test Address"
    )
    
    # Créer un élève
    from datetime import date
    eleve = Eleve.objects.create(
        nom="Test Élève",
        prenom="Cascade",
        matricule=f"CASCADE{uuid.uuid4().hex[:4].upper()}",
        sexe='M',
        date_naissance=date(2010, 1, 1),
        lieu_naissance="Conakry",
        classe=classe,
        date_inscription=date.today(),
        responsable_principal=responsable
    )
    
    # Créer un type de paiement
    type_paiement = TypePaiement.objects.create(
        nom=f"Scolarité Test Cascade {uuid.uuid4().hex[:4]}"
    )
    
    # Créer un mode de paiement
    from paiements.models import ModePaiement
    mode_paiement = ModePaiement.objects.create(
        nom=f"Espèces Test {uuid.uuid4().hex[:4]}"
    )
    
    # Créer des paiements pour l'élève
    from datetime import date
    paiements = []
    for i in range(2):
        paiement = Paiement.objects.create(
            eleve=eleve,
            type_paiement=type_paiement,
            mode_paiement=mode_paiement,
            montant=500000 + (i * 100000),
            statut='VALIDE',
            numero_recu=f"TEST{uuid.uuid4().hex[:8].upper()}",
            date_paiement=date.today()
        )
        paiements.append(paiement)
    
    print(f"✅ Élève créé: {eleve} (ID: {eleve.id})")
    print(f"✅ {len(paiements)} paiements créés")
    
    return {
        'eleve': eleve,
        'paiements': paiements,
        'admin_user': admin_user,
        'ecole': ecole,
        'classe': classe,
        'responsable': responsable,
        'type_paiement': type_paiement
    }

def test_suppression_normale_bloquee(test_data):
    """Test que la suppression normale est bloquée"""
    print("\n🚫 Test de blocage de la suppression normale...")
    
    eleve = test_data['eleve']
    admin_user = test_data['admin_user']
    
    client = Client()
    client.force_login(admin_user)
    
    # Obtenir le token CSRF
    detail_url = f"/administration/model/eleves/eleve/{eleve.id}/"
    detail_response = client.get(detail_url)
    
    if detail_response.status_code != 200:
        print(f"❌ Impossible d'accéder au détail de l'élève: {detail_response.status_code}")
        return False
    
    # Extraire le token CSRF
    content = detail_response.content.decode('utf-8')
    import re
    csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\'] value=["\']([^"\']+)["\']', content)
    csrf_token = csrf_match.group(1) if csrf_match else None
    
    if not csrf_token:
        print("❌ Token CSRF non trouvé")
        return False
    
    # Tenter la suppression normale
    delete_url = f"/administration/model/eleves/eleve/{eleve.id}/delete/"
    response = client.post(
        delete_url,
        data={'csrfmiddlewaretoken': csrf_token},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            if not data.get('success') and data.get('show_cascade_option'):
                print("✅ Suppression normale bloquée comme attendu")
                print(f"✅ Message: {data.get('cascade_message', 'N/A')}")
                return True, csrf_token
            else:
                print(f"❌ Réponse inattendue: {data}")
                return False, None
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON: {e}")
            return False, None
    else:
        print(f"❌ Erreur HTTP: {response.status_code}")
        return False, None

def test_suppression_cascade(test_data, csrf_token):
    """Test de la suppression cascade"""
    print("\n🗑️ Test de la suppression cascade...")
    
    eleve = test_data['eleve']
    admin_user = test_data['admin_user']
    paiements_ids = [p.id for p in test_data['paiements']]
    
    client = Client()
    client.force_login(admin_user)
    
    # Vérifier que l'élève et les paiements existent avant suppression
    print(f"📊 Avant suppression:")
    print(f"   - Élève existe: {Eleve.objects.filter(id=eleve.id).exists()}")
    print(f"   - Paiements existent: {Paiement.objects.filter(id__in=paiements_ids).count()}")
    
    # Exécuter la suppression cascade
    cascade_url = f"/administration/model/eleves/eleve/{eleve.id}/cascade-delete/"
    response = client.post(
        cascade_url,
        data={'csrfmiddlewaretoken': csrf_token},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    if response.status_code == 200:
        try:
            data = json.loads(response.content)
            if data.get('success'):
                print("✅ Suppression cascade réussie")
                print(f"✅ Message: {data.get('message', 'N/A')}")
                
                # Vérifier que l'élève et les paiements ont été supprimés
                print(f"📊 Après suppression:")
                eleve_exists = Eleve.objects.filter(id=eleve.id).exists()
                paiements_count = Paiement.objects.filter(id__in=paiements_ids).count()
                
                print(f"   - Élève existe: {eleve_exists}")
                print(f"   - Paiements restants: {paiements_count}")
                
                if not eleve_exists and paiements_count == 0:
                    print("✅ Suppression cascade complète réussie")
                    return True
                else:
                    print("❌ Suppression cascade incomplète")
                    return False
            else:
                print(f"❌ Erreur cascade: {data.get('error', 'N/A')}")
                return False
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON cascade: {e}")
            return False
    else:
        print(f"❌ Erreur HTTP cascade: {response.status_code}")
        print(f"Contenu: {response.content[:200]}...")
        return False

def cleanup_test_data(test_data):
    """Nettoyer les données de test"""
    print("\n🧹 Nettoyage des données de test...")
    
    try:
        # Supprimer dans l'ordre pour éviter les contraintes FK
        if 'admin_user' in test_data:
            test_data['admin_user'].delete()
        if 'mode_paiement' in test_data:
            test_data['mode_paiement'].delete()
        if 'type_paiement' in test_data:
            test_data['type_paiement'].delete()
        if 'classe' in test_data:
            test_data['classe'].delete()
        if 'responsable' in test_data:
            test_data['responsable'].delete()
        if 'ecole' in test_data:
            test_data['ecole'].delete()
        
        print("✅ Données de test nettoyées")
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage: {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Test de suppression définitive avec cascade")
    print("=" * 60)
    
    test_data = None
    try:
        # 1. Créer les données de test
        test_data = create_test_data()
        
        # 2. Tester le blocage de la suppression normale
        blocked, csrf_token = test_suppression_normale_bloquee(test_data)
        if not blocked:
            print("❌ Test de blocage échoué")
            return False
        
        # 3. Tester la suppression cascade
        cascade_success = test_suppression_cascade(test_data, csrf_token)
        if not cascade_success:
            print("❌ Test de suppression cascade échoué")
            return False
        
        print("\n🎉 TOUS LES TESTS RÉUSSIS!")
        print("✅ Système de suppression cascade opérationnel")
        return True
        
    except Exception as e:
        print(f"\n💥 ERREUR LORS DES TESTS: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Nettoyer les données de test
        if test_data:
            cleanup_test_data(test_data)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
