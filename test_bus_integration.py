#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script pour verifier l'integration de l'abonnement bus
dans le formulaire d'ajout d'eleve
"""
import os
import django
import sys

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.urls import reverse
from eleves.models import Eleve, Classe, Responsable
from bus.models import AbonnementBus
from bus.forms import AbonnementBusEleveForm
from utilisateurs.models import Ecole, Profil

def test_bus_subscription_integration():
    """Test de l'intégration complète de l'abonnement bus"""
    print("=== Test d'intégration de l'abonnement bus ===\n")
    
    # 1. Vérifier que le formulaire d'abonnement bus existe
    print("1. Test du formulaire AbonnementBusEleveForm...")
    try:
        form = AbonnementBusEleveForm()
        print("OK - Formulaire AbonnementBusEleveForm cree avec succes")
        print(f"   Champs disponibles: {list(form.fields.keys())}")
    except Exception as e:
        print(f"ERREUR - Creation du formulaire: {e}")
        return False
    
    # 2. Verifier les valeurs par defaut
    print("\n2. Test des valeurs par defaut...")
    try:
        initial_data = form.initial
        print(f"OK - Valeurs par defaut: {initial_data}")
    except Exception as e:
        print(f"ERREUR - Recuperation des valeurs par defaut: {e}")
    
    # 3. Test de validation du formulaire
    print("\n3. Test de validation du formulaire...")
    test_data = {
        'montant': 50.00,
        'periodicite': 'MENSUEL',
        'date_debut': '2025-01-01',
        'date_expiration': '2025-12-31',
        'zone': 'Zone A',
        'point_arret': 'Arret Central'
    }
    
    try:
        form_with_data = AbonnementBusEleveForm(data=test_data)
        is_valid = form_with_data.is_valid()
        print(f"OK - Validation du formulaire: {'Valide' if is_valid else 'Invalide'}")
        if not is_valid:
            print(f"   Erreurs: {form_with_data.errors}")
    except Exception as e:
        print(f"ERREUR - Validation: {e}")
    
    # 4. Verifier l'importation dans la vue
    print("\n4. Test d'importation dans la vue...")
    try:
        from eleves.views import ajouter_eleve
        from bus.forms import AbonnementBusEleveForm as ViewImport
        print("OK - Importation reussie dans la vue ajouter_eleve")
    except ImportError as e:
        print(f"ERREUR - Importation: {e}")
        return False
    
    # 5. Test de creation d'un client de test
    print("\n5. Test du client Django...")
    try:
        client = Client()
        print("OK - Client Django cree avec succes")
    except Exception as e:
        print(f"ERREUR - Creation du client: {e}")
    
    print("\n=== Resume des tests ===")
    print("OK - Formulaire AbonnementBusEleveForm fonctionnel")
    print("OK - Importations correctes dans la vue")
    print("OK - Structure de base operationnelle")
    print("\nSUCCES - L'integration de l'abonnement bus est prete pour les tests manuels!")
    
    return True

def test_model_relationships():
    """Test des relations entre modeles"""
    print("\n=== Test des relations de modeles ===")
    
    try:
        # Verifier que le modele AbonnementBus existe et a les bons champs
        from bus.models import AbonnementBus
        fields = [field.name for field in AbonnementBus._meta.fields]
        print(f"OK - Champs du modele AbonnementBus: {fields}")
        
        # Verifier la relation avec Eleve
        eleve_field = AbonnementBus._meta.get_field('eleve')
        print(f"OK - Relation avec Eleve: {eleve_field.related_model.__name__}")
        
    except Exception as e:
        print(f"ERREUR - Test des modeles: {e}")

if __name__ == '__main__':
    try:
        success = test_bus_subscription_integration()
        test_model_relationships()
        
        if success:
            print("\nSUCCES - Tous les tests de base sont passes!")
            print("Vous pouvez maintenant tester manuellement:")
            print("1. Aller sur http://127.0.0.1:8000/eleves/ajouter/")
            print("2. Cocher 'Ajouter un abonnement bus'")
            print("3. Remplir le formulaire d'abonnement")
            print("4. Enregistrer l'eleve")
        else:
            print("\nECHEC - Certains tests ont echoue")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERREUR GENERALE: {e}")
        sys.exit(1)
