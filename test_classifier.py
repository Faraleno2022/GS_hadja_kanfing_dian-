#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test du classificateur intelligent de classes
"""

from notes.classifier import classify

# Test cases
test_classes = [
    # Primaire
    "CP1",
    "CP 2",
    "CE1",
    "CE 2",
    "CM1",
    "CM 2",
    
    # Collège
    "7ème Année",
    "7ème Année A",
    "7ème Année B",
    "8ème Année",
    "9ème Année",
    "10ème Année",
    
    # Lycée
    "11ème Année",
    "11ème Série littéraire",
    "11ème Série scientifique",
    "12ème Année",
    "12ème Série littéraire",
    "12ème Série scientifique",
    "Terminale",
    "Terminale SE",
    "Terminale SM",
    "Terminale SS",
    
    # Cas complexes
    "7ème A",
    "12ème SL",
    "Terminale Scientifique",
]

print("="*80)
print("   TEST DU CLASSIFICATEUR INTELLIGENT DE CLASSES")
print("="*80)

for class_name in test_classes:
    niveau, serie, section = classify(class_name)
    
    info = f"📚 {class_name:<30}"
    info += f" → Niveau: {niveau:<12}"
    
    if serie:
        info += f" Série: {serie:<25}"
    else:
        info += f" Série: {'—':<25}"
    
    if section:
        info += f" Section: {section}"
    else:
        info += f" Section: —"
    
    print(info)

print("\n" + "="*80)
print("   ✅ TEST TERMINÉ")
print("="*80)
