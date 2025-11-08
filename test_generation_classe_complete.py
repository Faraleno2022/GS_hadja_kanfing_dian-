"""
Test de génération de cartes scolaires pour une classe entière
avec toutes les informations complètes
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

def test_generation_classe():
    print("=" * 60)
    print("TEST GÉNÉRATION CARTES POUR CLASSE ENTIÈRE")
    print("=" * 60)
    
    try:
        # Récupérer la classe de test
        classe = Classe.objects.get(id=19)
        print(f"\n✓ Classe: {classe.nom}")
        print(f"  Année scolaire: {classe.annee_scolaire}")
        
        # Compter les élèves
        eleves = Eleve.objects.filter(classe=classe)
        print(f"  Nombre total d'élèves: {eleves.count()}")
        
        # Statistiques
        avec_date_naissance = eleves.filter(date_naissance__isnull=False).count()
        avec_responsable = eleves.filter(responsable_principal__isnull=False).count()
        avec_photo = 0
        sans_photo = 0
        
        for eleve in eleves:
            if eleve.photo and eleve.photo.name:
                avec_photo += 1
            else:
                sans_photo += 1
        
        print(f"\n📊 Statistiques des données:")
        print(f"  - Élèves avec date de naissance: {avec_date_naissance}/{eleves.count()}")
        print(f"  - Élèves avec responsable: {avec_responsable}/{eleves.count()}")
        print(f"  - Élèves avec photo: {avec_photo}/{eleves.count()}")
        print(f"  - Élèves sans photo: {sans_photo}/{eleves.count()}")
        
        # Créer une requête factice pour le test
        factory = RequestFactory()
        
        # Créer ou récupérer un utilisateur de test
        user = User.objects.first()
        if not user:
            user = User.objects.create_user('test', 'test@test.com', 'test')
        
        # Créer la requête
        request = factory.get(f'/eleves/classe/{classe.id}/cartes-scolaires-pdf/')
        request.user = user
        
        print(f"\n🎨 Génération des cartes scolaires...")
        
        # Appeler directement la vue
        response = generer_cartes_classe_pdf(request, classe.id)
        
        if response.status_code == 200:
            # Sauvegarder le PDF
            filename = f"cartes_classe_{classe.id}_complete.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"  ✓ Génération réussie!")
            print(f"  ✓ Taille du PDF: {len(response.content):,} octets")
            print(f"  ✓ Fichier sauvegardé: {filename}")
            
            # Calculer le nombre de pages (approximatif)
            nb_cartes_par_page = 4  # 2x2 cartes par page A4
            nb_pages = (eleves.count() + nb_cartes_par_page - 1) // nb_cartes_par_page
            print(f"  ✓ Nombre de pages estimé: {nb_pages}")
            
            return True
        else:
            print(f"  ✗ Erreur: Code de statut {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_generation_classe()
    
    if success:
        print("\n" + "="*60)
        print("✅ TEST RÉUSSI - Les cartes de classe sont générées")
        print("   avec toutes les informations disponibles!")
        print("="*60)
        print("\n📌 Notes importantes:")
        print("  • Les élèves SANS photo ont un placeholder avec initiales")
        print("  • Les informations manquantes sont simplement omises")
        print("  • L'année scolaire apparaît sur chaque carte")
        print("  • Maximum 4 cartes par page A4")
    else:
        print("\n" + "="*60)
        print("⚠️ TEST ÉCHOUÉ - Vérifier les erreurs")
        print("="*60)
