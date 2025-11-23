#!/usr/bin/env python
import os, sys, django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve, Ecole

classe_note = ClasseNote.objects.get(pk=61)
print(f'ClasseNote 61: "{classe_note.nom}" - "{classe_note.ecole.nom}" - {classe_note.annee_scolaire}')

# Chercher toutes les classes avec le même nom
classes_meme_nom = ClasseEleve.objects.filter(nom=classe_note.nom)
print(f'Classes avec nom "{classe_note.nom}": {classes_meme_nom.count()}')
for c in classes_meme_nom:
    print(f'  - {c.id}: "{c.nom}" ({c.annee_scolaire}) - "{c.ecole.nom}"')

# Chercher toutes les classes de la même école
ecole = classe_note.ecole
classes_meme_ecole = ClasseEleve.objects.filter(ecole=ecole)
print(f'Classes de "{ecole.nom}": {classes_meme_ecole.count()}')
for c in classes_meme_ecole:
    print(f'  - {c.id}: "{c.nom}" ({c.annee_scolaire})')

# Chercher avec la même année scolaire
classes_meme_annee = ClasseEleve.objects.filter(annee_scolaire=classe_note.annee_scolaire)
print(f'Classes 2024-2025: {classes_meme_annee.count()}')
for c in classes_meme_annee:
    print(f'  - {c.id}: "{c.nom}" - "{c.ecole.nom}"')
