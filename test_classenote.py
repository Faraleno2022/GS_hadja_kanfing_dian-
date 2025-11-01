#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Ecole

print("=" * 60)
print("TEST CLASSENOTE")
print("=" * 60)

# Écoles
ecoles = Ecole.objects.all()
print(f"\n📚 ÉCOLES: {ecoles.count()}")
for ecole in ecoles:
    print(f"  ✓ {ecole.nom} (ID: {ecole.id})")

# ClasseNote
classes_note = ClasseNote.objects.all()
print(f"\n🏫 CLASSENOTE: {classes_note.count()}")
for classe in classes_note:
    ecole_nom = classe.ecole.nom if classe.ecole else "Aucune école"
    actif = "✓" if classe.actif else "✗"
    print(f"  {actif} {classe.nom} (ID: {classe.id}) - École: {ecole_nom} - Actif: {classe.actif}")

# ClasseNote actives
classes_actives = ClasseNote.objects.filter(actif=True)
print(f"\n✅ CLASSENOTE ACTIVES: {classes_actives.count()}")
for classe in classes_actives[:10]:
    print(f"  ✓ {classe.nom} (ID: {classe.id})")
if classes_actives.count() > 10:
    print(f"  ... et {classes_actives.count() - 10} autres")

# Test de requête comme dans la vue
print("\n" + "=" * 60)
print("TEST REQUÊTE VUE")
print("=" * 60)

ecole_test = Ecole.objects.first()
print(f"\nÉcole utilisée: {ecole_test.nom if ecole_test else 'Aucune'}")

if ecole_test:
    classes_ecole = ClasseNote.objects.filter(ecole=ecole_test, actif=True).order_by('nom')
    print(f"Classes de cette école: {classes_ecole.count()}")
    for classe in classes_ecole[:5]:
        print(f"  ✓ {classe.nom}")

classes_toutes = ClasseNote.objects.filter(actif=True).order_by('nom')
print(f"\nToutes les classes actives: {classes_toutes.count()}")
for classe in classes_toutes[:5]:
    print(f"  ✓ {classe.nom}")

print("\n" + "=" * 60)
print("RÉSULTAT")
print("=" * 60)
print(f"Total ClasseNote: {classes_note.count()}")
print(f"ClasseNote actives: {classes_actives.count()}")
print(f"ClasseNote inactives: {classes_note.count() - classes_actives.count()}")
print("=" * 60)
