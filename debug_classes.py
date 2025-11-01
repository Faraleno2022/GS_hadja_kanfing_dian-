#!/usr/bin/env python
"""Script pour diagnostiquer le problème de correspondance des classes"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from eleves.models import Classe as ClasseEleve, Eleve

print("=" * 80)
print("DIAGNOSTIC DES CLASSES")
print("=" * 80)

# Classes dans le module Notes
print("\n📘 CLASSES DANS LE MODULE NOTES:")
print("-" * 80)
classes_notes = ClasseNote.objects.all()
for cn in classes_notes:
    print(f"ID: {cn.id} | Nom: '{cn.nom}' | Année: '{cn.annee_scolaire}' | Niveau: {cn.niveau}")

# Classes dans le module Élèves
print("\n📗 CLASSES DANS LE MODULE ÉLÈVES:")
print("-" * 80)
classes_eleves = ClasseEleve.objects.all()
for ce in classes_eleves:
    nb_eleves = Eleve.objects.filter(classe=ce, statut='ACTIF').count()
    print(f"ID: {ce.id} | Nom: '{ce.nom}' | Année: '{ce.annee_scolaire}' | Élèves actifs: {nb_eleves}")

# Vérifier la correspondance pour classe_id=2
print("\n🔍 VÉRIFICATION POUR classe_id=2 (Notes):")
print("-" * 80)
try:
    classe_note = ClasseNote.objects.get(pk=2)
    print(f"✓ Classe Notes trouvée: '{classe_note.nom}' (Année: '{classe_note.annee_scolaire}')")
    
    # Chercher la correspondance
    try:
        classe_eleve = ClasseEleve.objects.get(
            nom=classe_note.nom, 
            annee_scolaire=classe_note.annee_scolaire
        )
        print(f"✓ Classe Élèves correspondante trouvée: '{classe_eleve.nom}'")
        
        # Compter les élèves
        eleves = Eleve.objects.filter(classe=classe_eleve, statut='ACTIF')
        print(f"✓ Nombre d'élèves actifs: {eleves.count()}")
        
        if eleves.exists():
            print("\n📋 Liste des élèves:")
            for e in eleves:
                print(f"  - {e.matricule}: {e.nom} {e.prenom}")
        
    except ClasseEleve.DoesNotExist:
        print(f"✗ AUCUNE classe Élèves trouvée avec:")
        print(f"  nom='{classe_note.nom}'")
        print(f"  annee_scolaire='{classe_note.annee_scolaire}'")
        
        # Chercher des correspondances partielles
        print("\n🔎 Recherche de correspondances partielles par nom:")
        classes_similaires = ClasseEleve.objects.filter(nom__icontains=classe_note.nom.split()[0])
        if classes_similaires.exists():
            for cs in classes_similaires:
                print(f"  - '{cs.nom}' (Année: '{cs.annee_scolaire}')")
        else:
            print("  Aucune correspondance trouvée")
        
except ClasseNote.DoesNotExist:
    print("✗ Classe Notes avec ID=2 non trouvée")

print("\n" + "=" * 80)
