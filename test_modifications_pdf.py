"""
Script de test pour vérifier les modifications des PDFs
Date : 11 novembre 2024

Modifications testées :
1. Ticket de retrait : plus de cercle vide si pas de photo
2. Ticket bus : plus de cercle vide si pas de photo
3. Carte scolaire : format PVC par défaut (86mm x 54mm)
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from eleves.models import Eleve
from bus.models import AbonnementBus
from django.contrib.auth.models import User

def tester_modifications():
    """Test des modifications apportées aux PDFs"""
    
    print("="*80)
    print("TEST DES MODIFICATIONS PDFs - 11 NOVEMBRE 2024")
    print("="*80)
    
    try:
        # Récupérer des élèves pour les tests
        eleve_avec_photo = Eleve.objects.filter(
            statut='ACTIF',
            photo__isnull=False
        ).exclude(photo='').first()
        
        eleve_sans_photo = Eleve.objects.filter(
            statut='ACTIF'
        ).filter(photo__isnull=True).first()
        
        if not eleve_sans_photo:
            eleve_sans_photo = Eleve.objects.filter(
                statut='ACTIF',
                photo=''
            ).first()
        
        print("\n📋 ÉLÈVES DE TEST :")
        print("-"*50)
        
        if eleve_avec_photo:
            print(f"✅ Élève AVEC photo : {eleve_avec_photo.prenom} {eleve_avec_photo.nom}")
            print(f"   ID : {eleve_avec_photo.id}")
            print(f"   Matricule : {eleve_avec_photo.matricule}")
            print(f"   Classe : {eleve_avec_photo.classe.nom}")
        else:
            print("❌ Aucun élève avec photo trouvé")
        
        if eleve_sans_photo:
            print(f"\n✅ Élève SANS photo : {eleve_sans_photo.prenom} {eleve_sans_photo.nom}")
            print(f"   ID : {eleve_sans_photo.id}")
            print(f"   Matricule : {eleve_sans_photo.matricule}")
            print(f"   Classe : {eleve_sans_photo.classe.nom}")
        else:
            print("❌ Aucun élève sans photo trouvé")
        
        # TEST 1 : TICKET DE RETRAIT
        print("\n\n🎫 TEST 1 : TICKET DE RETRAIT")
        print("-"*50)
        print("COMPORTEMENT ATTENDU :")
        print("✅ Si photo disponible → Affichage de la photo dans un cercle")
        print("✅ Si pas de photo → AUCUN cercle vide (supprimé)")
        
        if eleve_avec_photo:
            niveau = eleve_avec_photo.classe.niveau.upper() if eleve_avec_photo.classe.niveau else ''
            if any(x in niveau for x in ['PRIMAIRE', 'PN', 'MATERNELLE', 'GARDERIE']):
                print(f"\nÉlève avec photo ({eleve_avec_photo.prenom}) :")
                print(f"→ URL : /eleves/{eleve_avec_photo.id}/ticket-retrait-pdf/")
                print("→ Résultat attendu : Photo visible dans le cercle")
            else:
                print(f"\nÉlève avec photo n'est pas du primaire/maternelle")
        
        if eleve_sans_photo:
            niveau = eleve_sans_photo.classe.niveau.upper() if eleve_sans_photo.classe.niveau else ''
            if any(x in niveau for x in ['PRIMAIRE', 'PN', 'MATERNELLE', 'GARDERIE']):
                print(f"\nÉlève sans photo ({eleve_sans_photo.prenom}) :")
                print(f"→ URL : /eleves/{eleve_sans_photo.id}/ticket-retrait-pdf/")
                print("→ Résultat attendu : PAS de cercle vide, PAS de texte 'PHOTO'")
            else:
                print(f"\nÉlève sans photo n'est pas du primaire/maternelle")
        
        # TEST 2 : TICKET BUS
        print("\n\n🚌 TEST 2 : TICKET BUS")
        print("-"*50)
        print("COMPORTEMENT ATTENDU :")
        print("✅ Si photo disponible → Affichage de la photo dans un cercle")
        print("✅ Si pas de photo → AUCUN cercle vide (supprimé)")
        
        # Vérifier les abonnements bus
        if eleve_avec_photo:
            abonnement = AbonnementBus.objects.filter(
                eleve=eleve_avec_photo,
                statut='ACTIF'
            ).first()
            
            if abonnement:
                print(f"\nÉlève avec photo et abonnement bus ({eleve_avec_photo.prenom}) :")
                print(f"→ URL : /eleves/{eleve_avec_photo.id}/ticket-bus-pdf/")
                print("→ Résultat attendu : Photo visible dans le cercle")
            else:
                print(f"\n{eleve_avec_photo.prenom} n'a pas d'abonnement bus actif")
        
        if eleve_sans_photo:
            abonnement = AbonnementBus.objects.filter(
                eleve=eleve_sans_photo,
                statut='ACTIF'
            ).first()
            
            if abonnement:
                print(f"\nÉlève sans photo avec abonnement bus ({eleve_sans_photo.prenom}) :")
                print(f"→ URL : /eleves/{eleve_sans_photo.id}/ticket-bus-pdf/")
                print("→ Résultat attendu : PAS de cercle vide, PAS de texte 'PHOTO'")
            else:
                print(f"\n{eleve_sans_photo.prenom} n'a pas d'abonnement bus actif")
        
        # TEST 3 : CARTE SCOLAIRE FORMAT PVC
        print("\n\n💳 TEST 3 : CARTE SCOLAIRE - FORMAT PVC PAR DÉFAUT")
        print("-"*50)
        print("COMPORTEMENT ATTENDU :")
        print("✅ Par défaut → Format PVC (86mm x 54mm) - taille carte bancaire")
        print("✅ Pas de page A4, carte unique directement imprimable")
        print("✅ Nom de l'école en police agrandie (12-14pt)")
        print("✅ En-tête agrandi (16mm) avec logo (12mm)")
        
        if eleve_avec_photo:
            print(f"\nÉlève avec photo ({eleve_avec_photo.prenom}) :")
            print(f"→ URL par défaut : /eleves/{eleve_avec_photo.id}/carte-scolaire-pdf/")
            print("→ Format attendu : PVC 86mm x 54mm (carte unique)")
            print("→ Nom du fichier : carte_pvc_{eleve_avec_photo.matricule}.pdf")
            
            print(f"\n→ URL format standard : /eleves/{eleve_avec_photo.id}/carte-scolaire-pdf/?format=standard")
            print("→ Format attendu : Standard si demandé explicitement")
        
        # RÉSUMÉ DES CHANGEMENTS
        print("\n\n📊 RÉSUMÉ DES MODIFICATIONS")
        print("="*80)
        print("1. TICKETS (retrait & bus) :")
        print("   ❌ AVANT : Cercle vide avec 'PHOTO' si pas de photo")
        print("   ✅ APRÈS : Rien si pas de photo (plus propre)")
        
        print("\n2. CARTE SCOLAIRE :")
        print("   ❌ AVANT : Format A4 par défaut")
        print("   ✅ APRÈS : Format PVC (86mm x 54mm) par défaut")
        print("   → Carte unique, pas de page A4")
        print("   → Directement imprimable sur PVC")
        print("   → Design moderne conservé")
        
        print("\n3. AMÉLIORATIONS VISUELLES :")
        print("   ✅ Nom école : Police 12-14pt (avant 9-11pt)")
        print("   ✅ En-tête : 16mm (avant 14mm)")
        print("   ✅ Logo : 12mm (avant 10mm)")
        print("   ✅ Filigrane : 15% opacité, rotation 15°")
        
        # URLs de test rapide
        print("\n\n🔗 URLS DE TEST RAPIDE")
        print("="*80)
        print("Démarrez le serveur : python manage.py runserver")
        print("\nPuis testez ces URLs :")
        
        if eleve_avec_photo:
            print(f"\n📸 Élève AVEC photo (ID {eleve_avec_photo.id}) :")
            print(f"http://127.0.0.1:8000/eleves/{eleve_avec_photo.id}/carte-scolaire-pdf/")
            
            niveau = eleve_avec_photo.classe.niveau.upper() if eleve_avec_photo.classe.niveau else ''
            if any(x in niveau for x in ['PRIMAIRE', 'PN', 'MATERNELLE', 'GARDERIE']):
                print(f"http://127.0.0.1:8000/eleves/{eleve_avec_photo.id}/ticket-retrait-pdf/")
        
        if eleve_sans_photo:
            print(f"\n📷 Élève SANS photo (ID {eleve_sans_photo.id}) :")
            print(f"http://127.0.0.1:8000/eleves/{eleve_sans_photo.id}/carte-scolaire-pdf/")
            
            niveau = eleve_sans_photo.classe.niveau.upper() if eleve_sans_photo.classe.niveau else ''
            if any(x in niveau for x in ['PRIMAIRE', 'PN', 'MATERNELLE', 'GARDERIE']):
                print(f"http://127.0.0.1:8000/eleves/{eleve_sans_photo.id}/ticket-retrait-pdf/")
        
        print("\n" + "="*80)
        print("✅ TESTS DE VALIDATION PRÊTS")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    tester_modifications()
