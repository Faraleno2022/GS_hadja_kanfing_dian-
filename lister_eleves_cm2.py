#!/usr/bin/env python
"""Liste tous les élèves de CM2 pour mapping manuel"""
import os, sys, django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve

print("=" * 80)
print("  📋 LISTE DES ÉLÈVES CM2 (6ÈME ANNÉE)")
print("=" * 80)

eleves = Eleve.objects.filter(classe__nom='CM2', statut='ACTIF').order_by('nom', 'prenom')

print(f"\n✅ {eleves.count()} élèves trouvés:\n")

for i, e in enumerate(eleves, 1):
    print(f"{i:2d}. {e.prenom} {e.nom} (Matricule: {e.matricule})")

print("\n" + "=" * 80)
print("💡 Utilisez ces noms pour créer le fichier CSV d'import")
print("=" * 80)
