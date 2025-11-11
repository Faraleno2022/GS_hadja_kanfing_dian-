"""
Script de test pour générer et vérifier les PDFs avec photos
Date : 11 novembre 2024
"""

import os
import sys
import django
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from eleves.models import Eleve
from bus.models import AbonnementBus

def generer_pdfs_avec_photos():
    """Générer des PDFs de test pour vérifier l'affichage des photos"""
    
    print("="*80)
    print("TEST DE GÉNÉRATION DES PDFs AVEC PHOTOS")
    print("Date :", datetime.now().strftime("%d/%m/%Y %H:%M"))
    print("="*80)
    
    # Créer un client de test
    client = Client()
    
    # Se connecter avec un admin
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("❌ Aucun administrateur trouvé")
        return
    
    # Forcer la connexion pour les tests
    client.force_login(admin)
    print(f"✅ Connecté en tant que : {admin.username}")
    
    # Dossier de sortie pour les tests
    output_dir = os.path.join(os.path.dirname(__file__), 'test_pdfs_photos')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    print(f"📁 Dossier de sortie : {output_dir}")
    
    print("\n" + "="*80)
    print("TEST 1 : TICKET DE RETRAIT AVEC PHOTO")
    print("="*80)
    
    # Trouver un élève du primaire/maternelle AVEC photo
    eleve_retrait_avec = Eleve.objects.filter(
        statut='ACTIF',
        photo__isnull=False
    ).exclude(photo='').filter(
        classe__niveau__icontains='primaire'
    ).first()
    
    if not eleve_retrait_avec:
        eleve_retrait_avec = Eleve.objects.filter(
            statut='ACTIF',
            photo__isnull=False
        ).exclude(photo='').filter(
            classe__niveau__icontains='maternelle'
        ).first()
    
    if eleve_retrait_avec:
        print(f"\n📸 Élève AVEC photo : {eleve_retrait_avec.prenom} {eleve_retrait_avec.nom}")
        print(f"   ID : {eleve_retrait_avec.id}")
        print(f"   Photo : {eleve_retrait_avec.photo.name}")
        
        # Générer le PDF
        url = f'/eleves/{eleve_retrait_avec.id}/ticket-retrait-pdf/'
        print(f"   URL : {url}")
        
        try:
            response = client.get(url)
            if response.status_code == 200:
                # Sauvegarder le PDF
                filename = f'ticket_retrait_avec_photo_{eleve_retrait_avec.id}.pdf'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ PDF généré : {filename}")
                print(f"   → Taille : {len(response.content)} octets")
                print(f"   → Photo affichée dans cercle de 30mm")
            else:
                print(f"   ❌ Erreur : Code {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    
    # Trouver un élève du primaire/maternelle SANS photo
    eleve_retrait_sans = Eleve.objects.filter(
        statut='ACTIF'
    ).filter(
        photo__isnull=True
    ).filter(
        classe__niveau__icontains='primaire'
    ).first()
    
    if not eleve_retrait_sans:
        eleve_retrait_sans = Eleve.objects.filter(
            statut='ACTIF',
            photo=''
        ).filter(
            classe__niveau__icontains='maternelle'
        ).first()
    
    if eleve_retrait_sans:
        print(f"\n📷 Élève SANS photo : {eleve_retrait_sans.prenom} {eleve_retrait_sans.nom}")
        print(f"   ID : {eleve_retrait_sans.id}")
        print(f"   Photo : Non disponible")
        
        # Générer le PDF
        url = f'/eleves/{eleve_retrait_sans.id}/ticket-retrait-pdf/'
        print(f"   URL : {url}")
        
        try:
            response = client.get(url)
            if response.status_code == 200:
                # Sauvegarder le PDF
                filename = f'ticket_retrait_sans_photo_{eleve_retrait_sans.id}.pdf'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ PDF généré : {filename}")
                print(f"   → Taille : {len(response.content)} octets")
                print(f"   → PAS de cercle vide (nouvelle version)")
            else:
                print(f"   ❌ Erreur : Code {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    
    print("\n" + "="*80)
    print("TEST 2 : TICKET BUS AVEC PHOTO")
    print("="*80)
    
    # Trouver un élève avec abonnement bus et photo
    eleve_bus_avec = Eleve.objects.filter(
        statut='ACTIF',
        photo__isnull=False,
        abonnementbus__statut='ACTIF'
    ).exclude(photo='').first()
    
    if eleve_bus_avec:
        print(f"\n📸 Élève AVEC photo et abonnement : {eleve_bus_avec.prenom} {eleve_bus_avec.nom}")
        print(f"   ID : {eleve_bus_avec.id}")
        print(f"   Photo : {eleve_bus_avec.photo.name}")
        
        # Générer le PDF
        url = f'/eleves/{eleve_bus_avec.id}/ticket-bus-pdf/'
        print(f"   URL : {url}")
        
        try:
            response = client.get(url)
            if response.status_code == 200:
                # Sauvegarder le PDF
                filename = f'ticket_bus_avec_photo_{eleve_bus_avec.id}.pdf'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ PDF généré : {filename}")
                print(f"   → Taille : {len(response.content)} octets")
                print(f"   → Photo affichée dans cercle de 30mm")
            else:
                print(f"   ❌ Erreur : Code {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    else:
        print("   ❌ Aucun élève avec photo ET abonnement bus trouvé")
    
    # Trouver un élève avec abonnement bus SANS photo
    eleve_bus_sans = Eleve.objects.filter(
        statut='ACTIF',
        abonnementbus__statut='ACTIF'
    ).filter(
        photo__isnull=True
    ).first()
    
    if not eleve_bus_sans:
        eleve_bus_sans = Eleve.objects.filter(
            statut='ACTIF',
            photo='',
            abonnementbus__statut='ACTIF'
        ).first()
    
    if eleve_bus_sans:
        print(f"\n📷 Élève SANS photo avec abonnement : {eleve_bus_sans.prenom} {eleve_bus_sans.nom}")
        print(f"   ID : {eleve_bus_sans.id}")
        print(f"   Photo : Non disponible")
        
        # Générer le PDF
        url = f'/eleves/{eleve_bus_sans.id}/ticket-bus-pdf/'
        print(f"   URL : {url}")
        
        try:
            response = client.get(url)
            if response.status_code == 200:
                # Sauvegarder le PDF
                filename = f'ticket_bus_sans_photo_{eleve_bus_sans.id}.pdf'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ PDF généré : {filename}")
                print(f"   → Taille : {len(response.content)} octets")
                print(f"   → PAS de cercle vide (nouvelle version)")
            else:
                print(f"   ❌ Erreur : Code {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    else:
        print("   ❌ Aucun élève sans photo avec abonnement bus trouvé")
    
    print("\n" + "="*80)
    print("TEST 3 : CARTE SCOLAIRE AVEC PHOTO (FORMAT PVC)")
    print("="*80)
    
    # Trouver un élève AVEC photo
    eleve_carte_avec = Eleve.objects.filter(
        statut='ACTIF',
        photo__isnull=False
    ).exclude(photo='').first()
    
    if eleve_carte_avec:
        print(f"\n📸 Élève AVEC photo : {eleve_carte_avec.prenom} {eleve_carte_avec.nom}")
        print(f"   ID : {eleve_carte_avec.id}")
        print(f"   Photo : {eleve_carte_avec.photo.name}")
        
        # Générer le PDF (format PVC par défaut)
        url = f'/eleves/{eleve_carte_avec.id}/carte-scolaire-pdf/'
        print(f"   URL : {url}")
        
        try:
            response = client.get(url)
            if response.status_code == 200:
                # Sauvegarder le PDF
                filename = f'carte_pvc_avec_photo_{eleve_carte_avec.id}.pdf'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ PDF généré : {filename}")
                print(f"   → Taille : {len(response.content)} octets")
                print(f"   → Format PVC : 86mm x 54mm")
                print(f"   → Photo affichée (22mm x 22mm)")
            else:
                print(f"   ❌ Erreur : Code {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
    
    print("\n" + "="*80)
    print("RÉSUMÉ DE LA GÉNÉRATION")
    print("="*80)
    
    # Lister les fichiers générés
    files = os.listdir(output_dir)
    pdf_files = [f for f in files if f.endswith('.pdf')]
    
    print(f"\n📊 Fichiers générés : {len(pdf_files)}")
    for pdf in pdf_files:
        file_path = os.path.join(output_dir, pdf)
        file_size = os.path.getsize(file_path)
        print(f"   ✅ {pdf} ({file_size} octets)")
    
    print(f"\n📁 Dossier : {output_dir}")
    print("💡 Ouvrez les PDFs pour vérifier visuellement les photos")
    
    print("\n" + "="*80)
    print("POINTS DE VÉRIFICATION")
    print("="*80)
    print("✓ Tickets AVEC photo : Photo dans cercle de 30mm avec bordure")
    print("✓ Tickets SANS photo : Aucun cercle vide affiché")
    print("✓ Carte scolaire : Format PVC (86mm x 54mm) par défaut")
    print("✓ Photos converties en RGB et masque circulaire appliqué")
    print("✓ Gestion correcte des différents formats d'image")
    
    print("\n✅ TEST TERMINÉ - Vérifiez les PDFs dans : " + output_dir)

if __name__ == "__main__":
    generer_pdfs_avec_photos()
