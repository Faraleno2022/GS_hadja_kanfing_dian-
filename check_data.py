#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from eleves.models import Eleve, Classe, Ecole
from notes.models import MatiereNote, NoteMensuelle, CompositionNote

print("=" * 60)
print("VÉRIFICATION DES DONNÉES DU SYSTÈME")
print("=" * 60)

# Écoles
ecoles = Ecole.objects.all()
print(f"\n📚 ÉCOLES: {ecoles.count()}")
for ecole in ecoles:
    print(f"  ✓ {ecole.nom} (ID: {ecole.id})")
    if hasattr(ecole, 'ville'):
        print(f"    Ville: {ecole.ville}")

# Classes
classes = Classe.objects.all()
print(f"\n🏫 CLASSES: {classes.count()}")
for classe in classes:
    ecole_nom = classe.ecole.nom if classe.ecole else "Aucune école"
    print(f"  ✓ {classe.nom} (ID: {classe.id}) - École: {ecole_nom}")

# Élèves
eleves = Eleve.objects.all()
print(f"\n👨‍🎓 ÉLÈVES: {eleves.count()}")
if eleves.exists():
    for classe in classes:
        eleves_classe = Eleve.objects.filter(classe=classe)
        if eleves_classe.exists():
            print(f"  ✓ {classe.nom}: {eleves_classe.count()} élèves")
            for eleve in eleves_classe[:3]:
                print(f"    - {eleve.nom} {eleve.prenom}")
            if eleves_classe.count() > 3:
                print(f"    ... et {eleves_classe.count() - 3} autres")

# Matières
matieres = MatiereNote.objects.all()
print(f"\n📖 MATIÈRES: {matieres.count()}")
for classe in classes:
    matieres_classe = MatiereNote.objects.filter(classe=classe)
    if matieres_classe.exists():
        print(f"  ✓ {classe.nom}: {matieres_classe.count()} matières")

# Notes
notes_mensuelles = NoteMensuelle.objects.all()
notes_compo = CompositionNote.objects.all()
print(f"\n📝 NOTES:")
print(f"  ✓ Notes mensuelles: {notes_mensuelles.count()}")
print(f"  ✓ Notes composition: {notes_compo.count()}")

print("\n" + "=" * 60)
print("RÉSUMÉ")
print("=" * 60)
print(f"Écoles: {ecoles.count()}")
print(f"Classes: {classes.count()}")
print(f"Élèves: {eleves.count()}")
print(f"Matières: {matieres.count()}")
print(f"Notes totales: {notes_mensuelles.count() + notes_compo.count()}")
print("=" * 60)
print("✅ Données prêtes pour tester les interfaces modernes!")
print("🌐 Accédez au dashboard: http://127.0.0.1:8001/notes/")
