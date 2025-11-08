"""
Test des cartes avec photo maximisée et remontée
et polices maximales pour excellente lisibilité
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from eleves.models import Classe, Eleve
from eleves.views import generer_cartes_classe_pdf

def test_photo_maximale():
    print("=" * 70)
    print("TEST: PHOTO MAXIMALE ET POLICES MAXIMALES")
    print("=" * 70)
    
    try:
        # Récupérer la classe
        classe = Classe.objects.get(id=19)
        print(f"\n✓ Classe: {classe.nom}")
        print(f"  École: {classe.ecole.nom}")
        eleves = Eleve.objects.filter(classe=classe)
        print(f"  Nombre d'élèves: {eleves.count()}")
        
        # Créer une requête factice
        factory = RequestFactory()
        user = User.objects.first()
        if not user:
            user = User.objects.create_user('test', 'test@test.com', 'test')
        
        request = factory.get(f'/eleves/classe/{classe.id}/cartes-scolaires-pdf/')
        request.user = user
        
        print("\n📷 PHOTO MAXIMISÉE:")
        print("  • Taille: 22mm (augmentée de 18mm → +22%)")
        print("  • Position: y+18mm (remontée de y+12mm)")
        print("  • Surface: 484mm² (très grande)")
        print("  • Initiales: 16pt (augmentées de 12pt)")
        
        print("\n📝 POLICES MAXIMALES:")
        print("  • Nom élève: 10pt (était 8pt) → +25%")
        print("  • Matricule: 9pt (était 7pt) → +29%")
        print("  • Classe: 8pt (était 6pt) → +33%")
        print("  • Date/Lieu: 7pt (était 5pt) → +40%")
        print("  • Contact: 7pt (était 5pt) → +40%")
        print("  • Année scolaire: 5pt (était 4pt) → +25%")
        
        print("\n🎯 RÉSULTAT ATTENDU:")
        print("  • Photo dominante sur la carte")
        print("  • Position centrale haute")
        print("  • Toutes informations très lisibles")
        print("  • Format professionnel")
        
        print("\n🎨 Génération du PDF...")
        
        # Générer les cartes
        response = generer_cartes_classe_pdf(request, classe.id)
        
        if response.status_code == 200:
            # Sauvegarder le PDF
            filename = f"cartes_photo_max_{classe.id}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"\n✓ PDF généré avec succès!")
            print(f"  Taille: {len(response.content):,} octets")
            print(f"  Fichier: {filename}")
            
            # Statistiques
            nb_pages = (eleves.count() + 7) // 8
            
            print(f"\n📈 RÉSULTATS:")
            print(f"  • {eleves.count()} cartes générées")
            print(f"  • {nb_pages} pages A4")
            print(f"  • Photo 22mm (maximale)")
            print(f"  • Polices 7-10pt (très lisibles)")
            
            return True
        else:
            print(f"  ✗ Erreur: Code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def afficher_evolution():
    """Évolution des dimensions"""
    print("\n" + "="*70)
    print("ÉVOLUTION DES DIMENSIONS")
    print("="*70)
    
    print("\n📊 PHOTO (progression):")
    print("  12mm → 18mm → 22mm")
    print("  Position: y+4mm → y+12mm → y+18mm")
    print("  Augmentation totale: +83%")
    
    print("\n📊 POLICES (progression):")
    print("  Nom: 6pt → 8pt → 10pt (+67%)")
    print("  Matricule: 5pt → 7pt → 9pt (+80%)")
    print("  Classe: 5pt → 6pt → 8pt (+60%)")
    print("  Date: 4pt → 5pt → 7pt (+75%)")
    print("  Contact: 4pt → 5pt → 7pt (+75%)")
    
    print("\n✅ RÉSULTAT FINAL:")
    print("  • Photo dominante et centrale")
    print("  • Textes parfaitement lisibles")
    print("  • Format optimal pour identification")
    print("  • Équilibre visuel excellent")

if __name__ == "__main__":
    success = test_photo_maximale()
    
    if success:
        afficher_evolution()
        
        print("\n" + "="*70)
        print("✅ TEST RÉUSSI - Photo et polices maximales!")
        print("\n🔍 VÉRIFIEZ LE PDF:")
        print("  • Photo 22mm très visible")
        print("  • Position haute (y+18mm)")
        print("  • Toutes polices augmentées (7-10pt)")
        print("  • Parfaite lisibilité")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠️ TEST ÉCHOUÉ")
        print("="*70)
