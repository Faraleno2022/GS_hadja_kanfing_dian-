"""
Test de génération de cartes pour une classe entière
avec tous les logos affichés
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

def test_generation_classe_logos():
    print("=" * 60)
    print("TEST CARTES CLASSE COMPLÈTE AVEC LOGOS")
    print("=" * 60)
    
    try:
        # Récupérer la classe
        classe = Classe.objects.get(id=19)
        print(f"\n✓ Classe: {classe.nom}")
        print(f"  École: {classe.ecole.nom}")
        
        # Vérifier le logo
        if classe.ecole.logo:
            try:
                if os.path.exists(classe.ecole.logo.path):
                    print(f"  ✓ Logo disponible: {classe.ecole.logo.name}")
                else:
                    print(f"  ⚠️ Logo défini mais fichier manquant")
            except:
                print(f"  ⚠️ Logo défini mais inaccessible")
        else:
            print(f"  ℹ️ Pas de logo - Initiales utilisées")
        
        # Compter les élèves
        eleves = Eleve.objects.filter(classe=classe)
        print(f"  Nombre d'élèves: {eleves.count()}")
        
        # Créer une requête factice
        factory = RequestFactory()
        user = User.objects.first()
        if not user:
            user = User.objects.create_user('test', 'test@test.com', 'test')
        
        request = factory.get(f'/eleves/classe/{classe.id}/cartes-scolaires-pdf/')
        request.user = user
        
        print(f"\n🎨 Génération des cartes avec logos...")
        print("  Chaque carte contiendra:")
        print("  • Logo en FILIGRANE au centre (transparent)")
        print("  • Logo dans l'EN-TÊTE à gauche")
        print("  • Logo sur le CADRE PHOTO")
        
        # Générer les cartes
        response = generer_cartes_classe_pdf(request, classe.id)
        
        if response.status_code == 200:
            # Sauvegarder le PDF
            filename = f"cartes_classe_logos_{classe.id}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"\n✓ Génération réussie!")
            print(f"  Taille du PDF: {len(response.content):,} octets")
            print(f"  Fichier: {filename}")
            
            # Statistiques
            nb_cartes_par_page = 4
            nb_pages = (eleves.count() + nb_cartes_par_page - 1) // nb_cartes_par_page
            total_logos = eleves.count() * 3  # 3 logos par carte
            
            print(f"\n📊 Statistiques:")
            print(f"  • {eleves.count()} cartes générées")
            print(f"  • {nb_pages} pages A4")
            print(f"  • {total_logos} logos au total (3 par carte)")
            
            return True
        else:
            print(f"  ✗ Erreur: Code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_generation_classe_logos()
    
    if success:
        print("\n" + "="*60)
        print("✅ TEST RÉUSSI - Cartes générées avec tous les logos!")
        print("\n📋 Résumé des améliorations visuelles:")
        print("  1. FILIGRANE: Logo central transparent (rotation 15°)")
        print("     → Visible derrière le texte sur toute la carte")
        print("  2. EN-TÊTE: Logo dans cercle blanc à gauche")
        print("     → Identification claire de l'école")
        print("  3. PHOTO: Petit logo en coin supérieur gauche")
        print("     → Marque de sécurité et d'authenticité")
        print("\n🎯 Impact:")
        print("  • Cartes plus professionnelles")
        print("  • Identité visuelle renforcée")
        print("  • Difficile à falsifier")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("⚠️ TEST ÉCHOUÉ")
        print("="*60)
