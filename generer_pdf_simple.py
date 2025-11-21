"""
Script simplifié pour générer un bulletin PDF avec ReportLab
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from eleves.models import Eleve
from notes.models import ClasseNote
from notes.views import bulletin_mensuel_pdf
from notes.export_classement import _generer_classement_general

print("=" * 100)
print("GENERATION DU BULLETIN PDF (ReportLab)")
print("=" * 100)

# Récupérer la classe de test
eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF').order_by('nom', 'prenom')
if not eleves.exists():
    print("\nERREUR : Aucun élève L12SC trouvé")
    sys.exit(1)

classe_eleve = eleves.first().classe
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()

print(f"\nClasse : {classe_eleve.nom}")
print(f"Nombre d'élèves : {eleves.count()}")

# Créer un utilisateur admin
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("\nERREUR : Aucun superuser trouvé")
    sys.exit(1)

print(f"Utilisateur : {user.username}")

# Afficher le classement
print("\n" + "=" * 100)
print("CLASSEMENT GENERAL - OCTOBRE 2025")
print("=" * 100)

classement_data, titre = _generer_classement_general(
    eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

print(f"\n{'Rang':<15} {'Matricule':<15} {'Nom Complet':<40} {'Moyenne':<10}")
print("-" * 85)

for i, data in enumerate(classement_data, 1):
    if data.get('moyenne') is not None:
        rang = data.get('rang', 'N/A')
        matricule = data.get('matricule', 'N/A')
        nom = data.get('nom_complet', 'N/A')
        moyenne = data.get('moyenne')
        print(f"{rang:<15} {matricule:<15} {nom:<40} {moyenne:<10.2f}")

# Sélectionner un élève pour le bulletin
eleve_test = eleves.filter(nom__icontains="DIALLO", prenom__icontains="Alpha Ousmane").first()
if not eleve_test:
    eleve_test = eleves[9]  # 10ème élève

print("\n" + "=" * 100)
print(f"GENERATION DU BULLETIN POUR : {eleve_test.nom} {eleve_test.prenom}")
print("=" * 100)

# Trouver son rang dans le classement
rang_eleve = None
moyenne_eleve = None
for data in classement_data:
    if data.get('matricule') == eleve_test.matricule:
        rang_eleve = data.get('rang')
        moyenne_eleve = data.get('moyenne')
        break

print(f"\nMatricule : {eleve_test.matricule}")
print(f"Rang attendu : {rang_eleve}")
print(f"Moyenne attendue : {moyenne_eleve:.2f}")

# Générer le bulletin avec ReportLab
factory = RequestFactory()
request = factory.get(f'/notes/bulletin-mensuel-pdf/{classe_eleve.id}/{eleve_test.id}/10/')
request.user = user

try:
    response = bulletin_mensuel_pdf(request, classe_eleve.id, eleve_test.id, 10)
    
    # Sauvegarder le PDF
    pdf_path = f'bulletin_{eleve_test.matricule}_OCTOBRE.pdf'
    with open(pdf_path, 'wb') as f:
        f.write(response.content)
    
    print(f"\n✅ Bulletin PDF généré : {pdf_path}")
    print(f"   Taille : {len(response.content):,} octets")
    print(f"\n📄 Ouvrez le fichier pour vérifier que le rang affiché est : {rang_eleve}")
except Exception as e:
    print(f"\n❌ Erreur : {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 100)
print("VERIFICATION A FAIRE")
print("=" * 100)
print(f"\n1. Ouvrez le fichier : bulletin_{eleve_test.matricule}_OCTOBRE.pdf")
print(f"2. Vérifiez que le rang affiché est : {rang_eleve}")
print(f"3. Vérifiez que la moyenne affichée est : {moyenne_eleve:.2f}")
print(f"4. Comparez avec le classement ci-dessus")
print("\n" + "=" * 100)
