#!/usr/bin/env python
"""Script pour calculer et sauvegarder les classements"""
import os, sys, django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from notes.models import ClasseNote
from notes.calcul_classement import recalculer_tous_classements

print("=" * 80)
print("  📊 CALCUL DES CLASSEMENTS")
print("=" * 80)

# Récupérer toutes les classes actives
classes = ClasseNote.objects.filter(actif=True)

print(f"\n✅ {classes.count()} classes trouvées\n")

total_crees = 0
total_mis_a_jour = 0
total_erreurs = 0
classes_traitees = 0

for classe in classes:
    print(f"📚 Classe: {classe.nom}")
    
    try:
        stats = recalculer_tous_classements(classe)
        
        if stats['periodes_traitees'] > 0:
            print(f"   ✅ {stats['periodes_traitees']} périodes traitées")
            print(f"   📝 {stats['total_crees']} classements créés")
            print(f"   🔄 {stats['total_mis_a_jour']} classements mis à jour")
            
            if stats['total_erreurs'] > 0:
                print(f"   ⚠️  {stats['total_erreurs']} erreurs")
            
            total_crees += stats['total_crees']
            total_mis_a_jour += stats['total_mis_a_jour']
            total_erreurs += stats['total_erreurs']
            classes_traitees += 1
        else:
            print(f"   ⏭️  Aucune évaluation trouvée")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        total_erreurs += 1
    
    print()

print("=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)
print(f"Classes traitées: {classes_traitees}/{classes.count()}")
print(f"Classements créés: {total_crees}")
print(f"Classements mis à jour: {total_mis_a_jour}")
print(f"Erreurs: {total_erreurs}")
print("=" * 80)

if total_erreurs == 0:
    print("✅ CALCUL TERMINÉ AVEC SUCCÈS")
else:
    print(f"⚠️  CALCUL TERMINÉ AVEC {total_erreurs} ERREURS")
