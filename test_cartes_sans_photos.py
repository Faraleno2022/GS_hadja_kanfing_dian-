"""
Script de test pour vérifier que la génération de cartes scolaires
fonctionne correctement même avec des élèves sans photo
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe
from eleves.carte_scolaire_generator import generer_carte_scolaire_moderne
from django.contrib.auth.models import User
from io import BytesIO

def test_generation_cartes():
    print("=" * 50)
    print("TEST GÉNÉRATION CARTES SCOLAIRES SANS PHOTOS")
    print("=" * 50)
    
    # Récupérer une classe
    try:
        classe = Classe.objects.get(id=19)  # La classe qui posait problème
        print(f"\n✓ Classe trouvée: {classe.nom}")
        
        # Récupérer les élèves
        eleves = Eleve.objects.filter(
            classe=classe
        ).order_by('nom', 'prenom')
        
        print(f"✓ Nombre d'élèves trouvés: {eleves.count()}")
        
        # Compter les élèves sans photo
        eleves_sans_photo = 0
        eleves_avec_photo = 0
        
        for eleve in eleves:
            if not eleve.photo or not eleve.photo.name:
                eleves_sans_photo += 1
                print(f"  - {eleve.matricule} {eleve.prenom} {eleve.nom}: SANS PHOTO")
            else:
                eleves_avec_photo += 1
                print(f"  - {eleve.matricule} {eleve.prenom} {eleve.nom}: AVEC PHOTO")
        
        print(f"\nStatistiques:")
        print(f"  - Élèves avec photo: {eleves_avec_photo}")
        print(f"  - Élèves sans photo: {eleves_sans_photo}")
        
        # Tester la génération d'une carte pour un élève sans photo
        eleve_test = eleves.filter(photo='').first() or eleves.first()
        if eleve_test:
            print(f"\n✓ Test de génération de carte pour: {eleve_test.prenom} {eleve_test.nom}")
            
            try:
                # Créer un buffer pour le PDF
                buffer = BytesIO()
                
                # Générer la carte
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import mm
                
                c = canvas.Canvas(buffer, pagesize=A4)
                
                # Utiliser la fonction de dessin simple
                from eleves.carte_scolaire_generator import _dessiner_carte_simple
                
                # Paramètres de carte
                card_width = 243.78
                card_height = 153.07
                x = 50
                y = 500
                
                # Dessiner la carte
                _dessiner_carte_simple(c, eleve_test, x, y, card_width, card_height, 'Helvetica', 'Helvetica-Bold')
                
                c.save()
                buffer.seek(0)
                
                print("  ✓ Carte générée avec succès!")
                print(f"  ✓ Taille du PDF: {len(buffer.getvalue())} octets")
                
                # Sauvegarder le fichier de test
                test_file = "test_carte_sans_photo.pdf"
                with open(test_file, 'wb') as f:
                    f.write(buffer.getvalue())
                print(f"  ✓ Fichier de test sauvegardé: {test_file}")
                
                return True
                
            except Exception as e:
                print(f"  ✗ Erreur lors de la génération: {e}")
                import traceback
                traceback.print_exc()
                return False
        
    except Classe.DoesNotExist:
        print("✗ Classe avec ID 19 non trouvée")
        return False
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_generation_cartes()
    
    if success:
        print("\n" + "="*50)
        print("✓ TEST RÉUSSI - Les cartes peuvent être générées")
        print("  même pour les élèves sans photo!")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("✗ TEST ÉCHOUÉ - Vérifier les erreurs ci-dessus")
        print("="*50)
        sys.exit(1)
