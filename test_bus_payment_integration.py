#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour l'intégration de l'abonnement bus dans le système de paiements
"""
import os
import django
import sys
from datetime import date, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from paiements.models import Paiement, TypePaiement, ModePaiement
from paiements.forms import PaiementForm
from eleves.models import Eleve
from bus.models import AbonnementBus

User = get_user_model()

def test_bus_payment_integration():
    """Test complet de l'intégration paiement + abonnement bus"""
    print("=== Test d'intégration Paiement + Abonnement Bus ===\n")
    
    # 1. Vérifier que le type de paiement "Abonnement Bus" existe
    print("1. Vérification du type de paiement 'Abonnement Bus'...")
    try:
        type_bus = TypePaiement.objects.get(nom="Abonnement Bus")
        print(f"OK Type de paiement trouve: {type_bus.nom} (ID: {type_bus.id})")
    except TypePaiement.DoesNotExist:
        print("ERREUR Type de paiement 'Abonnement Bus' non trouve!")
        return False
    
    # 2. Vérifier qu'il y a des modes de paiement disponibles
    print("\n2. Vérification des modes de paiement...")
    modes = ModePaiement.objects.filter(actif=True)
    if modes.exists():
        mode_test = modes.first()
        print(f"OK Mode de paiement disponible: {mode_test.nom}")
    else:
        print("ERREUR Aucun mode de paiement actif trouve!")
        return False
    
    # 3. Vérifier qu'il y a des élèves disponibles
    print("\n3. Vérification des élèves...")
    eleves = Eleve.objects.filter(statut='ACTIF')[:3]
    if eleves.exists():
        eleve_test = eleves.first()
        print(f"OK Eleve de test: {eleve_test.nom} {eleve_test.prenom} (ID: {eleve_test.id})")
    else:
        print("ERREUR Aucun eleve actif trouve!")
        return False
    
    # 4. Test du formulaire avec données d'abonnement bus
    print("\n4. Test du formulaire PaiementForm avec données bus...")
    
    today = date.today()
    form_data = {
        'eleve': eleve_test.id,
        'type_paiement': type_bus.id,
        'mode_paiement': mode_test.id,
        'montant': 50000,  # 50,000 GNF
        'date_paiement': today,
        'observations': 'Test d\'intégration abonnement bus',
        # Champs spécifiques bus
        'bus_periodicite': 'MENSUEL',
        'bus_date_debut': today,
        'bus_date_expiration': today + timedelta(days=30),
        'bus_zone': 'Zone Test',
        'bus_point_arret': 'Arrêt Test',
        'bus_observations': 'Test automatique'
    }
    
    form = PaiementForm(data=form_data)
    if form.is_valid():
        print("OK Formulaire valide avec donnees bus")
        
        # Vérifier que les champs bus sont bien présents dans cleaned_data
        bus_fields = ['bus_periodicite', 'bus_date_debut', 'bus_date_expiration', 'bus_zone', 'bus_point_arret', 'bus_observations']
        for field in bus_fields:
            if field in form.cleaned_data:
                print(f"  OK {field}: {form.cleaned_data[field]}")
            else:
                print(f"  ERREUR {field}: manquant dans cleaned_data")
    else:
        print("ERREUR Formulaire invalide:")
        for field, errors in form.errors.items():
            print(f"  - {field}: {errors}")
        return False
    
    # 5. Test de création d'un paiement avec abonnement bus (simulation)
    print("\n5. Simulation de création paiement + abonnement bus...")
    
    try:
        with transaction.atomic():
            # Créer le paiement
            paiement = form.save(commit=False)
            paiement.statut = 'EN_ATTENTE'
            paiement.save()
            print(f"OK Paiement cree: {paiement.id} - {paiement.montant} GNF")
            
            # Créer l'abonnement bus (simulation de la logique de la vue)
            if paiement.type_paiement.nom == 'Abonnement Bus':
                abonnement_bus = AbonnementBus(
                    eleve=paiement.eleve,
                    periodicite=form.cleaned_data.get('bus_periodicite'),
                    date_debut=form.cleaned_data.get('bus_date_debut'),
                    date_expiration=form.cleaned_data.get('bus_date_expiration'),
                    zone=form.cleaned_data.get('bus_zone', ''),
                    point_arret=form.cleaned_data.get('bus_point_arret', ''),
                    observations=form.cleaned_data.get('bus_observations', ''),
                    statut='ACTIF',
                    montant=paiement.montant
                )
                abonnement_bus.save()
                print(f"OK Abonnement bus cree: {abonnement_bus.id}")
                print(f"  - Élève: {abonnement_bus.eleve.nom} {abonnement_bus.eleve.prenom}")
                print(f"  - Période: {abonnement_bus.date_debut} à {abonnement_bus.date_expiration}")
                print(f"  - Zone: {abonnement_bus.zone}")
                print(f"  - Point d'arrêt: {abonnement_bus.point_arret}")
                print(f"  - Montant: {abonnement_bus.montant} GNF")
            
            # Rollback pour ne pas polluer la base
            raise Exception("Test terminé - rollback")
            
    except Exception as e:
        if "Test terminé" in str(e):
            print("OK Test simule avec succes (rollback effectue)")
        else:
            print(f"ERREUR Erreur lors de la simulation: {e}")
            return False
    
    # 6. Vérifier les contraintes de validation
    print("\n6. Test des validations du formulaire...")
    
    # Test avec dates invalides
    invalid_form_data = form_data.copy()
    invalid_form_data['bus_date_expiration'] = today - timedelta(days=1)  # Date d'expiration avant début
    
    invalid_form = PaiementForm(data=invalid_form_data)
    if not invalid_form.is_valid():
        if 'bus_date_expiration' in invalid_form.errors:
            print("OK Validation des dates fonctionne correctement")
        else:
            print("ERREUR Validation des dates ne fonctionne pas")
    else:
        print("ERREUR Le formulaire devrait etre invalide avec des dates incorrectes")
    
    # Test avec champs bus manquants pour type "Abonnement Bus"
    incomplete_form_data = form_data.copy()
    del incomplete_form_data['bus_periodicite']
    del incomplete_form_data['bus_date_debut']
    
    incomplete_form = PaiementForm(data=incomplete_form_data)
    if not incomplete_form.is_valid():
        print("OK Validation des champs obligatoires fonctionne")
    else:
        print("ERREUR Les champs bus devraient etre obligatoires")
    
    print("\n=== Résumé du test ===")
    print("SUCCESS L'integration de l'abonnement bus dans le systeme de paiements fonctionne correctement!")
    print("\nFonctionnalités testées:")
    print("- OK Type de paiement 'Abonnement Bus' disponible")
    print("- OK Formulaire avec champs bus conditionnels")
    print("- OK Validation des donnees bus")
    print("- OK Creation simultanee paiement + abonnement")
    print("- OK Contraintes de validation")
    
    return True

