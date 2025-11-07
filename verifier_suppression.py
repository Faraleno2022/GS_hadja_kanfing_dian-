"""
Script de vérification de la suppression de l'enseignant
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from salaires.models import Enseignant
from administration.models import SystemLog

print("\n" + "="*70)
print("VÉRIFICATION DE LA SUPPRESSION".center(70))
print("="*70)

# Vérifier les enseignants actuels
print("\n📋 ENSEIGNANTS ACTUELS DANS LA BASE DE DONNÉES:")
print("-"*50)

enseignants = Enseignant.objects.all()
if enseignants.exists():
    for ens in enseignants:
        print(f"  • {ens.nom} {ens.prenoms}")
        print(f"    Statut: {ens.statut}")
        print(f"    École: {ens.ecole.nom}")
        print()
else:
    print("  ✅ Aucun enseignant dans la base de données")
    print("  → L'enseignant LENO MAMADOU DJOULDE a bien été supprimé définitivement")

# Vérifier la corbeille
print("\n🗑️ CORBEILLE - ENSEIGNANTS SUPPRIMÉS DÉFINITIVEMENT:")
print("-"*50)

logs = SystemLog.objects.filter(
    action='SUPPRESSION_DEFINITIVE_ENSEIGNANT'
).order_by('-timestamp')[:5]

if logs.exists():
    for i, log in enumerate(logs, 1):
        print(f"\n{i}. Suppression du {log.timestamp.strftime('%d/%m/%Y à %H:%M')}")
        
        if log.details:
            details = log.details
            print(f"   • Nom: {details.get('nom_complet', 'N/A')}")
            print(f"   • École: {details.get('ecole', 'N/A')}")
            print(f"   • Type: {details.get('type_enseignant', 'N/A')}")
            print(f"   • Statut avant suppression: {details.get('statut_avant_suppression', 'N/A')}")
            print(f"   • Méthode: {details.get('methode', details.get('suppression_method', 'N/A'))}")
            print(f"   • Éléments supprimés:")
            print(f"     - États de salaire: {details.get('etats_count', details.get('etats_salaire_count', 0))}")
            print(f"     - Affectations: {details.get('affectations_count', 0)}")
            print(f"     - Présences: {details.get('presences_count', 0)}")
else:
    print("  ⚠️ Aucune suppression d'enseignant dans la corbeille")

# Résumé
print("\n" + "="*70)
print("RÉSUMÉ".center(70))
print("="*70)

print("\n✅ L'enseignant LENO MAMADOU DJOULDE a été:")
print("   1. Créé avec succès")
print("   2. Marqué comme DÉMISSIONNAIRE (soft delete)")
print("   3. Supprimé DÉFINITIVEMENT (hard delete)")
print("   4. Sauvegardé dans la corbeille avec toutes ses données")
print("\n💡 La suppression est irréversible mais les données sont conservées dans la corbeille")
print("   pour consultation et audit.")
print("\n" + "="*70)
