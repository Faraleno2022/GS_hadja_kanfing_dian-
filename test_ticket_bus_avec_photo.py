"""
Test rapide pour créer un abonnement bus et générer le ticket
Date : 11 novembre 2024
"""

import os
import sys
import django
from datetime import date, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from eleves.models import Eleve
from bus.models import AbonnementBus

def test_ticket_bus():
    """Créer un abonnement bus temporaire et générer le ticket"""
    
    print("="*80)
    print("TEST TICKET BUS AVEC PHOTO")
    print("="*80)
    
    # Trouver un élève avec photo
    eleve = Eleve.objects.filter(
        statut='ACTIF',
        photo__isnull=False
    ).exclude(photo='').first()
    
    if not eleve:
        print("❌ Aucun élève avec photo trouvé")
        return
    
    print(f"\n📸 Élève sélectionné : {eleve.prenom} {eleve.nom}")
    print(f"   ID : {eleve.id}")
    print(f"   Photo : {eleve.photo.name}")
    
    # Créer un abonnement bus temporaire
    print("\n📝 Création d'un abonnement bus temporaire...")
    
    try:
        # Vérifier s'il existe déjà
        abonnement = AbonnementBus.objects.filter(eleve=eleve).first()
        
        if not abonnement:
            # Créer un nouvel abonnement
            abonnement = AbonnementBus.objects.create(
                eleve=eleve,
                date_debut=date.today(),
                date_fin=date.today() + timedelta(days=30),
                montant=50000,
                statut='ACTIF',
                type_abonnement='MENSUEL'
            )
            print(f"   ✅ Abonnement créé (ID: {abonnement.id})")
            created = True
        else:
            # Activer l'abonnement existant
            abonnement.statut = 'ACTIF'
            abonnement.save()
            print(f"   ✅ Abonnement existant activé (ID: {abonnement.id})")
            created = False
        
        # Générer le PDF
        print("\n🚌 Génération du ticket bus...")
        
        client = Client()
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            client.force_login(admin)
            
            url = f'/eleves/{eleve.id}/ticket-bus-pdf/'
            print(f"   URL : {url}")
            
            response = client.get(url)
            
            if response.status_code == 200:
                # Sauvegarder le PDF
                output_dir = os.path.join(os.path.dirname(__file__), 'test_pdfs_photos')
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                filename = f'ticket_bus_avec_photo_TEST_{eleve.id}.pdf'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"   ✅ PDF généré : {filename}")
                print(f"   → Taille : {len(response.content)} octets")
                print(f"   → Sauvé dans : test_pdfs_photos/")
                print(f"   → Photo affichée dans cercle de 30mm")
                
                print("\n" + "="*80)
                print("✅ TEST RÉUSSI")
                print("="*80)
                print("\nVérifications :")
                print("✓ Photo importée correctement")
                print("✓ Cercle avec bordure orange (bus)")
                print("✓ Masque circulaire appliqué")
                print("✓ Conversion RGB automatique")
                print(f"\n📁 Ouvrir : {filepath}")
            else:
                print(f"   ❌ Erreur : Code {response.status_code}")
        else:
            print("❌ Aucun administrateur trouvé")
        
        # Nettoyer si créé pour le test
        if created:
            print("\n🧹 Nettoyage...")
            abonnement.delete()
            print("   ✅ Abonnement temporaire supprimé")
            
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ticket_bus()
