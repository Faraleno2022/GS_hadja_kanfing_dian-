#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lister toutes les classes disponibles
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, NoteMensuelle, CompositionNote

print("="*80)
print(" "*25 + "CLASSES DISPONIBLES")
print("="*80)

classes = ClasseNote.objects.all().order_by('id')

print(f"\n📚 Total de classes: {classes.count()}")
print("\n" + "-"*80)

for classe in classes:
    print(f"\n🏫 ID: {classe.id}")
    print(f"   Nom: {classe.nom}")
    print(f"   Année scolaire: {classe.annee_scolaire}")
    print(f"   École: {classe.ecole.nom}")
    print(f"   Actif: {'✅' if classe.actif else '❌'}")
    
    # Compter les notes de février
    notes_fevrier = NoteMensuelle.objects.filter(
        matiere__classe=classe,
        mois='FEVRIER',
        annee_scolaire=classe.annee_scolaire
    ).count()
    
    print(f"   Notes FÉVRIER: {notes_fevrier}")
    
    # Vérifier toutes les périodes
    mois_avec_notes = NoteMensuelle.objects.filter(
        matiere__classe=classe,
        annee_scolaire=classe.annee_scolaire
    ).values_list('mois', flat=True).distinct()
    
    if mois_avec_notes:
        print(f"   Mois avec notes: {', '.join(mois_avec_notes)}")
    
    print(f"   🔗 URL: http://127.0.0.1:8000/notes/statistiques/?classe_id={classe.id}&periode=FEVRIER")

print("\n" + "="*80)
print("\n💡 Pour accéder aux statistiques de FÉVRIER:")
print("   Utilisez l'ID d'une classe qui existe ci-dessus")
print("   Exemple: http://127.0.0.1:8000/notes/statistiques/?classe_id=6&periode=FEVRIER")
