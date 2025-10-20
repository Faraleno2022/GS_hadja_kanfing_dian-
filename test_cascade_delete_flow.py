#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test complet du système de suppression en cascade
Vérifie que les élèves avec paiements peuvent être supprimés via cascade delete
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Responsable, Classe
from paiements.models import Paiement, TypePaiement
from utilisateurs.models import Profil, Ecole

User = get_user_model()

def test_cascade_delete_flow():
    """Test complet du flux de suppression en cascade"""
    print("🧪 Test du système de suppression en cascade")
    print("=" * 50)
    
    # 1. Créer les données de test
    print("1. Création des données de test...")
    
    # Créer une école
    ecole = Ecole.objects.create(
        nom="École Test Cascade",
        adresse="Test Address",
        telephone="123456789"
    )
    
    # Créer un utilisateur admin
    admin_user = User.objects.create_user(
        username='admin_test',
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
        nom="Test Classe",
        niveau="PRIMAIRE",
        ecole=ecole
    )
    
    # Créer un responsable
    responsable = Responsable.objects.create(
        nom="Test Responsable",
        prenom="Responsable",
        relation="PERE",
        telephone="+224987654321",
        adresse="Test Address"
    )
    
    # Créer un élève
    eleve = Eleve.objects.create(
        nom="Test Élève",
        prenom="Cascade",
        matricule="TEST001",
        classe=classe,
        responsable=responsable,
        ecole=ecole
    )
    
    # Créer un type de paiement
    type_paiement = TypePaiement.objects.create(
        nom="Scolarité Test",
        ecole=ecole
    )
    
    # Créer un paiement pour l'élève
    paiement = Paiement.objects.create(
        eleve=eleve,
        type_paiement=type_paiement,
        montant=500000,
        statut='VALIDE'
    )
    
    print(f"✅ Élève créé: {eleve} (ID: {eleve.id})")
    print(f"✅ Paiement créé: {paiement.montant} GNF (ID: {paiement.id})")
    
    # 2. Tester la suppression normale (doit échouer)
    print("\n2. Test de suppression normale (doit échouer)...")
    
    client = Client()
    client.force_login(admin_user)
    
    url_delete = f"/administration/model/eleves/eleve/{eleve.id}/delete/"
    response = client.post(url_delete, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    
    if response.status_code == 200:
        data = json.loads(response.content)
        if not data.get('success') and data.get('show_cascade_option'):
            print("✅ Suppression normale bloquée comme attendu")
            print(f"✅ Option cascade proposée: {data.get('cascade_message')}")
        else:
            print("❌ Erreur: La suppression normale n'a pas été bloquée")
            return False
    else:
        print(f"❌ Erreur HTTP: {response.status_code}")
        return False
    
    # 3. Tester la suppression en cascade
    print("\n3. Test de suppression en cascade...")
    
    url_cascade = f"/administration/model/eleves/eleve/{eleve.id}/cascade-delete/"
    response = client.post(url_cascade, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    
    if response.status_code == 200:
        data = json.loads(response.content)
        if data.get('success'):
            print("✅ Suppression en cascade réussie")
            print(f"✅ Message: {data.get('message')}")
            
            # Vérifier que l'élève et le paiement ont été supprimés
            if not Eleve.objects.filter(id=eleve.id).exists():
                print("✅ Élève supprimé de la base de données")
            else:
                print("❌ Erreur: Élève toujours présent")
                return False
                
            if not Paiement.objects.filter(id=paiement.id).exists():
                print("✅ Paiement supprimé de la base de données")
            else:
                print("❌ Erreur: Paiement toujours présent")
                return False
                
        else:
            print(f"❌ Erreur cascade: {data.get('error')}")
            return False
    else:
        print(f"❌ Erreur HTTP cascade: {response.status_code}")
        return False
    
    print("\n🎉 Test de suppression en cascade RÉUSSI!")
    return True

def test_bulk_cascade_delete():
    """Test de suppression en cascade en masse"""
    print("\n🧪 Test de suppression en cascade en masse")
    print("=" * 50)
    
    # Créer les données de test
    ecole = Ecole.objects.create(
        nom="École Test Bulk",
        adresse="Test Address",
        telephone="123456789"
    )
    
    admin_user = User.objects.create_user(
        username='admin_bulk',
        password='testpass123',
        is_superuser=True,
        is_staff=True
    )
    
    profil_admin = Profil.objects.create(
        user=admin_user,
        ecole=ecole,
        role='ADMIN'
    )
    
    classe = Classe.objects.create(
        nom="Test Classe Bulk",
        niveau="PRIMAIRE",
        ecole=ecole
    )
    
    responsable = Responsable.objects.create(
        nom="Test Responsable Bulk",
        prenom="Responsable",
        relation="PERE",
        telephone="+224987654321",
        adresse="Test Address"
    )
    
    type_paiement = TypePaiement.objects.create(
        nom="Scolarité Bulk",
        ecole=ecole
    )
    
    # Créer plusieurs élèves avec paiements
    eleves_ids = []
    for i in range(3):
        eleve = Eleve.objects.create(
            nom=f"Test Élève {i+1}",
            prenom="Bulk",
            matricule=f"BULK00{i+1}",
            classe=classe,
            responsable=responsable,
            ecole=ecole
        )
        
        Paiement.objects.create(
            eleve=eleve,
            type_paiement=type_paiement,
            montant=300000 + (i * 100000),
            statut='VALIDE'
        )
        
        eleves_ids.append(eleve.id)
    
    print(f"✅ {len(eleves_ids)} élèves créés avec paiements")
    
    # Test suppression bulk normale (doit échouer)
    client = Client()
    client.force_login(admin_user)
    
    url_bulk_delete = "/administration/model/eleves/eleve/bulk-delete/"
    data = {'ids[]': eleves_ids}
    response = client.post(url_bulk_delete, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    
    if response.status_code == 200:
        data = json.loads(response.content)
        if not data.get('success') and data.get('show_cascade_option'):
            print("✅ Suppression bulk normale bloquée comme attendu")
        else:
            print("❌ Erreur: La suppression bulk normale n'a pas été bloquée")
            return False
    
    # Test suppression bulk cascade
    url_bulk_cascade = "/administration/model/eleves/eleve/bulk-cascade-delete/"
    data = {'ids[]': eleves_ids}
    response = client.post(url_bulk_cascade, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    
    if response.status_code == 200:
        data = json.loads(response.content)
        if data.get('success'):
            print("✅ Suppression bulk cascade réussie")
            
            # Vérifier que tous les élèves ont été supprimés
            remaining = Eleve.objects.filter(id__in=eleves_ids).count()
            if remaining == 0:
                print("✅ Tous les élèves supprimés")
            else:
                print(f"❌ Erreur: {remaining} élèves toujours présents")
                return False
                
        else:
            print(f"❌ Erreur bulk cascade: {data.get('error')}")
            return False
    
    print("🎉 Test de suppression bulk cascade RÉUSSI!")
    return True

def cleanup_test_data():
    """Nettoyer les données de test"""
    print("\n🧹 Nettoyage des données de test...")
    
    # Supprimer toutes les données de test
    Paiement.objects.filter(eleve__ecole__nom__contains="Test").delete()
    Eleve.objects.filter(ecole__nom__contains="Test").delete()
    Classe.objects.filter(ecole__nom__contains="Test").delete()
    Responsable.objects.filter(nom__contains="Test").delete()
    TypePaiement.objects.filter(ecole__nom__contains="Test").delete()
    Profil.objects.filter(ecole__nom__contains="Test").delete()
    User.objects.filter(username__contains="test").delete()
    Ecole.objects.filter(nom__contains="Test").delete()
    
    print("✅ Données de test nettoyées")

if __name__ == "__main__":
    try:
        # Exécuter les tests
        success1 = test_cascade_delete_flow()
        success2 = test_bulk_cascade_delete()
        
        if success1 and success2:
            print("\n🎉 TOUS LES TESTS RÉUSSIS!")
            print("✅ Le système de suppression en cascade fonctionne parfaitement")
        else:
            print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
            
    except Exception as e:
        print(f"\n💥 ERREUR LORS DES TESTS: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Nettoyer les données de test
        cleanup_test_data()
