"""
Script pour générer le PDF du classement et un bulletin pour vérification
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
from notes.export_classement import exporter_classement_classe_pdf
from notes.views import bulletin_dynamique_pdf

print("=" * 100)
print("GENERATION DES PDF POUR VERIFICATION")
print("=" * 100)

# Récupérer la classe de test
eleves = Eleve.objects.filter(matricule__startswith='L12SC-', statut='ACTIF').order_by('nom', 'prenom')
if not eleves.exists():
    print("\nERREUR : Aucun élève L12SC trouvé")
    print("Exécutez d'abord : python init_ecole_simple.py")
    sys.exit(1)

classe_eleve = eleves.first().classe
classe_note = ClasseNote.objects.filter(nom__icontains="12 SERIE").first()

print(f"\nClasse : {classe_eleve.nom}")
print(f"Nombre d'élèves : {eleves.count()}")

# Créer un utilisateur admin pour les requêtes
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("\nERREUR : Aucun superuser trouvé")
    sys.exit(1)

print(f"Utilisateur : {user.username}")

# Créer une factory de requêtes
factory = RequestFactory()

# 1. Générer le PDF du classement général
print("\n" + "=" * 100)
print("1. GENERATION DU CLASSEMENT GENERAL PDF")
print("=" * 100)

request = factory.get(
    f'/notes/exporter-classement-classe-pdf/?classe_id={classe_note.id}&type_note=mensuelle&periode=OCTOBRE'
)
request.user = user

try:
    response = exporter_classement_classe_pdf(request)
    
    # Sauvegarder le PDF
    pdf_classement_path = 'classement_general_OCTOBRE.pdf'
    with open(pdf_classement_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✅ Classement PDF généré : {pdf_classement_path}")
    print(f"   Taille : {len(response.content)} octets")
except Exception as e:
    print(f"❌ Erreur lors de la génération du classement : {e}")
    import traceback
    traceback.print_exc()

# 2. Générer un bulletin pour un élève spécifique (le 9ème du classement)
print("\n" + "=" * 100)
print("2. GENERATION D'UN BULLETIN INDIVIDUEL PDF")
print("=" * 100)

# Choisir DIALLO Alpha Ousmane (devrait être 10ème/18 selon nos tests)
eleve_test = eleves.filter(nom__icontains="DIALLO", prenom__icontains="Alpha Ousmane").first()
if not eleve_test:
    # Prendre le premier élève
    eleve_test = eleves.first()

print(f"Élève sélectionné : {eleve_test.nom} {eleve_test.prenom} ({eleve_test.matricule})")

request = factory.post('/notes/bulletin-dynamique-pdf/')
request.user = user
request.POST = {
    'classe_id': str(classe_note.id),
    'eleve_id': str(eleve_test.id),
    'periode': 'OCTOBRE',
    'system_type': 'mensuel',
    'annee_scolaire': '2025-2026'
}

try:
    response = bulletin_dynamique_pdf(request)
    
    # Sauvegarder le PDF
    pdf_bulletin_path = f'bulletin_{eleve_test.matricule}_OCTOBRE.pdf'
    with open(pdf_bulletin_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✅ Bulletin PDF généré : {pdf_bulletin_path}")
    print(f"   Taille : {len(response.content)} octets")
except Exception as e:
    print(f"❌ Erreur lors de la génération du bulletin : {e}")
    import traceback
    traceback.print_exc()

# 3. Afficher les rangs pour vérification
print("\n" + "=" * 100)
print("3. VERIFICATION DES RANGS")
print("=" * 100)

from notes.export_classement import _generer_classement_general

classement_data, titre = _generer_classement_general(
    eleves, classe_note, 'mensuelle', 'OCTOBRE'
)

print(f"\n{'Rang':<15} {'Matricule':<15} {'Nom Complet':<40} {'Moyenne':<10}")
print("-" * 85)

for i, data in enumerate(classement_data[:10], 1):  # Top 10
    if data.get('moyenne') is not None:
        rang = data.get('rang', 'N/A')
        matricule = data.get('matricule', 'N/A')
        nom = data.get('nom_complet', 'N/A')
        moyenne = data.get('moyenne')
        
        marker = " ⭐" if matricule == eleve_test.matricule else ""
        print(f"{rang:<15} {matricule:<15} {nom:<40} {moyenne:<10.2f}{marker}")

print("\n" + "=" * 100)
print("FICHIERS GENERES")
print("=" * 100)
print(f"\n1. Classement général : classement_general_OCTOBRE.pdf")
print(f"2. Bulletin individuel : bulletin_{eleve_test.matricule}_OCTOBRE.pdf")
print(f"\n⭐ Élève test : {eleve_test.nom} {eleve_test.prenom}")
print(f"\nVérifiez que le rang dans le bulletin correspond au rang dans le classement !")
print("\n" + "=" * 100)
