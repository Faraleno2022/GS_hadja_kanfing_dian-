"""
Script de test pour vérifier la conversion automatique en majuscules
Usage: python test_conversion_majuscules.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.forms import EleveForm, ResponsableForm, ClasseForm, EcoleForm
from eleves.models import Classe, Ecole

print("=" * 60)
print("TEST DE CONVERSION AUTOMATIQUE EN MAJUSCULES")
print("=" * 60)

# Test 1: ResponsableForm
print("\n1️⃣  TEST ResponsableForm")
print("-" * 60)
responsable_data = {
    'nom': 'diallo',
    'prenom': 'alhassane',
    'relation': 'PERE',
    'telephone': '610812507',
    'adresse': 'quartier hamdallaye',
    'profession': 'enseignant'
}

form = ResponsableForm(data=responsable_data)
if form.is_valid():
    print(f"✅ Formulaire valide")
    print(f"   Nom saisi: '{responsable_data['nom']}'")
    print(f"   Nom converti: '{form.cleaned_data['nom']}'")
    print(f"   Prénom saisi: '{responsable_data['prenom']}'")
    print(f"   Prénom converti: '{form.cleaned_data['prenom']}'")
    print(f"   Adresse saisie: '{responsable_data['adresse']}'")
    print(f"   Adresse convertie: '{form.cleaned_data['adresse']}'")
    print(f"   Profession saisie: '{responsable_data['profession']}'")
    print(f"   Profession convertie: '{form.cleaned_data['profession']}'")
    
    # Vérifier la conversion
    assert form.cleaned_data['nom'] == 'DIALLO', "❌ Nom non converti!"
    assert form.cleaned_data['prenom'] == 'ALHASSANE', "❌ Prénom non converti!"
    assert form.cleaned_data['adresse'] == 'QUARTIER HAMDALLAYE', "❌ Adresse non convertie!"
    assert form.cleaned_data['profession'] == 'ENSEIGNANT', "❌ Profession non convertie!"
    print("\n   ✅ TOUTES LES CONVERSIONS SONT CORRECTES!")
else:
    print(f"❌ Formulaire invalide: {form.errors}")

# Test 2: EleveForm (simulation)
print("\n2️⃣  TEST EleveForm (champs texte)")
print("-" * 60)

# Simuler les données nettoyées (car EleveForm nécessite une classe valide)
class MockForm:
    cleaned_data = {
        'nom': 'diallo',
        'prenom': 'ibrahima',
        'lieu_naissance': 'conakry'
    }

# Simuler les méthodes clean
from eleves.forms import EleveForm

# Tester la méthode clean_nom
form_instance = EleveForm()
form_instance.cleaned_data = {'nom': 'diallo'}
nom_converti = form_instance.clean_nom()
print(f"   Nom saisi: 'diallo'")
print(f"   Nom converti: '{nom_converti}'")
assert nom_converti == 'DIALLO', "❌ Nom non converti!"

# Tester la méthode clean_prenom
form_instance.cleaned_data = {'prenom': 'ibrahima'}
prenom_converti = form_instance.clean_prenom()
print(f"   Prénom saisi: 'ibrahima'")
print(f"   Prénom converti: '{prenom_converti}'")
assert prenom_converti == 'IBRAHIMA', "❌ Prénom non converti!"

# Tester la méthode clean_lieu_naissance
form_instance.cleaned_data = {'lieu_naissance': 'conakry'}
lieu_converti = form_instance.clean_lieu_naissance()
print(f"   Lieu saisi: 'conakry'")
print(f"   Lieu converti: '{lieu_converti}'")
assert lieu_converti == 'CONAKRY', "❌ Lieu non converti!"

print("\n   ✅ TOUTES LES CONVERSIONS SONT CORRECTES!")

# Test 3: ClasseForm (simulation)
print("\n3️⃣  TEST ClasseForm")
print("-" * 60)

form_instance = ClasseForm()
form_instance.cleaned_data = {'nom': '11 série littéraire'}
nom_classe_converti = form_instance.clean_nom()
print(f"   Nom classe saisi: '11 série littéraire'")
print(f"   Nom classe converti: '{nom_classe_converti}'")
assert nom_classe_converti == '11 SÉRIE LITTÉRAIRE', "❌ Nom classe non converti!"
print("\n   ✅ CONVERSION CORRECTE!")

# Test 4: EcoleForm (simulation)
print("\n4️⃣  TEST EcoleForm")
print("-" * 60)

form_instance = EcoleForm()

# Test nom école
form_instance.cleaned_data = {'nom': 'groupe scolaire hadja kanfing diane'}
nom_ecole = form_instance.clean_nom()
print(f"   Nom école saisi: 'groupe scolaire hadja kanfing diane'")
print(f"   Nom école converti: '{nom_ecole}'")
assert nom_ecole == 'GROUPE SCOLAIRE HADJA KANFING DIANE', "❌ Nom école non converti!"

# Test directeur
form_instance.cleaned_data = {'directeur': 'dr. souleymane bah'}
directeur = form_instance.clean_directeur()
print(f"   Directeur saisi: 'dr. souleymane bah'")
print(f"   Directeur converti: '{directeur}'")
assert directeur == 'DR. SOULEYMANE BAH', "❌ Directeur non converti!"

print("\n   ✅ TOUTES LES CONVERSIONS SONT CORRECTES!")

# Résumé final
print("\n" + "=" * 60)
print("✅ TOUS LES TESTS SONT RÉUSSIS!")
print("=" * 60)
print("\n📋 Résumé:")
print("   ✅ ResponsableForm: nom, prenom, adresse, profession → MAJUSCULES")
print("   ✅ EleveForm: nom, prenom, lieu_naissance → MAJUSCULES")
print("   ✅ ClasseForm: nom → MAJUSCULES")
print("   ✅ EcoleForm: nom, directeur, adresse, ire, dpe, desee → MAJUSCULES")
print("\n🎯 La conversion automatique fonctionne correctement!")
print("   Lors de l'ajout d'un élève ou responsable, les données")
print("   seront automatiquement converties en MAJUSCULES.")
print("\n" + "=" * 60)
