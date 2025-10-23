"""
Script pour ajouter des données de test dans le système
Usage: python ajouter_donnees_test.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Ecole, Classe, GrilleTarifaire
from decimal import Decimal
from datetime import date

print("=" * 60)
print("AJOUT DE DONNÉES DE TEST")
print("=" * 60)

# 1. Créer une école de test
print("\n1️⃣  Création de l'école...")
ecole, created = Ecole.objects.get_or_create(
    nom="école de test",  # En minuscules pour tester la conversion
    defaults={
        'adresse': 'quartier test, conakry',
        'telephone': '+224610000000',
        'email': 'test@ecole.com',
        'directeur': 'directeur test',
        'ire': 'conakry',
        'dpe': 'dixinn',
        'desee': 'commune',
        'etat': 'VALIDE',
        'code_prefixe': 'TEST/'
    }
)

if created:
    print(f"   ✅ École créée: {ecole.nom}")
else:
    print(f"   ℹ️  École existante: {ecole.nom}")

# 2. Créer des classes
print("\n2️⃣  Création des classes...")
annee_scolaire = "2024-2025"

classes_data = [
    {'nom': 'garderie', 'niveau': 'GARDERIE', 'code': 'GA'},
    {'nom': 'petite section', 'niveau': 'MATERNELLE', 'code': 'MPS'},
    {'nom': '1ère année', 'niveau': 'PRIMAIRE_1', 'code': 'PN1'},
    {'nom': '2ème année', 'niveau': 'PRIMAIRE_2', 'code': 'PN2'},
    {'nom': '3ème année', 'niveau': 'PRIMAIRE_3', 'code': 'PN3'},
    {'nom': '7ème année', 'niveau': 'COLLEGE_7', 'code': 'CN7'},
    {'nom': '10ème année', 'niveau': 'COLLEGE_10', 'code': 'CN10'},
    {'nom': '11ème série littéraire', 'niveau': 'LYCEE_11', 'code': 'L11SL'},
]

classes_creees = []
for classe_data in classes_data:
    classe, created = Classe.objects.get_or_create(
        ecole=ecole,
        nom=classe_data['nom'],
        annee_scolaire=annee_scolaire,
        defaults={
            'niveau': classe_data['niveau'],
            'code_matricule': classe_data['code'],
            'capacite_max': 30
        }
    )
    classes_creees.append(classe)
    if created:
        print(f"   ✅ Classe créée: {classe.nom}")
    else:
        print(f"   ℹ️  Classe existante: {classe.nom}")

# 3. Créer des grilles tarifaires
print("\n3️⃣  Création des grilles tarifaires...")

tarifs_data = {
    'GARDERIE': {
        'inscription': 50000,
        'reinscription': 40000,
        'tranche_1': 320000,  # 1ère tranche (4 mois)
        'tranche_2': 320000,  # 2ème tranche (4 mois)
        'tranche_3': 320000,  # 3ème tranche (4 mois)
    },
    'MATERNELLE': {
        'inscription': 60000,
        'reinscription': 50000,
        'tranche_1': 400000,
        'tranche_2': 400000,
        'tranche_3': 400000,
    },
    'PRIMAIRE_1': {
        'inscription': 80000,
        'reinscription': 70000,
        'tranche_1': 480000,
        'tranche_2': 480000,
        'tranche_3': 480000,
    },
    'PRIMAIRE_2': {
        'inscription': 80000,
        'reinscription': 70000,
        'tranche_1': 480000,
        'tranche_2': 480000,
        'tranche_3': 480000,
    },
    'PRIMAIRE_3': {
        'inscription': 80000,
        'reinscription': 70000,
        'tranche_1': 480000,
        'tranche_2': 480000,
        'tranche_3': 480000,
    },
    'COLLEGE_7': {
        'inscription': 100000,
        'reinscription': 90000,
        'tranche_1': 600000,
        'tranche_2': 600000,
        'tranche_3': 600000,
    },
    'COLLEGE_10': {
        'inscription': 120000,
        'reinscription': 110000,
        'tranche_1': 720000,
        'tranche_2': 720000,
        'tranche_3': 720000,
    },
    'LYCEE_11': {
        'inscription': 150000,
        'reinscription': 140000,
        'tranche_1': 800000,
        'tranche_2': 800000,
        'tranche_3': 800000,
    },
}

for niveau, tarifs in tarifs_data.items():
    grille, created = GrilleTarifaire.objects.get_or_create(
        ecole=ecole,
        niveau=niveau,
        annee_scolaire=annee_scolaire,
        defaults={
            'frais_inscription': Decimal(tarifs['inscription']),
            'frais_reinscription': Decimal(tarifs['reinscription']),
            'tranche_1': Decimal(tarifs['tranche_1']),
            'tranche_2': Decimal(tarifs['tranche_2']),
            'tranche_3': Decimal(tarifs['tranche_3']),
        }
    )
    if created:
        print(f"   ✅ Grille créée pour {niveau}: {tarifs['tranche_1']:,.0f} GNF (tranche 1)")
    else:
        print(f"   ℹ️  Grille existante pour {niveau}")

# 4. Résumé
print("\n" + "=" * 60)
print("✅ DONNÉES AJOUTÉES AVEC SUCCÈS!")
print("=" * 60)
print(f"\n📊 Résumé:")
print(f"   - École: {ecole.nom}")
print(f"   - Classes créées: {len(classes_creees)}")
print(f"   - Grilles tarifaires: {len(tarifs_data)}")
print(f"\n🎯 Vous pouvez maintenant:")
print(f"   1. Ajouter des élèves dans ces classes")
print(f"   2. Tester la conversion en majuscules")
print(f"   3. Générer des bulletins et reçus")
print("\n" + "=" * 60)
