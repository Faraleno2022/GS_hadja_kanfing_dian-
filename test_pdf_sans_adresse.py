"""
Test rapide : vérifier que l'adresse n'apparaît plus dans le PDF
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

print("\n" + "="*80)
print("TEST : VÉRIFICATION SUPPRESSION DE L'ADRESSE DANS LE PDF")
print("="*80 + "\n")

# Trouver une classe
classe_note = ClasseNote.objects.first()

if not classe_note:
    print("❌ Aucune classe trouvée")
    exit(1)

print(f"✅ Classe : {classe_note.nom}")
print(f"   École : {classe_note.ecole.nom}")

# Vérifier l'adresse de l'école
if hasattr(classe_note.ecole, 'adresse') and classe_note.ecole.adresse:
    print(f"\n📍 Adresse de l'école : {classe_note.ecole.adresse}")
    print("   ⚠️  Cette adresse NE DOIT PAS apparaître dans le PDF")
else:
    print("\n📍 Aucune adresse configurée pour l'école")

# Créer une requête
factory = RequestFactory()
request = factory.get(f'/notes/exporter-classement-pdf/?classe_id={classe_note.id}')

user = User.objects.filter(is_superuser=True).first() or User.objects.first()
if user:
    request.user = user
else:
    print("❌ Aucun utilisateur trouvé")
    exit(1)

# Générer le PDF
try:
    print("\n🔄 Génération du PDF...")
    response = exporter_classement_classe_pdf(request)
    
    if response.status_code == 200:
        # Sauvegarder
        output_path = os.path.join(os.path.dirname(__file__), 'test_pdf_sans_adresse.pdf')
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ PDF généré : {output_path}")
        print(f"   Taille : {len(response.content):,} octets")
        print("\n" + "="*80)
        print("VÉRIFICATION MANUELLE REQUISE :")
        print("="*80)
        print("1. Ouvrir le fichier : test_pdf_sans_adresse.pdf")
        print("2. Vérifier que l'en-tête contient :")
        print("   ✅ République de Guinée")
        print("   ✅ Nom de l'école")
        print("   ✅ Téléphone et Email")
        print("3. Vérifier que l'adresse N'APPARAÎT PAS")
        print("="*80)
    else:
        print(f"❌ Erreur HTTP {response.status_code}")
        
except Exception as e:
    print(f"❌ Erreur : {e}")
    import traceback
    traceback.print_exc()
