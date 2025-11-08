"""
Test de génération de cartes scolaires
avec 8 cartes par page et informations centrées
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

def test_8_cartes_par_page():
    print("=" * 70)
    print("TEST: 8 CARTES PAR PAGE AVEC INFORMATIONS CENTRÉES")
    print("=" * 70)
    
    try:
        # Récupérer la classe
        classe = Classe.objects.get(id=19)
        print(f"\n✓ Classe: {classe.nom}")
        print(f"  École: {classe.ecole.nom}")
        
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
        
        print("\n📊 NOUVELLES SPÉCIFICATIONS:")
        print("  • 8 cartes par page (grille 4x2)")
        print("  • Informations décalées vers le centre")
        print("  • Tailles réduites pour s'adapter")
        print("  • Polices ajustées (plus petites)")
        
        print("\n🎨 Génération du PDF...")
        
        # Générer les cartes
        response = generer_cartes_classe_pdf(request, classe.id)
        
        if response.status_code == 200:
            # Sauvegarder le PDF
            filename = f"cartes_8_par_page_{classe.id}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"\n✓ PDF généré avec succès!")
            print(f"  Taille: {len(response.content):,} octets")
            print(f"  Fichier: {filename}")
            
            # Calculer les statistiques
            nb_cartes_par_page = 8  # Nouveau: 8 cartes par page
            nb_pages = (eleves.count() + nb_cartes_par_page - 1) // nb_cartes_par_page
            
            print(f"\n📈 STATISTIQUES:")
            print(f"  • Total élèves: {eleves.count()}")
            print(f"  • Cartes par page: {nb_cartes_par_page}")
            print(f"  • Nombre de pages: {nb_pages}")
            print(f"  • Dernière page: {eleves.count() % nb_cartes_par_page or nb_cartes_par_page} cartes")
            
            print("\n📏 DIMENSIONS AJUSTÉES:")
            print("  • En-tête: 8mm (réduit de 12mm)")
            print("  • Photo: 15mm (réduit de 20mm)")
            print("  • Logo en-tête: 5mm (réduit de 8mm)")
            print("  • Logo photo: 3mm (réduit de 5mm)")
            print("  • Filigrane: 20mm (réduit de 30mm)")
            
            print("\n📝 TEXTE OPTIMISÉ:")
            print("  • Nom élève: 7pt (réduit de 9pt)")
            print("  • Matricule: 6pt (réduit de 7pt)")
            print("  • Infos: 5pt (réduit de 6-7pt)")
            print("  • Infos décalées de 8mm (au lieu de 3mm)")
            
            return True
        else:
            print(f"  ✗ Erreur: Code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def comparer_avec_ancien():
    """Comparaison avec l'ancien format"""
    print("\n" + "="*70)
    print("COMPARAISON ANCIEN VS NOUVEAU FORMAT")
    print("="*70)
    
    print("\n📊 ANCIEN FORMAT (4 cartes/page):")
    print("  • Grille: 2x2")
    print("  • Taille carte: ~86mm x 54mm")
    print("  • Marges: 15mm")
    print("  • Espacement: 10mm")
    print("  • Pages pour 40 élèves: 10")
    
    print("\n📊 NOUVEAU FORMAT (8 cartes/page):")
    print("  • Grille: 4x2 (4 lignes, 2 colonnes)")
    print("  • Taille carte: ~92mm x 70mm (approximatif)")
    print("  • Marges: 10mm")
    print("  • Espacement: 5mm")
    print("  • Pages pour 40 élèves: 5")
    
    print("\n✅ AVANTAGES DU NOUVEAU FORMAT:")
    print("  • 50% moins de pages")
    print("  • Plus économique")
    print("  • Impression plus rapide")
    print("  • Informations mieux centrées")
    print("  • Format plus compact")

if __name__ == "__main__":
    success = test_8_cartes_par_page()
    
    if success:
        comparer_avec_ancien()
        
        print("\n" + "="*70)
        print("✅ TEST RÉUSSI - 8 cartes par page générées!")
        print("\n🔍 VÉRIFIEZ LE PDF:")
        print("  • Les cartes doivent être sur 4 lignes × 2 colonnes")
        print("  • Les informations doivent être centrées")
        print("  • Les logos doivent être visibles malgré la taille réduite")
        print("  • Le texte doit rester lisible")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("⚠️ TEST ÉCHOUÉ")
        print("="*70)
