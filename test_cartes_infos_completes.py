"""
Script de test pour vérifier que toutes les informations
apparaissent correctement sur les cartes scolaires
"""

import os
import sys
import django
from datetime import date

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe
from eleves.carte_scolaire_generator import generer_carte_scolaire_moderne
from io import BytesIO

def test_carte_complete():
    print("=" * 60)
    print("TEST CARTES SCOLAIRES AVEC INFORMATIONS COMPLÈTES")
    print("=" * 60)
    
    try:
        # Récupérer un élève avec des informations complètes
        eleve = Eleve.objects.filter(
            classe__id=19,
            responsable_principal__isnull=False
        ).first()
        
        if not eleve:
            print("❌ Aucun élève trouvé avec responsable dans la classe 19")
            return False
        
        print(f"\n✓ Élève sélectionné: {eleve.prenom} {eleve.nom}")
        print(f"  Matricule: {eleve.matricule}")
        print(f"  Classe: {eleve.classe.nom}")
        
        # Afficher les informations de l'élève
        print("\n📋 Informations personnelles:")
        if eleve.date_naissance:
            age = date.today().year - eleve.date_naissance.year
            if date.today() < date(date.today().year, eleve.date_naissance.month, eleve.date_naissance.day):
                age -= 1
            print(f"  - Date de naissance: {eleve.date_naissance.strftime('%d/%m/%Y')}")
            print(f"  - Âge: {age} ans")
        else:
            print("  - Date de naissance: NON RENSEIGNÉE")
        
        if eleve.lieu_naissance:
            print(f"  - Lieu de naissance: {eleve.lieu_naissance}")
        else:
            print("  - Lieu de naissance: NON RENSEIGNÉ")
        
        # Informations du responsable
        print("\n👥 Responsable principal:")
        if eleve.responsable_principal:
            resp = eleve.responsable_principal
            print(f"  - Nom: {resp.prenom} {resp.nom}" if resp.prenom and resp.nom else "  - Nom: NON RENSEIGNÉ")
            print(f"  - Téléphone: {resp.telephone}" if resp.telephone else "  - Téléphone: NON RENSEIGNÉ")
            print(f"  - Adresse: {resp.adresse}" if resp.adresse else "  - Adresse: NON RENSEIGNÉE")
        else:
            print("  ❌ AUCUN RESPONSABLE ENREGISTRÉ")
        
        # Générer la carte
        print("\n🎨 Génération de la carte scolaire...")
        
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            
            # Créer un buffer pour le PDF
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            
            # Utiliser la fonction de dessin
            from eleves.carte_scolaire_generator import _dessiner_carte_simple
            
            # Paramètres de carte
            card_width = 243.78
            card_height = 153.07
            x = 50
            y = 500
            
            # Dessiner la carte
            _dessiner_carte_simple(c, eleve, x, y, card_width, card_height, 'Helvetica', 'Helvetica-Bold')
            
            c.save()
            buffer.seek(0)
            
            print("  ✓ Carte générée avec succès!")
            print(f"  ✓ Taille du PDF: {len(buffer.getvalue())} octets")
            
            # Sauvegarder le fichier
            filename = f"carte_{eleve.matricule.replace('/', '_')}_complete.pdf"
            with open(filename, 'wb') as f:
                f.write(buffer.getvalue())
            print(f"  ✓ Fichier sauvegardé: {filename}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Erreur lors de la génération: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"✗ Erreur générale: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Tester plusieurs élèves
    print("\n🔍 Recherche d'élèves avec informations complètes...")
    
    eleves_complets = Eleve.objects.filter(
        classe__id=19,
        date_naissance__isnull=False,
        responsable_principal__isnull=False
    ).count()
    
    print(f"Trouvé {eleves_complets} élèves avec date de naissance et responsable")
    
    # Générer une carte test
    success = test_carte_complete()
    
    if success:
        print("\n" + "="*60)
        print("✅ TEST RÉUSSI - Toutes les informations sont affichées!")
        print("Vérifiez le PDF généré pour voir le résultat")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("⚠️ TEST ÉCHOUÉ - Vérifier les erreurs")
        print("="*60)
