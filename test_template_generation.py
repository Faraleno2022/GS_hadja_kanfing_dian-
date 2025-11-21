#!/usr/bin/env python
"""Test de génération de template Excel pour toutes les classes"""
import os, sys, django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote, MatiereNote
from notes.import_notes import generer_template_excel

print("=" * 80)
print("  🧪 TEST GÉNÉRATION TEMPLATE EXCEL")
print("=" * 80)

# Tester quelques classes
classes_test = ClasseNote.objects.filter(actif=True)[:5]

for classe in classes_test:
    print(f"\n📚 Classe: {classe.nom}")
    
    # Récupérer une matière de cette classe
    matiere = MatiereNote.objects.filter(classe=classe, actif=True).first()
    
    if not matiere:
        print("   ⚠️  Aucune matière trouvée")
        continue
    
    print(f"   📖 Matière: {matiere.nom}")
    
    try:
        df = generer_template_excel(classe.id, matiere.id)
        print(f"   ✅ Template généré: {len(df)} élèves")
        
        if len(df) > 0:
            print(f"   📋 Aperçu:")
            print(f"      - Matricule: {df['Matricule'].iloc[0]}")
            print(f"      - Prénom: {df['Prénom'].iloc[0]}")
            print(f"      - Nom: {df['Nom'].iloc[0]}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

print("\n" + "=" * 80)
print("✅ Test terminé")
print("=" * 80)
