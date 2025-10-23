"""
Script de test pour vérifier que les signals convertissent bien en majuscules
Usage: python test_signals_majuscules.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Responsable, Classe, Ecole
from decimal import Decimal

print("=" * 60)
print("TEST DES SIGNALS DE CONVERSION EN MAJUSCULES")
print("=" * 60)

# Test 1: Responsable
print("\n1️⃣  TEST Responsable")
print("-" * 60)
resp = Responsable(
    nom='diallo',
    prenom='alhassane',
    relation='PERE',
    telephone='+224610812507',
    adresse='quartier hamdallaye',
    profession='enseignant'
)
resp.save()

print(f"✅ Responsable créé")
print(f"   Nom saisi: 'diallo' → Enregistré: '{resp.nom}'")
print(f"   Prénom saisi: 'alhassane' → Enregistré: '{resp.prenom}'")
print(f"   Adresse saisie: 'quartier hamdallaye' → Enregistrée: '{resp.adresse}'")
print(f"   Profession saisie: 'enseignant' → Enregistrée: '{resp.profession}'")

assert resp.nom == 'DIALLO', f"❌ Nom non converti: {resp.nom}"
assert resp.prenom == 'ALHASSANE', f"❌ Prénom non converti: {resp.prenom}"
assert resp.adresse == 'QUARTIER HAMDALLAYE', f"❌ Adresse non convertie: {resp.adresse}"
assert resp.profession == 'ENSEIGNANT', f"❌ Profession non convertie: {resp.profession}"
print("\n   ✅ TOUTES LES CONVERSIONS SONT CORRECTES!")

# Test 2: École
print("\n2️⃣  TEST École")
print("-" * 60)
ecole = Ecole(
    nom='école de test signals',
    adresse='conakry, guinée',
    telephone='+224610000000',
    email='test@ecole.com',
    directeur='dr. souleymane bah',
    ire='conakry',
    dpe='dixinn',
    desee='commune',
    etat='VALIDE'
)
ecole.save()

print(f"✅ École créée")
print(f"   Nom saisi: 'école de test signals' → Enregistré: '{ecole.nom}'")
print(f"   Directeur saisi: 'dr. souleymane bah' → Enregistré: '{ecole.directeur}'")
print(f"   IRE saisie: 'conakry' → Enregistrée: '{ecole.ire}'")

assert ecole.nom == 'ÉCOLE DE TEST SIGNALS', f"❌ Nom école non converti: {ecole.nom}"
assert ecole.directeur == 'DR. SOULEYMANE BAH', f"❌ Directeur non converti: {ecole.directeur}"
assert ecole.ire == 'CONAKRY', f"❌ IRE non convertie: {ecole.ire}"
print("\n   ✅ TOUTES LES CONVERSIONS SONT CORRECTES!")

# Test 3: Classe
print("\n3️⃣  TEST Classe")
print("-" * 60)
classe = Classe(
    ecole=ecole,
    nom='11 série littéraire test',
    niveau='LYCEE_11',
    code_matricule='L11SL',
    annee_scolaire='2024-2025',
    capacite_max=30
)
classe.save()

print(f"✅ Classe créée")
print(f"   Nom saisi: '11 série littéraire test' → Enregistré: '{classe.nom}'")

assert classe.nom == '11 SÉRIE LITTÉRAIRE TEST', f"❌ Nom classe non converti: {classe.nom}"
print("\n   ✅ CONVERSION CORRECTE!")

# Test 4: Élève
print("\n4️⃣  TEST Élève")
print("-" * 60)
from datetime import date
eleve = Eleve(
    prenom='ibrahima',
    nom='diallo',
    sexe='M',
    date_naissance=date(2006, 1, 15),
    lieu_naissance='conakry',
    classe=classe,
    date_inscription=date.today(),
    statut='ACTIF',
    responsable_principal=resp
)
eleve.save()

print(f"✅ Élève créé")
print(f"   Nom saisi: 'diallo' → Enregistré: '{eleve.nom}'")
print(f"   Prénom saisi: 'ibrahima' → Enregistré: '{eleve.prenom}'")
print(f"   Lieu saisi: 'conakry' → Enregistré: '{eleve.lieu_naissance}'")
print(f"   Matricule généré: '{eleve.matricule}'")

assert eleve.nom == 'DIALLO', f"❌ Nom élève non converti: {eleve.nom}"
assert eleve.prenom == 'IBRAHIMA', f"❌ Prénom élève non converti: {eleve.prenom}"
assert eleve.lieu_naissance == 'CONAKRY', f"❌ Lieu non converti: {eleve.lieu_naissance}"
print("\n   ✅ TOUTES LES CONVERSIONS SONT CORRECTES!")

# Test 5: Modification
print("\n5️⃣  TEST Modification")
print("-" * 60)
eleve.nom = 'camara'
eleve.save()

print(f"✅ Élève modifié")
print(f"   Nouveau nom saisi: 'camara' → Enregistré: '{eleve.nom}'")

assert eleve.nom == 'CAMARA', f"❌ Nom modifié non converti: {eleve.nom}"
print("\n   ✅ CONVERSION LORS DE LA MODIFICATION CORRECTE!")

# Nettoyage
print("\n🧹 Nettoyage des données de test...")
eleve.delete()
classe.delete()
ecole.delete()
resp.delete()

# Résumé final
print("\n" + "=" * 60)
print("✅ TOUS LES TESTS SONT RÉUSSIS!")
print("=" * 60)
print("\n📋 Résumé:")
print("   ✅ Les signals Django fonctionnent correctement")
print("   ✅ Conversion automatique à la création")
print("   ✅ Conversion automatique à la modification")
print("   ✅ Fonctionne pour: Eleve, Responsable, Classe, Ecole")
print("\n🎯 Avantages des signals:")
print("   • Fonctionne partout (formulaires, admin, API, scripts)")
print("   • Pas besoin de modifier les formulaires")
print("   • Conversion garantie au niveau de la base de données")
print("   • Code centralisé et maintenable")
print("\n" + "=" * 60)