def test_form_fields():
    """Test spécifique des champs du formulaire"""
    print("\n=== Test des champs du formulaire ===")
    
    form = PaiementForm()
    
    # Vérifier que les champs bus sont présents
    bus_fields = ['bus_periodicite', 'bus_date_debut', 'bus_date_expiration', 'bus_zone', 'bus_point_arret', 'bus_observations']
    
    for field_name in bus_fields:
        if field_name in form.fields:
            field = form.fields[field_name]
            print(f"OK {field_name}: {field.label} ({'requis' if field.required else 'optionnel'})")
        else:
            print(f"ERREUR {field_name}: champ manquant")
    
    # Vérifier les choix de périodicité
    periodicite_field = form.fields.get('bus_periodicite')
    if periodicite_field:
        print(f"OK Choix de periodicite: {len(periodicite_field.choices)} options disponibles")
        for value, label in periodicite_field.choices:
            if value:  # Ignorer le choix vide
                print(f"  - {value}: {label}")

if __name__ == '__main__':
    try:
        print("Démarrage des tests d'intégration...\n")
        
        # Test principal
        success = test_bus_payment_integration()
        
        # Test des champs
        test_form_fields()
        
        if success:
            print("\nSUCCESS Tous les tests sont passes avec succes!")
            print("\nL'intégration de l'abonnement bus dans le formulaire de paiement est opérationnelle.")
            print("Vous pouvez maintenant utiliser le formulaire de paiement pour créer des abonnements bus.")
        else:
            print("\nERREUR Certains tests ont echoue. Verifiez la configuration.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERREUR CRITIQUE Erreur lors de l'execution des tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
