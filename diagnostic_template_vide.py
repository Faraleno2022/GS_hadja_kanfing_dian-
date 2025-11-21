#!/usr/bin/env python
"""Diagnostic pour template Excel vide"""
import os, sys, django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote
from eleves.models import Classe as ClasseEleve, Eleve

print("=" * 80)
print("  🔍 DIAGNOSTIC TEMPLATE EXCEL VIDE")
print("=" * 80)

# Lister toutes les ClasseNote
print("\n📚 Classes de Notes (ClasseNote):")
classes_note = ClasseNote.objects.filter(actif=True)[:20]
for cn in classes_note:
    print(f"   ID {cn.id}: {cn.nom} (Année: {cn.annee_scolaire})")

# Lister toutes les Classe d'élèves
print("\n👥 Classes d'Élèves (Classe):")
classes_eleve = ClasseEleve.objects.all()[:20]
for ce in classes_eleve:
    nb_eleves = Eleve.objects.filter(classe=ce, statut='ACTIF').count()
    print(f"   ID {ce.id}: {ce.nom} (Année: {ce.annee_scolaire}) - {nb_eleves} élèves")

# Test de correspondance
print("\n🔗 Test de Correspondance:")
print("-" * 80)

for cn in classes_note[:10]:
    print(f"\n📖 ClasseNote: {cn.nom}")
    
    # Essayer de trouver la correspondance
    ce = None
    
    # Méthode 1
    ce = ClasseEleve.objects.filter(nom__iexact=cn.nom, annee_scolaire=cn.annee_scolaire).first()
    if ce:
        nb = Eleve.objects.filter(classe=ce, statut='ACTIF').count()
        print(f"   ✅ Méthode 1 (exacte+année): {ce.nom} ({nb} élèves)")
        continue
    
    # Méthode 2
    ce = ClasseEleve.objects.filter(nom__iexact=cn.nom).first()
    if ce:
        nb = Eleve.objects.filter(classe=ce, statut='ACTIF').count()
        print(f"   ✅ Méthode 2 (exacte): {ce.nom} ({nb} élèves)")
        continue
    
    # Méthode 3
    premier_mot = cn.nom.split()[0] if cn.nom.split() else cn.nom
    ce = ClasseEleve.objects.filter(nom__icontains=premier_mot).first()
    if ce:
        nb = Eleve.objects.filter(classe=ce, statut='ACTIF').count()
        print(f"   ⚠️  Méthode 3 (partielle): {ce.nom} ({nb} élèves)")
        continue
    
    print(f"   ❌ Aucune correspondance trouvée")

print("\n" + "=" * 80)
print("💡 Si une classe n'a pas de correspondance, vérifiez:")
print("   1. Le nom de la ClasseNote correspond au nom de la Classe d'élèves")
print("   2. Les élèves sont bien affectés à la classe")
print("=" * 80)
