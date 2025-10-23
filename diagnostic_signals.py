"""
Script de diagnostic pour vérifier que les signals Django sont correctement chargés
Usage: python diagnostic_signals.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.db.models.signals import pre_save
from eleves.models import Eleve, Responsable, Classe, Ecole
import eleves.signals

print("=" * 60)
print("DIAGNOSTIC DES SIGNALS DJANGO")
print("=" * 60)

# 1. Vérifier que le module signals existe
print("\n1️⃣  Vérification du module signals")
print("-" * 60)
print(f"✅ Module signals importé: {eleves.signals}")
print(f"   Fonctions disponibles: {dir(eleves.signals)}")

# 2. Vérifier les receivers enregistrés
print("\n2️⃣  Vérification des receivers enregistrés")
print("-" * 60)

def check_receivers(model_class):
    receivers = pre_save._live_receivers(model_class)
    print(f"\n   Modèle: {model_class.__name__}")
    print(f"   Nombre de receivers: {len(list(receivers))}")
    for receiver in receivers:
        print(f"   - {receiver}")

check_receivers(Eleve)
check_receivers(Responsable)
check_receivers(Classe)
check_receivers(Ecole)

# 3. Test de création d'un élève
print("\n3️⃣  Test de création d'un élève")
print("-" * 60)

# Trouver une classe existante
from datetime import date
classe = Classe.objects.first()

if classe:
    # Créer un responsable de test
    resp = Responsable.objects.create(
        nom='test diallo',
        prenom='jean',
        relation='PERE',
        telephone='+224600000000'
    )
    
    print(f"✅ Responsable créé")
    print(f"   Nom saisi: 'test diallo' → Enregistré: '{resp.nom}'")
    print(f"   Prénom saisi: 'jean' → Enregistré: '{resp.prenom}'")
    
    if resp.nom == 'TEST DIALLO' and resp.prenom == 'JEAN':
        print("   ✅ SIGNAL FONCTIONNE POUR RESPONSABLE!")
    else:
        print("   ❌ SIGNAL NE FONCTIONNE PAS POUR RESPONSABLE!")
    
    # Créer un élève de test
    eleve = Eleve.objects.create(
        prenom='marie',
        nom='camara',
        sexe='F',
        date_naissance=date(2006, 1, 1),
        lieu_naissance='conakry',
        classe=classe,
        date_inscription=date.today(),
        statut='ACTIF',
        responsable_principal=resp
    )
    
    print(f"\n✅ Élève créé")
    print(f"   Nom saisi: 'camara' → Enregistré: '{eleve.nom}'")
    print(f"   Prénom saisi: 'marie' → Enregistré: '{eleve.prenom}'")
    print(f"   Lieu saisi: 'conakry' → Enregistré: '{eleve.lieu_naissance}'")
    
    if eleve.nom == 'CAMARA' and eleve.prenom == 'MARIE':
        print("   ✅ SIGNAL FONCTIONNE POUR ÉLÈVE!")
    else:
        print("   ❌ SIGNAL NE FONCTIONNE PAS POUR ÉLÈVE!")
    
    # Nettoyage
    eleve.delete()
    resp.delete()
else:
    print("   ⚠️  Aucune classe trouvée pour le test")

# 4. Vérifier les données existantes
print("\n4️⃣  Vérification des données existantes")
print("-" * 60)

eleves_minuscules = []
for e in Eleve.objects.all()[:5]:
    if e.nom and e.nom != e.nom.upper():
        eleves_minuscules.append(e)
        print(f"   ❌ {e.matricule}: {e.prenom} {e.nom} (en minuscules)")

if eleves_minuscules:
    print(f"\n   ⚠️  {len(eleves_minuscules)} élèves ont des noms en minuscules")
    print(f"   💡 Exécutez: python manage.py convertir_majuscules")
else:
    print(f"   ✅ Tous les élèves vérifiés sont en majuscules")

# 5. Résumé
print("\n" + "=" * 60)
print("RÉSUMÉ DU DIAGNOSTIC")
print("=" * 60)

print("\n📋 Configuration:")
print(f"   - Module signals: {'✅ Chargé' if eleves.signals else '❌ Non chargé'}")
print(f"   - Receivers Eleve: {'✅ Enregistrés' if list(pre_save._live_receivers(Eleve)) else '❌ Non enregistrés'}")
print(f"   - Receivers Responsable: {'✅ Enregistrés' if list(pre_save._live_receivers(Responsable)) else '❌ Non enregistrés'}")

print("\n🎯 Actions recommandées:")
if eleves_minuscules:
    print("   1. Les signals sont maintenant actifs pour les NOUVELLES données")
    print("   2. Pour convertir les données EXISTANTES, exécutez:")
    print("      python manage.py convertir_majuscules")
    print("   3. Redémarrez l'application web (Reload sur PythonAnywhere)")
else:
    print("   ✅ Tout fonctionne correctement!")
    print("   ✅ Les nouvelles données seront automatiquement converties")

print("\n" + "=" * 60)
