"""
Test de l'export PDF du classement avec en-tête et filigrane
"""
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from notes.export_classement import exporter_classement_classe_pdf
from notes.models import ClasseNote
from django.contrib.auth import get_user_model

User = get_user_model()

def tester_export_pdf():
    """Tester l'export PDF d'un classement"""
    
    print("\n" + "="*80)
    print("TEST EXPORT PDF DU CLASSEMENT")
    print("="*80 + "\n")
    
    # Trouver une classe
    classe_note = ClasseNote.objects.filter(nom__icontains='12').filter(nom__icontains='scien').first()
    
    if not classe_note:
        print("❌ Aucune classe note trouvée")
        return False
    
    print(f"✅ Classe sélectionnée: {classe_note.nom}")
    print(f"   École: {classe_note.ecole.nom}")
    print(f"   ID: {classe_note.id}")
    
    # Vérifier le logo
    if hasattr(classe_note.ecole, 'logo') and classe_note.ecole.logo:
        print(f"✅ Logo disponible: {classe_note.ecole.logo.path if hasattr(classe_note.ecole.logo, 'path') else 'URL'}")
    else:
        print(f"⚠️  Pas de logo (le PDF sera généré sans filigrane)")
    
    # Créer une requête simulée
    factory = RequestFactory()
    request = factory.get(f'/notes/exporter-classement-pdf/?classe_id={classe_note.id}&periode=TRIMESTRE_1')
    
    # Créer un utilisateur de test
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        
        if user:
            request.user = user
            print(f"✅ Utilisateur: {user.username}")
        else:
            print("❌ Aucun utilisateur trouvé")
            return False
    except Exception as e:
        print(f"❌ Erreur utilisateur: {e}")
        return False
    
    # Tester l'export
    try:
        print("\n🔄 Génération du PDF...")
        response = exporter_classement_classe_pdf(request)
        
        if response.status_code == 200:
            print(f"✅ PDF généré avec succès!")
            print(f"   Content-Type: {response.get('Content-Type')}")
            
            # Récupérer le nom du fichier
            content_disposition = response.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
                print(f"   Nom du fichier: {filename}")
            
            # Taille du PDF
            pdf_size = len(response.content)
            print(f"   Taille: {pdf_size:,} octets ({pdf_size/1024:.1f} Ko)")
            
            # Sauvegarder le PDF pour vérification
            output_path = os.path.join(os.path.dirname(__file__), 'test_classement_export.pdf')
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"\n✅ PDF sauvegardé: {output_path}")
            print(f"   Ouvrez ce fichier pour vérifier:")
            print(f"   - En-tête avec République de Guinée")
            print(f"   - Devise avec couleurs")
            print(f"   - Informations de l'école (IRE, DPE, DESEE)")
            print(f"   - Logo de l'école")
            print(f"   - Filigrane au centre (si logo disponible)")
            print(f"   - Classement avec rangs (1er/1ère selon le sexe)")
            print(f"   - Moyennes avec code couleur")
            print(f"   - Statistiques en bas")
            
            return True
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            if hasattr(response, 'content'):
                print(f"   Message: {response.content.decode('utf-8')[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = tester_export_pdf()
    
    print("\n" + "="*80)
    if success:
        print("✅ ✅ ✅ TEST RÉUSSI ✅ ✅ ✅")
    else:
        print("❌ ❌ ❌ TEST ÉCHOUÉ ❌ ❌ ❌")
    print("="*80 + "\n")
    
    exit(0 if success else 1)
